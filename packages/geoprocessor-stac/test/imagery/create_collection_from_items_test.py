import json
from dataclasses import replace
from os import environ
from typing import TYPE_CHECKING, Any, Iterator
from unittest.mock import patch

import pytest
from boto3 import client
from geoprocessor_common.files.fs_s3 import write
from geoprocessor_common.geometry import GeojsonPolygon
from geoprocessor_stac.imagery.collection import ImageryCollection
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.create_collection_from_items import NoItemsError, create_collection_from_items
from geoprocessor_stac.imagery.item import ImageryItem
from geoprocessor_stac.json_codec import dict_to_json_bytes
from geoprocessor_stac.testing.generators import any_stac_asset, any_stac_processing
from geoprocessor_stac.testing.helpers import any_epoch_datetime_string
from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests
from shapely.geometry import shape

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
else:
    S3Client = GetObjectOutputTypeDef = dict

URI = "s3://stacfiles/"
CONCURRENCY = 25


@pytest.fixture(name="item", autouse=True)
def setup() -> Iterator[ImageryItem]:
    # Create mocked STAC Item
    with patch.dict(environ, {"GIT_HASH": "any Git hash", "GIT_VERSION": "any Git version"}):
        item = ImageryItem("123", any_stac_asset(), any_stac_processing())
    geometry: GeojsonPolygon = {
        "type": "Polygon",
        "coordinates": [[[1799667.5, 5815977.0], [1800422.5, 5815977.0], [1800422.5, 5814986.0], [1799667.5, 5814986.0]]],
    }
    bbox = (1799667.5, 5814986.0, 1800422.5, 5815977.0)
    start_datetime = "2021-01-27T11:00:00Z"
    end_datetime = "2021-01-27T11:00:00Z"
    item.update_spatial(geometry, bbox)
    item.update_datetime(start_datetime, end_datetime)
    yield item


@mock_aws
def test_should_create_collection_file(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    # Mock AWS S3
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc"),
        uri=URI,
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
    )

    # Verify collection.json has been created
    resp = s3_client.get_object(Bucket="stacfiles", Key="collection.json")
    assert '"type": "Collection"' in resp["Body"].read().decode("utf-8")


@mock_aws
def test_should_create_coastal_collection_file(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    # Mock AWS S3
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc", category="dem", domain="coastal"),
        uri=URI,
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
    )

    # Verify collection.json has been created with "Coastal" information
    resp = s3_client.get_object(Bucket="stacfiles", Key="collection.json")
    assert "Coastal" in resp["Body"].read().decode("utf-8")


@mock_aws
def test_should_fail_if_collection_has_no_matching_items(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str], subtests: SubTests
) -> None:
    # Mock AWS S3
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item_collection_id = "abc"
    item.add_collection(item_collection_id)
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))
    # collection ID is `def` <> `abc`
    collection_id = "def"

    with raises(NoItemsError):
        create_collection_from_items(
            collection_context=replace(fake_collection_context, collection_id=collection_id),
            uri=URI,
            concurrency=CONCURRENCY,
            current_datetime=any_epoch_datetime_string(),
        )

    logs = capsys.readouterr().out

    with subtests.test(msg="Collection IDs do not match"):
        assert f"skipping: {item_collection_id} and {collection_id} do not match" in logs

    assert f"Collection {collection_id} has no items" in logs


@mock_aws
def test_should_not_add_if_not_item(fake_collection_context: CollectionContext, capsys: CaptureFixture[str]) -> None:
    # Mock AWS S3
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    # Create mocked "existing" Collection
    existing_collection = ImageryCollection(fake_collection_context, any_epoch_datetime_string(), any_epoch_datetime_string())
    write("s3://stacfiles/collection.json", dict_to_json_bytes(existing_collection.stac))
    assert fake_collection_context.collection_id is not None

    with raises(NoItemsError):
        create_collection_from_items(
            collection_context=fake_collection_context,
            uri=URI,
            concurrency=CONCURRENCY,
            current_datetime=any_epoch_datetime_string(),
        )

    assert "skipping: not a STAC item" in capsys.readouterr().out


