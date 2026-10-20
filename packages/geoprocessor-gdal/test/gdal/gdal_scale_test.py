import numpy as np
from geoprocessor_gdal.gdal.gdal_scale import (
    BandRange,
    ScaleRange,
    histogram_from_pixels,
    percentile_from_histogram,
    scale_range_from_histograms,
)
from pytest import raises
from pytest_subtests import SubTests


def test_scale_range_round_trip(subtests: SubTests) -> None:
    for value in ["301,4012", "301,4012;295,3980;310,4100", "0,65535"]:
        with subtests.test(msg=value):
            assert str(ScaleRange.parse(value)) == value


def test_scale_range_rejects_invalid(subtests: SubTests) -> None:
    for value in ["", "301", "301,4012,5000", "a,b", "4012,301", "301,301", "-1,4012", "301,65536", "1,2;3,4"]:
        with subtests.test(msg=value):
            with raises(ValueError):
                ScaleRange.parse(value)


def test_histogram_from_pixels_counts_each_band() -> None:
    pixels = np.array([[[1, 2], [2, 3]], [[10, 10], [10, 10]]], dtype=np.uint16)

    histogram = histogram_from_pixels(pixels)

    assert histogram.shape == (2, 65536)
    assert histogram[0, 1:4].tolist() == [1, 2, 1]
    assert histogram[1, 10] == 4


def test_histogram_from_pixels_ignores_masked_pixels(subtests: SubTests) -> None:
    pixels = np.array([[[0, 5], [7, 9]], [[0, 0], [7, 9]]], dtype=np.uint16)

    with subtests.test(msg="all-zero pixels"):
        histogram = histogram_from_pixels(pixels)
        assert histogram.sum(axis=1).tolist() == [3, 3]
        assert histogram[1, 0] == 1

    with subtests.test(msg="transparent pixels"):
        alpha = np.array([[65535, 65535], [0, 65535]], dtype=np.uint16)
        histogram = histogram_from_pixels(pixels, alpha=alpha)
        assert histogram[0, 7] == 0
        assert histogram.sum(axis=1).tolist() == [2, 2]

    with subtests.test(msg="nodata pixels"):
        histogram = histogram_from_pixels(pixels, nodata=9)
        assert histogram[:, 9].tolist() == [0, 0]


def test_percentile_from_histogram_matches_numpy(subtests: SubTests) -> None:
    values = np.random.default_rng(42).integers(100, 5000, size=10_000, dtype=np.uint16)
    histogram = np.bincount(values, minlength=65536).astype(np.int64)

    for percentile in [1, 2, 50, 98, 99, 100]:
        with subtests.test(msg=f"{percentile}%"):
            expected = int(np.percentile(values, percentile, method="inverted_cdf"))
            assert percentile_from_histogram(histogram, percentile) == expected


def test_percentile_from_histogram_zero_is_minimum() -> None:
    histogram = np.zeros(65536, dtype=np.int64)
    histogram[[200, 300]] = 1

    assert percentile_from_histogram(histogram, 0) == 200


def test_percentile_from_histogram_rejects_empty() -> None:
    with raises(ValueError, match="empty histogram"):
        percentile_from_histogram(np.zeros(65536, dtype=np.int64), 1)


def test_scale_range_from_histograms(subtests: SubTests) -> None:
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[0, 100:200] = 1
    histograms[1, 150:400] = 1
    histograms[2, 50:300] = 1

    with subtests.test(msg="single range"):
        assert scale_range_from_histograms(histograms, 0, 100, per_band=False) == ScaleRange((BandRange(50, 399),))

    with subtests.test(msg="per band"):
        assert scale_range_from_histograms(histograms, 0, 100, per_band=True) == ScaleRange(
            (BandRange(100, 199), BandRange(150, 399), BandRange(50, 299))
        )
