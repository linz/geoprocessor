import os


def write(destination: str, source: bytes) -> None:
    """Write the source to the local destination file.

    Args:
        destination: The local path to the file to write.
        source: The source file in bytes.
    """
    os.makedirs(os.path.dirname(destination), mode=0o777, exist_ok=True)
    with open(destination, "wb") as file:
        file.write(source)


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
