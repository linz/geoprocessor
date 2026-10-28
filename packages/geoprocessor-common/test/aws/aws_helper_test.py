from geoprocessor_common.aws.aws_helper import parse_path
from pytest_subtests import SubTests


def test_parse_path_s3(subtests: SubTests) -> None:
    s3_path = "s3://bucket-name/path/to/the/file.test"
    bucket, key = parse_path(s3_path)

    with subtests.test():
        assert bucket == "bucket-name"

    with subtests.test():
        assert key == "path/to/the/file.test"


def test_parse_path_local() -> None:
    local_path = "/home/tmp/file.test"
    _, file_path = parse_path(local_path)

    assert file_path == "/home/tmp/file.test"
