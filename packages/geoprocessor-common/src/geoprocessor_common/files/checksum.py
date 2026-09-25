import hashlib
import io

import multihash

CHUNK_SIZE = 1024 * 1024  # 1MB


def multihash_as_hex(file_content: bytes) -> str:
    """Convert file bytes to hexadecimal SHA-256 hash

    Args:
        file_content: content of a file to hash

    Returns:
        the hash of the file
    """
    file_hash = hashlib.sha256()
    file = io.BytesIO(file_content)
    while chunk := file.read(CHUNK_SIZE):
        file_hash.update(chunk)
    result: str = multihash.to_hex_string(multihash.encode(file_hash.digest(), "sha2-256"))
    return result
