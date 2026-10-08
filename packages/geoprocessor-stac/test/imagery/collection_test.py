import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import pytest
import shapely.geometry
from geoprocessor_common.data_type import DataType
from geoprocessor_common.files.files_helper import ContentType
from geoprocessor_common.files.fs import read, write
from geoprocessor_common.geometry import GeojsonPolygon
from geoprocessor_stac.imagery.collection import WARN_NO_PUBLISHED_CAPTURE_AREA, ImageryCollection, MissingMetadataError
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.item import ImageryItem, STACAsset
from geoprocessor_stac.imagery.provider import ProviderRole
from geoprocessor_stac.testing.generators import any_stac_processing
from geoprocessor_stac.testing.helpers import any_epoch_datetime_string, fake_linz_slug
from geoprocessor_stac.util.STAC_VERSION import STAC_VERSION
from geoprocessor_stac.util.stac_extensions import StacExtensions
from pytest import CaptureFixture, mark, param
from pytest_subtests import SubTests

# pylint: disable=too-many-lines


def test_metadata_initialised(fake_collection_context: CollectionContext, subtests: SubTests) -> None:
    fake_collection_context.event_name = "Cyclone Gabrielle"
    fake_collection_context.geographic_description = "Hawke's Bay Cyclone Gabrielle"
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())

    with subtests.test():
        assert collection.stac["id"]

    with subtests.test():
        assert collection.stac["linz:region"] == "hawkes-bay"

    with subtests.test():
        assert collection.stac["linz:geographic_description"] == "Hawke's Bay Cyclone Gabrielle"

    with subtests.test():
        assert collection.stac["linz:event_name"] == "Cyclone Gabrielle"

    with subtests.test():
        assert collection.stac["linz:lifecycle"] == "completed"

    with subtests.test():
        assert collection.stac["linz:geospatial_category"] == "rural-aerial-photos"

    with subtests.test():
        assert collection.stac["linz:security_classification"] == "unclassified"

    with subtests.test():
        assert collection.stac["gsd"] == 0.3


# `set_title()` TESTS


