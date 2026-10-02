import os
import shutil
from collections.abc import Generator
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from boto3 import client
from botocore.exceptions import ClientError
from geoprocessor_common.aws.aws_helper import get_session, parse_path
from geoprocessor_common.files import checksum, fs_local
from geoprocessor_common.log.time_helper import time_in_ms
from linz_logger import get_log

if TYPE_CHECKING:
    from botocore.response import StreamingBody
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef
else:
    S3Client = GetObjectOutputTypeDef = StreamingBody = dict


def write(destination: str, source: bytes, content_type: str | None = None) -> None:
    """Write a source (bytes) in a AWS s3 destination (path in a bucket).

    Args:
        destination: The AWS S3 path to the file to write.
        source: The source file in bytes.
        content_type: A standard Media Type describing the format of the contents.
    """
    start_time = time_in_ms()
    if source is None:
        get_log().error("write_s3_source_none", path=destination, error="The 'source' is None.")
        raise Exception("The 'source' is None.")
    bucket, key = parse_path(destination)
    s3_client: S3Client = client("s3")
    file_multihash = checksum.multihash_as_hex(source)

    try:
        if content_type:
            s3_client.put_object(
                Bucket=bucket, Key=key, Body=source, ContentType=content_type, Metadata={"multihash": file_multihash}
            )
        else:
            s3_client.put_object(Bucket=bucket, Key=key, Body=source, Metadata={"multihash": file_multihash})
        get_log().debug("write_s3_success", path=destination, duration=time_in_ms() - start_time)
    except ClientError as ce:
        get_log().error("write_s3_error", path=destination, error=f"Unable to write the file: {ce}")
        raise ce


def upload(source_path: str, destination: str, content_type: str | None = None) -> str:
    """Upload a local file to an AWS s3 destination (path in a bucket).

    Streams from disk using multipart uploads, so unlike `write()` it is not limited to 5GB.

    Args:
        source_path: The local path to the file to upload.
        destination: The AWS S3 path to the file to write.
        content_type: A standard Media Type describing the format of the contents.

    Returns:
        the multihash of the file content
    """
    start_time = time_in_ms()
    bucket, key = parse_path(destination)
    s3_client: S3Client = client("s3")
    file_multihash = checksum.multihash_from_path(source_path)
    extra_args: dict[str, Any] = {"Metadata": {"multihash": file_multihash}}
    if content_type:
        extra_args["ContentType"] = content_type

    try:
        s3_client.upload_file(Filename=source_path, Bucket=bucket, Key=key, ExtraArgs=extra_args)
    except ClientError as ce:
        get_log().error("upload_s3_error", path=destination, error=f"Unable to upload the file: {ce}")
        raise ce

    get_log().debug(
        "upload_s3_success",
        path=destination,
        size=os.path.getsize(source_path),
        multihash=file_multihash,
        duration=time_in_ms() - start_time,
    )
    return file_multihash


def _get_object_body(path: str, needs_credentials: bool = False) -> StreamingBody:
    """Get the body of a file on a AWS S3 bucket as a stream.

    Args:
        path: The AWS S3 path to the file to read.
        needs_credentials: Tells if credentials are needed. Defaults to False.

    Raises:
        ClientError

    Returns:
        The body of the object, to be read by the caller.
    """
    bucket, key = parse_path(path)
    s3_client: S3Client = client("s3")

    try:
        if needs_credentials:
            s3_client = get_session(path).client("s3")

        s3_object: GetObjectOutputTypeDef = s3_client.get_object(Bucket=bucket, Key=key)
        return s3_object["Body"]
    except s3_client.exceptions.NoSuchBucket as nsb:
        get_log().error("s3_bucket_not_found", path=path, error=f"The specified bucket does not seem to exist: {nsb}")
        raise
    except s3_client.exceptions.NoSuchKey as nsk:
        get_log().error("s3_key_not_found", path=path, error=f"The specified file does not seem to exist: {nsk}")
        raise
    except ClientError as ce:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html#parsing-error-responses-and-catching-exceptions-from-aws-services
        if not needs_credentials and ce.response["Error"]["Code"] == "AccessDenied":
            get_log().debug("read_s3_needs_credentials", path=path)
            return _get_object_body(path, True)
        raise


def read(path: str, needs_credentials: bool = False) -> bytes:
    """Read a file on a AWS S3 bucket.

    Args:
        path: The AWS S3 path to the file to read.
        needs_credentials:  Tells if credentials are needed. Defaults to False.

    Raises:
        ClientError

    Returns:
        The file in bytes.
    """
    start_time = time_in_ms()
    with _get_object_body(path, needs_credentials) as body:
        file: bytes = body.read()
    get_log().debug("read_s3_success", path=path, duration=time_in_ms() - start_time)
    return file


def download(path: str, destination: str, needs_credentials: bool = False) -> None:
    """Download a file from an AWS s3 bucket to a local path without loading it into memory.

    Args:
        path: The AWS S3 path to the file to read.
        destination: The local path to the file to write.
        needs_credentials: Tells if credentials are needed. Defaults to False.

    Raises:
        ClientError
    """
    start_time = time_in_ms()
    with fs_local.atomic_write_path(destination) as partial_destination:
        with _get_object_body(path, needs_credentials) as body, open(partial_destination, "wb") as file:
            shutil.copyfileobj(body, file, checksum.CHUNK_SIZE)
    get_log().debug("download_s3_success", path=path, duration=time_in_ms() - start_time)


