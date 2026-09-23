import os
import sys
import tempfile
from datetime import datetime, timezone
from functools import partial
from multiprocessing import Pool

from geoprocessor_common.cli.cli_helper import InputParameterError, TileFiles, load_input_files
from geoprocessor_common.cli.common_args import CommonArgumentParser
from geoprocessor_common.data_type import DataType
from geoprocessor_common.datetimes import RFC_3339_DATETIME_FORMAT
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_common.files.files_helper import SUFFIX_JSON, ContentType, is_tiff
from geoprocessor_common.files.fs import copy, exists, write, write_all
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_gdal.gdal.gdal_commands import get_gdal_command, get_hillshade_command
from geoprocessor_gdal.gdal.gdal_helper import get_gdal_version, run_gdal
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset, HillshadePreset
from geoprocessor_gdal.standardising import create_vrt
from geoprocessor_raster.create_item import create_item_from_tiff
from geoprocessor_stac.json_codec import dict_to_json_bytes
from linz_logger import get_log


def get_args_parser() -> CommonArgumentParser:
    parser = CommonArgumentParser(description="Generate hillshade TIFF files from input DEM/DSM TIFF files.")
    parser.add_argument(
        "--from-file",
        dest="from_file",
        required=True,
        help="Specify the path to a json file containing the input tiffs. "
        "Format: [{'output': 'tile1', 'inputs': ['path/input1.tiff', 'path/input2.tiff']}]",
    )
    parser.add_argument(
        "--preset",
        dest="preset",
        required=True,
        choices=[preset.value for preset in HillshadePreset],
        help="Type of hillshade to generate.",
    )
    parser.add_argument(
        "--collection-id",
        dest="collection_id",
        help="Unique id of the Collection. If not provided, STAC Items won't be created.",
    )
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
    parser.add_argument("--target", dest="target", required=True, help="Specify the path to save the generated hillshade to.")
    parser.add_argument(
        "--force",
        dest="force",
        help="Regenerate the hillshade TIFF files if already exist. Defaults to False.",
        action="store_true",
    )
    parser.add_argument(
        "--odr-url",
        dest="odr_url",
        help="The path of the published dataset. Example: 's3://nz-elevation/new-zealand/new-zealand/dem-hillshade_1m/2193/'",
        required=False,
    )

    return parser


def create_hillshade(
    tile: TileFiles,
    preset: str,
    target_output: str = "/tmp/",
    force: bool = False,
) -> tuple[str, list[str], str | None]:
    """Create a hillshade TIFF file from a `TileFiles` which include an output tile with its input TIFFs.

    Args:
        tile: a TileFiles object with the input TIFFs and the output tile name.
        preset: a `HillshadePreset` to use. See `gdal.gdal_presets.py`.
        target_output: path where the output files need to be saved to. Defaults to "/tmp/".
        force: overwrite existing output file. Defaults to False.

    Returns:
        The filename of the hillshade TIFF file if created, the path of the input files used to create it,
        and the multihash of its content (None if the file already existed and was not rewritten).
    """
    hillshade_file_name = tile.output + ".tiff"
    hillshade_file_path = os.path.join(target_output, hillshade_file_name)

    # Already processed can skip processing
    if exists(hillshade_file_path):
        if not force:
            get_log().info("Skipping: hillshade TIFF already exists.", path=hillshade_file_path)
            return hillshade_file_path, tile.inputs, None
        get_log().info("Overwriting: hillshade TIFF already exists.", path=hillshade_file_path)

    # Download any needed file from S3 ["/foo/bar.tiff", "s3://foo"] => "/tmp/bar.tiff", "/tmp/foo.tiff"
    with tempfile.TemporaryDirectory() as tmp_path:
        hillshade_working_path = os.path.join(tmp_path, hillshade_file_name)
        hillshade_cog_working_path = os.path.join(tmp_path, tile.output + "_cog.tiff")

        source_files = write_all(tile.inputs, f"{tmp_path}/source/")
        source_tiffs = [file for file in source_files if is_tiff(file)]

        # Start from base VRT
        input_file = create_vrt(source_tiffs, tmp_path)

        # Compute the hillshade
        run_gdal(get_hillshade_command(preset), input_file=input_file, output_file=hillshade_working_path)

        # COGify the hillshade output, using ZSTD compression
        run_gdal(
            get_gdal_command(CompressionPreset.DEM_ZSTD.value, EpsgNumber.NZTM_2000, DataType.FLOAT32.value),
            input_file=hillshade_working_path,
            output_file=hillshade_cog_working_path,
        )

        # Note: This file is used as an implicit indicator that processing has completed, so should be written last.
        file_checksum = copy(hillshade_cog_working_path, hillshade_file_path, content_type=ContentType.GEOTIFF.value)

        return hillshade_file_path, tile.inputs, file_checksum


def run_create_hillshade(
    todo: list[TileFiles],
    preset: str,
    concurrency: int,
    target_output: str = "/tmp/",
    force: bool = False,
) -> list[tuple[str, list[str], str | None]]:
    """Run `create_hillshade()` in parallel (see `concurrency`).

    Args:
        todo: list of TileFiles (tile name and input files) to hillshade
        preset: `HillshadePreset` to use. See `gdal.gdal_presets.py`
        concurrency: number of concurrent tiles to process
        target_output: output directory path. Defaults to "/tmp/"
        force: overwrite existing files. Defaults to False.

    Returns:
        the list of generated hillshade TIFF paths with their input files and content multihash.
    """
    with Pool(concurrency) as p:
        results = list(p.map(partial(create_hillshade, preset=preset, target_output=target_output, force=force), todo))
        p.close()
        p.join()

    return results


def main() -> None:
    start_time = time_in_ms()
    arguments_parser = get_args_parser()
    arguments = arguments_parser.parse_args()

    try:
        tile_files = load_input_files(arguments.from_file)
    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    gdal_version = get_gdal_version()

    get_log().info("generate_hillshade_start", gdalVersion=gdal_version, fileCount=len(tile_files), preset=arguments.preset)

    concurrency: int = 1
    if arguments.is_argo:
        concurrency = 4

    tiles = run_create_hillshade(tile_files, arguments.preset, concurrency, arguments.target, arguments.force)

    if arguments.collection_id:
        for path, derived_from_tiffs, file_checksum in tiles:
            stac_item_path = path.rsplit(".", 1)[0] + SUFFIX_JSON
            if not exists(stac_item_path):
                # Create STAC and save in target
                item = create_item_from_tiff(
                    asset_path=path,
                    start_datetime="",
                    end_datetime="",
                    collection_id=arguments.collection_id,
                    gdal_version=gdal_version,
                    current_datetime=arguments.current_datetime,
                    gdalinfo_result=None,
                    derived_from=[url_derived_from.rsplit(".", 1)[0] + SUFFIX_JSON for url_derived_from in derived_from_tiffs],
                    odr_url=arguments.odr_url,
                    asset_checksum=file_checksum,
                )
                write(stac_item_path, dict_to_json_bytes(item.stac), content_type=ContentType.GEOJSON.value)
            else:
                get_log().info("Skipping: STAC already exists.", path=stac_item_path)
    else:
        get_log().warning("No collection ID provided. Skipping STAC creation.")

    get_log().info("generate_hillshade_end", duration=time_in_ms() - start_time, fileCount=len(tiles), path=arguments.target)


if __name__ == "__main__":
    main()
