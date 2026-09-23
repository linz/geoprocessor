import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from geoprocessor_common.files import checksum


@contextmanager
def atomic_write_path(destination: str) -> Iterator[str]:
    """Create the parent directories of `destination` and yield a path to write to in its place.

    The written file is moved onto `destination` once the block completes, so that an interrupted write does not
    leave an empty file or a truncated file behind.

    Args:
        destination: The local path to the file to write.

    Yields:
        the path to write to, a sibling of `destination`
    """
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    partial_destination = destination + ".part"
    try:
        yield partial_destination
        os.replace(partial_destination, destination)
    finally:
        Path(partial_destination).unlink(missing_ok=True)


def write(destination: str, source: bytes) -> None:
    """Write the source to the local destination file.

    Args:
        destination: The local path to the file to write.
        source: The source file in bytes.
    """
    with atomic_write_path(destination) as partial_destination:
        with open(partial_destination, "wb") as file:
            file.write(source)


def copy_file(source_path: str, destination: str) -> None:
    """Copy a local file to another local destination without loading it into memory.

    Args:
        source_path: The local path to the file to copy.
        destination: The local path to the file to write.
    """
    with atomic_write_path(destination) as partial_destination:
        shutil.copyfile(source_path, partial_destination)


def multihash(path: str) -> str:
    """Get the multihash of a local file without loading it into memory.

    Args:
        path: A local path to a file.

    Returns:
        the multihash of the file content
    """
    return checksum.multihash_from_path(path)


def read(path: str) -> bytes:
    """Read the local file from its path.

    Args:
        path: A local path to a file.

    Returns:
        The file in bytes.
    """
    with open(path, "rb") as file:
        return file.read()


def exists(path: str) -> bool:
    """Check if path (file or directory) exists

    Args:
        path: A local path to a directory or file

    Returns:
        True if the path exists
    """
    return os.path.exists(path)
