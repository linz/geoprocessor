import os
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone

from geoprocessor_common.cli.cli_helper import (
    InputParameterError,
    load_input_files,
    str_to_bool,
    str_to_gsd,
    str_to_list_or_none,
    str_to_positive_int,
    valid_date,
)
from geoprocessor_common.data_type import DataType
from geoprocessor_common.datetimes import RFC_3339_DATETIME_FORMAT, format_rfc_3339_nz_midnight_datetime_string
from geoprocessor_common.files.files_helper import SUFFIX_JSON, ContentType
from geoprocessor_common.files.fs import exists, write
from geoprocessor_gdal.gdal.gdal_helper import get_gdal_version, get_srs, get_vfs_path
from geoprocessor_gdal.standardising import StandardisingConfig, run_standardising
from geoprocessor_gdal.tiff.file_tiff import FileTiff
from geoprocessor_raster.create_item import create_item_from_tiff
from geoprocessor_stac.json_codec import dict_to_json_bytes
from linz_logger import get_log


def get_args_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Standardise and validate imagery TIFF files, and create STAC Metadata.")
    parser.add_argument("--preset", dest="preset", required=True, help="Standardised file format. Example: webp")
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument(
        "--odr-url",
        dest="odr_url",
        help=(
            "The s3 URL of the published dataset in ODR if this is a re-supply. "
            "Example: 's3://nz-imagery/wellington/porirua_2024_0.1m/rgb/2193/'"
        ),
        required=False,
    )
    parser.add_argument(
        "--source-epsg", dest="source_epsg", type=int, required=True, help="The EPSG code of the source imagery"
    )
    parser.add_argument(
        "--target-epsg",
        dest="target_epsg",
        type=int,
        required=True,
        help="The target EPSG code. If different to source the imagery will be reprojected",
    )
    parser.add_argument("--gsd", dest="gsd", help="GSD of imagery Dataset, for example 0.3", type=str_to_gsd, required=True)
    parser.add_argument(
        "--data-type",
        dest="data_type",
        help="Dataset data type, e.g. uint8. `uint16` and `uint32` are only valid with the rgbnir_zstd preset",
        type=str,
        choices=[data_type.value for data_type in DataType],
        required=True,
    )
    parser.add_argument(
        "--create-footprints",
        dest="create_footprints",
        help="Create footprints for each tile ('true' / 'false')",
        type=str_to_bool,
        required=True,
    )
    parser.add_argument(
        "--simplify-footprints",
        dest="simplify_footprints",
        help="Simplify footprints for each tile using gdal_fillnodata ('true' / 'false')",
        type=str_to_bool,
        default=False,
    )
    parser.add_argument("--cutline", dest="cutline", help="Optional cutline to cut imagery to", required=False, nargs="?")
    parser.add_argument("--collection-id", dest="collection_id", help="Unique id for collection", required=True)
    parser.add_argument(
        "--start-datetime",
        dest="start_datetime",
        help="Start datetime in format YYYY-MM-DD. Only optional if includeDerived.",
        type=valid_date,
    )
    parser.add_argument(
        "--end-datetime",
        dest="end_datetime",
        help="End datetime in format YYYY-MM-DD. Only optional if includeDerived.",
        type=valid_date,
    )
    parser.add_argument("--target", dest="target", help="Target output", required=True)
    parser.add_argument(
        "--current-datetime",
        dest="current_datetime",
        help=(
            "The datetime to be used as current datetime in the metadata. "
            "Format: RFC 3339 UTC datetime, `YYYY-MM-DDThh:mm:ssZ`."
        ),
        required=False,
        default=datetime.now(timezone.utc).strftime(RFC_3339_DATETIME_FORMAT),
    )
    parser.add_argument(
        "--scale-to-resolution",
        dest="scale_to_resolution",
        type=str_to_list_or_none,
        nargs="?",
        help="Scale to x,y resolution (leave blank for no scaling)",
        required=False,
    )
    parser.add_argument(
        "--force",
        dest="force",
        help="Regenerate the standardised TIFF and STAC files if already exist. Defaults to False.",
        action="store_true",
    )
    parser.add_argument(
        "--concurrency",
        dest="concurrency",
        type=str_to_positive_int,
        help="Number of concurrent tile to standardise. Defaults to 1.",
        required=False,
        default=1,
    )
    return parser


def report_non_visual_qa_errors(file: FileTiff) -> None:
    """
    If the file is not valid (Non Visual QA errors) logs the `vsis3` path to use `gdal` on the file directly from `s3`.
    This is to help data analysts to verify the file.
    """
    original_path: list[str] = file.get_paths_original()
    standardised_path = file.get_path_standardised()
    if os.environ.get("ARGO_TEMPLATE"):
        standardised_path = get_vfs_path(file.get_path_standardised())
        original_s3_path: list[str] = []
        for path in original_path:
            original_s3_path.append(get_vfs_path(path))
        original_path = original_s3_path
    get_log().info(
        "non_visual_qa_errors",
        originalPath=",".join(original_path),
        standardisedPath=standardised_path,
        errors=file.get_errors(),
    )


def main() -> None:
    arguments = get_args_parser().parse_args()
    force = arguments.force

    standardising_config = StandardisingConfig(
        gdal_preset=arguments.preset,
        source_epsg=arguments.source_epsg,
        target_epsg=arguments.target_epsg,
        gsd=arguments.gsd,
        create_footprints=arguments.create_footprints,
        simplify_footprints=arguments.simplify_footprints,
        cutline=arguments.cutline,
        data_type=arguments.data_type,
        scale_to_resolution=arguments.scale_to_resolution,
        force=force,
    )

    try:
        tile_files = load_input_files(arguments.from_file)
    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    # When standardising output includeDerived, start_datetime and end_datetime are optional
    if arguments.start_datetime is None or arguments.end_datetime is None:
        for tile in tile_files:
            if not tile.includeDerived:
                raise Exception("--start_datetime and --end_datetime are required if standardising non-derived files.")
        start_datetime = ""
        end_datetime = ""
    else:
        start_datetime = format_rfc_3339_nz_midnight_datetime_string(arguments.start_datetime)
        end_datetime = format_rfc_3339_nz_midnight_datetime_string(arguments.end_datetime)

    gdal_version = get_gdal_version()

    tiff_files = run_standardising(tile_files, standardising_config, arguments.concurrency, gdal_version, arguments.target)

    if len(tiff_files) == 0:
        get_log().info("no_tiff_to_process", action="standardise_validate", reason="skipped")
        return

    # SRS needed for FileCheck (non visual QA)
    srs = get_srs(standardising_config.target_epsg)

    for file in tiff_files:
        stac_item_path = file.get_path_standardised().rsplit(".", 1)[0] + SUFFIX_JSON
        if force or not exists(stac_item_path):
            file.set_srs(srs)

            # Validate the file
            if not file.validate():
                report_non_visual_qa_errors(file)
            else:
                get_log().info("non_visual_qa_passed", path=file.get_path_standardised())

            # Create STAC and save in target
            item = create_item_from_tiff(
                file.get_path_standardised(),
                start_datetime,
                end_datetime,
                arguments.collection_id,
                gdal_version,
                arguments.current_datetime,
                file.get_gdalinfo(),
                file.get_derived_from_paths(),
                arguments.odr_url,
            )
            write(stac_item_path, dict_to_json_bytes(item.stac), content_type=ContentType.GEOJSON.value)
            get_log().info("stac_saved", path=stac_item_path)


if __name__ == "__main__":
    main()
