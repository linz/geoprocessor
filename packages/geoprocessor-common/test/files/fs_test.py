import os
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from boto3 import client
from geoprocessor_common.files.fs import NoSuchFileError, read, write, write_all, write_sidecars
from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME
from mypy_boto3_s3 import S3Client
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests


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
    # Raises an exception as all files are not writte·
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
    inputs: list[str] = []
    file_contents = "a" * 1000 * 1000
    i = 0
    while i < 10:
        path = Path(os.path.join(setup, str(i)))
        if i % 2 == 0:
            path.write_text(file_contents, encoding="utf-8")  # 1MB
        else:
            path.touch()
        inputs.append(path.as_posix())
        i += 1
    written_files = write_all(inputs=inputs, target=setup, generate_name=False)
    assert written_files == inputs