@mark.parametrize(
    "context,expected_title,expected_description",
    [
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Rural Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Aerial Imagery",
        ),
        param(
            CollectionContext(
                category="dem",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay LiDAR 0.3m DEM (2023)",
            "Digital Elevation Model within the Hawke's Bay region captured in 2023.",
            id="DEM",
        ),
        param(
            CollectionContext(
                category="dsm",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay LiDAR 0.3m DSM (2023)",
            "Digital Surface Model within the Hawke's Bay region captured in 2023.",
            id="DSM",
        ),
        param(
            CollectionContext(
                category="satellite-imagery",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Satellite Imagery (2023)",
            "Satellite imagery within the Hawke's Bay region captured in 2023.",
            id="Satellite",
        ),
        param(
            CollectionContext(
                category="near-infrared-satellite-imagery",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Near-Infrared Satellite Imagery (2023)",
            "Near-infrared satellite imagery within the Hawke's Bay region captured in 2023.",
            id="Near-Infrared Satellite",
        ),
        param(
            CollectionContext(
                category="near-infrared-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Near-Infrared Aerial Photos (2023)",
            "Near-infrared orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Near-Infrared Aerial",
        ),
        param(
            CollectionContext(
                category="scanned-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                historic_survey_number="SNC8844",
            ),
            "Hawke's Bay 0.3m SNC8844 (2023)",
            "Scanned aerial imagery within the Hawke's Bay region captured in 2023.",
            id="Historical imagery",
        ),
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="Ponsonby",
            ),
            "Ponsonby 0.3m Rural Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Geographic description",
        ),
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="Hawke's Bay Cyclone Gabrielle",
                event_name="Cyclone Gabrielle",
            ),
            "Hawke's Bay Cyclone Gabrielle 0.3m Rural Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season, \
published as a record of the Cyclone Gabrielle event.",
            id="Event Imagery",
        ),
        param(
            CollectionContext(
                category="dsm",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="Hawke's Bay Cyclone Gabrielle",
                event_name="Cyclone Gabrielle",
            ),
            "Hawke's Bay Cyclone Gabrielle LiDAR 0.3m DSM (2023)",
            "Digital Surface Model within the Hawke's Bay region captured in 2023, "
            "published as a record of the Cyclone Gabrielle event.",
            id="Event Elevation",
        ),
        param(
            CollectionContext(
                category="satellite-imagery",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="Hawke's Bay Cyclone Gabrielle",
                event_name="Cyclone Gabrielle",
            ),
            "Hawke's Bay Cyclone Gabrielle 0.3m Satellite Imagery (2023)",
            "Satellite imagery within the Hawke's Bay region captured in 2023, "
            "published as a record of the Cyclone Gabrielle event.",
            id="Event Satellite",
        ),
        param(
            CollectionContext(
                category="dsm",
                domain="land",
                region="hawkes-bay",
                lifecycle="preview",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay LiDAR 0.3m DSM (2023) - Preview",
            "Digital Surface Model within the Hawke's Bay region captured in 2023.",
            id="Preview DSM",
        ),
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="ongoing",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Rural Aerial Photos (2023) - Draft",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Draft",
        ),
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="ongoing",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                add_title_suffix=False,
            ),
            "Hawke's Bay 0.3m Rural Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="No title suffix",
        ),
        param(
            CollectionContext(
                category="rural-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "Hawke's Bay 0.3m Rural Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Empty optional",
        ),
        param(
            CollectionContext(
                category="dem-hillshade",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("8"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 8m DEM Hillshade",
            "Hillshade generated from the New Zealand Contour-Derived 8m DEM using GDAL’s "
            "default hillshading parameters of 315˚ azimuth and 45˚ elevation angle.",
            id="8m DEM Hillshade",
        ),
        param(
            CollectionContext(
                category="dem-hillshade-igor",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("8"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 8m DEM Hillshade - Igor",
            "Hillshade generated from the New Zealand Contour-Derived 8m DEM using the -igor option in GDAL. "
            "This renders a softer hillshade that tries to minimize effects on other map features.",
            id="8m DEM Hillshade Igor",
        ),
        param(
            CollectionContext(
                category="dsm-hillshade",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 1m DSM Hillshade",
            "Hillshade generated from the New Zealand LiDAR 1m DSM using GDAL’s "
            "default hillshading parameters of 315˚ azimuth and 45˚ elevation angle.",
            id="1m DSM Hillshade",
        ),
        param(
            CollectionContext(
                category="dsm-hillshade-igor",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 1m DSM Hillshade - Igor",
            "Hillshade generated from the New Zealand LiDAR 1m DSM using the -igor option in GDAL. "
            "This renders a softer hillshade that tries to minimize effects on other map features.",
            id="1m DSM Hillshade Igor",
        ),
        param(
            CollectionContext(
                category="dem-hillshade",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 1m DEM Hillshade",
            "Hillshade generated from the New Zealand LiDAR 1m DEM "
            "using GDAL’s default hillshading parameters of 315˚ azimuth and 45˚ elevation angle.",
            id="1m DEM Hillshade",
        ),
        param(
            CollectionContext(
                category="dem-hillshade-igor",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 1m DEM Hillshade - Igor",
            "Hillshade generated from the New Zealand LiDAR 1m DEM "
            "using the -igor option in GDAL. This renders a softer hillshade that tries to "
            "minimize effects on other map features.",
            id="1m DEM Hillshade Igor",
        ),
        param(
            CollectionContext(
                category="dem-hillshade",
                domain="land",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.25"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand 0.25m DEM Hillshade",
            "Hillshade generated from the New Zealand LiDAR 0.25m DEM "
            "using GDAL’s default hillshading parameters of 315˚ azimuth and 45˚ elevation angle.",
            id="0.25m DEM Hillshade",
        ),
        param(
            CollectionContext(
                category="dem",
                domain="coastal",
                region="bay-of-plenty",
                geographic_description="Tauranga",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Bay of Plenty - Tauranga Coastal LiDAR 1m DEM (2023)",
            "Coastal Digital Elevation Model within the Bay of Plenty region captured in 2023.",
            id="Coastal DEM",
        ),
        param(
            CollectionContext(
                category="dem-hillshade",
                domain="coastal",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand Coastal 1m DEM Hillshade",
            "Coastal Hillshade generated from the New Zealand LiDAR 1m DEM "
            "using GDAL’s default hillshading parameters of 315˚ azimuth and 45˚ elevation angle.",
            id="Coastal 1m DEM Hillshade",
        ),
        param(
            CollectionContext(
                category="dem-hillshade-igor",
                domain="coastal",
                region="new-zealand",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("1"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                geographic_description="",
                event_name="",
            ),
            "New Zealand Coastal 1m DEM Hillshade - Igor",
            "Coastal Hillshade generated from the New Zealand LiDAR 1m DEM "
            "using the -igor option in GDAL. This renders a softer hillshade that tries to "
            "minimize effects on other map features.",
            id="Coastal 1m DEM Hillshade Igor",
        ),
        param(
            CollectionContext(
                category="ancillary-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Ancillary Aerial Photos (2023)",
            "Ancillary orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Ancillary Aerial Photos",
        ),
        param(
            CollectionContext(
                category="ancillary-near-infrared-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
            ),
            "Hawke's Bay 0.3m Ancillary Near-Infrared Aerial Photos (2023)",
            "Ancillary near-infrared orthophotography within the Hawke's Bay region captured in the 2023 flying season.",
            id="Ancillary Near-Infrared Aerial Photos",
        ),
        param(
            CollectionContext(
                category="ancillary-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                event_name="Cyclone Gabrielle",
            ),
            "Hawke's Bay Cyclone Gabrielle 0.3m Aerial Photos (2023)",
            "Orthophotography within the Hawke's Bay region captured in the 2023 flying season, "
            "published as a record of the Cyclone Gabrielle event.",
            id="Ancillary Aerial Photos with Event",
        ),
        param(
            CollectionContext(
                category="ancillary-near-infrared-aerial-photos",
                domain="land",
                region="hawkes-bay",
                lifecycle="completed",
                linz_slug=fake_linz_slug(),
                gsd=Decimal("0.3"),
                data_type=DataType.UINT8,
                collection_id="a-random-collection-id",
                event_name="Cyclone Gabrielle",
            ),
            "Hawke's Bay Cyclone Gabrielle 0.3m Near-Infrared Aerial Photos (2023)",
            "Near-infrared orthophotography within the Hawke's Bay region captured in the 2023 flying season, "
            "published as a record of the Cyclone Gabrielle event.",
            id="Ancillary Near-Infrared Aerial Photos with Event",
        ),
    ],
)
def test_set_title_set_description(
    context: CollectionContext,
    expected_title: str,
    expected_description: str,
    subtests: SubTests,
) -> None:
    collection = ImageryCollection(context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.stac.setdefault("extent", {}).setdefault("temporal", {})["interval"] = [
        ["2022-12-31T11:00:00Z", "2023-12-30T11:00:00Z"]
    ]

    with subtests.test(msg="title"):
        collection.set_title()
        assert collection.stac["title"] == expected_title
    with subtests.test(msg="description"):
        collection.set_description()
        assert collection.stac["description"] == expected_description


def test_set_gsd(
    fake_collection_context: CollectionContext,
) -> None:
    fake_collection_context.gsd = Decimal("123.456")
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    assert collection.stac["gsd"] == 123.456


def test_set_title_set_description_long_date(fake_collection_context: CollectionContext, subtests: SubTests) -> None:
    fake_collection_context.category = "rural-aerial-photos"
    fake_collection_context.historic_survey_number = None
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.stac.setdefault("extent", {}).setdefault("temporal", {})["interval"] = [
        ["2022-12-31T11:00:00Z", "2024-12-30T11:00:00Z"]
    ]

    with subtests.test(msg="title"):
        collection.set_title()
        assert collection.stac["title"] == "Hawke's Bay 0.3m Rural Aerial Photos (2023-2024)"
    with subtests.test(msg="description"):
        collection.set_description()
        assert (
            collection.stac["description"]
            == "Orthophotography within the Hawke's Bay region captured in the 2023-2024 flying season."
        )


def test_get_title_historic_imagery_with_missing_number(fake_collection_context: CollectionContext) -> None:
    fake_collection_context.category = "scanned-aerial-photos"
    fake_collection_context.historic_survey_number = None
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.stac.setdefault("extent", {}).setdefault("temporal", {})["interval"] = [
        ["2022-12-31T11:00:00Z", "2023-12-30T11:00:00Z"]
    ]
    with pytest.raises(MissingMetadataError) as excinfo:
        collection.set_title()

    assert "historic_survey_number" in str(excinfo.value)


def test_id_parsed_on_init(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    assert collection.stac["id"] == fake_collection_context.collection_id


def test_bbox_updated_from_none(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    bbox = [1799667.5, 5814986.0, 1800422.5, 5815977.0]
    collection.update_spatial_extent(bbox)
    assert collection.stac["extent"]["spatial"]["bbox"] == [bbox]


def test_bbox_updated_from_existing(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    # init bbox
    bbox = [174.889641, -41.217532, 174.902344, -41.203521]
    collection.update_spatial_extent(bbox)
    # update bbox
    bbox = [174.917643, -41.211157, 174.922965, -41.205490]
    collection.update_spatial_extent(bbox)

    assert collection.stac["extent"]["spatial"]["bbox"] == [[174.889641, -41.217532, 174.922965, -41.203521]]


def test_interval_updated_from_none(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    start_datetime = "2021-01-27T00:00:00Z"
    end_datetime = "2021-01-27T00:00:00Z"
    collection.update_temporal_extent(start_datetime, end_datetime)
    assert collection.stac["extent"]["temporal"]["interval"] == [[start_datetime, end_datetime]]


def test_interval_updated_from_existing(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    # init interval
    start_datetime = "2021-01-27T00:00:00Z"
    end_datetime = "2021-01-27T00:00:00Z"
    collection.update_temporal_extent(start_datetime, end_datetime)
    # update interval
    start_datetime = "2021-02-01T00:00:00Z"
    end_datetime = "2021-02-20T00:00:00Z"
    collection.update_temporal_extent(start_datetime, end_datetime)

    assert collection.stac["extent"]["temporal"]["interval"] == [["2021-01-27T00:00:00Z", "2021-02-20T00:00:00Z"]]


def test_add_item(fake_collection_context: CollectionContext, subtests: SubTests) -> None:
    now_string = any_epoch_datetime_string()
    collection = ImageryCollection(fake_collection_context, now_string, now_string)
    asset_datetimes = {
        "created": any_epoch_datetime_string(),
        "updated": any_epoch_datetime_string(),
    }
    item = ImageryItem(
        "BR34_5000_0304",
        STACAsset(
            **{
                "href": "any href",
                "file:checksum": "any checksum",
                "created": asset_datetimes["created"],
                "updated": asset_datetimes["updated"],
            }
        ),
        any_stac_processing(),
    )
    geometry: GeojsonPolygon = {
        "type": "Polygon",
        "coordinates": [[[1799667.5, 5815977.0], [1800422.5, 5815977.0], [1800422.5, 5814986.0], [1799667.5, 5814986.0]]],
    }
    bbox = (1799667.5, 5814986.0, 1800422.5, 5815977.0)
    start_datetime = "2021-01-27T00:00:00Z"
    end_datetime = "2021-01-27T00:00:00Z"
    item.update_spatial(geometry, bbox)
    item.update_datetime(start_datetime, end_datetime)

    collection.add_item(item.stac)

    links = collection.stac["links"].copy()

    with subtests.test(msg="File checksum heuristic"):
        # The checksum changes based on the contents
        assert links[1].pop("file:checksum").startswith("1220")

    with subtests.test(msg="Main links content"):
        assert [
            {"href": "./collection.json", "rel": "self", "type": "application/json"},
            {"rel": "item", "href": "./BR34_5000_0304.json", "type": "application/geo+json"},
        ] == links

    with subtests.test():
        assert collection.stac["extent"]["temporal"]["interval"] == [[start_datetime, end_datetime]]

    with subtests.test():
        assert collection.stac["extent"]["spatial"]["bbox"] == [bbox]

    for property_name in ["created", "updated"]:
        with subtests.test(msg=f"collection {property_name}"):
            assert collection.stac[property_name] == now_string

        with subtests.test(msg=f"item properties.{property_name}"):
            assert item.stac["properties"][property_name] == asset_datetimes[property_name]

        with subtests.test(msg=f"item assets.visual.{property_name}"):
            assert item.stac["assets"]["visual"][property_name] == asset_datetimes[property_name]


def test_write_collection(fake_collection_context: CollectionContext) -> None:
    target = mkdtemp()
    collectionObj = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection_target = os.path.join(target, "collection.json")
    collectionObj.write_to(collection_target)
    collection = json.loads(read(collection_target))
    rmtree(target)

    assert collection["title"] == collectionObj.stac["title"]
    assert collection["gsd"] == collectionObj.stac["gsd"]


def test_write_collection_special_chars(fake_collection_context: CollectionContext) -> None:
    target = mkdtemp()
    title = "Manawatū-Whanganui"
    collectionObj = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collectionObj.stac["title"] = title
    collection_target = os.path.join(target, "collection.json")
    collectionObj.write_to(collection_target)
    collection = json.loads(read(collection_target))
    rmtree(target)

    assert collection["title"] == title


def test_capture_area_added(fake_collection_context: CollectionContext, subtests: SubTests) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    file_name = "capture-area.geojson"

    polygons = []
    polygons.append(
        shapely.geometry.shape(
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [178.259659571653, -38.40831927359251],
                            [178.26012930415902, -38.41478071250544],
                            [178.26560430668172, -38.41453416326152],
                            [178.26513409076952, -38.40807278109057],
                            [178.259659571653, -38.40831927359251],
                        ]
                    ]
                ],
            }
        )
    )
    polygons.append(
        shapely.geometry.shape(
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [178.25418498567294, -38.40856551170436],
                            [178.25465423474975, -38.41502700730107],
                            [178.26012930415902, -38.41478071250544],
                            [178.259659571653, -38.40831927359251],
                            [178.25418498567294, -38.40856551170436],
                        ]
                    ]
                ],
            }
        )
    )
    with tempfile.TemporaryDirectory() as tmp_path:
        artifact_path = os.path.join(tmp_path, "tmp")
        capture_area_description = "test description"
        collection.add_capture_area(polygons, tmp_path, capture_area_description, artifact_path)
        file_target = os.path.join(tmp_path, file_name)
        file_artifact = os.path.join(artifact_path, file_name)
        with subtests.test():
            assert os.path.isfile(file_target)

        with subtests.test():
            assert os.path.isfile(file_artifact)

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["href"] == f"./{file_name}"

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["title"] == "Capture area"

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["description"] == capture_area_description

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["type"] == "application/geo+json"

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["roles"] == ["metadata"]

    with subtests.test():
        assert StacExtensions.file.value in collection.stac["stac_extensions"]

    with subtests.test():
        assert "file:checksum" in collection.stac["assets"]["capture_area"]

    with subtests.test():
        assert (
            collection.stac["assets"]["capture_area"]["file:checksum"]
            == "122024fd55ea5f9812e80748ee78055893ad7bddbe2b5101dec1cc1b949edc295f51"
        )

    with subtests.test():
        assert "file:size" in collection.stac["assets"]["capture_area"]

    with subtests.test():
        assert collection.stac["assets"]["capture_area"]["file:size"] == 239


def test_supplied_capture_area_with_existing_capture_area(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.capture_area = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [175.33070754, -38.23087459],
                    [175.34114274, -38.55504694],
                    [175.61631903, -38.54921714],
                    [175.60466049, -38.22511173],
                    [175.33070754, -38.23087459],
                ]
            ],
        },
        "type": "Feature",
        "properties": {},
    }

    polygons = []
    polygons.append(
        shapely.geometry.shape(
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [175.0566807, -38.23599854],
                            [175.06589127, -38.56023041],
                            [175.34114274, -38.55504694],
                            [175.33070754, -38.23087459],
                            [175.0566807, -38.23599854],
                        ]
                    ]
                ],
            }
        )
    )
    with tempfile.TemporaryDirectory() as tmp_path:
        artifact_path = os.path.join(tmp_path, "tmp")
        collection.add_capture_area(polygons, tmp_path, "", artifact_path)
        capture_area_file = json.loads(read(f"{tmp_path}/capture-area.geojson"))

    assert capture_area_file["geometry"] == {
        "type": "Polygon",
        "coordinates": [
            [
                [175.33070754, -38.23087459],
                [175.0566807, -38.23599854],
                [175.06589127, -38.56023041],
                [175.34114274, -38.55504694],
                [175.61631903, -38.54921714],
                [175.60466049, -38.22511173],
                [175.33070754, -38.23087459],
            ]
        ],
    }


def test_should_not_add_capture_area(
    fake_collection_context: CollectionContext,
    subtests: SubTests,
    capsys: CaptureFixture[str],
) -> None:
    """Verify that if an already published dataset does not have a capture-area
    (older datasets haven't been processed with this feature),
    the capture-area is not created as it may miss existing Item footprints.
    """
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    file_name = "capture-area.geojson"

    polygons = [
        shapely.geometry.shape(
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [178.259659571653, -38.40831927359251],
                            [178.26012930415902, -38.41478071250544],
                            [178.26560430668172, -38.41453416326152],
                            [178.26513409076952, -38.40807278109057],
                            [178.259659571653, -38.40831927359251],
                        ]
                    ]
                ],
            }
        )
    ]

    with tempfile.TemporaryDirectory() as tmp_path:
        artifact_path = os.path.join(tmp_path, "tmp")
        collection.published_location = "s3://bucket/dataset/collection.json"
        collection.publish_capture_area = False
        collection.add_capture_area(polygons, tmp_path, "", artifact_path)
        logs = json.loads(capsys.readouterr().out)
        assert WARN_NO_PUBLISHED_CAPTURE_AREA in logs["msg"]
        file_target = os.path.join(tmp_path, file_name)
        file_artifact = os.path.join(artifact_path, file_name)
        with subtests.test():
            assert not os.path.isfile(file_target)

        with subtests.test():
            assert not os.path.isfile(file_artifact)

    with subtests.test():
        assert "capture_area" not in collection.stac.get("assets", {})


