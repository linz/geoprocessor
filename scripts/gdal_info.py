import argparse
import json
import os
import sys
import tempfile
from functools import partial
from multiprocessing import Pool
from typing import Any, Dict

from linz_logger import get_log

from scripts.cli.cli_helper import InputParameterError
from scripts.files.fs import read, write
from scripts.gdal.gdal_helper import gdal_info
from scripts.logging.time_helper import time_in_ms


def run_gdalinfo(file: str) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp_path:
        target_tmp = f"{tmp_path}/source/"
        source_file = write(os.path.join(target_tmp, os.path.basename(file)), read(file))
        gdalinfo_result = gdal_info(source_file)
        bands_info = gdalinfo_result.get("bands", [])
        get_log().info("bands_info", file=file, bands=len(bands_info), details=bands_info)
        return {file: bands_info}


def main() -> None:
    start_time = time_in_ms()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--report-location", dest="report_location", required=True)
    arguments = parser.parse_args()
    try:
        groups = json.loads(read(arguments.from_file))
        all_files = [file for group in groups for file in group]

    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    get_log().info("bulk_gdal_info_start")

    with Pool(4) as p:
        tiffs = [
            entry
            for entry in p.map(
                partial(run_gdalinfo),
                all_files,
            )
            if entry is not None
        ]
        p.close()
        p.join()

    write(arguments.report_location, json.dumps(tiffs, ensure_ascii=False).encode("utf-8"))

    get_log().info(
        "bulk_gdal_info_complete",
        action="gdal_info",
        files=len(tiffs),
        duration=time_in_ms() - start_time,
    )


if __name__ == "__main__":
    main()
