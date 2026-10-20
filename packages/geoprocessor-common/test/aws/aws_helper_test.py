from unittest.mock import patch

from geoprocessor_common.aws.aws_credential_source import CredentialSource
from geoprocessor_common.aws.aws_helper import has_role, parse_path
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


def test_has_role(subtests: SubTests) -> None:
    role = CredentialSource(
        bucket="bucket-name", type="s3", prefix="s3://bucket-name/", accountId="123", roleArn="arn:aws:iam::123:role/read"
    )
    with patch("geoprocessor_common.aws.aws_helper.bucket_roles", [role]):
        with subtests.test():
            assert has_role("s3://bucket-name/path/file.tiff") is True

        with subtests.test():
            assert has_role("s3://other-bucket/path/file.tiff") is False