def test_event_name_is_present(fake_collection_context: CollectionContext) -> None:
    fake_collection_context.event_name = "Cyclone Gabrielle"
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    assert "Cyclone Gabrielle" == collection.stac["linz:event_name"]


def test_geographic_description_is_present(fake_collection_context: CollectionContext) -> None:
    fake_collection_context.geographic_description = "Hawke's Bay Cyclone Gabrielle"
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    assert "Hawke's Bay Cyclone Gabrielle" == collection.stac["linz:geographic_description"]


def test_linz_slug_is_present(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    assert fake_collection_context.linz_slug == collection.stac["linz:slug"]


def test_capture_dates_added(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    with tempfile.TemporaryDirectory() as tmp_path:
        write(os.path.join(tmp_path, "capture-dates.geojson"), b"")
        collection.add_capture_dates(tmp_path)
    assert collection.stac["assets"]["capture_dates"] == {
        "href": "./capture-dates.geojson",
        "title": "Capture dates",
        "description": "Boundaries of individual surveys or flight runs that make up the overall collection with the "
        "data collection dates, data source links and other associated metadata, such as producers and licensors, "
        "where available. Excludes nodata areas in the source data. Geometries are simplified.",
        "type": ContentType.GEOJSON,
        "roles": ["metadata"],
        "file:checksum": "1220e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "file:size": 0,
    }


def test_reset_extent(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.update_temporal_extent("2021-01-27T00:00:00Z", "2021-01-27T00:00:00Z")
    collection.update_spatial_extent([1799667.5, 5814986.0, 1800422.5, 5815977.0])
    collection.reset_extent()
    assert collection.stac["extent"]["spatial"]["bbox"] is None
    assert collection.stac["extent"]["temporal"]["interval"] is None


def test_get_items_from_collection(tmp_path: Path, fake_collection_context: CollectionContext) -> None:
    created_datetime = any_epoch_datetime_string()

    existing_item_path = tmp_path / "item_a.json"
    existing_item = {
        "type": "Feature",
        "id": "item_a",
    }
    existing_item_path.write_text(json.dumps(existing_item))
    existing_item_link = {
        "rel": "item",
        "href": "./item_a.json",
        "type": "application/geo+json",
    }

    existing_collection_content = {
        "type": "Collection",
        "stac_version": STAC_VERSION,
        "id": fake_collection_context.collection_id,
        "linz:slug": fake_collection_context.linz_slug,
        "links": [
            {
                "rel": "root",
                "href": "https://nz-imagery.s3.ap-southeast-2.amazonaws.com/catalog.json",
                "type": "application/json",
            },
            {"rel": "self", "href": "./collection.json", "type": "application/json"},
            existing_item_link,
        ],
        "created": created_datetime,
        "updated": created_datetime,
    }
    existing_collection_path = tmp_path / "collection.json"
    existing_collection_path.write_text(json.dumps(existing_collection_content))

    collection = ImageryCollection.from_file(existing_collection_path.as_posix())
    collection_items = collection.get_items_stac()
    assert len(collection_items) == 1
    assert collection_items[0] == existing_item


def test_reset_items_in_collection(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    links = [
        {"rel": "item", "href": "./item_a.json"},
        {"rel": "item", "href": "./item_b.json"},
        {"rel": "item", "href": "./item_c.json"},
    ]
    collection.stac["links"] = links
    collection.reset_items()
    assert [link for link in collection.stac["links"] if link.get("rel") == "item"] == []


def test_remove_item_geometry_from_capture_area(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.capture_area = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [174.8593132, -41.1583333],
                    [174.5733776, -41.1625951],
                    [174.5811963, -41.4867503],
                    [174.8685509, -41.4824399],
                    [175.1558379, -41.4774122],
                    [175.1451823, -41.1533623],
                    [174.8593132, -41.1583333],
                ]
            ],
        },
        "type": "Feature",
        "properties": {},
    }

    item_to_remove = {
        "type": "Feature",
        "id": "item_a",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [174.5733776, -41.1625951],
                    [174.5811963, -41.4867503],
                    [174.8685509, -41.4824399],
                    [174.8593132, -41.1583333],
                    [174.5733776, -41.1625951],
                ]
            ],
        },
    }

    collection.remove_item_geometry_from_capture_area(item_to_remove)

    assert collection.capture_area["geometry"] == {
        "coordinates": [
            [
                [175.1451823, -41.1533623],
                [175.1558379, -41.4774122],
                [174.8685509, -41.4824399],
                [174.8593132, -41.1583333],
                [175.1451823, -41.1533623],
            ]
        ],
        "type": "Polygon",
    }


