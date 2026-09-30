import os

import pytest
from geoprocessor_common.files.fs_local import exists, read, write


@pytest.mark.dependency(name="write")
def test_write(setup: str) -> None:
    target = setup
    path = os.path.join(target, "test.file")
    write(path, b"test")
    assert os.path.isfile(path)


def test_write_non_existing_dir(setup: str) -> None:
    target = setup
    path = os.path.join(target, "new_dir/test.file")
    write(path, b"test")
    assert os.path.isfile(path)


@pytest.mark.dependency(name="read", depends=["write"])
def test_read(setup: str) -> None:
    content = b"test content"
    target = setup
    path = os.path.join(target, "test.file")
    write(path, content)
    file_content = read(path)
    assert file_content == content


@pytest.mark.dependency(name="exists", depends=["write"])
def test_exists(setup: str) -> None:
    content = b"test content"
    target = setup
    path = os.path.join(target, "test.file")
    write(path, content)
    found = exists(path)
    assert found is True


def test_exists_file_not_found() -> None:
    found = exists("/tmp/test.file")
    assert found is False
