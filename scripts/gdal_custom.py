import argparse
import os
import sys
import tempfile
from functools import partial
from multiprocessing import Pool
from typing import List

from linz_logger import get_log

from scripts.cli.cli_helper import InputParameterError, TileFiles, load_input_files
from scripts.files.fs import read, write, write_sidecars
from scripts.gdal.gdal_helper import run_gdal
from scripts.logging.time_helper import time_in_ms


def run_custom_gdal(files: TileFiles, command: List[str], target: str) -> None:
    """
    Run custom GDAL processing on the provided files.
    Args:
        files: TileFiles object containing input files and output file name.
        command: List of GDAL command arguments to run.
        target: Target directory where the processed file will be saved.
    Returns:
        None
    """

    processed_path = os.path.join(target, f"{files.output}.tiff")
    # assuming there is only one input file
    input_file = files.inputs[0]
    with tempfile.TemporaryDirectory() as tmp_path:
        target_tmp = f"{tmp_path}/source/"
        tmp_file = os.path.join(tmp_path, os.path.basename(input_file))
        sidecars = [f"{os.path.splitext(input_file)[0]}{extension}" for extension in [".prj", ".tfw"]]
        write_sidecars(sidecars, target_tmp)
        source_file = write(os.path.join(target_tmp, os.path.basename(input_file)), read(input_file))
        run_gdal(
            command=command,
            input_file=source_file,
            output_file=tmp_file,
        )
        write(processed_path, read(tmp_file))


def main() -> None:
    start_time = time_in_ms()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--target", dest="target", required=True, help="Target location")
    parser.add_argument(
        "--gdal-command",
        required=True,
        help="The GDAL command to run on the input files. Do not include the input and output file arguments. "
        "They will be added automatically.",
    )
    arguments = parser.parse_args()
    try:
        tile_files = load_input_files(arguments.from_file)
    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    gdal_command = arguments.gdal_command.strip().split()
    get_log().info(
        "custom_gdal_processing_start",
        command=" ".join(gdal_command),
    )

    with Pool(4) as p:
        tiffs = [
            entry
            for entry in p.map(
                partial(
                    run_custom_gdal,
                    command=gdal_command,
                    target=arguments.target,
                ),
                tile_files,
            )
            if entry is not None
        ]
        p.close()
        p.join()

    get_log().info(
        "custom_gdal_processing_complete",
        action="custom_gdal",
        processed_files=len(tiffs),
        target=arguments.target,
        duration=time_in_ms() - start_time,
    )


if __name__ == "__main__":
    main()
