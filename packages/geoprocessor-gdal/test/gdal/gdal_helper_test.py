from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from botocore.credentials import ReadOnlyCredentials
from fake_gdalinfo import fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_helper import (
    GDALExecutionException,
    get_gdal_version,
    get_vsis3_env,
    is_geotiff,
    run_gdal,
)
from pytest_subtests import SubTests


def test_is_geotiff(subtests: SubTests) -> None:
    gdalinfo_geotiff = fake_gdalinfo()
    gdalinfo_not_geotiff = fake_gdalinfo()
    gdalinfo_geotiff["driverShortName"] = "GTiff"
    gdalinfo_not_geotiff["driverShortName"] = "GTiff"
    gdalinfo_geotiff["coordinateSystem"] = {"wkt": "PROJCRS['NZGD2000 / New Zealand Transverse Mercator 2000']"}

    with subtests.test():
        assert is_geotiff("file.tiff", gdalinfo_geotiff) is True

    with subtests.test():
        assert is_geotiff("file.tiff", gdalinfo_not_geotiff) is False


def test_get_gdal_version_returns_the_reported_version() -> None:
    get_gdal_version.cache_clear()
    with patch(
        "geoprocessor_gdal.gdal.gdal_helper.run_gdal",
        return_value=CompletedProcess([], 0, b"GDAL 3.10.3, released 2025/04/01\n", b""),
    ):
        assert get_gdal_version() == "GDAL 3.10.3, released 2025/04/01"


def test_get_gdal_version_rejects_a_successful_run_that_reports_nothing() -> None:
    get_gdal_version.cache_clear()
    with patch("geoprocessor_gdal.gdal.gdal_helper.run_gdal", return_value=CompletedProcess([], 0, b"  \n", b"")):
        with pytest.raises(GDALExecutionException, match="reported no version"):
            get_gdal_version()


def test_get_vsis3_env_uses_bucket_role() -> None:
    with (
        patch("geoprocessor_gdal.gdal.gdal_helper.has_role", return_value=True),
        patch(
            "geoprocessor_gdal.gdal.gdal_helper.get_session_credentials",
            return_value=ReadOnlyCredentials("key", "secret", "token"),
        ),
    ):
        assert get_vsis3_env("s3://bucket/file.tiff") == {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_SESSION_TOKEN": "token",
        }


def test_get_vsis3_env_without_bucket_role() -> None:
    with patch("geoprocessor_gdal.gdal.gdal_helper.has_role", return_value=False):
        assert get_vsis3_env("s3://bucket/file.tiff") == {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR"}


def test_run_gdal_reads_s3_through_vsis3() -> None:
    with (
        patch("geoprocessor_gdal.gdal.gdal_helper.get_vsis3_env", return_value={"AWS_ACCESS_KEY_ID": "key"}),
        patch("geoprocessor_gdal.gdal.gdal_helper.copy") as copy,
        patch("geoprocessor_gdal.gdal.gdal_helper.subprocess.run", return_value=CompletedProcess([], 0, b"", b"")) as run,
    ):
        run_gdal(["gdalinfo"], input_file="s3://bucket/file.tiff", vsis3=True)

    copy.assert_not_called()
    assert run.call_args.args[0] == ["gdalinfo", "/vsis3/bucket/file.tiff"]
    assert run.call_args.kwargs["env"]["AWS_ACCESS_KEY_ID"] == "key"
