import json
import os
import tempfile
from functools import partial
from multiprocessing import Pool
from typing import Any, Iterable

from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.cli.common_args import CommonArgumentParser
from geoprocessor_common.files.files_helper import ContentType
from geoprocessor_common.files.fs import NoSuchFileError, copy, exists, read, write
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_common.cli.cli_helper import str_to_positive_int
from geoprocessor_pdal.pdal_commands import (
    get_pdal_translate_copc_command,
    get_pdal_version,
    run_pdal,
)
from linz_logger import get_log


def get_args_parser() -> CommonArgumentParser:
    parser = CommonArgumentParser(
        description="Convert LAS/LAZ files to Cloud Optimized Point Cloud (COPC) files with consistent CRS information."
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
        type=json_file_loader,
        required=True,
        help="JSON file containing a nested list of files to process.",
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


def flatten(items: list[Any]) -> Iterable[Any]:
    """Recursively flatten a nested list into a flat sequence.

    Args:
        items: a potentially nested list

    Returns:
        Any: The flattened elements, one by one
    """
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


def json_file_loader(path: str) -> list[str]:
    """Load a JSON file and return its contents as a list of strings.

    Args: path: path to the JSON file
    Returns:
        A list of strings contained in the JSON file.
    """
    if not path:
        return []
    try:
        return list(flatten(json.loads(read(path))))
    except NoSuchFileError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        return []


def get_copc_file_name(source_file: str) -> str:
    """Get the name of the COPC file to create from a LAS/LAZ file.

    Args:
        source_file: /path/to/a/file (S3 or local).

    Returns:
        The file name with its extension replaced by `.copc.laz`, for example `BQ31_1000_0101.copc.laz`
        for `s3://bucket/BQ31_1000_0101.laz`. An input that is already COPC keeps its name.
    """
    stem = os.path.splitext(source_file.split("/")[-1])[0]
    if stem.lower().endswith(".copc"):
        stem = stem[: -len(".copc")]
    return f"{stem}.copc.laz"


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
    source_file: str,
    target: str = "/tmp/",
    force: bool = False,
    source_crs: str | None = None,
) -> str:
    """Convert a LAS/LAZ file to COPC with `source_crs` as its CRS, keeping its header and extra dimensions.

    Args:
        source_file: /path/to/a/file to process (S3 or local).
        target: path where the output files need to be saved to. Defaults to "/tmp/".
        force: overwrite existing output file. Defaults to False.
        source_crs: CRS of the source file, e.g. "EPSG:2193+7839". Defaults to NZTM2000 + NZVD2016.

    Raises:
        ValueError: if the COPC file would overwrite the source file, which happens when a COPC source file is
            processed into its own directory.

    Returns:
        The path of the COPC file.
    """
    copc_file_name = get_copc_file_name(source_file)
    target_file = os.path.join(target, copc_file_name)

    if is_same_file(source_file, target_file):
        error_message = f"The output file would overwrite the source file, use a different target: {source_file}"
        get_log().error(error_message, target=target)
        raise ValueError(error_message)

    # Already processed can skip processing
    if exists(target_file):
        if not force:
            get_log().info("Skipping: Output file already exists.", path=target_file)
            return target_file
        get_log().info("Overwriting: Output file already exists.", path=target_file)

    with tempfile.TemporaryDirectory() as tmp_path:  # pdal needs local files
        tmp_file_in = os.path.join(tmp_path, "in_" + source_file.split("/")[-1])
        tmp_file_out = os.path.join(tmp_path, copc_file_name)

        copy(source=source_file, target=tmp_file_in)

        run_pdal(get_pdal_translate_copc_command(source_crs), input_file=tmp_file_in, output_file=tmp_file_out)

        copy(source=tmp_file_out, target=target_file)  # copy back to target location (S3 or local)

    return target_file


def run_pdal_standardise_copc(
    files_to_process: list[str],
    concurrency: int,
    target: str = "/tmp/",
    force: bool = False,
    source_crs: str | None = None,
) -> list[str]:
    """Run `pdal_standardise_copc()` in parallel (see `concurrency`).

    Args:
        files_to_process: list of files to process
        concurrency: number of concurrent files to process
        target: output directory path. Defaults to "/tmp/"
        force: overwrite existing files. Defaults to False.
        source_crs: CRS of the source files, e.g. "EPSG:2193+7839". Defaults to NZTM2000 + NZVD2016.

    Returns:
        the list of COPC file paths, in the same order as `files_to_process`.
    """
    with Pool(concurrency) as p:
        results = list(
            p.map(
                partial(pdal_standardise_copc, target=target, force=force, source_crs=source_crs),
                files_to_process,
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

    input_files = list(flatten(arguments.from_file))

    if len(input_files) == 0:
        get_log().info("no_files_to_process", action="pdal_standardise_copc", reason="skipped")
        return

    pdal_version = get_pdal_version()

    get_log().info(
        "pdal_standardise_copc_start", pdalVersion=pdal_version, inputFileCount=len(input_files), sourceCrs=source_crs
    )

    output_files = run_pdal_standardise_copc(
        input_files,
        concurrency=arguments.concurrency,
        target=arguments.target,
        force=arguments.force,
        source_crs=source_crs,
    )
    write("/tmp/processed.json", bytes(json.dumps(output_files, indent=0), "UTF-8"), content_type=ContentType.JSON)

    get_log().info("pdal_standardise_copc_end", duration=time_in_ms() - start_time, outputFileCount=len(output_files))


if __name__ == "__main__":
    main()
