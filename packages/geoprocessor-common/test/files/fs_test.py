import os
from collections.abc import Callable
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import patch

from boto3 import client
from botocore.exceptions import ClientError
from geoprocessor_common.files.files_helper import ContentType
from geoprocessor_common.files.fs import (
    NoSuchFileError,
    copy,
    multihash,
    read,
    write,
    write_all,
    write_sidecars,
)
from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME
from mypy_boto3_s3 import S3Client
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests

TEST_CONTENT_MULTIHASH = "12206ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"


def test_read_key_not_found_local() -> None:
    with raises(NoSuchFileError):
        read("test_dir/test.file")


@mock_aws
def test_read_key_not_found_s3(capsys: CaptureFixture[str]) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")

    with raises(NoSuchFileError):
        read("s3://testbucket/test.file")

    assert "s3_key_not_found" in capsys.readouterr().out


def test_write_all_file_not_found_local() -> None:
    # Raises an exception as all files are not written
    with raises(Exception) as e:
        write_all(["/test.prj"], "/tmp")

    assert str(e.value) == "Not all mandatory source files were written"


def test_write_sidecars_file_not_found_local(capsys: CaptureFixture[str]) -> None:
    write_sidecars(["/test.prj"], "/tmp")
    assert "No sidecar file found; skipping" in capsys.readouterr().out


@mock_aws
def test_write_all_key_not_found_s3() -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")

    # Raises an exception as all files are not written
    with raises(Exception) as e:
        write_all(["s3://testbucket/test.tif"], "/tmp")

    assert str(e.value) == "Not all mandatory source files were written"


@mock_aws
def test_write_sidecars_key_not_found_s3(capsys: CaptureFixture[str]) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")

    write_sidecars(["s3://testbucket/test.prj"], "/tmp")

    # capsys.readouterr().out json string format is not valid which implies
    # we can't parse it to find the actual `msg`
    assert "No sidecar file found; skipping" in capsys.readouterr().out


def test_write_sidecars_one_found(capsys: CaptureFixture[str], subtests: SubTests) -> None:
    target = mkdtemp()
    # Add a file to read
    content = b"test content"
    path = os.path.join(target, "test.tfw")
    write(path, content)
    non_existing_path = os.path.join(target, "test.prj")
    # Write the sidecar files with one unexisting
    write_sidecars([non_existing_path, path], os.path.join(target, "/tmp"))
    logs = capsys.readouterr().out
    with subtests.test(msg="One has not been found"):
        assert "No sidecar file found; skipping" in logs

    with subtests.test(msg="One has been found"):
        assert "wrote_sidecar_file" in logs

    rmtree(target)


def test_write_all_in_order(setup: str) -> None:
    source_dir = os.path.join(setup, "source")
    target_dir = os.path.join(setup, "target")
    os.makedirs(source_dir)
    inputs: list[str] = []
    file_contents = "a" * 1000 * 1000
    i = 0
    while i < 10:
        path = Path(os.path.join(source_dir, str(i)))
        if i % 2 == 0:
            path.write_text(file_contents, encoding="utf-8")  # 1MB
        else:
            path.touch()
        inputs.append(path.as_posix())
        i += 1
    written_files = write_all(inputs=inputs, target=target_dir, generate_name=False)
    assert written_files == [os.path.join(target_dir, str(i)) for i in range(10)]


def test_multihash_local(setup: str) -> None:
    path = os.path.join(setup, "test.file")
    write(path, b"test content")

    assert multihash(path) == TEST_CONTENT_MULTIHASH


def test_multihash_key_not_found_local() -> None:
    with raises(NoSuchFileError):
        multihash("test_dir/test.file")


@mock_aws
def test_multihash_s3() -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    s3_client.put_object(Bucket="testbucket", Key="test.file", Body=b"test content")

    assert multihash("s3://testbucket/test.file") == TEST_CONTENT_MULTIHASH