def multihash(path: str, needs_credentials: bool = False) -> str:
    """Get the multihash of a file on a AWS S3 bucket without loading it into memory.

    Args:
        path: The AWS S3 path to the file to hash.
        needs_credentials: Tells if credentials are needed. Defaults to False.

    Raises:
        ClientError

    Returns:
        the multihash of the file content
    """
    start_time = time_in_ms()
    with _get_object_body(path, needs_credentials) as body:
        file_multihash = checksum.multihash_from_stream(body)
    get_log().debug("multihash_s3_success", path=path, multihash=file_multihash, duration=time_in_ms() - start_time)
    return file_multihash


def exists(path: str, needs_credentials: bool = False) -> bool:
    """Check if s3 Object exists

    Args:
        path: path to the s3 object/key
        needs_credentials: if acces to object needs credentials. Defaults to False.

    Raises:
        ClientError
        NoSuchBucket

    Returns:
        True if the S3 Object exists
    """
    bucket, key = parse_path(path)
    s3_client: S3Client = client("s3")

    try:
        if needs_credentials:
            s3_client = get_session(path).client("s3")

        if path.endswith("/"):
            # MaxKeys limits to 1 object in the response
            objects = s3_client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
            if len(list(objects)) > 0:
                return True
            return False

        s3_client.head_object(Bucket=bucket, Key=key)

        return True
    except s3_client.exceptions.NoSuchBucket as nsb:
        get_log().debug("s3_bucket_not_found", path=path, info=f"The specified bucket does not seem to exist: {nsb}")
        return False
    except ClientError as ce:
        if not needs_credentials and ce.response["Error"]["Code"] == "AccessDenied":
            get_log().debug("read_s3_needs_credentials", path=path)
            return exists(path, True)
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html#parsing-error-responses-and-catching-exceptions-from-aws-services
        # 404 for NoSuchKey - https://github.com/boto/boto3/issues/2442
        if ce.response["Error"]["Code"] == "404":
            get_log().debug("s3_key_not_found", path=path, info=f"The specified key does not seem to exist: {ce}")
            return False
        get_log().error("s3_client_error", path=path, error=f"ClientError raised: {ce}")
        raise


def bucket_name_from_path(path: str) -> str:
    """Get the bucket name from an `s3` path.

    Args:
        path: an `s3` path

    Returns:
        the bucket name

    Example:
        >>> bucket_name_from_path("s3://linz-imagery/wellingon/")
        'linz-imagery'
    """
    path_parts = path.replace("s3://", "").split("/")
    return path_parts.pop(0)


def prefix_from_path(path: str) -> str:
    """Get the s3 prefix from an s3 path.

    Args:
        path: an `s3` path

    Returns:
        the prefix

    Example:
        >>> prefix_from_path("s3://linz-imagery/wellington/wellington_2021_0.075m/rgb/2193/BP31_500_097091.tiff")
        'wellington/wellington_2021_0.075m/rgb/2193/BP31_500_097091.tiff'
    """
    bucket_name = bucket_name_from_path(path)
    return path.replace(f"s3://{bucket_name}/", "")


def list_files_in_uri(uri: str, suffixes: list[str], s3_client: S3Client | None) -> list[str]:
    """Get a list of file paths from a s3 path based on their suffixes

    Args:
        uri: an s3 path
        suffixes: a a list of suffixes. example: [".json", "_meta.xml"]
        s3_client: an s3 client

    Returns:
        a list of file paths
    """
    s3_client = s3_client or client("s3")
    files = []
    paginator = s3_client.get_paginator("list_objects_v2")
    response_iterator = paginator.paginate(Bucket=bucket_name_from_path(uri), Prefix=prefix_from_path(uri))

    for response in response_iterator:
        for contents_data in response["Contents"]:
            key = contents_data["Key"]
            if not key.lower().endswith(tuple(suffixes)):
                get_log().trace("skipping file not json", file=key, action="collection_from_items", reason="skip")
                continue
            files.append(key)
    get_log().info("Files Listed", number_of_files=len(files))
    return files


def _get_object(bucket: str, file_name: str, s3_client: S3Client) -> GetObjectOutputTypeDef:
    """Get the object from `s3`

    Args:
        bucket: a `s3` bucket
        file_name: the name of the object
        s3_client: an `s3` client

    Returns:
        an s3 object
    """
    get_log().info("Retrieving File", path=f"s3://{bucket}/{file_name}")
    return s3_client.get_object(Bucket=bucket, Key=file_name)


def get_object_parallel_multithreading(
    bucket: str, files_to_read: list[str], s3_client: S3Client | None, concurrency: int
) -> Generator[Any, Any | BaseException, None]:
    """Get s3 objects in parallel

    Args:
        bucket: a `s3` bucket
        files_to_read: list of object names to get
        s3_client: an `s3` client
        concurrency: number of concurrent calls

    Yields:
        the object when got
    """
    s3_client = s3_client or client("s3")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_key = {executor.submit(_get_object, bucket, key, s3_client): key for key in files_to_read}

        for future in futures.as_completed(future_to_key):
            key = future_to_key[future]
            exception = future.exception()

            if not exception:
                yield key, future.result()
            else:
                yield key, exception
