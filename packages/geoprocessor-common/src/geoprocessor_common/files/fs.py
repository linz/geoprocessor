import os
from collections.abc import Generator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from tempfile import TemporaryDirectory

from botocore.exceptions import ClientError
from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.files import fs_local, fs_s3
from geoprocessor_common.files.checksum import multihash_as_hex
from geoprocessor_common.log.time_helper import time_in_ms
from linz_logger import get_log


@contextmanager
def _missing_file_as_no_such_file_error(path: str) -> Generator[None, None, None]:
    """Translate "the file is not there" into `NoSuchFileError`, whether the path is local or on `s3`.

    Any other `ClientError` is re-raised unchanged.

    Args:
        path: the path to name in the error

    Raises:
        NoSuchFileError: if the file does not exist
        ClientError: if `s3` fails for any other reason
    """
    try:
        yield
    except FileNotFoundError as error:
        raise NoSuchFileError(path) from error
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html#parsing-error-responses-and-catching-exceptions-from-aws-services
    except ClientError as ce:
        # Error codes are listed at
        # https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#ErrorCodeList
        if ce.response["Error"]["Code"] == "NoSuchKey":
            raise NoSuchFileError(path) from ce
        raise


def write(destination: str, source: bytes, content_type: str | None = None) -> str:
    """Write a file from its source to a destination path.

    Args:
        destination: A path to where the file will be written.
        source: The source file in bytes.
        content_type: A standard Media Type describing the format of the contents.
    """
    get_log().debug("write", path=destination)
    if is_s3(destination):
        fs_s3.write(destination, source, content_type)
    else:
        fs_local.write(destination, source)
    return destination


def multihash(path: str) -> str:
    """Get the multihash of a file without loading it into memory.

    Args:
        path: A path to a file.

    Returns:
        the multihash of the file content
    """
    start_time = time_in_ms()

    with _missing_file_as_no_such_file_error(path):
        file_multihash = fs_s3.multihash(path) if is_s3(path) else fs_local.multihash(path)

    get_log().debug("multihash_success", path=path, multihash=file_multihash, duration=time_in_ms() - start_time)
    return file_multihash


def read(path: str) -> bytes:
    """Read a file from its path.

    Args:
        path: A path to a file to read.

    Returns:
        bytes: The bytes content of the file.
    """
    get_log().debug("read", path=path)

    with _missing_file_as_no_such_file_error(path):
        return fs_s3.read(path) if is_s3(path) else fs_local.read(path)


def copy(source: str, target: str, content_type: str | None = None) -> str:
    """Copy a `source` file to a `target`, streaming it rather than holding it in memory.

    Unlike `write()` this is not limited to 5GB when the target is on `s3`.

    Args:
        source: A path to a file to copy
        target: A path of the copy to create
        content_type: A standard Media Type describing the format of the contents.

    Returns:
        the multihash of the file content
    """
    get_log().debug("copy", source=source, target=target)
    start_time = time_in_ms()

    with _missing_file_as_no_such_file_error(source):
        if is_s3(source) and is_s3(target):
            with TemporaryDirectory() as tmp_path:
                local_copy = os.path.join(tmp_path, os.path.basename(target))
                fs_s3.download(source, local_copy)
                file_multihash = fs_s3.upload(local_copy, target, content_type)
        elif is_s3(source):
            fs_s3.download(source, target)
            file_multihash = fs_local.multihash(target)
        elif is_s3(target):
            file_multihash = fs_s3.upload(source, target, content_type)
        else:
            fs_local.copy_file(source, target)
            file_multihash = fs_local.multihash(target)

    get_log().debug("copy_success", source=source, target=target, multihash=file_multihash, duration=time_in_ms() - start_time)
    return file_multihash


def exists(path: str) -> bool:
    """Check if path (file or directory) exists.

    Args:
        path: A path to a directory or file

    Returns:
        bool: True if the path exists
    """
    if is_s3(path):
        return fs_s3.exists(path)
    return fs_local.exists(path)


def write_all(inputs: list[str], target: str, concurrency: int | None = 4, generate_name: bool | None = True) -> list[str]:
    """Writes list of files to target destination using multithreading.
    Args:
        inputs: list of files to read
        target: target folder to write to
        concurrency: max thread pool workers
        generated_name: create a target file name based on multihash the source filename

    Returns:
        list of written file paths
    """
    results: list[Future] = []  # type: ignore
    written_tiffs: list[str] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for input_ in inputs:
            results.append(executor.submit(write_file, input_, target, generate_name))

    for future in results:
        if future.exception():
            get_log().warn("Failed Read-Write", error=future.exception())
        else:
            written_tiffs.append(future.result())

    if len(inputs) != len(written_tiffs):
        get_log().error("Missing Files", count=len(inputs) - len(written_tiffs))
        raise Exception("Not all mandatory source files were written")

    return written_tiffs


def write_sidecars(inputs: list[str], target: str, concurrency: int | None = 4) -> None:
    """Writes list of files (if found) to target destination using multithreading.
    The copy of the files have a generated file name (@see `write_file`)

    Args:
        inputs: list of files to read
        target: target folder to write to
        concurrency: max thread pool workers
    """
    results: list[Future] = []  # type: ignore
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for input_ in inputs:
            results.append(executor.submit(write_file, input_, target))

    for future in results:
        future_ex = future.exception()
        if isinstance(future_ex, NoSuchFileError):
            get_log().info("No sidecar file found; skipping", error=future.exception())
        else:
            get_log().info("wrote_sidecar_file", path=future.result())


def write_file(input_: str, target: str, generate_name: bool | None = True) -> str:
    """Read a file from a path and write it to a target path.
    Args:
        input: A path to a file to read.
        target: A path to write the file to.
        generate_name: create a target file name based on multihash the source filename

    Returns:
        str: Target file name.
    """
    get_log().info(f"Trying write from file: {input_}")

    if generate_name:
        file_name, file_extension = os.path.splitext(input_)
        target_file_name = f"{multihash_as_hex(str.encode(file_name))}{file_extension}"
    else:
        target_file_name = os.path.basename(input_)

    target_path = os.path.join(target, target_file_name)
    copy(input_, target_path)
    return target_path


class NoSuchFileError(Exception):
    def __init__(self, path: str) -> None:
        self.message = f"File not found: {path}"
        self.path = path
