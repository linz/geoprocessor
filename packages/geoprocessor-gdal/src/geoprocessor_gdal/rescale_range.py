from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

UINT16_MAX = 65535


class BandRange(NamedTuple):
    min: int
    max: int


@dataclass(frozen=True)
class RescaleRange:
    """Source pixel ranges to scale to 8-bit, one for all bands or one per band.

    Examples:
        >>> str(RescaleRange.parse("301,4012"))
        '301,4012'
        >>> RescaleRange.parse("301,4012;295,3980;310,4100").ranges[1]
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
    def parse(cls, value: str) -> RescaleRange:
        """Parse `min,max` or `min,max;min,max;min,max`.

        Args:
            value: the rescale range string

        Returns:
            the parsed `RescaleRange`
        """
        try:
            ranges = tuple(BandRange(*(int(number) for number in band.split(","))) for band in value.split(";"))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid rescale range, expected 'min,max' or 'min,max;min,max;min,max': {value}") from e
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
            >>> RescaleRange.parse("301,4012").for_band(3)
            BandRange(min=301, max=4012)
        """
        return self.ranges[0] if len(self.ranges) == 1 else self.ranges[band - 1]
