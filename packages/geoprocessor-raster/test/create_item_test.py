from importlib.metadata import version
from pathlib import Path
from typing import cast

from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from geoprocessor_raster.create_item import create_item_from_tiff
from geoprocessor_stac.testing.helpers import any_epoch_datetime_string
from pytest_subtests import SubTests

DATA_DIR = Path(__file__).parent / "data"


def any_gdalinfo_result() -> GdalInfo:
    return cast(GdalInfo, {"wgs84Extent": {"type": "Polygon", "coordinates": [[[0, 1], [1, 1], [1, 0], [0, 0]]]}})


def test_should_derive_spatial_extents_from_gdalinfo() -> None:
    """`create_item_from_tiff` converts a `gdalinfo` result into the geometry and bbox of the Item."""
    item = create_item_from_tiff(
        str(DATA_DIR / "empty.tiff"),
        any_epoch_datetime_string(),
        any_epoch_datetime_string(),
        "any collection id",
        "any GDAL version",
        any_epoch_datetime_string(),
        any_gdalinfo_result(),
    )

    assert item.stac["geometry"] == {"type": "Polygon", "coordinates": [[[0, 1], [1, 1], [1, 0], [0, 0]]]}
    assert item.stac["bbox"] == (0.0, 0.0, 1.0, 1.0)


def test_should_record_gdal_and_raster_package_versions(subtests: SubTests) -> None:
    """`create_item_from_tiff` records the GDAL version it is given and the installed raster package version."""
    item = create_item_from_tiff(
        str(DATA_DIR / "empty.tiff"),
        any_epoch_datetime_string(),
        any_epoch_datetime_string(),
        "any collection id",
        "any GDAL version",
        any_epoch_datetime_string(),
        any_gdalinfo_result(),
    )
    software = item.stac["properties"]["processing:software"]

    with subtests.test(msg="gdal version"):
        assert software["gdal"] == "any GDAL version"

    with subtests.test(msg="raster package version"):
        assert software["geoprocessor-raster"] == version("geoprocessor-raster")
