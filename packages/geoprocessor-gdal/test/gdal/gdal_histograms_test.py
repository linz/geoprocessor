from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import numpy as np
import numpy.typing as npt
import tifffile
from fake_gdalinfo import add_band, fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_histograms import (
    get_histograms,
    get_sample_cache_mb,
    get_sample_command,
    histogram_from_pixels,
    luminance_from_pixels,
    percentile_from_histogram,
    rescale_gamma_from_median,
    rescale_range_from_histograms,
)
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from geoprocessor_gdal.rescale_range import BandRange, RescaleRange
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests


def staggered_bands() -> npt.NDArray[np.int64]:
    """Histograms of three bands with one pixel per value: red 100-199, green 150-399, blue 50-299."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[0, 100:200] = bands[1, 150:400] = bands[2, 50:300] = 1
    return bands


def rgb_gdalinfo(
    width: int, height: int, alpha: bool = True, no_data_value: int | None = None, block: tuple[int, int] = (256, 256)
) -> GdalInfo:
    """`gdalinfo` of a `width` x `height` RGB TIFF in `block` blocks, with an alpha band unless `alpha` is false."""
    gdalinfo: GdalInfo = fake_gdalinfo()
    gdalinfo["description"] = "file.tiff"
    gdalinfo["size"] = [width, height]
    for color in ["Red", "Green", "Blue"] + (["Alpha"] if alpha else []):
        add_band(gdalinfo, color, no_data_value)
        gdalinfo["bands"][-1]["block"] = list(block)
    return gdalinfo


def sample_writer(pixels: npt.NDArray[Any]) -> Callable[..., None]:
    """Fake `run_gdal` that writes `pixels` as the sample TIFF."""

    def write_sample(_command: list[str], **kwargs: Any) -> None:
        tifffile.imwrite(kwargs["output_file"], pixels, photometric="minisblack", planarconfig="separate")

    return write_sample


@contextmanager
def sampling(pixels: npt.NDArray[Any], gdalinfo: GdalInfo | None = None) -> Iterator[tuple[MagicMock, MagicMock, MagicMock]]:
    """Patch downloading, `gdalinfo` and sampling so that every source TIFF is sampled as `pixels`.

    Yields:
        the mocked `download`, `gdal_info` and `run_gdal`
    """
    with (
        patch("geoprocessor_gdal.gdal.gdal_histograms.download") as download,
        patch(
            "geoprocessor_gdal.gdal.gdal_histograms.gdal_info", return_value=gdalinfo or rgb_gdalinfo(2, 2, alpha=False)
        ) as info,
        patch("geoprocessor_gdal.gdal.gdal_histograms.run_gdal", side_effect=sample_writer(pixels)) as run,
    ):
        yield download, info, run


def test_histogram_from_pixels(subtests: SubTests) -> None:
    """Pixel values are counted per band, leaving out all-zero, transparent and nodata pixels."""
    with subtests.test(msg="counts each band"):
        histogram = histogram_from_pixels(np.array([[[1, 2], [2, 3]], [[10, 10], [10, 10]]], dtype=np.uint16))
        assert histogram.shape == (2, 65536)
        assert histogram[0, 1:4].tolist() == [1, 2, 1]
        assert histogram[1, 10] == 4

    pixels = np.array([[[0, 5], [7, 9]], [[0, 0], [7, 9]]], dtype=np.uint16)

    with subtests.test(msg="ignores all-zero pixels"):
        histogram = histogram_from_pixels(pixels)
        assert histogram.sum(axis=1).tolist() == [3, 3]
        assert histogram[1, 0] == 1

    with subtests.test(msg="ignores transparent pixels"):
        histogram = histogram_from_pixels(pixels, alpha=np.array([[65535, 65535], [0, 65535]], dtype=np.uint16))
        assert histogram[0, 7] == 0
        assert histogram.sum(axis=1).tolist() == [2, 2]

    with subtests.test(msg="ignores nodata pixels"):
        assert histogram_from_pixels(pixels, nodata=9)[:, 9].tolist() == [0, 0]

    with subtests.test(msg="counts a pixel with only some bands at nodata"):
        assert histogram_from_pixels(pixels, nodata=5)[:, [0, 5]].tolist() == [[0, 1], [1, 0]]


def test_luminance_from_pixels(subtests: SubTests) -> None:
    """Luminance is the weighted sum of red, green and blue, leaving out the same pixels as the band histograms."""
    pixels = np.array([[[1000, 0, 7, 1000]], [[2000, 0, 7, 2000]], [[3000, 0, 7, 3000]]], dtype=np.uint16)

    with subtests.test(msg="weighted sum of red, green and blue, without all-zero and nodata pixels"):
        assert np.flatnonzero(luminance_from_pixels(pixels, nodata=7)).tolist() == [1860]
        assert luminance_from_pixels(pixels, nodata=7)[1860] == 2

    with subtests.test(msg="with a pixel with only some bands at nodata"):
        assert luminance_from_pixels(pixels, nodata=1000)[1860] == 2

    with subtests.test(msg="without transparent pixels"):
        alpha = np.array([[65535, 65535, 65535, 0]], dtype=np.uint16)
        assert luminance_from_pixels(pixels, alpha=alpha, nodata=7)[1860] == 1

    with subtests.test(msg="gray is its own luminance"):
        assert np.flatnonzero(luminance_from_pixels(pixels[:1])).tolist() == [7, 1000]


def test_percentile_from_histogram(subtests: SubTests) -> None:
    """Percentiles read off a histogram match `np.percentile` on the pixel values."""
    values = np.random.default_rng(42).integers(100, 5000, size=10_000, dtype=np.uint16)
    histogram = np.bincount(values, minlength=65536).astype(np.int64)

    for percentile in [1, 2, 50, 98, 99, 100]:
        with subtests.test(msg=f"matches numpy at {percentile}%"):
            expected = int(np.percentile(values, percentile, method="inverted_cdf"))
            assert percentile_from_histogram(histogram, percentile) == expected

    with subtests.test(msg="0% is the minimum"):
        assert percentile_from_histogram(histogram, 0) == values.min()

    with subtests.test(msg="rejects an empty histogram"):
        with raises(ValueError, match="empty histogram"):
            percentile_from_histogram(np.zeros(65536, dtype=np.int64), 1)


def test_rescale_range_from_histograms(subtests: SubTests) -> None:
    """The clip percentiles give one range across all bands or one per band, and must not give the same value."""
    bands = staggered_bands()

    with subtests.test(msg="single range"):
        assert rescale_range_from_histograms(bands, 0, 100, rescale_per_band=False) == RescaleRange((BandRange(50, 399),))

    with subtests.test(msg="per band"):
        assert rescale_range_from_histograms(bands, 0, 100, rescale_per_band=True) == RescaleRange(
            (BandRange(100, 199), BandRange(150, 399), BandRange(50, 299))
        )

    with subtests.test(msg="rejects percentiles giving the same value"):
        narrow = np.zeros((3, 65536), dtype=np.int64)
        narrow[:, 1000] = 100
        narrow[0, 2000] = 1
        with raises(ValueError, match="Low percentile 1 and high percentile 99 both give 1000"):
            rescale_range_from_histograms(narrow, 1, 99, rescale_per_band=True)
        assert rescale_range_from_histograms(narrow, 0, 100, rescale_per_band=False) == RescaleRange((BandRange(1000, 2000),))


def test_get_sample_cache_mb(subtests: SubTests, capsys: CaptureFixture[str]) -> None:
    """The cache holds one row of blocks of every band with 25% headroom, from 32 MB up to `max_cache_mb`."""
    with subtests.test(msg="one row of blocks of every band"):
        assert get_sample_cache_mb(rgb_gdalinfo(10000, 15000, block=(512, 512)), 4096) == 50
        assert get_sample_cache_mb(rgb_gdalinfo(10000, 15000, alpha=False, block=(512, 512)), 4096) == 38

    with subtests.test(msg="at least 32 MB"):
        assert get_sample_cache_mb(rgb_gdalinfo(4800, 7200), 4096) == 32
        assert get_sample_cache_mb(rgb_gdalinfo(4800, 7200, block=(4800, 1)), 4096) == 32

    with subtests.test(msg="capped at max_cache_mb with a warning"):
        assert get_sample_cache_mb(rgb_gdalinfo(10000, 15000, block=(512, 512)), 40) == 40
        assert "sample_cache_capped" in capsys.readouterr().out


def test_rescale_gamma_from_median(subtests: SubTests) -> None:
    """The gamma scales a gray median to the target through each band range, weighted like luminance, clamped to 0.5 - 3."""
    for msg, rescale_range, median, target, expected in [
        ("brightens a dark median", "428,60228", 8796, 0.4, 2.15),
        ("keeps a median at the target", "0,1000", 400, 0.4, 1.0),
        ("darkens a bright median", "0,1000", 600, 0.4, 0.56),
        ("same per band ranges match a single range", "428,60228;428,60228;428,60228", 8796, 0.4, 2.15),
        ("weights per band ranges like the luminance", "428,60228;900,30000;428,58000", 8796, 0.4, 1.58),
        ("clips per band fractions to 0 - 1", "500,1000;0,800;200,300", 400, 0.4, 0.92),
        ("clamps a very dark median to 3", "1000,2000", 1001, 0.4, 3.0),
        ("gives 3 for a median at the low end", "1000,2000", 1000, 0.4, 3.0),
        ("gives 3 for a median below the low end", "1000,2000", 500, 0.4, 3.0),
        ("clamps a very bright median to 0.5", "1000,2000", 1990, 0.4, 0.5),
        ("gives 0.5 for a median at the high end", "1000,2000", 2000, 0.4, 0.5),
        ("gives 0.5 for a median above the high end", "1000,2000", 3000, 0.4, 0.5),
    ]:
        with subtests.test(msg=msg):
            assert rescale_gamma_from_median(RescaleRange.parse(rescale_range), median, target) == expected


def test_get_sample_command(subtests: SubTests) -> None:
    """Every `step`th full-resolution pixel of the colour bands and alpha is sampled."""
    with subtests.test(msg="reads full resolution pixels, not overviews"):
        command = get_sample_command(rgb_gdalinfo(4800, 7200), step=8, cache_mb=32)
        assert command[command.index("-oo") + 1] == "OVERVIEW_LEVEL=NONE"

    with subtests.test(msg="sets the GDAL block cache"):
        command = get_sample_command(rgb_gdalinfo(4800, 7200), step=8, cache_mb=50)
        assert command[command.index("--config") + 1 : command.index("--config") + 3] == ["GDAL_CACHEMAX", "50"]

    with subtests.test(msg="rgb with alpha"):
        command = get_sample_command(rgb_gdalinfo(4801, 7200), step=8, cache_mb=32)
        assert command[command.index("-outsize") + 1 : command.index("-outsize") + 3] == ["601", "900"]
        assert command[-8:] == ["-b", "1", "-b", "2", "-b", "3", "-b", "4"]

    with subtests.test(msg="step 1 reads every pixel"):
        command = get_sample_command(rgb_gdalinfo(500, 400, alpha=False), step=1, cache_mb=32)
        assert command[command.index("-outsize") + 1 : command.index("-outsize") + 3] == ["500", "400"]
        assert command[-6:] == ["-b", "1", "-b", "2", "-b", "3"]

    with subtests.test(msg="gray"):
        gdalinfo = fake_gdalinfo()
        gdalinfo["size"] = [100, 100]
        add_band(gdalinfo, "Gray")
        assert get_sample_command(gdalinfo, step=1, cache_mb=32)[-2:] == ["-b", "1"]


def test_get_histograms(subtests: SubTests) -> None:
    """A uint16 source is downloaded, sampled and counted at full resolution without its transparent and nodata pixels."""
    with subtests.test(msg="downloads the source and masks alpha and nodata"):
        pixels = np.array(
            [[[100, 200], [300, 7]], [[110, 210], [310, 7]], [[120, 220], [320, 7]], [[65535, 0], [65535, 65535]]],
            dtype=np.uint16,
        )
        with sampling(pixels, rgb_gdalinfo(2, 2, no_data_value=7)) as (download, info, run):
            histograms = get_histograms("s3://bucket/file.tiff")

        local_path = download.call_args.args[1]
        assert download.call_args.args[0] == "s3://bucket/file.tiff"
        assert local_path.endswith("/file.tiff")
        info.assert_called_once_with(local_path)
        assert run.call_args.kwargs["input_file"] == local_path
        assert histograms.bands.shape == (3, 65536)
        assert np.flatnonzero(histograms.bands[0]).tolist() == [100, 300]
        assert np.flatnonzero(histograms.bands[2]).tolist() == [120, 320]
        assert np.flatnonzero(histograms.luminance).tolist() == [109, 309]

    with subtests.test(msg="scales the counts to the full resolution"):
        with sampling(np.full((3, 2, 2), 100, dtype=np.uint16), rgb_gdalinfo(3000, 2000, alpha=False)) as (_, _, run):
            histograms = get_histograms("file.tiff")
        command = run.call_args.args[0]
        assert command[command.index("-outsize") + 1 : command.index("-outsize") + 3] == ["1000", "667"]
        assert histograms.bands[:, 100].tolist() == [36, 36, 36]
        assert histograms.luminance[100] == 36

    with subtests.test(msg="sizes the GDAL block cache"):
        gdalinfo = rgb_gdalinfo(10000, 15000, alpha=False, block=(512, 512))
        with sampling(np.full((3, 2, 2), 100, dtype=np.uint16), gdalinfo) as (_, _, run):
            get_histograms("file.tiff", max_cache_mb=4096)
        command = run.call_args.args[0]
        assert command[command.index("GDAL_CACHEMAX") + 1] == "38"

    with subtests.test(msg="rejects non-uint16 sources"):
        with sampling(np.ones((3, 2, 2), dtype=np.uint8)):
            with raises(ValueError, match="Expected uint16"):
                get_histograms("file.tiff")
