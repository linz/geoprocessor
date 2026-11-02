import numpy as np
import numpy.typing as npt
from geoprocessor_gdal.gdal.gdal_histograms import (
    Histograms,
    get_clip_percentiles,
    histogram_from_pixels,
    luminance_from_pixels,
    percentile_from_histogram,
    rescale_range_from_histograms,
)
from geoprocessor_gdal.rescale_range import BandRange, RescaleRange
from pytest import raises
from pytest_subtests import SubTests


def staggered_bands() -> npt.NDArray[np.int64]:
    """Histograms of three bands with one pixel per value: red 100-199, green 150-399, blue 50-299."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[0, 100:200] = bands[1, 150:400] = bands[2, 50:300] = 1
    return bands


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


def test_get_clip_percentiles() -> None:
    """Each percentile gives the bands combined with `combine`, then red, green, blue and luminance."""
    bands = staggered_bands()

    assert get_clip_percentiles(Histograms(bands, bands[1]), [100, 0, 2.5], max) == {
        "0": [150, 100, 150, 50, 150],
        "2.5": [156, 102, 156, 56, 156],
        "100": [399, 199, 399, 299, 399],
    }
