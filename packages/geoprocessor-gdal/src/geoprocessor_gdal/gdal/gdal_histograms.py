import math
import os
import tempfile
from collections.abc import Iterable
from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import tifffile
from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.files.fs_s3 import download
from geoprocessor_gdal.gdal.gdal_bands import find_band, get_rgb_bands_args
from geoprocessor_gdal.gdal.gdal_helper import gdal_info, run_gdal
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from geoprocessor_gdal.rescale_range import UINT16_MAX, BandRange, RescaleRange
from linz_logger import get_log

UINT16_VALUE_COUNT = UINT16_MAX + 1
SAMPLE_SIZE = 1024
SAMPLE_CACHE_MIN_MB = 32
BAND_NAMES = {1: ("gray",), 3: ("red", "green", "blue")}


# Rec. 709 luminance weights of the red, green and blue bands, https://en.wikipedia.org/wiki/Rec._709#Luma_coefficients
LUMINANCE_WEIGHTS = np.array([0.2126, 0.7152, 0.0722])


class Histograms(NamedTuple):
    """Value counts of each colour band, with shape (bands, 65536), and of their luminance, with shape (65536,)."""

    bands: npt.NDArray[np.int64]
    luminance: npt.NDArray[np.int64]


def get_counted_pixels(
    pixels: npt.NDArray[np.uint16], alpha: npt.NDArray[np.uint16] | None = None, nodata: int | None = None
) -> npt.NDArray[np.bool_]:
    """Get the pixels to count: not transparent, and not zero or nodata in every band.

    Args:
        pixels: pixel values with shape (bands, rows, columns)
        alpha: alpha band with shape (rows, columns)
        nodata: nodata value of the bands

    Returns:
        whether each pixel is counted, with shape (rows, columns)
    """
    counted: npt.NDArray[np.bool_] = np.any(pixels != 0, axis=0)
    if alpha is not None:
        counted &= alpha != 0
    if nodata is not None:
        counted &= np.any(pixels != nodata, axis=0)
    return counted


def histogram_from_pixels(
    pixels: npt.NDArray[np.uint16], alpha: npt.NDArray[np.uint16] | None = None, nodata: int | None = None
) -> npt.NDArray[np.int64]:
    """Count the values of each band of the pixels from `get_counted_pixels`.

    Args:
        pixels: pixel values with shape (bands, rows, columns)
        alpha: alpha band with shape (rows, columns)
        nodata: nodata value of the bands

    Returns:
        value counts with shape (bands, 65536)
    """
    counted = get_counted_pixels(pixels, alpha, nodata)
    return np.stack([np.bincount(band[counted], minlength=UINT16_VALUE_COUNT) for band in pixels]).astype(np.int64)


def luminance_from_pixels(
    pixels: npt.NDArray[np.uint16], alpha: npt.NDArray[np.uint16] | None = None, nodata: int | None = None
) -> npt.NDArray[np.int64]:
    """Count the luminance values of the pixels from `get_counted_pixels`.

    Args:
        pixels: gray or red, green and blue pixel values with shape (bands, rows, columns)
        alpha: alpha band with shape (rows, columns)
        nodata: nodata value of the bands

    Returns:
        value counts with shape (65536,)

    Examples:
        >>> pixels = np.array([[[1000, 0]], [[2000, 0]], [[3000, 0]]], dtype=np.uint16)
        >>> np.flatnonzero(luminance_from_pixels(pixels)).tolist()
        [1860]
    """
    counted = get_counted_pixels(pixels, alpha, nodata)
    values = pixels[0][counted] if len(pixels) == 1 else np.rint(LUMINANCE_WEIGHTS @ pixels[:, counted]).astype(np.uint16)
    return np.bincount(values, minlength=UINT16_VALUE_COUNT).astype(np.int64)


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


def rescale_range_from_histograms(
    histograms: npt.NDArray[np.int64],
    rescale_clip_low_percentile: float,
    rescale_clip_high_percentile: float,
    rescale_per_band: bool,
) -> RescaleRange:
    """Get the rescale range from the band histograms.

    Args:
        histograms: value counts with shape (bands, 65536)
        rescale_clip_low_percentile: percentile to scale to 0
        rescale_clip_high_percentile: percentile to scale to 255
        rescale_per_band: return one range per band instead of one range for all bands

    Returns:
        the `RescaleRange`
    """
    ranges = tuple(
        BandRange(
            percentile_from_histogram(histogram, rescale_clip_low_percentile),
            percentile_from_histogram(histogram, rescale_clip_high_percentile),
        )
        for histogram in histograms
    )
    if not rescale_per_band:
        ranges = (BandRange(min(band_range.min for band_range in ranges), max(band_range.max for band_range in ranges)),)
    for band_range in ranges:
        if band_range.min >= band_range.max:
            raise ValueError(
                f"Low percentile {rescale_clip_low_percentile} and high percentile {rescale_clip_high_percentile} "
                f"both give {band_range.min}: {ranges}"
            )
    return RescaleRange(ranges)


