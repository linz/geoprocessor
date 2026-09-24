import argparse
import json
from datetime import datetime
from typing import Any

import boto3
from linz_logger import get_log

from scripts.datetimes import format_rfc_3339_datetime_string
from scripts.files.files_helper import ContentType
from scripts.files.fs import read, write
from scripts.files.fs_s3 import bucket_name_from_path, prefix_from_path
from scripts.json_codec import dict_to_json_bytes
from scripts.logging.time_helper import time_in_ms


def load_versions(path: str) -> dict[str, Any]:
    s3_client = boto3.client("s3")
    versions = s3_client.list_object_versions(Bucket=bucket_name_from_path(path), Prefix=prefix_from_path(path))
    return sorted(versions.get("Versions", []), key=lambda v: v["LastModified"])


def get_object_version_modified_dates(versions: dict[str, Any]) -> list[datetime]:
    modified_dates = []
    for version in versions:
        modified_dates.append(version["LastModified"])

    return modified_dates


def get_latest_version_modified_date(versions: dict[str, Any]) -> datetime:
    for version in versions:
        if version["IsLatest"]:
            return version["LastModified"]
    raise Exception("No latest version found")


def get_closest_date(date: datetime, dates: list[datetime]) -> datetime:
    closest = min(dates, key=lambda d: abs(d - date))
    return closest


def main() -> None:
    start_time = time_in_ms()
    parser = argparse.ArgumentParser()
    parser.add_argument("collection_path")
    parser.add_argument("--target", dest="target", help="Target output", required=True)
    arguments = parser.parse_args()
    collection_path = arguments.collection_path
    target_path = arguments.target.rstrip("/") + "/"
    dataset_path = f"{collection_path.rsplit('/', 1)[0]}/"

    collection_versions = load_versions(collection_path)
    collection_modified_dates = get_object_version_modified_dates(collection_versions)
    collection_updated_date = get_latest_version_modified_date(collection_versions)
    get_log().debug("Collection S3 Object versions", count=len(collection_modified_dates))
    collection = json.loads(read(collection_path))

    item_count = 0
    for link in collection["links"]:
        if link["rel"] != "item":
            continue

        item_filename = link["href"].lstrip("./")
        item_path = f"{dataset_path}{item_filename}"
        get_log().debug("Updating Item", filename=item_filename)

        item = json.loads(read(item_path))
        item_object_versions = load_versions(item_path)
        item_object_created_date = get_object_version_modified_dates(item_object_versions)[0]
        item_object_updated_date = get_latest_version_modified_date(item_object_versions)
        item_created = get_closest_date(item_object_created_date, collection_modified_dates)
        item_updated = get_closest_date(item_object_updated_date, collection_modified_dates)

        asset_filename = item["assets"]["visual"]["href"].lstrip("./")
        asset_path = f"{dataset_path}{asset_filename}"
        asset_object_versions = load_versions(asset_path)
        asset_object_updated_date = get_latest_version_modified_date(asset_object_versions)
        asset_created = item_created
        asset_updated = get_closest_date(asset_object_updated_date, collection_modified_dates)

        item.get("properties", {})
        item["properties"]["created"] = format_rfc_3339_datetime_string(item_created)
        item["properties"]["updated"] = format_rfc_3339_datetime_string(item_updated)
        item["assets"]["visual"]["created"] = format_rfc_3339_datetime_string(asset_created)
        item["assets"]["visual"]["updated"] = format_rfc_3339_datetime_string(asset_updated)

        target_item_path = f"{target_path}{item_filename}"
        write(target_item_path, dict_to_json_bytes(item.stac), content_type=ContentType.GEOJSON.value)
        get_log().info("Write Item to target", path=target_item_path)
        item_count += 1

    collection["created"] = format_rfc_3339_datetime_string(collection_modified_dates[0])
    collection["updated"] = format_rfc_3339_datetime_string(collection_updated_date)
    target_collection_path = f"{target_path}collection.json"
    write(target_collection_path, dict_to_json_bytes(collection), content_type=ContentType.JSON.value)
    get_log().info("Write Collection to target", path=target_collection_path)

    get_log().info("Update completed", path=dataset_path, count=item_count + 1, duration=time_in_ms() - start_time)


if __name__ == "__main__":
    main()