@mock_aws
def test_multihash_key_not_found_s3() -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")

    with raises(NoSuchFileError):
        multihash("s3://testbucket/test.file")


def test_copy_local_to_local(subtests: SubTests, setup: str) -> None:
    source_path = os.path.join(setup, "source.tiff")
    target_path = os.path.join(setup, "new_dir/target.tiff")
    write(source_path, b"test content")

    file_multihash = copy(source_path, target_path, ContentType.GEOTIFF.value)

    with subtests.test(msg="content"):
        assert read(target_path) == b"test content"

    with subtests.test(msg="returned multihash"):
        assert file_multihash == TEST_CONTENT_MULTIHASH


@mock_aws
def test_copy_local_to_s3(subtests: SubTests, setup: str) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    source_path = os.path.join(setup, "source.tiff")
    write(source_path, b"test content")

    file_multihash = copy(source_path, "s3://testbucket/target.tiff", ContentType.GEOTIFF.value)

    resp = s3_client.get_object(Bucket="testbucket", Key="target.tiff")
    with subtests.test(msg="content"):
        assert resp["Body"].read() == b"test content"

    with subtests.test(msg="content type"):
        assert resp["ContentType"] == ContentType.GEOTIFF.value

    with subtests.test(msg="returned multihash"):
        assert file_multihash == TEST_CONTENT_MULTIHASH


@mock_aws
def test_copy_s3_to_local(subtests: SubTests, setup: str) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    s3_client.put_object(Bucket="testbucket", Key="source.tiff", Body=b"test content")
    target_path = os.path.join(setup, "new_dir/target.tiff")

    file_multihash = copy("s3://testbucket/source.tiff", target_path)

    with subtests.test(msg="content"):
        assert read(target_path) == b"test content"

    with subtests.test(msg="returned multihash"):
        assert file_multihash == TEST_CONTENT_MULTIHASH


@mock_aws
def test_copy_s3_to_s3(subtests: SubTests) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    s3_client.put_object(Bucket="testbucket", Key="source.tiff", Body=b"test content")

    file_multihash = copy("s3://testbucket/source.tiff", "s3://testbucket/target.tiff", ContentType.GEOTIFF.value)

    with subtests.test(msg="content"):
        assert read("s3://testbucket/target.tiff") == b"test content"

    with subtests.test(msg="returned multihash"):
        assert file_multihash == TEST_CONTENT_MULTIHASH


@mock_aws
def test_s3_errors_that_are_not_a_missing_key_are_reraised(subtests: SubTests, setup: str) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    error = ClientError({"Error": {"Code": "InternalError", "Message": "any error"}}, "GetObject")
    path = "s3://testbucket/test.file"
    calls: dict[str, Callable[[], object]] = {
        "read": lambda: read(path),
        "download": lambda: copy(path, os.path.join(setup, "test.file")),
        "multihash": lambda: multihash(path),
    }

    for patched, call in calls.items():
        with subtests.test(msg=patched):
            with patch(f"geoprocessor_common.files.fs_s3.{patched}", side_effect=error):
                with raises(ClientError):
                    call()


def test_copy_source_not_found_local(setup: str) -> None:
    with raises(NoSuchFileError):
        copy("test_dir/test.file", os.path.join(setup, "test.file"))


@mock_aws
def test_copy_source_not_found_s3(subtests: SubTests, setup: str) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")
    destination = os.path.join(setup, "source/test.prj")

    with subtests.test(msg="raises NoSuchFileError"):
        with raises(NoSuchFileError):
            copy("s3://testbucket/test.prj", destination)

    with subtests.test(msg="leaves no file behind"):
        assert os.listdir(os.path.join(setup, "source")) == []


@mock_aws
def test_copy_local_source_not_found_with_s3_target() -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="testbucket")

    with raises(NoSuchFileError):
        copy("test_dir/test.file", "s3://testbucket/test.file")