def test_add_providers_roles_order_sorted(fake_collection_context: CollectionContext) -> None:
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    collection.add_providers([{"name": "Maxar", "roles": [ProviderRole.PRODUCER, ProviderRole.LICENSOR]}])
    assert {"name": "Maxar", "roles": [ProviderRole.LICENSOR, ProviderRole.PRODUCER]} in collection.stac["providers"]


def test_update_metadata(fake_collection_context: CollectionContext, subtests: SubTests) -> None:
    fake_collection_context.event_name = "Cyclone Gabrielle"
    fake_collection_context.geographic_description = "Hawke's Bay Cyclone Gabrielle"
    collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    old_slug = collection.stac["linz:slug"]
    new_metadata = CollectionContext(
        category="rural-aerial-photos",
        domain="land",
        region="hawkes-bay",
        gsd=Decimal("0.3"),
        data_type=DataType.UINT8,
        lifecycle="ongoing",
        linz_slug=fake_linz_slug(),
        collection_id="a-random-collection-id",
        producers=["Maxar"],
        licensors=["Maxar"],
    )
    collection.update(new_metadata, "2025-01-01T00:00:00Z")
    collection.stac.setdefault("extent", {}).setdefault("temporal", {})["interval"] = [
        ["2024-12-31T11:00:00Z", "2025-12-30T11:00:00Z"]
    ]
    collection.set_title()
    collection.set_description()
    with subtests.test(msg="Metadata should be updated"):
        assert collection.stac["linz:lifecycle"] == "ongoing"
        assert collection.stac["providers"] == [
            {"name": "Toitū Te Whenua Land Information New Zealand", "roles": [ProviderRole.HOST, ProviderRole.PROCESSOR]},
            {"name": "Maxar", "roles": [ProviderRole.LICENSOR, ProviderRole.PRODUCER]},
        ]
        assert collection.stac["title"] == "Hawke's Bay 0.3m Rural Aerial Photos (2025) - Draft"
        assert (
            collection.stac["description"]
            == "Orthophotography within the Hawke's Bay region captured in the 2025 flying season."
        )
        assert collection.stac["linz:security_classification"] == "unclassified"
        assert collection.stac["gsd"] == 0.3

    with subtests.test(msg="Slug should remain the same"):
        assert collection.stac["linz:slug"] == old_slug
    with subtests.test(msg="Optional metadata should be removed if not passed"):
        assert collection.stac.get("linz:event_name") is None
        assert collection.stac.get("linz:geographic_description") is None


