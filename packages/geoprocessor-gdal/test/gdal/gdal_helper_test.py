from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from fake_gdalinfo import fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_helper import GDALExecutionException, get_gdal_version, is_geotiff
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
