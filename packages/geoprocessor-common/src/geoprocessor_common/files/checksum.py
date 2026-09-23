import hashlib
import io
from typing import Protocol

import multihash

CHUNK_SIZE = 1024 * 1024  # 1MB


class Readable(Protocol):  # pylint: disable=too-few-public-methods
    """A file object or a `boto3` `StreamingBody`."""

    def read(self, size: int = ..., /) -> bytes: ...


def multihash_from_stream(stream: Readable) -> str:
    """Read a stream in chunks to get its hexadecimal SHA-256 hash, without holding it all in memory.

    Args:
        stream: an open stream of the content to hash

    Returns:
        the hash of the content
    """
    file_hash = hashlib.sha256()
    while chunk := stream.read(CHUNK_SIZE):
        file_hash.update(chunk)
    result: str = multihash.to_hex_string(multihash.encode(file_hash.digest(), "sha2-256"))
    return result


def multihash_from_path(path: str) -> str:
    """Read a local file in chunks to get its hexadecimal SHA-256 hash.

    Args:
        path: a local path to the file to hash

    Returns:
        the hash of the file
    """
    with open(path, "rb") as file:
        return multihash_from_stream(file)


def multihash_as_hex(file_content: bytes) -> str:
    """Convert file bytes to hexadecimal SHA-256 hash

    Args:
        file_content: content of a file to hash

    Returns:
        the hash of the file
    """
    return multihash_from_stream(io.BytesIO(file_content))
