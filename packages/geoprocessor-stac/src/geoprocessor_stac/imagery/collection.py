import json
import os
from decimal import Decimal
from typing import Any

import ulid
from geoprocessor_common.data_type import DataType
from geoprocessor_common.datetimes import convert_utc_to_nz_datetime, format_rfc_3339_datetime_string, parse_rfc_3339_datetime
from geoprocessor_common.files import checksum
from geoprocessor_common.files.files_helper import ContentType
from geoprocessor_common.files.fs import NoSuchFileError, exists, read, write
from geoprocessor_stac.imagery.capture_area import generate_capture_area
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.constants import (
    ANCILLARY_AERIAL_PHOTOS,
    ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS,
    DATA_CATEGORIES,
    DATA_DOMAINS,
    DEM,
    DEM_HILLSHADE,
    DEM_HILLSHADE_IGOR,
    DSM,
    DSM_HILLSHADE,
    DSM_HILLSHADE_IGOR,
    HUMAN_READABLE_REGIONS,
    LIFECYCLE_SUFFIXES,
    NEAR_INFRARED_AERIAL_PHOTOS,
    NEAR_INFRARED_SATELLITE_IMAGERY,
    RURAL_AERIAL_PHOTOS,
    SATELLITE_IMAGERY,
    SCANNED_AERIAL_PHOTOS,
    URBAN_AERIAL_PHOTOS,
)
from geoprocessor_stac.imagery.provider import Provider
from geoprocessor_stac.json_codec import dict_to_json_bytes
from geoprocessor_stac.link import Link, Relation
from geoprocessor_stac.util.STAC_VERSION import STAC_VERSION
from geoprocessor_stac.util.media_type import StacMediaType
from geoprocessor_stac.util.stac_extensions import StacExtensions
from linz_logger import get_log
from shapely import to_geojson
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

ANY_ORTHO_AERIAL_PHOTOS = {
    ANCILLARY_AERIAL_PHOTOS,
    ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS,
    URBAN_AERIAL_PHOTOS,
    RURAL_AERIAL_PHOTOS,
    NEAR_INFRARED_AERIAL_PHOTOS,
}
ANY_SATELLITE_IMAGERY = {SATELLITE_IMAGERY, NEAR_INFRARED_SATELLITE_IMAGERY}
NEAR_INFRARED_CATEGORIES = {
    ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS,
    NEAR_INFRARED_AERIAL_PHOTOS,
    NEAR_INFRARED_SATELLITE_IMAGERY,
}
IMAGERY = {SCANNED_AERIAL_PHOTOS, *ANY_SATELLITE_IMAGERY, *ANY_ORTHO_AERIAL_PHOTOS}
ELEVATION = {DEM, DSM}
HILLSHADES = {DEM_HILLSHADE, DEM_HILLSHADE_IGOR, DSM_HILLSHADE, DSM_HILLSHADE_IGOR}
COLLECTION_FILE_NAME = "collection.json"
CAPTURE_AREA_FILE_NAME = "capture-area.geojson"
CAPTURE_DATES_FILE_NAME = "capture-dates.geojson"
WARN_NO_PUBLISHED_CAPTURE_AREA = "no_published_capture_area"
GSD_UNIT = "m"
ANCILLARY_CATEGORIES = {ANCILLARY_AERIAL_PHOTOS, ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS}
# When an ancillary category is published as part of a named event, the title/description
# read as plain (non-ancillary) orthophotography instead of "Ancillary ...".
EVENTS = {
    ANCILLARY_AERIAL_PHOTOS: {"title": "Aerial Photos", "description": "Orthophotography"},
    ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS: {
        "title": "Near-Infrared Aerial Photos",
        "description": "Near-infrared orthophotography",
    },
}


class SubtypeParameterError(Exception):
    def __init__(self, category: str) -> None:
        self.message = f"Unrecognised/Unimplemented Subtype Parameter: {category}"


class MissingMetadataError(Exception):
    def __init__(self, metadata: str) -> None:
        self.message = f"Missing metadata: {metadata}"
        self.message = f"Missing metadata: {metadata}"


