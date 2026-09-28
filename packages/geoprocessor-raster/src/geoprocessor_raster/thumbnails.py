import json
import os
import tempfile
from functools import partial
from multiprocessing import Pool

from geoprocessor_common.cli.common_args import CommonArgumentParser
from geoprocessor_common.files.files_helper import ContentType, get_file_name_from_path, is_tiff
from geoprocessor_common.files.fs import copy, exists, read
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_gdal.gdal import gdal_helper
from geoprocessor_gdal.gdal.gdal_commands import get_thumbnail_command
from geoprocessor_gdal.gdal.gdal_helper import is_geotiff, run_gdal
from linz_logger import get_log


def thumbnails(path: str, target: str) -> str | None:
    """Generate a thumbnail `jpg` file from the TIFF (currently specific to Topo50-250).
    GeoTIFF and TIFF (not georeferenced) thumbnails are generated differently.

    Args:
        path: path to the TIFF file
        target: output directory

    Returns:
        path to the thumbnail generated
    """
    with tempfile.TemporaryDirectory() as tmp_path:
        if not is_tiff(path):
            get_log().debug("thumbnails_skip_not_tiff", file=path)
            return None

        basename = get_file_name_from_path(path)
        target_thumbnail = os.path.join(target, f"{basename}-thumbnail.jpg")
        # Verify the thumbnail has not been already generated
        if exists(target_thumbnail):
            get_log().info("thumbnails_already_exists", path=target_thumbnail)
            return None
        transitional_jpg = os.path.join(tmp_path, f"{basename}.jpg")
        tmp_thumbnail = os.path.join(tmp_path, f"{basename}-thumbnail.jpg")
        source_tiff = os.path.join(tmp_path, f"{basename}.tiff")
        # Download source file
        copy(path, source_tiff)

        # Generate thumbnail
        # For both GeoTIFF and TIFF (not georeferenced) this is done in 2 steps.
        # Why? because it hasn't been found another way to get the same visual aspect.
        gdalinfo_data = gdal_helper.gdal_info(source_tiff)
        if is_geotiff(source_tiff, gdalinfo_data):
            get_log().info("thumbnail_generate_geotiff", path=target_thumbnail)
            run_gdal(get_thumbnail_command("jpeg", source_tiff, transitional_jpg, "50%", "50%", None, gdalinfo_data))
            run_gdal(get_thumbnail_command("jpeg", transitional_jpg, tmp_thumbnail, "30%", "30%", None, gdalinfo_data))
        else:
            get_log().info("thumbnail_generate_tiff", path=target_thumbnail)
            run_gdal(
                get_thumbnail_command(
                    "jpeg",
                    source_tiff,
                    transitional_jpg,
                    "50%",
                    "50%",
                    # `-srcwin` select a window of the source image.
                    # This window size has been determined to remove white borders of the original file.
                    # https://gdal.org/programs/gdal_translate.html#cmdoption-gdal_translate-srcwin
                    ["-srcwin", "1280", "730", "7140", "9950"],
                    gdalinfo_data,
                )
            )
            run_gdal(get_thumbnail_command("jpeg", transitional_jpg, tmp_thumbnail, "30%", "30%", None, gdalinfo_data))

        # Upload to target
        copy(tmp_thumbnail, target_thumbnail, content_type=ContentType.JPEG.value)
    return target_thumbnail


def main() -> None:
    start_time = time_in_ms()
    parser = CommonArgumentParser(description="Generate thumbnails from TIFF files.")
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--target", dest="target", required=True, help="Output location path")
    arguments = parser.parse_args()

    get_log().info("thumbnails_start")

    from_file = arguments.from_file
    source = json.loads(read(from_file))

    concurrency = 25
    thumbnail_list = []

    for tiff_list in source:
        with Pool(concurrency) as p:
            thumbnail_list_current = p.map(
                partial(
                    thumbnails,
                    target=arguments.target,
                ),
                tiff_list,
            )
            p.close()
            p.join()
            thumbnail_list.extend(thumbnail_list_current)

    count = sum(f is not None for f in thumbnail_list)
    get_log().info("thumbnails_end", count=count, duration=time_in_ms() - start_time)


if __name__ == "__main__":
    main()
