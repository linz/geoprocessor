import json
import os
import subprocess
from functools import cache
from shutil import rmtree
from tempfile import mkdtemp
from typing import cast

from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_common.files.files_helper import get_file_name_from_path
from geoprocessor_common.files.fs import copy
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from linz_logger import get_log


class GDALExecutionException(Exception):
    pass


def get_vfs_path(path: str) -> str:
    """Make the path as a GDAL Virtual File Systems path.

    Args:
        path (str): a path to a file.

    Returns:
        str: the path modified to comply with the corresponding storage service.
    Examples:
        >>> get_vfs_path("s3://scratch-bucket/path/to/file.tiff")
        '/vsis3/scratch-bucket/path/to/file.tiff'
    """
    return path.replace("s3://", "/vsis3/")


def command_to_string(command: list[str]) -> str:
    """Format the command, each arguments separated by a white space.

    Args:
        command (list[str]): each arguments of the command as a string in a list.

    Returns:
        str: the formatted command.
    """
    return " ".join(command)


def run_gdal(
    command: list[str],
    input_file: str | None = None,
    output_file: str | None = None,
) -> "subprocess.CompletedProcess[bytes]":
    """Run the GDAL command. The permissions to access to the input file are applied to the gdal environment.

    Args:
        command: each arguments of the GDAL command
        input_file: the input file path
        output_file: the output file path

    Raises:
        CalledProcessError is raised if something goes wrong during the execution of the command

    Returns:
        subprocess.CompletedProcess: the output process.
    """
    gdal_env = os.environ.copy()
    temp_command = command.copy()
    temp_dir = None

    if input_file:
        if is_s3(input_file):
            # Download the file from S3
            temp_dir = mkdtemp()
            input_file = copy(source=input_file, target=os.path.join(temp_dir, get_file_name_from_path(input_file)))

        temp_command.append(input_file)

    if output_file:
        temp_command.append(output_file)

    start_time = time_in_ms()
    try:
        get_log().debug("run_gdal_start", command=command_to_string(temp_command))
        proc = subprocess.run(temp_command, env=gdal_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as cpe:
        get_log().error("run_gdal_failed", command=command_to_string(temp_command), error=str(cpe.stderr, "utf-8"))
        raise GDALExecutionException(f"GDAL {str(cpe.stderr, 'utf-8')}") from cpe
    finally:
        get_log().info("run_gdal_end", command=command_to_string(temp_command), duration=time_in_ms() - start_time)

    if proc.stderr:
        get_log().warning("run_gdal_stderr", command=command_to_string(temp_command), stderr=proc.stderr.decode())

    if temp_dir:
        rmtree(temp_dir)

    get_log().trace("run_gdal_succeeded", command=command_to_string(temp_command), stdout=proc.stdout.decode())

    return proc


@cache
def get_gdal_version() -> str:
    """Get the version of GDAL available to this process (cached).

    Raises:
        GDALExecutionException: if `gdalinfo` cannot be run, or reports no version

    Returns:
        the `gdalinfo --version` output, for example "GDAL 3.10.3, released 2025/04/01"
    """
    version = run_gdal(["gdalinfo", "--version"]).stdout.decode().strip()
    if not version:  # falsy value raises to prevent empty STAC metadata `processing:software`
        raise GDALExecutionException("`gdalinfo --version` reported no version")

    return version


def get_srs_command(epsg: int = EpsgNumber.NZTM_2000) -> list[str]:
    """Build a `gdalsrsinfo` command for the given EPSG code.

    Args:
        epsg: the EPSG code to get the srs for. Defaults to 2193 (NZTM).

    Returns:
        a list of arguments to run `gdalsrsinfo`

    Examples:
        >>> get_srs_command(EpsgNumber.NZTM_2000)
        ['gdalsrsinfo', '-o', 'wkt', 'EPSG:2193']
        >>> get_srs_command(EpsgNumber.CITM_2000)
        ['gdalsrsinfo', '-o', 'wkt', 'EPSG:3793']
    """
    return ["gdalsrsinfo", "-o", "wkt", f"EPSG:{epsg}"]


def get_srs(epsg: int = EpsgNumber.NZTM_2000) -> bytes:
    """Run `gdalsrsinfo` with the given EPSG code.

    Args:
        epsg: the EPSG code to get the srs for. Defaults to 2193 (NZTM).

    Raises:
        Exception: if `gdal` has an stderr

    Returns:
        the output of `gdalsrsinfo`
    """
    gdalsrsinfo_result = run_gdal(get_srs_command(epsg))
    if gdalsrsinfo_result.stderr:
        raise Exception(
            f"Error trying to retrieve srs from epsg code, no files have been checked\n{gdalsrsinfo_result.stderr!r}"
        )
    return gdalsrsinfo_result.stdout


def gdal_info(path: str) -> GdalInfo:
    """run gdalinfo on the provided file

    Args:
        path: path to file to gdalinfo

    Returns:
        GdalInfo output
    """
    # Set GDAL_PAM_ENABLED to NO to temporarily disable PAM support and prevent creation of auxiliary XML file.
    gdalinfo_command = ["gdalinfo", "-json", "--config", "GDAL_PAM_ENABLED", "NO"]

    try:
        gdalinfo_process = run_gdal(gdalinfo_command, path)
        return cast(GdalInfo, json.loads(gdalinfo_process.stdout))
    except json.JSONDecodeError as e:
        get_log().error("load_gdalinfo_result_error", file=path, error=e)
        raise e
    except GDALExecutionException as e:
        get_log().error("gdalinfo_failed", file=path, error=str(e))
        raise e


def is_geotiff(path: str, gdalinfo_data: GdalInfo | None = None) -> bool:
    """Verifies if a file is a GTiff based on the presence of the
    `coordinateSystem`.

    Args:
        path: a path to a file
        gdalinfo_data: gdalinfo of the file. Defaults to None.

    Returns:
        True if the file is a GTiff
    """
    if not gdalinfo_data:
        gdalinfo_data = gdal_info(path)
    if "coordinateSystem" not in gdalinfo_data:
        return False
    if gdalinfo_data["driverShortName"] == "GTiff":
        return True
    return False