def get_clip_percentiles(histograms: npt.NDArray[np.int64], percentiles: Iterable[float]) -> dict[str, list[int]]:
    """Get the value of each band at each percentile.

    Args:
        histograms: value counts with shape (bands, 65536)
        percentiles: percentiles between 0 and 100

    Returns:
        the value of each band, per percentile

    Examples:
        >>> bands = np.zeros((2, 65536), dtype=np.int64)
        >>> bands[0, 10:20] = bands[1, 30:40] = 1
        >>> get_clip_percentiles(bands, [100, 0])
        {'0': [10, 30], '100': [19, 39]}
    """
    return {
        f"{percentile:g}": [percentile_from_histogram(histogram, percentile) for histogram in histograms]
        for percentile in sorted(percentiles)
    }


def get_sample_step(info: GdalInfo, size: int = SAMPLE_SIZE) -> int:
    """Get the step between the sampled pixels so that the sample fits in `size`.

    Args:
        info: gdalinfo of the source file
        size: maximum width and height of the sample

    Returns:
        the step in pixels, 1 to read every pixel

    Examples:
        >>> get_sample_step({"size": [3200, 4800]}, 1024)
        5
        >>> get_sample_step({"size": [2048, 1024]}, 1024)
        2
        >>> get_sample_step({"size": [500, 400]}, 1024)
        1
    """
    return math.ceil(max(info["size"]) / size)


def get_sample_cache_mb(info: GdalInfo, max_cache_mb: int) -> int:
    """Get the GDAL block cache that holds one row of blocks of every band, so that each block is decoded once.

    Args:
        info: gdalinfo of the source file
        max_cache_mb: maximum cache in MB

    Returns:
        the cache in MB, at least `SAMPLE_CACHE_MIN_MB` and at most `max_cache_mb`

    Examples:
        >>> get_sample_cache_mb({"size": [10000, 15000], "bands": [{"block": [512, 512]}] * 4}, 4096)
        50
    """
    bands = info["bands"]
    block_width, block_height = bands[0]["block"]
    blocks_per_row = math.ceil(info["size"][0] / block_width)
    # Pixel-interleaved sources cache the blocks of every band, sampled or not
    row_bytes = blocks_per_row * block_width * block_height * len(bands) * np.dtype(np.uint16).itemsize
    cache_mb = max(SAMPLE_CACHE_MIN_MB, math.ceil(row_bytes * 1.25 / 2**20))
    if cache_mb > max_cache_mb:
        get_log().warning("sample_cache_capped", path=info["description"], cacheMb=max_cache_mb, requiredCacheMb=cache_mb)
        return max_cache_mb
    return cache_mb


def get_sample_command(info: GdalInfo, step: int, cache_mb: int) -> list[str]:
    """Get a `gdal_translate` command to sample every `step`th full-resolution pixel of the colour and alpha bands.

    Args:
        info: gdalinfo of the source file
        step: step between the sampled pixels
        cache_mb: GDAL block cache in MB

    Returns:
        a list of arguments to run `gdal_translate`
    """
    width, height = info["size"]
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
        "--config",
        "GDAL_CACHEMAX",
        str(cache_mb),
        # Overviews are averaged, which narrows the histogram
        "-oo",
        "OVERVIEW_LEVEL=NONE",
        "-of",
        "GTiff",
        "-co",
        "interleave=band",
        "-outsize",
        str(math.ceil(width / step)),
        str(math.ceil(height / step)),
        "-r",
        "nearest",
        *band_args,
    ]


def get_histograms(path: str, size: int = SAMPLE_SIZE, max_cache_mb: int = SAMPLE_CACHE_MIN_MB) -> Histograms:
    """Get the colour band and luminance histograms of a TIFF read at reduced resolution.

    Args:
        path: path to the TIFF
        size: maximum width and height of the sample
        max_cache_mb: maximum GDAL block cache in MB

    Returns:
        value counts of the bands and of their luminance, scaled to the full resolution of the TIFF
    """
    with tempfile.TemporaryDirectory() as tmp_path:
        local_path = path
        if is_s3(path):
            local_path = os.path.join(tmp_path, os.path.basename(path))
            download(path, local_path)
        info = gdal_info(local_path)
        step = get_sample_step(info, size)
        sample_path = os.path.join(tmp_path, "sample.tiff")
        command = get_sample_command(info, step, get_sample_cache_mb(info, max_cache_mb))
        run_gdal(command, input_file=local_path, output_file=sample_path)
        pixels = tifffile.imread(sample_path)
    if pixels.dtype != np.uint16:
        raise ValueError(f"Expected uint16 pixels, got {pixels.dtype}: {path}")
    if pixels.ndim == 2:
        pixels = pixels[np.newaxis]
    alpha = None
    if find_band(info["bands"], "Alpha"):
        alpha = pixels[-1]
        pixels = pixels[:-1]
    nodata_value = info["bands"][0].get("noDataValue")
    nodata = None if nodata_value is None else int(nodata_value)
    # Each sampled pixel stands for step x step source pixels
    weight = step * step
    histograms = Histograms(
        histogram_from_pixels(pixels, alpha=alpha, nodata=nodata) * weight,
        luminance_from_pixels(pixels, alpha=alpha, nodata=nodata) * weight,
    )
    get_log().debug("histograms_computed", path=path, pixelCount=int(histograms.bands[0].sum()))
    return histograms
