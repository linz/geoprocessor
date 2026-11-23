import json
import os
from typing import TYPE_CHECKING

from boto3 import client
from geoprocessor_common.cli.cli_helper import get_geometry_from_geojson_feature, get_non_empty_features
from geoprocessor_common.files.files_helper import SUFFIX_FOOTPRINT, SUFFIX_JSON
from geoprocessor_common.files.fs import list_file_names
from geoprocessor_common.files.fs_s3 import bucket_name_from_path, get_object_parallel_multithreading, prefix_from_path, read
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_stac.imagery.collection import CAPTURE_DATES_FILE_NAME, COLLECTION_FILE_NAME, ImageryCollection
from geoprocessor_stac.imagery.collection_context import CollectionContext
from geoprocessor_stac.imagery.create_stac import create_collection
from linz_logger import get_log

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
else:
    S3Client = dict


class NoItemsError(Exception):
    pass


# pylint: disable=too-many-locals
# pylint: disable=too-many-positional-arguments
def create_collection_from_items(
    collection_context: CollectionContext,
    uri: str,
    concurrency: int,
    current_datetime: str,
    odr_url: str | None = None,
    supplied_capture_area: str | None = None,
    simplified_capture_area: bool = False,
) -> ImageryCollection:
    """Create a STAC Collection from the STAC Items already written to `uri`, and write it alongside them.

    Items whose `collection` does not match `collection_context.collection_id` are skipped. Unless a
    capture area is supplied, one is generated from any footprint files found next to the Items.

    Args:
        collection_context: context to create the Collection, including the Collection ID to match Items against
        uri: s3 path holding the STAC Items, and the write location of the Collection
        concurrency: number of files to read concurrently
        current_datetime: date and time for setting consistent update and/or creation timestamps
        odr_url: S3 URL of the already published dataset (if this is a resupply). Defaults to None.
        supplied_capture_area: s3 path to an externally supplied EPSG:4326 capture area. Defaults to None.
            Ignored if `collection_context.add_capture_dates` is set, which supplies the capture area
            from the Collection's capture dates file.
        simplified_capture_area: whether the Item footprints have been simplified. Defaults to False.

    Raises:
        NoItemsError: if no Item in `uri` belongs to this Collection

    Returns:
        the ImageryCollection that was written
    """
    start_time = time_in_ms()
    collection_id = collection_context.collection_id

    if collection_context.add_capture_dates:
        supplied_capture_area = os.path.join(uri, CAPTURE_DATES_FILE_NAME)
        get_log().info("Using capture dates file to generate capture area", capture_dates_path=supplied_capture_area)

    s3_client: S3Client = client("s3")

    files_to_read = [
        os.path.join(prefix_from_path(uri), name)
        for name in list_file_names(uri, recursive=True)
        if name.endswith((SUFFIX_JSON, SUFFIX_FOOTPRINT))
    ]
    get_log().info("Files Listed", number_of_files=len(files_to_read))

    items_to_add = []
    polygons = []

    if supplied_capture_area:
        content = json.loads(read(supplied_capture_area))
        features = get_non_empty_features(content, supplied_capture_area)
        for feature in features:
            polygons.append(get_geometry_from_geojson_feature(feature, supplied_capture_area))

    for key, result in get_object_parallel_multithreading(bucket_name_from_path(uri), files_to_read, s3_client, concurrency):
        content = json.load(result["Body"])
        # The following if/else looks like it could be avoided by listing each suffix separately,
        # but we would have to call `get_object_parallel_multithreading()` for each of them to avoid this if/else.
        if key.endswith(SUFFIX_JSON):
            if content["type"] != "Feature":
                get_log().warn(
                    "skipping: not a STAC item",
                    file=key,
                    action="collection_from_items",
                    reason="skip",
                )
                continue
            item_collection_id = content.get("collection")
            if collection_id != item_collection_id:
                get_log().warn(
                    f"skipping: {item_collection_id} and {collection_id} do not match",
                    file=key,
                    action="collection_from_items",
                    reason="skip",
                )
                continue
            items_to_add.append(content)
            get_log().info("Item will be added to Collection", item=content["id"], file=key)
        elif key.endswith(SUFFIX_FOOTPRINT) and not supplied_capture_area:
            features = get_non_empty_features(content, key)
            for feature in features:
                polygons.append(get_geometry_from_geojson_feature(feature, key))

    if len(items_to_add) == 0:
        get_log().error(
            f"Collection {collection_id} has no items. Collection will not be created.",
        )
        raise NoItemsError(f"Collection {collection_id} has no items")

    collection = create_collection(
        collection_context=collection_context,
        current_datetime=current_datetime,
        stac_items=items_to_add,
        item_polygons=polygons,
        uri=uri,
        odr_url=odr_url,
        supplied_capture_area=supplied_capture_area,
        simplified_capture_area=simplified_capture_area,
    )

    destination = os.path.join(uri, COLLECTION_FILE_NAME)
    collection.write_to(destination)

    get_log().info(
        "Collection created",
        item_count=len(files_to_read),
        item_match_count=len(items_to_add),
        duration=time_in_ms() - start_time,
        destination=destination,
    )

    return collection
