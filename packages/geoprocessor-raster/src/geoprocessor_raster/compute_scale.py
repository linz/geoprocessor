import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from geoprocessor_common.cli.cli_helper import InputParameterError, load_input_files, str_to_bool, str_to_positive_int
from geoprocessor_common.files.files_helper import ContentType, is_tiff
from geoprocessor_common.files.fs import write
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_gdal.gdal.gdal_scale import get_dataset_histograms, percentile_from_histogram, scale_range_from_histograms
from geoprocessor_stac.json_codec import dict_to_json_bytes
from linz_logger import get_log

SCALE_RANGE_FILE_NAME = "scale-range"


def str_to_percentile(value: str) -> float:
    """Parse a percentile between 0 and 100.

    Args:
        value: the percentile string

    Returns:
        the percentile
    """
    try:
        percentile = float(value)
    except ValueError as e:
        raise ArgumentTypeError(f"not a number: {value}") from e
    if not 0 <= percentile <= 100:
        raise ArgumentTypeError(f"not between 0 and 100: {value}")
    return percentile


def get_args_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Compute the range to scale 16-bit TIFFs to 8-bit from the pixel values of all TIFFs.")
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--target", dest="target", required=True, help="Output directory")
    parser.add_argument(
        "--low-percentile",
        dest="low_percentile",
        type=str_to_percentile,
        default=1.0,
        help="Percentile scaled to 0. Defaults to 1.",
    )
    parser.add_argument(
        "--high-percentile",
        dest="high_percentile",
        type=str_to_percentile,
        default=99.0,
        help="Percentile scaled to 255. Defaults to 99.",
    )
    parser.add_argument(
        "--per-band",
        dest="per_band",
        type=str_to_bool,
        default=False,
        help="Compute one range per band instead of one range for all bands ('true' / 'false'). Defaults to false.",
    )
    parser.add_argument(
        "--concurrency",
        dest="concurrency",
        type=str_to_positive_int,
        default=1,
        help="Number of concurrent tiffs to read. Defaults to 1.",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    start_time = time_in_ms()
    parser = get_args_parser()
    arguments = parser.parse_args(args)
    if arguments.low_percentile >= arguments.high_percentile:
        parser.error("--low-percentile must be lower than --high-percentile")

    try:
        tile_files = load_input_files(arguments.from_file)
    except InputParameterError as e:
        get_log().error("An error occurred when loading the input file.", error=str(e))
        sys.exit(1)

    files = sorted({path for tile in tile_files for path in tile.inputs if is_tiff(path)})
    if not files:
        get_log().error("compute_scale_no_tiff", from_file=arguments.from_file)
        sys.exit(1)

    get_log().info("compute_scale_start", fileCount=len(files))
    histograms = get_dataset_histograms(files, arguments.concurrency)
    scale_range = scale_range_from_histograms(
        histograms, arguments.low_percentile, arguments.high_percentile, arguments.per_band
    )

    write(os.path.join(arguments.target, SCALE_RANGE_FILE_NAME), str(scale_range).encode("utf-8"))
    write(
        os.path.join(arguments.target, f"{SCALE_RANGE_FILE_NAME}.json"),
        dict_to_json_bytes(
            {
                "scaleRange": str(scale_range),
                "lowPercentile": arguments.low_percentile,
                "highPercentile": arguments.high_percentile,
                "perBand": arguments.per_band,
                "bands": [
                    {
                        "low": percentile_from_histogram(histogram, arguments.low_percentile),
                        "high": percentile_from_histogram(histogram, arguments.high_percentile),
                        "pixelCount": int(histogram.sum()),
                    }
                    for histogram in histograms
                ],
                "fileCount": len(files),
            }
        ),
        content_type=ContentType.JSON.value,
    )

    get_log().info("compute_scale_end", scaleRange=str(scale_range), fileCount=len(files), duration=time_in_ms() - start_time)


if __name__ == "__main__":
    main()