def test_data_type_uint8_omitted_from_stac() -> None:
    """Verify that uint8 is omitted from STAC JSON output, as only the higher bit depths are recorded."""
    context = CollectionContext(
        category="rural-aerial-photos",
        domain="land",
        region="hawkes-bay",
        gsd=Decimal("0.3"),
        data_type=DataType.UINT8,
        lifecycle="completed",
        linz_slug=fake_linz_slug(),
    )
    collection = ImageryCollection(context, any_epoch_datetime_string(), any_epoch_datetime_string())

    assert "data_type" not in collection.stac, "uint8 should be omitted from STAC"


def test_data_type_uint16_included_in_stac() -> None:
    """Verify that uint16 is included in STAC JSON output for near-infrared imagery."""
    context = CollectionContext(
        category="near-infrared-aerial-photos",
        domain="land",
        region="hawkes-bay",
        gsd=Decimal("1.0"),
        data_type=DataType.UINT16,
        lifecycle="completed",
        linz_slug=fake_linz_slug(),
    )
    collection = ImageryCollection(context, any_epoch_datetime_string(), any_epoch_datetime_string())

    assert collection.stac["data_type"] == "uint16", "uint16 should be included in STAC JSON"


def test_data_type_float32_omitted_from_stac() -> None:
    """Verify that float32 is omitted from STAC JSON output, DEM collections do not record it"""
    context = CollectionContext(
        category="dem",
        domain="land",
        region="hawkes-bay",
        gsd=Decimal("1.0"),
        data_type=DataType.FLOAT32,
        lifecycle="completed",
        linz_slug=fake_linz_slug(),
    )
    collection = ImageryCollection(context, any_epoch_datetime_string(), any_epoch_datetime_string())

    assert "data_type" not in collection.stac, "float32 should be omitted from STAC"


def test_data_type_uint16_omitted_from_stac_for_rgb() -> None:
    """Verify that uint16 is omitted from STAC JSON output for RGB imagery, as it is the input data type"""
    context = CollectionContext(
        category="rural-aerial-photos",
        domain="land",
        region="hawkes-bay",
        gsd=Decimal("0.3"),
        data_type=DataType.UINT16,
        lifecycle="completed",
        linz_slug=fake_linz_slug(),
    )
    collection = ImageryCollection(context, any_epoch_datetime_string(), any_epoch_datetime_string())

    assert "data_type" not in collection.stac, "uint16 should be omitted from STAC for RGB imagery"
