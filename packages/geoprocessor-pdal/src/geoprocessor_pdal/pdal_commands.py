import json
import os
import subprocess
from functools import cache
from shutil import rmtree
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any

from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_common.files.fs import copy
from geoprocessor_common.log.time_helper import time_in_ms
from linz_logger import get_log


class PDALExecutionException(Exception):
    pass


def _pdal_executable() -> str:
    """The `pdal` executable to run.

    Returns:
        the value of `PDAL_EXECUTABLE`, or `pdal` to find it on the path
    """
    return os.environ.get("PDAL_EXECUTABLE", "pdal")


def get_pdal_command(command: str, options: list[str]) -> list[str]:
    """Build a `pdal` command.

    Args:
        command: pdal command to run (e.g. 'translate', 'info', etc.)
        options: options to pass to the pdal command

    Returns:
        a list of arguments for `pdal`
    """
    get_log().info("pdal command", command=command, options=options)
    if command not in [
        "chamfer",
        "delta",
        "density",
        "eval",
        "fauxplugin",
        "ground",
        "hausdorff",
        "info",
        "merge",
        "pipeline",
        "random",
        "sort",
        "split",
        "tile",
        "tindex",
        "translate",
    ]:
        raise ValueError(f"Unsupported PDAL command: {command}")

    pdal_command: list[str] = [command]
    pdal_command.extend(options)

    return pdal_command


pdal_translate_add_proj_command = get_pdal_command(
    "translate",
    [
        f"--readers.las.spatialreference=EPSG:{EpsgNumber.NZTM_2000}+{EpsgNumber.NZVD_2016}",
        "--writers.las.filesource_id=0",
        "--writers.las.forward=all",
    ],
)


# `writers.copc` options shared by the translate command and the merge pipeline.
# `forward` keeps the global encoding (GPS time type), scale, offset and VLRs of the input file. The other header
# fields describe the reprocessed file: `filesource_id` and `system_id` are set here, and `software_id`, the creation
# date and `project_id` (all zeros, i.e. unassigned) are left to the writer.
# `a_srs` replaces the CRS of the input file, which may be malformed (see `pdal_translate_add_proj_command`), without
# reprojecting.
COPC_WRITER_OPTIONS: dict[str, str] = {
    "forward": "global_encoding,scale,offset,vlr",
    "filesource_id": "0",
    "extra_dims": "all",
    "system_id": "TRANSFORMATION",
    "a_srs": f"EPSG:{EpsgNumber.NZTM_2000}+{EpsgNumber.NZVD_2016}",
}

pdal_translate_copc_command = get_pdal_command(
    "translate",
    ["--writer=writers.copc", *(f"--writers.copc.{k}={v}" for k, v in COPC_WRITER_OPTIONS.items())],
)

pdal_pipeline_command = get_pdal_command("pipeline", [])


def get_merge_copc_pipeline(input_files: list[str], output_file: str) -> list[Any]:
    """Build a PDAL pipeline that merges LAS/LAZ/COPC files into one COPC file.

    PDAL merges every reader that feeds a writer, so the pipeline is the input files followed by the COPC writer.

    Args:
        input_files: local paths of the files to merge
        output_file: local path of the COPC file to write

    Raises:
        ValueError: if there are no input files, or if any path is on S3

    Returns:
        the pipeline, ready to be written as JSON
    """
    if not input_files:
        raise ValueError("At least one input file is needed to merge")
    # `run_pdal` only moves the pipeline file to and from S3; the paths inside it go to PDAL as they are.
    if s3_paths := [path for path in [*input_files, output_file] if is_s3(path)]:
        raise ValueError(f"Merge paths must be local, download from and upload to S3 around the merge: {s3_paths}")

    writer: dict[str, str] = {"type": "writers.copc", "filename": output_file, **COPC_WRITER_OPTIONS}

    return [*input_files, writer]


