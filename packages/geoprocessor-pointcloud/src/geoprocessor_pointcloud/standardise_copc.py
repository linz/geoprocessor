import json
import os
import sys
import tempfile
from functools import partial
from multiprocessing import Pool

from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.cli.cli_helper import InputParameterError, TileFiles, load_input_files, str_to_positive_int
from geoprocessor_common.cli.common_args import CommonArgumentParser
from geoprocessor_common.files.files_helper import ContentType
from geoprocessor_common.files.fs import copy, exists, write
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_pdal.pdal_commands import get_pdal_version, pdal_merge_copc
from linz_logger import get_log


def get_args_parser() -> CommonArgumentParser:
    parser = CommonArgumentParser(
        description="Merge the LAS/LAZ files of each tile into one Cloud Optimized Point Cloud (COPC) file "
        "with consistent CRS information."
    )

    parser.add_argument(
        "--force",
        dest="force",
        help="Overwrite output files that already exist. Defaults to False.",
        action="store_true",
    )
    parser.add_argument(
        "--from-file",
        dest="from_file",
        required=True,
        help="JSON file listing each tile and the files to merge into it.",
    )
    parser.add_argument(
        "--target",
        dest="target",
        required=False,
        default="/tmp/",
        help="Path where the output files will be saved to. Defaults to '/tmp/'.",
    )
    parser.add_argument(
        "--source-crs",
        dest="source_crs",
        required=False,
        default="",
        help='CRS of the source point clouds, e.g. "EPSG:2193+7839". Defaults to NZTM2000 + NZVD2016 if empty.',
    )
    parser.add_argument(
        "--concurrency",
        dest="concurrency",
        type=str_to_positive_int,
        required=False,
        default=1,
        help="Number of concurrent processes to use. Defaults to 1.",
    )

    return parser


def is_same_file(path_a: str, path_b: str) -> bool:
    """Check whether two paths are the same file. Local paths are resolved first, so `./a.laz` and `a.laz` are the same
    file. S3 paths are compared as they are, because S3 keys are not resolved: `a//b.laz` and `a/b.laz` are different
    objects.

    Args:
        path_a: /path/to/a/file (S3 or local).
        path_b: /path/to/a/file (S3 or local).

    Returns:
        True if both paths are the same file.
    """
    if is_s3(path_a) or is_s3(path_b):
        return path_a == path_b
    return os.path.realpath(path_a) == os.path.realpath(path_b)


def pdal_standardise_copc(
    tile: TileFiles,
    target: str = "/tmp/",
    force: bool = False,
    source_crs: str | None = None,
) -> str:
    """Merge the LAS/LAZ files of a tile into one COPC file named after the tile, with `source_crs` as its CRS,
    keeping their header and extra dimensions.

    Args:
        tile: the tile name (`output`) and the files to merge into it (`inputs`, S3 or local).
        target: path where the output files need to be saved to. Defaults to "/tmp/".
        force: overwrite existing output file. Defaults to False.
        source_crs: CRS of the source files, e.g. "EPSG:2193+7839". Defaults to NZTM2000 + NZVD2016.

    Raises:
        ValueError: if the COPC file would overwrite one of the source files.

    Returns:
        The path of the COPC file, for example `<target>/BY16_5000_0410.copc.laz` for the tile `BY16_5000_0410`.
    """
    copc_file_name = f"{tile.output}.copc.laz"
    target_file = os.path.join(target, copc_file_name)

    for source_file in tile.inputs:
        if is_same_file(source_file, target_file):
            error_message = f"The output file would overwrite a source file, use a different target: {source_file}"
            get_log().error(error_message, target=target)
            raise ValueError(error_message)

    # Already processed can skip processing
    if exists(target_file):
        if not force:
            get_log().info("Skipping: Output file already exists.", path=target_file)
            return target_file
        get_log().info("Overwriting: Output file already exists.", path=target_file)

    with tempfile.TemporaryDirectory() as tmp_path:  # pdal needs local files
        local_inputs = []
        for index, source_file in enumerate(tile.inputs):
            # The index keeps inputs with the same file name from different directories apart.
            local_file = os.path.join(tmp_path, f"in_{index}_{source_file.split('/')[-1]}")
            copy(source=source_file, target=local_file)
            local_inputs.append(local_file)

        tmp_file_out = os.path.join(tmp_path, copc_file_name)
        pdal_merge_copc(local_inputs, tmp_file_out, source_crs)

        copy(source=tmp_file_out, target=target_file)  # copy back to target location (S3 or local)

    return target_file


def run_pdal_standardise_copc(
    tiles: list[TileFiles],
    concurrency: int,
    target: str = "/tmp/",
    force: bool = False,
    source_crs: str | None = None,
) -> list[str]:
    """Run `pdal_standardise_copc()` in parallel (see `concurrency`).

    Args:
        tiles: the tiles to create, each with the files to merge into it
        concurrency: number of tiles to process at the same time
        target: output directory path. Defaults to "/tmp/"
        force: overwrite existing files. Defaults to False.
        source_crs: CRS of the source files, e.g. "EPSG:2193+7839". Defaults to NZTM2000 + NZVD2016.

    Returns:
        the list of COPC file paths, in the same order as `tiles`.
    """
    with Pool(concurrency) as p:
        results = list(
            p.map(
                partial(pdal_standardise_copc, target=target, force=force, source_crs=source_crs),
                tiles,
            )
        )
        p.close()
        p.join()

    return results


def main() -> None:
    start_time = time_in_ms()
    arguments_parser = get_args_parser()
    arguments = arguments_parser.parse_args()
    source_crs = arguments.source_crs.strip() or None

    try:
        tiles = load_input_files(arguments.from_file)
    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    if len(tiles) == 0:
        get_log().info("no_tiles_to_process", action="pdal_standardise_copc", reason="skipped")
        return

    pdal_version = get_pdal_version()

    get_log().info("pdal_standardise_copc_start", pdalVersion=pdal_version, tileCount=len(tiles), sourceCrs=source_crs)

    output_files = run_pdal_standardise_copc(
        tiles,
        concurrency=arguments.concurrency,
        target=arguments.target,
        force=arguments.force,
        source_crs=source_crs,
    )
    write("/tmp/processed.json", bytes(json.dumps(output_files, indent=0), "UTF-8"), content_type=ContentType.JSON)

    get_log().info("pdal_standardise_copc_end", duration=time_in_ms() - start_time, outputFileCount=len(output_files))


if __name__ == "__main__":
    main()
