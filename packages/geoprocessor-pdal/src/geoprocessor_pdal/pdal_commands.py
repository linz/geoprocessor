import os
import subprocess
from functools import cache
from shutil import rmtree
from tempfile import mkdtemp

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
        input_file = copy(source=input_file, target=os.path.join(temp_dir, input_file.split("/")[-1]))

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
