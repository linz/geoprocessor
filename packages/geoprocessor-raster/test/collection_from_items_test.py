from os import environ
from typing import TYPE_CHECKING, Any, Iterator
from unittest.mock import patch

import pytest
from boto3 import client
from geoprocessor_common.files.fs_s3 import write
from geoprocessor_common.geometry import GeojsonPolygon
from geoprocessor_raster.collection_from_items import main
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.item import ImageryItem
from geoprocessor_stac.json_codec import dict_to_json_bytes
from geoprocessor_stac.testing.generators import any_stac_asset, any_stac_processing
from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME
from pytest import CaptureFixture, raises

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
else:
    S3Client = GetObjectOutputTypeDef = dict


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
    item.update_spatial(geometry, bbox)
    item.update_datetime("2021-01-27T11:00:00Z", "2021-01-27T11:00:00Z")
    yield item


def base_args(linz_slug: str | None = None) -> list[str]:
    """The arguments every invocation needs, so each test only spells out the ones it is about."""
    args = [
        "--uri",
        "s3://stacfiles/",
        "--collection-id",
        "abc",
        "--category",
        "urban-aerial-photos",
        "--region",
        "hawkes-bay",
        "--gsd",
        "1",
        "--data-type",
        "uint8",
        "--lifecycle",
        "ongoing",
        "--producer",
        "Placeholder",
        "--licensor",
        "Placeholder",
        "--concurrency",
        "25",
    ]
    if linz_slug is not None:
        args += ["--linz-slug", linz_slug]

    return args


def test_should_fail_to_create_collection_file_without_linz_slug(capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        main(base_args())

    assert "the following arguments are required: --linz-slug" in capsys.readouterr().err


def test_should_reject_a_uri_that_is_not_an_s3_path(fake_collection_context: CollectionContext) -> None:
    args = base_args(fake_collection_context.linz_slug)
    args[args.index("--uri") + 1] = "/local/path/"

    with raises(Exception, match="uri is not a s3 path"):
        main(args)


@mock_aws
def test_should_fail_with_both_supplied_and_simplified_capture_area(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str]
) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))
    write("s3://stacfiles/supplied-capture-area.geojson", dict_to_json_bytes({"type": "FeatureCollection", "features": []}))

    args = base_args(fake_collection_context.linz_slug) + [
        "--supplied-capture-area",
        "s3://stacfiles/supplied-capture-area.geojson",
        "--simplified-capture-area",
        "true",
    ]

    with raises(SystemExit):
        main(args)

    assert "error: --supplied-capture-area and --simplified-capture-area cannot be used together" in capsys.readouterr().err


@mock_aws
def test_should_fail_with_both_supplied_capture_area_and_capture_dates(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str]
) -> None:
    s3_client: S3Client = client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="stacfiles")
    item.add_collection("abc")
    write("s3://stacfiles/item.json", dict_to_json_bytes(item.stac))
    write("s3://stacfiles/supplied-capture-area.geojson", dict_to_json_bytes({"type": "FeatureCollection", "features": []}))

    args = base_args(fake_collection_context.linz_slug) + [
        "--supplied-capture-area",
        "s3://stacfiles/supplied-capture-area.geojson",
        "--capture-dates",
        "true",
    ]

    with raises(SystemExit):
        main(args)

    assert "error: --supplied-capture-area and --capture-dates cannot be used together" in capsys.readouterr().err


@mock_aws
def test_should_pass_with_empty_supplied_capture_area_and_capture_dates(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str]
) -> None:
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

    args = base_args(fake_collection_context.linz_slug) + [
        "--supplied-capture-area",
        "",
        "--capture-dates",
        "true",
    ]

    main(args)

    assert "error:" not in capsys.readouterr().err


@mock_aws
def test_should_pass_with_default_capture_area_arguments_and_capture_dates(
    item: ImageryItem, fake_collection_context: CollectionContext, capsys: CaptureFixture[str]
) -> None:
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

    args = base_args(fake_collection_context.linz_slug) + [
        "--supplied-capture-area",
        "",
        "--simplified-capture-area",
        "false",
        "--capture-dates",
        "true",
    ]

    main(args)

    assert "error:" not in capsys.readouterr().err
