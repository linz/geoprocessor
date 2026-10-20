from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import reduce
from multiprocessing import Pool
from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import tifffile
from geoprocessor_gdal.gdal.gdal_bands import find_band, get_rgb_bands_args
from geoprocessor_gdal.gdal.gdal_helper import gdal_info, run_gdal
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from linz_logger import get_log

UINT16_MAX = 65535
UINT16_VALUE_COUNT = UINT16_MAX + 1
SAMPLE_SIZE = 1024


class BandRange(NamedTuple):
    min: int
    max: int


@dataclass(frozen=True)
class ScaleRange:
    """Source pixel ranges to scale to 8-bit, one for all bands or one per band.

    Examples:
        >>> str(ScaleRange.parse("301,4012"))
        '301,4012'
        >>> ScaleRange.parse("301,4012;295,3980;310,4100").ranges[1]
        BandRange(min=295, max=3980)
    """

    ranges: tuple[BandRange, ...]

    def __post_init__(self) -> None:
        if len(self.ranges) not in (1, 3):
            raise ValueError(f"Expected 1 or 3 band ranges, got {len(self.ranges)}: {self}")
        for band_range in self.ranges:
            if not 0 <= band_range.min < band_range.max <= UINT16_MAX:
                raise ValueError(f"Invalid band range, expected 0 <= min < max <= {UINT16_MAX}: {self}")

    @classmethod
    def parse(cls, value: str) -> ScaleRange:
        """Parse `min,max` or `min,max;min,max;min,max`.

        Args:
            value: the scale range string

        Returns:
            the parsed `ScaleRange`
        """
        try:
            ranges = tuple(BandRange(*(int(number) for number in band.split(","))) for band in value.split(";"))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid scale range, expected 'min,max' or 'min,max;min,max;min,max': {value}") from e
        return cls(ranges)

    def __str__(self) -> str:
        return ";".join(f"{band_range.min},{band_range.max}" for band_range in self.ranges)


def histogram_from_pixels(
    pixels: npt.NDArray[np.uint16], alpha: npt.NDArray[np.uint16] | None = None, nodata: int | None = None
) -> npt.NDArray[np.int64]:
    """Count the values of each band, ignoring transparent, nodata and all-zero pixels.

    Args:
        pixels: pixel values with shape (bands, rows, columns)
        alpha: alpha band with shape (rows, columns)
        nodata: nodata value of the bands

    Returns:
        value counts with shape (bands, 65536)
    """
    valid = np.any(pixels != 0, axis=0)
    if alpha is not None:
        valid &= alpha != 0
    histogram = np.stack([np.bincount(band[valid], minlength=UINT16_VALUE_COUNT) for band in pixels]).astype(np.int64)
    if nodata is not None and 0 <= nodata <= UINT16_MAX:
        histogram[:, nodata] = 0
    return histogram


def percentile_from_histogram(histogram: npt.NDArray[np.int64], percentile: float) -> int:
    """Get the lowest value with at least `percentile` percent of the counted pixels at or below it.

    Args:
        histogram: value counts of a band
        percentile: percentile between 0 and 100

    Returns:
        the value at the percentile
    """
    cumulative = np.cumsum(histogram)
    if cumulative[-1] == 0:
        raise ValueError("Cannot compute a percentile from an empty histogram")
    # At least one pixel so 0% gives the minimum value
    return int(np.searchsorted(cumulative, max(cumulative[-1] * percentile / 100, 1)))


def scale_range_from_histograms(
    histograms: npt.NDArray[np.int64], low_percentile: float, high_percentile: float, per_band: bool
) -> ScaleRange:
    """Get the scale range from the band histograms.

    Args:
        histograms: value counts with shape (bands, 65536)
        low_percentile: percentile to scale to 0
        high_percentile: percentile to scale to 255
        per_band: return one range per band instead of one range for all bands

    Returns:
        the `ScaleRange`
    """
    ranges = tuple(
        BandRange(percentile_from_histogram(histogram, low_percentile), percentile_from_histogram(histogram, high_percentile))
        for histogram in histograms
    )
    if per_band:
        return ScaleRange(ranges)
    return ScaleRange((BandRange(min(band_range.min for band_range in ranges), max(band_range.max for band_range in ranges)),))


def get_sample_command(info: GdalInfo, size: int = SAMPLE_SIZE) -> list[str]:
    """Get a `gdal_translate` command to read the colour and alpha bands at reduced resolution.

    Args:
        info: gdalinfo of the source file
        size: maximum width and height of the sample

    Returns:
        a list of arguments to run `gdal_translate`
    """
    width, height = info["size"]
    factor = min(1.0, size / max(width, height))
    bands = info["bands"]
    if band_gray := find_band(bands, "Gray"):
        band_args = ["-b", str(band_gray["band"])]
    else:
        band_args = get_rgb_bands_args(bands)
    if band_alpha := find_band(bands, "Alpha"):
        band_args += ["-b", str(band_alpha["band"])]
    return [
        "gdal_translate",
        "-q",
        "-of",
        "GTiff",
        "-co",
        "interleave=band",
        "-outsize",
        str(max(1, round(width * factor))),
        str(max(1, round(height * factor))),
        "-r",
        "nearest",
        *band_args,
    ]


def get_histograms(path: str, size: int = SAMPLE_SIZE) -> npt.NDArray[np.int64]:
    """Get the colour band histograms of a TIFF read at reduced resolution.

    Args:
        path: path to the TIFF
        size: maximum width and height of the sample

    Returns:
        value counts with shape (bands, 65536)
    """
    info = gdal_info(path, vsis3=True)
    with tempfile.TemporaryDirectory() as tmp_path:
        sample_path = os.path.join(tmp_path, "sample.tiff")
        run_gdal(get_sample_command(info, size), input_file=path, output_file=sample_path, vsis3=True)
        pixels = tifffile.imread(sample_path)
    if pixels.dtype != np.uint16:
        raise ValueError(f"Expected uint16 pixels, got {pixels.dtype}: {path}")
    if pixels.ndim == 2:
        pixels = pixels[np.newaxis]
    alpha = None
    if find_band(info["bands"], "Alpha"):
        alpha = pixels[-1]
        pixels = pixels[:-1]
    nodata = info["bands"][0].get("noDataValue")
    histograms = histogram_from_pixels(pixels, alpha=alpha, nodata=None if nodata is None else int(nodata))
    get_log().debug("histograms_computed", path=path, pixelCount=int(histograms[0].sum()))
    return histograms


def get_dataset_histograms(files: list[str], concurrency: int = 1) -> npt.NDArray[np.int64]:
    """Sum the colour band histograms of all TIFFs.

    Args:
        files: paths to the TIFFs
        concurrency: number of TIFFs to read concurrently

    Returns:
        value counts with shape (bands, 65536)
    """
    with Pool(concurrency) as p:
        histograms: npt.NDArray[np.int64] = reduce(np.add, p.imap_unordered(get_histograms, files))
    return histograms
