from typing import Any

import pytest


@pytest.fixture
def fake_imagery_item_stac() -> dict[str, Any]:
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "empty",
        "links": [{"href": "./empty.json", "rel": "self", "type": "application/geo+json"}],
        "assets": {
            "visual": {
                "href": "any href",
                "file:checksum": "my_checksum",
                "created": "any created datetime",
                "updated": "any processing datetime",
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            }
        },
        "stac_extensions": [
            "https://stac-extensions.github.io/file/v2.0.0/schema.json",
            "https://stac-extensions.github.io/processing/v1.2.0/schema.json",
        ],
        "properties": {
            "created": "any created datetime",
            "updated": "any processing datetime",
            "processing:datetime": "any processing datetime",
            "processing:software": {
                "gdal": "any GDAL version",
                "geoprocessor/raster": "any geoprocessor/raster version",
                "linz/geoprocessor": "any linz/geoprocessor commit-sha",
            },
            "processing:version": "any processing version",
            "start_datetime": "2021-01-27T00:00:00Z",
            "end_datetime": "2021-01-29T00:00:00Z",
            "datetime": None,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[1799667.5, 5815977.0], [1800422.5, 5815977.0], [1800422.5, 5814986.0], [1799667.5, 5814986.0]]],
        },
        "bbox": (1799667.5, 5814986.0, 1800422.5, 5815977.0),
    }
