import json
from typing import Any, TypedDict

from geoprocessor_common.files.fs import read
from geoprocessor_common.geometry import BoundingBox, GeojsonPolygon
from geoprocessor_stac.link import Link, Relation
from geoprocessor_stac.util.STAC_VERSION import STAC_VERSION
from geoprocessor_stac.util.media_type import StacMediaType
from geoprocessor_stac.util.stac_extensions import StacExtensions

STACAsset = TypedDict("STACAsset", {"href": str, "file:checksum": str, "created": str, "updated": str})

STACProcessingSoftwareGdal = TypedDict(
    "STACProcessingSoftwareGdal",
    {"gdal": str, "geoprocessor/raster": str, "linz/geoprocessor": str},
)
"""STAC Processing extension LINZ specific fields for a raster asset produced by GDAL"""

STACProcessingSoftwarePdal = TypedDict(
    "STACProcessingSoftwarePdal", {"pdal": str, "geoprocessor/pointcloud": str, "linz/geoprocessor": str}
)
"""STAC Processing extension LINZ specific fields for a point cloud asset produced by PDAL"""

type STACProcessingSoftware = STACProcessingSoftwareGdal | STACProcessingSoftwarePdal
"""An Item names the one software that produced its asset, so these are alternatives rather than
optional fields: a raster Item carries `gdal` and a point cloud Item carries `pdal`, never both
and never neither.
"""

STACProcessing = TypedDict(
    "STACProcessing",
    {
        "processing:datetime": str,
        "processing:software": STACProcessingSoftware,
        "processing:version": str,
    },
)
"""Some of the STAC processing extension fields are not declared in this TypedDict 
(https://github.com/stac-extensions/processing?tab=readme-ov-file#fields)
"""


class ImageryItem:
    stac: dict[str, Any]

    def __init__(self, id_: str, stac_asset: STACAsset, stac_processing: STACProcessing) -> None:
        self.stac = {
            "type": "Feature",
            "stac_version": STAC_VERSION,
            "id": id_,
            "links": [Link(path=f"./{id_}.json", rel=Relation.SELF, media_type=StacMediaType.GEOJSON).stac],
            "assets": {"visual": {**stac_asset, "type": "image/tiff; application=geotiff; profile=cloud-optimized"}},
            "stac_extensions": [StacExtensions.file.value, StacExtensions.processing.value],
            "properties": {"created": stac_asset["created"], "updated": stac_asset["updated"], **stac_processing},
        }

    @classmethod
    def from_file(cls, file_name: str) -> "ImageryItem":
        """Create an ImageryItem from a file.

        Args:
            file_name: The s3 URL or local path of the file to load.

        Returns:
            ImageryItem: The new ImageryItem.
        """
        file_content = read(file_name)
        stac_from_file = json.loads(file_content.decode("UTF-8"))
        if (bbox := stac_from_file.get("bbox")) is not None:
            stac_from_file["bbox"] = tuple(bbox)
        new_item = cls(
            id_=stac_from_file["id"],
            stac_asset=stac_from_file["assets"]["visual"],
            stac_processing=stac_from_file["properties"],
        )
        new_item.stac = stac_from_file

        return new_item

    def update_checksum_related_metadata(self, file_content_checksum: str, stac_processing_data: STACProcessing) -> None:
        """Set the assets.visual.file:checksum attribute if it has changed.
        If the checksum has changed, this also updates the following attributes:
            assets.visual.updated
            properties.updated
            properties.processing:datetime
            properties.processing:software
            properties.processing:version

        Args:
            file_content_checksum (str): the new checksum
            stac_processing_data (STACProcessing): new data for the STAC processing extension attributes for this asset/item
        """
        if file_content_checksum != self.stac["assets"]["visual"]["file:checksum"]:
            self.stac["assets"]["visual"]["file:checksum"] = file_content_checksum
            self.stac["assets"]["visual"]["updated"] = stac_processing_data["processing:datetime"]
            self.stac["properties"].update(stac_processing_data)
            self.stac["properties"]["updated"] = stac_processing_data["processing:datetime"]

    def update_datetime(self, start_datetime: str, end_datetime: str) -> None:
        """Update the Item `start_datetime` and `end_datetime` property.

        Args:
            start_datetime: a start date in `YYYY-MM-DD` format
            end_datetime: a end date in `YYYY-MM-DD` format
        """
        self.stac.setdefault("properties", {})
        self.stac["properties"]["start_datetime"] = start_datetime
        self.stac["properties"]["end_datetime"] = end_datetime
        self.stac["properties"]["datetime"] = None

    def update_spatial(self, geometry: GeojsonPolygon, bbox: BoundingBox) -> None:
        """Update the `geometry` and `bbox` (bounding box) of the Item.

        Args:
            geometry: a geometry
            bbox: a bounding box
        """
        self.stac["geometry"] = geometry
        self.stac["bbox"] = bbox

    def add_collection(self, collection_id: str) -> None:
        """Link a Collection to the Item as its `collection` and `parent`.

        Args:
            collection_id: the id of the collection to link
        """
        self.stac["collection"] = collection_id
        self.add_link(Link(path="./collection.json", rel=Relation.COLLECTION, media_type=StacMediaType.JSON))
        self.add_link(Link(path="./collection.json", rel=Relation.PARENT, media_type=StacMediaType.JSON))

    def add_link(self, link: Link) -> None:
        if self.stac.get("links") and link.stac["rel"] in [
            Relation.COLLECTION,
            Relation.PARENT,
            Relation.SELF,
        ]:  # STAC specification prescribes there can be only one of these
            self.stac["links"][:] = [l for l in self.stac["links"] if l.get("rel") != link.stac["rel"]]

        self.stac.setdefault("links", []).append(link.stac)
