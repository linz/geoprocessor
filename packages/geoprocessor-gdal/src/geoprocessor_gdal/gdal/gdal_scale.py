from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from multiprocessing import Pool
from typing import Any, NamedTuple

import numpy as np
import numpy.typing as npt
import tifffile
from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.files.fs import list_file_names, read, write
from geoprocessor_common.files.fs_s3 import download
from geoprocessor_gdal.gdal.gdal_bands import find_band, get_rgb_bands_args
from geoprocessor_gdal.gdal.gdal_helper import gdal_info, run_gdal
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from linz_logger import get_log

UINT16_MAX = 65535
UINT16_VALUE_COUNT = UINT16_MAX + 1
SAMPLE_SIZE = 1024
BAND_NAMES = {1: ("gray",), 3: ("red", "green", "blue")}
HISTOGRAM_FILE_VERSION = 1
HISTOGRAM_FILE_SUFFIX = ".npz"
HISTOGRAM_FILE_HASH_LENGTH = 12


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

    def for_band(self, band: int) -> BandRange:
        """Get the range of a colour band.

        Args:
            band: band number, starting at 1

        Returns:
            the `BandRange` of the band

        Examples:
            >>> ScaleRange.parse("301,4012").for_band(3)
            BandRange(min=301, max=4012)
        """
        return self.ranges[0] if len(self.ranges) == 1 else self.ranges[band - 1]


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
    if not per_band:
        ranges = (BandRange(min(band_range.min for band_range in ranges), max(band_range.max for band_range in ranges)),)
    for band_range in ranges:
        if band_range.min >= band_range.max:
            raise ValueError(
                f"Low percentile {low_percentile} and high percentile {high_percentile} both give {band_range.min}: {ranges}"
            )
    return ScaleRange(ranges)


def get_clip_percentiles(
    histograms: npt.NDArray[np.int64],
    names: Sequence[str],
    percentiles: Iterable[float],
    combine: Callable[[Iterable[int]], int],
) -> list[dict[str, Any]]:
    """Get the value at each percentile per band and combined for all bands.

    Args:
        histograms: value counts with shape (bands, 65536)
        names: band names
        percentiles: percentiles between 0 and 100
        combine: combines the band values into one value, `min` for low and `max` for high percentiles

    Returns:
        one entry per percentile with the combined value and the value of each band
    """
    entries = []
    for percentile in sorted(percentiles):
        values = {
            name: percentile_from_histogram(histogram, percentile) for name, histogram in zip(names, histograms, strict=True)
        }
        entries.append({"percentile": percentile, "value": combine(values.values()), "bands": values})
    return entries


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
    with tempfile.TemporaryDirectory() as tmp_path:
        local_path = path
        if is_s3(path):
            local_path = os.path.join(tmp_path, os.path.basename(path))
            download(path, local_path)
        info = gdal_info(local_path)
        sample_path = os.path.join(tmp_path, "sample.tiff")
        run_gdal(get_sample_command(info, size), input_file=local_path, output_file=sample_path)
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


def get_histogram_file_name(source: str) -> str:
    """Get the name of the histogram file of a source: its file name and a hash of its full path.

    Args:
        source: path to the source TIFF

    Returns:
        the histogram file name

    Examples:
        >>> get_histogram_file_name("s3://bucket/BQ25_1000_0101.tiff")
        'BQ25_1000_0101.tiff.5a82fdd96e42.npz'
    """
    digest = hashlib.sha256(source.encode()).hexdigest()[:HISTOGRAM_FILE_HASH_LENGTH]
    # Safe in s3 keys and within the 255 byte limit of local file names
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(source))[:200]
    return f"{name}.{digest}{HISTOGRAM_FILE_SUFFIX}"


