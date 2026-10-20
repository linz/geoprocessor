from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import numpy.typing as npt

UINT16_MAX = 65535
UINT16_VALUE_COUNT = UINT16_MAX + 1


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