@mock_aws
def test_should_fail_if_uri_has_no_files(fake_collection_context: CollectionContext) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")

    with raises(NoItemsError):
        create_collection_from_items(
            collection_context=fake_collection_context,
            uri=URI,
            concurrency=CONCURRENCY,
            current_datetime=any_epoch_datetime_string(),
        )


@mock_aws
def test_should_read_items_in_subdirectories_of_uri(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/flat/sub/item.json", dict_to_json_bytes(item.stac))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc"),
        uri="s3://stacfiles/flat",
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
    )

    resp = s3_client.get_object(Bucket="stacfiles", Key="flat/collection.json")
    assert '"type": "Collection"' in resp["Body"].read().decode("utf-8")


@mock_aws
def test_should_determine_dates_from_items(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    # Mock AWS S3
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item_a.json", dict_to_json_bytes(item.stac))
    item.stac["properties"]["start_datetime"] = "2022-04-12T12:00:00Z"
    item.stac["properties"]["end_datetime"] = "2022-04-12T12:00:00Z"
    write("s3://stacfiles/item_b.json", dict_to_json_bytes(item.stac))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc"),
        uri=URI,
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
    )

    # Verify collection.json has been created
    resp = s3_client.get_object(Bucket="stacfiles", Key="collection.json")
    assert "(2021-2022)" in resp["Body"].read().decode("utf-8")


@mock_aws
def test_should_accept_simplified_capture_area_flag(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))

    footprint = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [178.259659571653, -38.40831927359251],
                            [178.26012930415902, -38.41478071250544],
                            [178.26560430668172, -38.41453416326152],
                            [178.26513409076952, -38.40807278109057],
                            [178.259659571653, -38.40831927359251],
                        ]
                    ],
                },
            }
        ],
    }
    write("s3://stacfiles/item_footprint.geojson", dict_to_json_bytes(footprint))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc"),
        uri=URI,
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
        simplified_capture_area=True,
    )

    resp = s3_client.get_object(Bucket="stacfiles", Key="collection.json")
    collection_content = resp["Body"].read().decode("utf-8")
    collection_json = json.loads(collection_content)

    assert "capture_area" in collection_json["assets"]
    expected_description = (
        "Boundary of the total capture area for this collection. "
        "May include some areas of nodata where capture was attempted but unsuccessful. "
        "Geometries are simplified."
    )
    assert collection_json["assets"]["capture_area"]["description"] == expected_description


@mock_aws
def test_should_use_capture_dates_for_capture_area(item: ImageryItem, fake_collection_context: CollectionContext) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))

    capture_dates: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [173.08592083, -41.23816732],
                            [173.08596333, -41.2705955],
                            [173.11461773, -41.27057054],
                            [173.11456106, -41.23814238],
                            [173.08592083, -41.23816732],
                        ]
                    ],
                },
            }
        ],
    }
    write("s3://stacfiles/capture-dates.geojson", dict_to_json_bytes(capture_dates))

    footprint = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [173.11456106, -41.23814238],
                            [173.11461773, -41.27057054],
                            [173.14327209, -41.27053845],
                            [173.14320125, -41.23811033],
                            [173.11456106, -41.23814238],
                        ]
                    ],
                },
            }
        ],
    }
    write("s3://stacfiles/item_footprint.geojson", dict_to_json_bytes(footprint))

    create_collection_from_items(
        collection_context=replace(fake_collection_context, collection_id="abc", add_capture_dates=True),
        uri=URI,
        concurrency=CONCURRENCY,
        current_datetime=any_epoch_datetime_string(),
    )

    capture_area_resp = s3_client.get_object(Bucket="stacfiles", Key="capture-area.geojson")
    capture_area: dict[str, Any] = json.loads(capture_area_resp["Body"].read().decode("utf-8"))
    expected_feature: dict[str, Any] = capture_dates["features"][0]

    assert shape(capture_area["geometry"]).equals(shape(expected_feature["geometry"]))


@mock_aws
def test_should_fail_when_capture_dates_file_missing(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str]
) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))

    with raises(Exception):
        create_collection_from_items(
            collection_context=replace(fake_collection_context, collection_id="abc", add_capture_dates=True),
            uri=URI,
            concurrency=CONCURRENCY,
            current_datetime=any_epoch_datetime_string(),
        )

    logs = capsys.readouterr().out

    assert "s3_key_not_found" in logs
