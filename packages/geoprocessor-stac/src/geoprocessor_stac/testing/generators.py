from datetime import datetime
from os import urandom
from typing import Callable

from geoprocessor_common.files.checksum import multihash_as_hex
from geoprocessor_common.geometry import BoundingBox, GeojsonPolygon
from geoprocessor_stac.imagery.item import STACAsset, STACProcessing, STACProcessingSoftwareGdal
from shapely.geometry import Polygon


def fixed_now_function(now: datetime) -> Callable[[], datetime]:
    def func() -> datetime:
        return now

    return func


def any_stac_asset() -> STACAsset:
    return STACAsset(
        **{
            "href": "any href",
            "file:checksum": "any checksum",
            "created": "any created datetime",
            "updated": "any updated datetime",
        }
    )


def any_stac_processing() -> STACProcessing:
    return STACProcessing(
        **{
            "processing:datetime": "any processing datetime",
            "processing:software": STACProcessingSoftwareGdal(
                **{
                    "gdal": "any GDAL version",
                    "geoprocessor/raster": "any geoprocessor/raster version",
                    "linz/geoprocessor": "any linz/geoprocessor commit-sha",
                }
            ),
            "processing:version": "any processing version",
        }
    )


def any_multihash_as_hex() -> str:
    return multihash_as_hex(urandom(64))


def any_geometry_and_bbox() -> tuple[GeojsonPolygon, BoundingBox]:
    """A geometry and a matching bounding box, for tests that need spatial extents but do not assert on them."""
    geometry: GeojsonPolygon = {"type": "Polygon", "coordinates": [[[0, 1], [1, 1], [1, 0], [0, 0]]]}

    return geometry, Polygon(geometry["coordinates"][0]).bounds