class ImageryCollection:  # pylint: disable=too-many-instance-attributes
    stac: dict[str, Any]
    gsd: Decimal
    domain: str
    data_type: DataType
    capture_area: dict[str, Any] | None = None
    publish_capture_area = True
    published_location: str | None = None
    add_title_suffix: bool = True

    def __init__(
        self,
        context: CollectionContext,
        created_datetime: str,
        updated_datetime: str,
    ) -> None:
        if not context.collection_id:
            context.collection_id = str(ulid.ULID())

        self.gsd = context.gsd
        self.domain = context.domain
        self.data_type = context.data_type
        self.add_title_suffix = context.add_title_suffix

        self.stac = {
            "type": "Collection",
            "stac_version": STAC_VERSION,
            "id": context.collection_id,
            "title": "",
            "description": "",
            "license": "CC-BY-4.0",
            "links": [{"rel": "self", "href": "./collection.json", "type": "application/json"}],
            "providers": [],
            "linz:lifecycle": context.lifecycle,
            "linz:geospatial_category": context.category,
            "linz:region": context.region,
            "linz:security_classification": "unclassified",
            "linz:slug": context.linz_slug,
            "gsd": float(context.gsd),
            "created": created_datetime,
            "updated": updated_datetime,
        }

        # Only include data_type for `UINT16` near-infrared imagery
        # as only near-infrared output stays 16-bit, other `UINT16` sources are rescaled to 8-bit (WEBP)
        if self.data_type == DataType.UINT16 and context.category in NEAR_INFRARED_CATEGORIES:
            self.stac["data_type"] = self.data_type.value

        # Optional metadata - if not provided, the field will not be added to the Collection
        if event_name := context.event_name:
            self.stac["linz:event_name"] = event_name
        if geographic_description := context.geographic_description:
            self.stac["linz:geographic_description"] = geographic_description
        if historic_survey_number := context.historic_survey_number:
            self.stac["linz:historic_survey_number"] = historic_survey_number

        self.add_providers(context.providers)

    @classmethod
    def from_file(cls, path: str, load_capture_area: bool = True) -> "ImageryCollection":
        """Load an ImageryCollection object from a STAC Collection file.

        Args:
            path: The path to the STAC Collection file to load.
            load_capture_area: Whether to load the capture area from a separate file.

        Returns:
            The ImageryCollection loaded from the file.
        """
        file_content = read(path)
        stac_from_file = json.loads(file_content.decode("UTF-8"))
        collection = cls.__new__(cls)
        collection.stac = stac_from_file
        collection.published_location = os.path.dirname(path)
        if load_capture_area:
            capture_area_path = os.path.join(collection.published_location, CAPTURE_AREA_FILE_NAME)
            # Some published datasets may not have a capture-area.geojson file (TDE-988)
            if exists(capture_area_path):
                collection.capture_area = json.loads(read(capture_area_path))
            else:
                collection.publish_capture_area = False
        return collection

    def update(self, context: CollectionContext, updated_datetime: str) -> None:
        """Update the Collection with new metadata.

        Args:
            context: The context containing the updated metadata.
            updated_datetime: The updated datetime of the Collection.
        """
        self.stac["gsd"] = float(context.gsd)
        # Only include data_type for `UINT16` near-infrared imagery
        # as only near-infrared output stays 16-bit, other `UINT16` sources are rescaled to 8-bit (WEBP)
        if context.data_type == DataType.UINT16 and context.category in NEAR_INFRARED_CATEGORIES:
            self.stac["data_type"] = context.data_type.value
        else:
            self.stac.pop("data_type", None)
        self.stac["linz:security_classification"] = "unclassified"
        if context.lifecycle:
            self.stac["linz:lifecycle"] = context.lifecycle
        if context.category:
            self.stac["linz:geospatial_category"] = context.category
        if context.region:
            self.stac["linz:region"] = context.region
        if context.producers or context.licensors:
            self.stac["providers"] = []
            self.add_providers(context.providers)

        # Optional metadata - if not provided, the field will be removed from the Collection
        if context.geographic_description:
            self.stac["linz:geographic_description"] = context.geographic_description
        else:
            self.stac.pop("linz:geographic_description", None)
        if context.event_name:
            self.stac["linz:event_name"] = context.event_name
        else:
            self.stac.pop("linz:event_name", None)
        if context.historic_survey_number:
            self.stac["linz:historic_survey_number"] = context.historic_survey_number
        else:
            self.stac.pop("linz:historic_survey_number", None)

        self.stac["updated"] = updated_datetime
        self.gsd = context.gsd
        self.data_type = context.data_type
        self.domain = context.domain
        self.add_title_suffix = context.add_title_suffix

    def set_title(self) -> None:
        """Set the title based on the STAC metadata.
        Satellite Imagery / Near-Infrared Satellite Imagery / Urban Aerial Photos / Rural Aerial Photos /
        Near-Infrared Aerial Photos / Ancillary Aerial Photos / Ancillary Near-Infrared Aerial Photos /
        Scanned Aerial Photos:
          https://github.com/linz/imagery/blob/master/docs/naming.md
        DEM / DSM / DEM Hillshade / DEM Hillshade Igor / DSM Hillshade / DSM Hillshade Igor:
          https://github.com/linz/elevation/blob/master/docs/naming.md

        Raises:
            MissingMetadataError: if required metadata is missing
            SubtypeParameterError: if category is not recognised

        Returns:
            Dataset Title
        """
        category = self.stac["linz:geospatial_category"]
        is_ancillary_event = category in ANCILLARY_CATEGORIES and bool(self.stac.get("linz:event_name"))

        temporal_extent = self.stac.get("extent", {}).get("temporal", {}).get("interval")
        if not temporal_extent:
            raise ValueError("temporal extent must be set before setting the title")
        # format optional metadata
        geographic_description = self.stac.get("linz:geographic_description")
        historic_survey_number = self.stac.get("linz:historic_survey_number")

        # format region
        region = HUMAN_READABLE_REGIONS[self.stac["linz:region"]]

        # format date
        start_year = convert_utc_to_nz_datetime(parse_rfc_3339_datetime(temporal_extent[0][0])).year
        end_year = convert_utc_to_nz_datetime(parse_rfc_3339_datetime(temporal_extent[0][1])).year
        date = f"({start_year})" if start_year == end_year else f"({start_year}-{end_year})"

        # format gsd
        gsd_str = f"{self.gsd}{GSD_UNIT}"

        # determine suffix based on its lifecycle
        lifecycle_suffix = LIFECYCLE_SUFFIXES.get(self.stac["linz:lifecycle"], "") if self.add_title_suffix else None
        event_name = self.stac.get("linz:event_name")

        if category == SCANNED_AERIAL_PHOTOS:
            if not historic_survey_number:
                raise MissingMetadataError("historic_survey_number")
            components = [
                self._combine_with_event(geographic_description or region, event_name),
                gsd_str,
                historic_survey_number,
                date,
                lifecycle_suffix,
            ]

        elif category in {*ANY_SATELLITE_IMAGERY, *ANY_ORTHO_AERIAL_PHOTOS}:
            category_title = EVENTS[category]["title"] if is_ancillary_event else DATA_CATEGORIES[category]
            components = [
                self._combine_with_event(geographic_description or region, event_name),
                gsd_str,
                category_title,
                date,
                lifecycle_suffix,
            ]

        elif category in ELEVATION:
            components = [
                self._combine_with_region(region, self._combine_with_event(geographic_description, event_name)),
                DATA_DOMAINS[self.domain],
                "LiDAR",
                gsd_str,
                DATA_CATEGORIES[category],
                date,
                lifecycle_suffix,
            ]

        elif category in HILLSHADES:
            components = [
                region,
                DATA_DOMAINS[self.domain],
                gsd_str,
                DATA_CATEGORIES[category],
            ]

        else:
            raise SubtypeParameterError(category)

        self.stac["title"] = " ".join(filter(None, components))

    @staticmethod
    def _combine_with_event(term: str | None, event_name: str | None) -> str | None:
        """Combine a location/description term with an event name, without repeating an overlapping term."""
        if not event_name:
            return term
        if not term:
            return event_name
        if term.lower() in event_name.lower():
            return event_name
        if event_name.lower() in term.lower():
            return term
        return f"{term} {event_name}"

    @staticmethod
    def _combine_with_region(region: str, term: str | None) -> str:
        """Combine a region with a location term, avoiding repeated region text."""
        if not term:
            return region
        if region.lower() in term.lower():
            return term
        return f"{region} - {term}"

    def set_description(self) -> None:
        """Set the descriptions for imagery and elevation datasets.
        Urban / Rural Aerial Photos / Near-Infrared Aerial Photos:
          [Orthophotography / Near-infrared orthophotography] within the [Region] region captured in the
          [year(s)] flying season.
        Ancillary Aerial Photos / Ancillary Near-Infrared Aerial Photos:
          [Ancillary orthophotography / Ancillary near-infrared orthophotography] within the [Region] region
          captured in the [year(s)] flying season. If published as part of a named event, the "Ancillary"
          prefix is dropped and the description reads as plain (near-infrared) orthophotography instead.
        DEM / DSM:
          [Digital Elevation Model / Digital Surface Model] within the [Region] region captured in [year(s)].
        DEM/DSM Hillshade / Hillshade Igor:
          [Digital Elevation Model / Digital Surface Model] [mono-directional / whiter multi-directional]
          hillshade derived from 1m LiDAR. Gaps filled with lower resolution elevation data (8m contour) as needed.
        Satellite Imagery / Near-Infrared Satellite Imagery / Scanned Aerial Photos:
          [Satellite imagery / Near-infrared satellite imagery / Scanned aerial imagery] within the [Region]
          region captured in [year(s)].

        If `linz:event_name` is set, the description is suffixed with
        ", published as a record of the [event name] event."

        Returns:
            Dataset Description
        """

        category = self.stac["linz:geospatial_category"]

        components = [DATA_DOMAINS[self.domain] if category in {*ELEVATION, *HILLSHADES} else None]
        if category in {*IMAGERY, *ELEVATION}:
            components.extend(self._get_imagery_description_components())
        elif category in HILLSHADES:
            components.extend(self._get_hillshade_description_components())
        else:
            raise SubtypeParameterError(category)

        desc = " ".join(filter(None, components)) + (
            f", published as a record of the {self.stac['linz:event_name']} event."
            if self.stac.get("linz:event_name")
            else "."
        )

        self.stac["description"] = desc

    def _get_imagery_description_components(self) -> list[str | None]:
        temporal_extent = self.stac.get("extent", {}).get("temporal", {}).get("interval")
        if not temporal_extent:
            raise ValueError("temporal extent must be set before setting the description")
        # format date
        start_year = convert_utc_to_nz_datetime(parse_rfc_3339_datetime(temporal_extent[0][0])).year
        end_year = convert_utc_to_nz_datetime(parse_rfc_3339_datetime(temporal_extent[0][1])).year

        category = self.stac["linz:geospatial_category"]
        is_ancillary_event = category in ANCILLARY_CATEGORIES and bool(self.stac.get("linz:event_name"))

        base_descriptions = {
            SCANNED_AERIAL_PHOTOS: "Scanned aerial imagery",
            SATELLITE_IMAGERY: "Satellite imagery",
            NEAR_INFRARED_SATELLITE_IMAGERY: "Near-infrared satellite imagery",
            ANCILLARY_AERIAL_PHOTOS: "Ancillary orthophotography",
            ANCILLARY_NEAR_INFRARED_AERIAL_PHOTOS: "Ancillary near-infrared orthophotography",
            URBAN_AERIAL_PHOTOS: "Orthophotography",
            RURAL_AERIAL_PHOTOS: "Orthophotography",
            NEAR_INFRARED_AERIAL_PHOTOS: "Near-infrared orthophotography",
            DEM: "Digital Elevation Model",
            DSM: "Digital Surface Model",
        }

        base_description = EVENTS[category]["description"] if is_ancillary_event else base_descriptions[category]

        components = [
            base_description,
            "within the",
            HUMAN_READABLE_REGIONS[self.stac["linz:region"]],
            "region captured in",
            "the" if category in ANY_ORTHO_AERIAL_PHOTOS else None,
            str(start_year) if start_year == end_year else f"{start_year}-{end_year}",
            "flying season" if category in ANY_ORTHO_AERIAL_PHOTOS else None,
        ]

        return components

    def _get_hillshade_description_components(self) -> list[str]:
        """Generates the description for hillshade datasets."""

        region = HUMAN_READABLE_REGIONS[self.stac["linz:region"]]
        category = DATA_CATEGORIES[self.stac["linz:geospatial_category"]]
        category_prefix = category[0:3]  # e.g. "dem" or "dsm"
        category_suffix = category[4:]  # e.g. "hillshade" or "hillshade-igor"
        gsd_str = f"{self.gsd}{GSD_UNIT}"

        if category_suffix == "Hillshade":
            shading_option = "GDAL’s default hillshading parameters of 315˚ azimuth and 45˚ elevation angle"
        else:
            shading_option = (
                "the -igor option in GDAL. "
                "This renders a softer hillshade that tries to minimize effects on other map features"
            )

        components = [
            "Hillshade generated from the",
            region,
            "LiDAR" if gsd_str != "8m" else "Contour-Derived",
            gsd_str,
            category_prefix,
            "using",
            shading_option,
        ]

        return components

    def add_capture_area(
        self, polygons: list[BaseGeometry], target: str, description: str, artifact_target: str = "/tmp"
    ) -> None:
        """Add the capture area of the Collection.
        If the Collection is an update of a published dataset, and the capture area has not been supplied,
        the existing capture area will be merged with the new one.
        The `href` or path of the capture-area.geojson is always set as the relative `./capture-area.geojson`

        Args:
            polygons: list of BaseGeometries
            target: location where the capture-area.geojson file will be saved
            description: description of the capture area
            artifact_target: location where the capture-area.geojson artifact file will be saved.
            This is useful for Argo Workflow in order to expose the file to the user for testing/validation purpose.
        """
        # If published dataset does not have a capture-area,
        # system should skip its creation as it may miss existing Item footprints
        if not self.publish_capture_area:
            get_log().warn(
                f"{WARN_NO_PUBLISHED_CAPTURE_AREA}: a new capture-area can't be generated.",
            )
            return
        # If published dataset with a capture-area update, merge the existing capture area with the new one
        if self.capture_area and self.capture_area.get("geometry"):
            polygons.append(shape(self.capture_area["geometry"]))
        # The GSD is measured in meters (e.g., `0.3m`)
        capture_area_document = generate_capture_area(polygons, self.gsd)
        capture_area_content: bytes = dict_to_json_bytes(capture_area_document)
        file_checksum = checksum.multihash_as_hex(capture_area_content)
        capture_area = {
            "href": f"./{CAPTURE_AREA_FILE_NAME}",
            "title": "Capture area",
            "description": description,
            "type": ContentType.GEOJSON,
            "roles": ["metadata"],
            "file:checksum": file_checksum,
            "file:size": len(capture_area_content),
        }
        self.stac.setdefault("assets", {})["capture_area"] = capture_area

        # Save `capture-area.geojson` in target
        write(
            os.path.join(target, CAPTURE_AREA_FILE_NAME),
            capture_area_content,
            content_type=ContentType.GEOJSON.value,
        )

        # Save `capture-area.geojson` as artifact for Argo UI
        write(os.path.join(artifact_target, CAPTURE_AREA_FILE_NAME), capture_area_content)

        self.stac["stac_extensions"] = self.stac.get("stac_extensions", [])

        if StacExtensions.file.value not in self.stac["stac_extensions"]:
            self.stac["stac_extensions"].append(StacExtensions.file.value)

    def add_capture_dates(self, source_directory: str) -> None:
        """Add the capture dates metadata file for the National 1m DEM dataset.
        The `href` or path of capture-dates.geojson is always set as the relative `./capture-dates.geojson`

        Args:
            source_directory: the location of the capture-dates.geojson file to be linked
        """

        capture_dates_content = read(os.path.join(source_directory, CAPTURE_DATES_FILE_NAME))
        file_checksum = checksum.multihash_as_hex(capture_dates_content)
        capture_dates = {
            "href": f"./{CAPTURE_DATES_FILE_NAME}",
            "title": "Capture dates",
            "description": "Boundaries of individual surveys or flight runs that make up the overall collection with "
            "the data collection dates, data source links and other associated metadata, such as producers and licensors, "
            "where available. Excludes nodata areas in the source data. Geometries are simplified.",
            "type": ContentType.GEOJSON,
            "roles": ["metadata"],
            "file:checksum": file_checksum,
            "file:size": len(capture_dates_content),
        }
        self.stac.setdefault("assets", {})["capture_dates"] = capture_dates

    def add_item(self, item: dict[Any, Any]) -> None:
        """Add an `Item` to the `links` of the `Collection`.
        Update the spatial and temporal extent of the `Collection` based on the `Item` bounding box and datetime.

        Args:
            item: STAC Item to add
        """
        item_self_link = next((feat for feat in item["links"] if feat["rel"] == "self"), None)
        if item_self_link:
            self.stac["links"].append(
                Link(
                    path=item_self_link["href"],
                    rel=Relation.ITEM,
                    media_type=StacMediaType.GEOJSON,
                    file_content=dict_to_json_bytes(item),
                ).stac
            )

            self.update_temporal_extent(item["properties"]["start_datetime"], item["properties"]["end_datetime"])
            self.update_spatial_extent(item["bbox"])

    def add_providers(self, providers: list[Provider]) -> None:
        """Add a list of Providers to the existing list of `providers` of the Collection.
        The provider roles are sorted alphabetically.

        Args:
            providers: a list of `Provider` objects
        """
        for p in providers:
            p["roles"] = sorted(p["roles"])
            self.stac["providers"].append(p)

    def update_spatial_extent(self, item_bbox: list[float]) -> None:
        """Update (if needed) the Collection spatial extent from a bounding box.

        Args:
            item_bbox: bounding box of an item added to the Collection
        """
        if not self.stac.get("extent", {}).get("spatial", {}).get("bbox"):
            self.update_extent(bbox=item_bbox)
            return

        bbox = self.stac["extent"]["spatial"]["bbox"][0]

        min_x = min(bbox[0], bbox[2], item_bbox[0], item_bbox[2])
        min_y = min(bbox[1], bbox[3], item_bbox[1], item_bbox[3])
        max_x = max(bbox[0], bbox[2], item_bbox[0], item_bbox[2])
        max_y = max(bbox[1], bbox[3], item_bbox[1], item_bbox[3])

        self.update_extent(bbox=[min_x, min_y, max_x, max_y])

    def update_temporal_extent(self, item_start_datetime: str, item_end_datetime: str) -> None:
        """Update (if needed) the temporal extent of the collection.

        Args:
            item_start_datetime: start date of an item added to the Collection
            item_end_datetime: end date of an item added to the Collection
        """
        if not self.stac.get("extent", {}).get("temporal", {}).get("interval"):
            self.update_extent(interval=[item_start_datetime, item_end_datetime])
            return

        interval = self.stac["extent"]["temporal"]["interval"][0]

        item_start = parse_rfc_3339_datetime(item_start_datetime)
        item_end = parse_rfc_3339_datetime(item_end_datetime)

        collection_datetimes = []
        for date in interval:
            collection_datetimes.append(parse_rfc_3339_datetime(date))

        start_datetime = min(collection_datetimes[0], collection_datetimes[1], item_start)
        end_datetime = max(collection_datetimes[0], collection_datetimes[1], item_end)

        self.update_extent(
            interval=[
                format_rfc_3339_datetime_string(start_datetime),
                format_rfc_3339_datetime_string(end_datetime),
            ]
        )

    def update_extent(self, bbox: list[float] | None = None, interval: list[str] | None = None) -> None:
        """Update an extent of the Collection whereas it's spatial or temporal.

        Args:
            bbox: bounding box. Defaults to None.
            interval: datetime interval. Defaults to None.
        """
        if "extent" not in self.stac:
            self.reset_extent()
        if bbox:
            self.stac["extent"]["spatial"]["bbox"] = [bbox]
        if interval:
            self.stac["extent"]["temporal"]["interval"] = [interval]

    def reset_extent(self) -> None:
        """Reset the spatial and temporal extents of the Collection."""
        self.stac.setdefault("extent", {}).setdefault("spatial", {})["bbox"] = None
        self.stac.setdefault("extent", {}).setdefault("temporal", {})["interval"] = None

    def get_items_stac(self) -> list[dict[str, Any]]:
        """Get the STAC Items content from the Collection links.

        Returns:
            a list of STAC Item contents
        """
        if not self.published_location:
            get_log().info("Collection is not published: no STAC Item to load.")
            return []
        items_stac = []
        for link in self.stac.get("links", []):
            if link["rel"] != Relation.ITEM:
                continue
            item_path = os.path.join(self.published_location, os.path.basename(link["href"]))
            if not exists(item_path):
                get_log().error(f"STAC Item not found: {item_path}")
                raise NoSuchFileError(item_path)
            existing_item_stac = json.loads(read(item_path))
            items_stac.append(existing_item_stac)
        return items_stac

    def reset_items(self) -> None:
        """Reset the STAC Item links list in the Collection links."""
        self.stac["links"] = [link for link in self.stac["links"] if link.get("rel") != "item"]

    def write_to(self, destination: str) -> None:
        """Write the Collection in JSON format to the specified `destination`.

        Args:
            destination: path of the destination
        """
        write(destination, dict_to_json_bytes(self.stac), content_type=ContentType.JSON.value)

    def remove_item_geometry_from_capture_area(self, item: dict[str, Any]) -> None:
        """Remove the geometry of an Item from the capture area of the Collection.
        The Item's geometry, usually tile shape (covering total or more of the footprint),
        is removed from the capture area in case of the resupplied Item footprint is not covering the former Item's footprint.

        Args:
            item: an Item to remove from the capture area
        """
        if not self.capture_area:
            get_log().warn(
                WARN_NO_PUBLISHED_CAPTURE_AREA,
            )
            return
        item_geometry = shape(item["geometry"])
        capture_area_geometry = shape(self.capture_area["geometry"])
        updated_capture_area_geometry = capture_area_geometry.difference(item_geometry)
        self.capture_area["geometry"] = json.loads(to_geojson(updated_capture_area_geometry))