def histograms_to_bytes(source: str, histograms: npt.NDArray[np.int64], sample_size: int = SAMPLE_SIZE) -> bytes:
    """Serialise the histograms of a source to a compressed `.npz` file.

    Args:
        source: path to the source TIFF
        histograms: value counts with shape (bands, 65536)
        sample_size: maximum width and height the source was sampled at

    Returns:
        the `.npz` file content
    """
    metadata = {
        "version": HISTOGRAM_FILE_VERSION,
        "source": source,
        "bands": BAND_NAMES[len(histograms)],
        "sampleSize": sample_size,
    }
    buffer = io.BytesIO()
    np.savez_compressed(buffer, histograms=histograms, metadata=np.array(json.dumps(metadata)))
    return buffer.getvalue()


def histograms_from_bytes(data: bytes, source: str) -> npt.NDArray[np.int64]:
    """Read the histograms of a source from a `.npz` file.

    Args:
        data: the `.npz` file content
        source: path to the source TIFF the file must belong to

    Returns:
        value counts with shape (bands, 65536)
    """
    with np.load(io.BytesIO(data), allow_pickle=False) as npz:
        metadata = json.loads(str(npz["metadata"]))
        histograms: npt.NDArray[np.int64] = np.array(npz["histograms"], dtype=np.int64)
    if metadata["version"] != HISTOGRAM_FILE_VERSION:
        raise ValueError(f"Expected histogram file version {HISTOGRAM_FILE_VERSION}, got {metadata['version']}: {source}")
    if metadata["source"] != source:
        raise ValueError(f"Expected the histogram file of {source}, got {metadata['source']}")
    return histograms


def get_source_histograms(source: str, histogram_dir: str, saved: bool) -> tuple[str, npt.NDArray[np.int64]]:
    """Read the colour band histograms of a source TIFF from its histogram file, or compute and save them.

    Args:
        source: path to the TIFF
        histogram_dir: directory of the histogram files
        saved: whether the histogram file of the source exists

    Returns:
        the source path and its value counts with shape (bands, 65536)
    """
    path = os.path.join(histogram_dir, get_histogram_file_name(source))
    if saved:
        return source, histograms_from_bytes(read(path), source)
    histograms = get_histograms(source)
    write(path, histograms_to_bytes(source, histograms))
    return source, histograms


def _get_source_histograms(task: tuple[str, str, bool]) -> tuple[str, npt.NDArray[np.int64]]:
    """Unpack the arguments of `get_source_histograms` for `Pool.imap_unordered`."""
    return get_source_histograms(*task)


def sum_histograms(source_histograms: Iterable[tuple[str, npt.NDArray[np.int64]]]) -> npt.NDArray[np.int64]:
    """Sum the histograms of all sources, which must have the same number of bands.

    Args:
        source_histograms: source path and value counts with shape (bands, 65536) of each source

    Returns:
        value counts with shape (bands, 65536)
    """
    total: npt.NDArray[np.int64] | None = None
    for source, histograms in source_histograms:
        if total is None:
            total = histograms.copy()
        elif histograms.shape != total.shape:
            raise ValueError(f"Expected {len(total)} bands like the other sources, got {len(histograms)}: {source}")
        else:
            total += histograms
    if total is None:
        raise ValueError("No histograms to sum")
    return total


def get_dataset_histograms(
    files: list[str], histogram_dir: str, concurrency: int = 1, force: bool = False
) -> npt.NDArray[np.int64]:
    """Sum the colour band histograms of all TIFFs, reading the histogram files already in `histogram_dir`.

    Args:
        files: paths to the TIFFs
        histogram_dir: directory of the histogram file of each TIFF
        concurrency: number of TIFFs to read concurrently
        force: recompute the histogram files that already exist

    Returns:
        value counts with shape (bands, 65536)
    """
    saved = set() if force else list_file_names(histogram_dir, HISTOGRAM_FILE_SUFFIX)
    tasks = [(file, histogram_dir, get_histogram_file_name(file) in saved) for file in files]
    get_log().info("dataset_histograms_start", fileCount=len(files), savedCount=sum(task[2] for task in tasks))
    with Pool(concurrency) as p:
        return sum_histograms(p.imap_unordered(_get_source_histograms, tasks))
