import io
import os

from geoprocessor_common.files.checksum import CHUNK_SIZE, multihash_as_hex, multihash_from_path, multihash_from_stream

TEST_CONTENT_MULTIHASH = "12206ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"


def test_multihash_as_hex() -> None:
    assert multihash_as_hex(b"test content") == TEST_CONTENT_MULTIHASH


def test_multihash_from_stream() -> None:
    assert multihash_from_stream(io.BytesIO(b"test content")) == TEST_CONTENT_MULTIHASH


def test_multihash_from_stream_is_same_as_from_bytes_over_multiple_chunks() -> None:
    content = os.urandom(CHUNK_SIZE * 2 + 1)

    assert multihash_from_stream(io.BytesIO(content)) == multihash_as_hex(content)


def test_multihash_from_stream_empty() -> None:
    assert multihash_from_stream(io.BytesIO(b"")) == multihash_as_hex(b"")


def test_multihash_from_path(setup: str) -> None:
    path = os.path.join(setup, "test.file")
    with open(path, "wb") as file:
        file.write(b"test content")

    assert multihash_from_path(path) == TEST_CONTENT_MULTIHASH
