import math
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from geoprocessor_common.cli.cli_helper import InputParameterError, load_input_files, str_to_bool, str_to_positive_int
from geoprocessor_common.files.files_helper import ContentType, is_tiff
from geoprocessor_common.files.fs import write
from geoprocessor_common.log.time_helper import time_in_ms
from geoprocessor_gdal.gdal.gdal_rescale import (
    BAND_NAMES,
    get_clip_percentiles,
    get_dataset_histograms,
    percentile_from_histogram,
    rescale_range_from_histograms,
)
from geoprocessor_stac.json_codec import dict_to_json_bytes
from linz_logger import get_log

RESCALE_RANGE_FILE_NAME = "rescale-range"
# Clip percentiles at each end: 0 to 1 in 0.1 steps, then up to 5 in 0.5 steps
CLIP_PERCENTILES = tuple(step / 10 for step in range(10)) + tuple(step / 2 for step in range(2, 11))


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


def str_to_positive_float(value: str) -> float:
    """Parse a positive number.

    Args:
        value: the number string

    Returns:
        the number
    """
    try:
        number = float(value)
    except ValueError as e:
        raise ArgumentTypeError(f"not a number: {value}") from e
    if not math.isfinite(number) or number <= 0:
        raise ArgumentTypeError(f"not a positive number: {value}")
    return number


def get_args_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Compute the range to scale 16-bit TIFFs to 8-bit from the pixel values of all TIFFs.")
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--target", dest="target", required=True, help="Output directory")
    parser.add_argument(
        "--histogram-dir",
        dest="histogram_dir",
        help="Directory of the histogram file of each TIFF, reused on the next run. Defaults to <target>/histograms.",
    )
    parser.add_argument(
        "--rescale-clip-low-percentile",
        dest="rescale_clip_low_percentile",
        type=str_to_percentile,
        default=0.5,
        help="Percentile scaled to 0. Defaults to 0.5.",
    )
    parser.add_argument(
        "--rescale-clip-high-percentile",
        dest="rescale_clip_high_percentile",
        type=str_to_percentile,
        default=99.5,
        help="Percentile scaled to 255. Defaults to 99.5.",
    )
    parser.add_argument(
        "--rescale-per-band",
        dest="rescale_per_band",
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
    parser.add_argument(
        "--max-download-gb",
        dest="max_download_gb",
        type=str_to_positive_float,
        help="Maximum size in GB of the source TIFFs downloaded at a time, lowers the concurrency for large TIFFs. "
        "Defaults to no limit.",
    )
    parser.add_argument(
        "--force",
        dest="force",
        help="Recompute the histogram files that already exist. Defaults to False.",
        action="store_true",
    )
    return parser


def main(args: list[str] | None = None) -> None:
    start_time = time_in_ms()
    parser = get_args_parser()
    arguments = parser.parse_args(args)
    if arguments.rescale_clip_low_percentile >= arguments.rescale_clip_high_percentile:
        parser.error("--rescale-clip-low-percentile must be lower than --rescale-clip-high-percentile")

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
    histogram_dir = arguments.histogram_dir or os.path.join(arguments.target, "histograms")
    max_download_bytes = None if arguments.max_download_gb is None else int(arguments.max_download_gb * 1e9)
    histograms = get_dataset_histograms(files, histogram_dir, arguments.concurrency, arguments.force, max_download_bytes)
    try:
        rescale_range = rescale_range_from_histograms(
            histograms,
            arguments.rescale_clip_low_percentile,
            arguments.rescale_clip_high_percentile,
            arguments.rescale_per_band,
        )
    except ValueError as e:
        get_log().error("compute_scale_failed", error=str(e))
        sys.exit(1)
    band_names = BAND_NAMES[len(histograms)]

    write(os.path.join(arguments.target, RESCALE_RANGE_FILE_NAME), str(rescale_range).encode("utf-8"))
    write(
        os.path.join(arguments.target, f"{RESCALE_RANGE_FILE_NAME}.json"),
        dict_to_json_bytes(
            {
                "rescaleRange": str(rescale_range),
                "rescaleClipLowPercentile": arguments.rescale_clip_low_percentile,
                "rescaleClipHighPercentile": arguments.rescale_clip_high_percentile,
                "rescalePerBand": arguments.rescale_per_band,
                "bands": [
                    {
                        "name": name,
                        "low": percentile_from_histogram(histogram, arguments.rescale_clip_low_percentile),
                        "high": percentile_from_histogram(histogram, arguments.rescale_clip_high_percentile),
                        "pixelCount": int(histogram.sum()),
                    }
                    for name, histogram in zip(band_names, histograms, strict=True)
                ],
                "rescaleClipPercentiles": {
                    "low": get_clip_percentiles(
                        histograms, band_names, {*CLIP_PERCENTILES, arguments.rescale_clip_low_percentile}, min
                    ),
                    "high": get_clip_percentiles(
                        histograms,
                        band_names,
                        {*(round(100 - p, 1) for p in CLIP_PERCENTILES), arguments.rescale_clip_high_percentile},
                        max,
                    ),
                },
                "fileCount": len(files),
            }
        ),
        content_type=ContentType.JSON.value,
    )

    get_log().info(
        "compute_scale_end", rescaleRange=str(rescale_range), fileCount=len(files), duration=time_in_ms() - start_time
    )


if __name__ == "__main__":
    main()