def pdal_merge_copc(input_files: list[str], output_file: str) -> str:
    """Merge local LAS/LAZ/COPC files into one local COPC file.

    Args:
        input_files: local paths of the files to merge
        output_file: local path of the COPC file to write

    Returns:
        the path of the merged COPC file
    """
    pipeline = get_merge_copc_pipeline(input_files, output_file)

    with TemporaryDirectory() as tmp_path:
        pipeline_file = os.path.join(tmp_path, "merge_copc.json")
        with open(pipeline_file, "w", encoding="utf-8") as file:
            json.dump(pipeline, file)
        get_log().info("pdal_merge_copc", inputFileCount=len(input_files), output=output_file)
        run_pdal(pdal_pipeline_command, input_file=pipeline_file)

    return output_file


pdal_info_command = get_pdal_command(
    "info",
    ["--metadata", "--summary", "--json"],
)


def run_pdal(
    command_options_args: list[str],
    input_file: str | None = None,
    output_file: str | None = None,
) -> "subprocess.CompletedProcess[bytes]":
    """Run the PDAL command. The permissions to access to the input file are applied to the pdal environment.

    Args:
        command_options_args: list of command, options and arguments to be passed to the PDAL command
        input_file: /path/to/the/input_file
        output_file: /path/to/the/output_file

    Raises:
        PDALExecutionException: If no input file is provided or if something goes wrong during the execution of the command

    Returns:
        subprocess.CompletedProcess: the output process.
    """
    start_time = time_in_ms()
    pdal_env = os.environ.copy()
    pdal_exec = _pdal_executable()
    pdal_command = [pdal_exec, *command_options_args]

    if not input_file:
        raise PDALExecutionException("An input file must be provided")

    temp_dir = mkdtemp()
    if is_s3(input_file):  # Download the file from S3
        local_input_file = os.path.join(temp_dir, input_file.split("/")[-1])
        copy(source=input_file, target=local_input_file)
        input_file = local_input_file

    pdal_command.append(input_file)

    temp_output_file = None
    if output_file:
        if is_s3(output_file):
            temp_output_file = os.path.join(temp_dir, output_file.split("/")[-1])
            pdal_command.append(temp_output_file)
        else:
            pdal_command.append(output_file)

    try:
        get_log().debug("run_pdal_start", command=" ".join(pdal_command))
        proc = subprocess.run(pdal_command, env=pdal_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as cpe:
        get_log().error("run_pdal_failed", command=" ".join(pdal_command), error=str(cpe.stderr, "utf-8"))
        raise PDALExecutionException(f"PDAL {str(cpe.stderr, 'utf-8')}") from cpe
    finally:
        get_log().info("run_pdal_end", command=" ".join(pdal_command), duration=time_in_ms() - start_time)

    if proc.stderr:
        get_log().warning("run_pdal_stderr", command=" ".join(pdal_command), stderr=proc.stderr.decode())

    rmtree(temp_dir)
    if temp_output_file and output_file:  # Upload the file to S3
        copy(source=temp_output_file, target=output_file)

    get_log().trace("run_pdal_succeeded", command=" ".join(pdal_command), stdout=proc.stdout.decode())

    return proc


@cache
def get_pdal_version() -> str:
    """Get the version of PDAL available to this process (cached).

    Raises:
        PDALExecutionException: if the `pdal` executable cannot be run, or reports no version

    Returns:
        the `pdal --version` core output, for example "pdal 2.10.2 (git-version: 27008f)"
    """
    pdal_exec = _pdal_executable()
    try:
        proc = subprocess.run([pdal_exec, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.CalledProcessError, OSError) as error:
        raise PDALExecutionException(f"Could not determine the PDAL version: {error}") from error

    # `pdal --version` frames the version in dashes:
    #     --------------------------------------------------------------------------------
    #     pdal 2.10.2 (git-version: 27008f)
    #     --------------------------------------------------------------------------------
    output = proc.stdout.decode().strip()
    # Keep only non-dash lines.
    version = " ".join(line for line in (raw.strip() for raw in output.splitlines()) if line.strip("-"))

    if not version:  # falsy value raises to prevent empty STAC metadata `processing:software`
        raise PDALExecutionException(f"`{pdal_exec} --version` reported no version: {output!r}")

    return version
