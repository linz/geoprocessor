from geoprocessor_gdal.gdal.gdal_helper import gdal_info
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from geoprocessor_gdal.tiff.geotiff import get_extents
from geoprocessor_stac.imagery.create_stac import create_item
from geoprocessor_stac.imagery.item import ImageryItem


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def create_item_from_tiff(
    asset_path: str,
    start_datetime: str,
    end_datetime: str,
    collection_id: str,
    gdal_version: str,
    current_datetime: str,
    gdalinfo_result: GdalInfo | None = None,
    derived_from: list[str] | None = None,
    odr_url: str | None = None,
) -> ImageryItem:
    """Create an ImageryItem (STAC) for a TIFF, deriving its spatial extents with GDAL.

    Args:
        asset_path: path of the visual asset (TIFF)
        start_datetime: start date of the survey
        end_datetime: end date of the survey
        collection_id: collection id to link to the Item
        gdal_version: GDAL version
        current_datetime: date and time for setting consistent update and/or creation timestamp
        gdalinfo_result: result of the gdalinfo command. Defaults to None.
        derived_from: list of STAC Items from where this Item is derived. Defaults to None.
        odr_url: S3 URL of the already published files in ODR (if this is a resupply). Defaults to None.

    Returns:
        a STAC Item wrapped in ImageryItem
    """
    if not gdalinfo_result:
        gdalinfo_result = gdal_info(asset_path)
    geometry, bbox = get_extents(gdalinfo_result)

    return create_item(
        asset_path,
        start_datetime,
        end_datetime,
        collection_id,
        gdal_version,
        current_datetime,
        geometry,
        bbox,
        derived_from=derived_from,
        odr_url=odr_url,
    )
