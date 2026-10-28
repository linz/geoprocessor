from typing import Any, Callable
from unittest.mock import patch

import numpy as np
import numpy.typing as npt
import tifffile
from fake_gdalinfo import add_band, fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_scale import (
    BandRange,
    ScaleRange,
    get_clip_percentiles,
    get_dataset_histograms,
    get_histogram_file_name,
    get_histograms,
    get_sample_command,
    histogram_from_pixels,
    histograms_from_bytes,
    histograms_to_bytes,
    percentile_from_histogram,
    scale_range_from_histograms,
    sum_histograms,
)
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
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


def rgb_gdalinfo(width: int, height: int, alpha: bool = True, no_data_value: int | None = None) -> GdalInfo:
    gdalinfo: GdalInfo = fake_gdalinfo()
    gdalinfo["size"] = [width, height]
    for color in ["Red", "Green", "Blue"] + (["Alpha"] if alpha else []):
        add_band(gdalinfo, color, no_data_value)
    return gdalinfo


def test_get_sample_command(subtests: SubTests) -> None:
    with subtests.test(msg="rgb with alpha is downsampled"):
        command = get_sample_command(rgb_gdalinfo(4800, 7200), size=1024)
        assert command[command.index("-outsize") + 1 : command.index("-outsize") + 3] == ["683", "1024"]
        assert command[-8:] == ["-b", "1", "-b", "2", "-b", "3", "-b", "4"]

    with subtests.test(msg="small tiff is not upsampled"):
        command = get_sample_command(rgb_gdalinfo(500, 400, alpha=False), size=1024)
        assert command[command.index("-outsize") + 1 : command.index("-outsize") + 3] == ["500", "400"]
        assert command[-6:] == ["-b", "1", "-b", "2", "-b", "3"]

    with subtests.test(msg="gray"):
        gdalinfo = fake_gdalinfo()
        gdalinfo["size"] = [100, 100]
        add_band(gdalinfo, "Gray")
        assert get_sample_command(gdalinfo)[-2:] == ["-b", "1"]


def sample_writer(pixels: npt.NDArray[Any]) -> Callable[..., None]:
    def write_sample(_command: list[str], **kwargs: Any) -> None:
        tifffile.imwrite(kwargs["output_file"], pixels, photometric="minisblack", planarconfig="separate")

    return write_sample


def test_get_histograms_masks_alpha_and_nodata() -> None:
    pixels = np.array(
        [[[100, 200], [300, 7]], [[110, 210], [310, 7]], [[120, 220], [320, 7]], [[65535, 0], [65535, 65535]]],
        dtype=np.uint16,
    )

    with (
        patch("geoprocessor_gdal.gdal.gdal_scale.copy") as copy,
        patch("geoprocessor_gdal.gdal.gdal_scale.gdal_info", return_value=rgb_gdalinfo(2, 2, no_data_value=7)) as info,
        patch("geoprocessor_gdal.gdal.gdal_scale.run_gdal", side_effect=sample_writer(pixels)) as run,
    ):
        histograms = get_histograms("s3://bucket/file.tiff")

    local_path = copy.call_args.args[1]
    assert copy.call_args.args[0] == "s3://bucket/file.tiff"
    assert local_path.endswith("/file.tiff")
    info.assert_called_once_with(local_path)
    assert run.call_args.kwargs["input_file"] == local_path
    assert histograms.shape == (3, 65536)
    assert np.flatnonzero(histograms[0]).tolist() == [100, 300]
    assert np.flatnonzero(histograms[2]).tolist() == [120, 320]


def test_get_histograms_rejects_non_uint16() -> None:
    with (
        patch("geoprocessor_gdal.gdal.gdal_scale.gdal_info", return_value=rgb_gdalinfo(2, 2, alpha=False)),
        patch("geoprocessor_gdal.gdal.gdal_scale.run_gdal", side_effect=sample_writer(np.ones((3, 2, 2), dtype=np.uint8))),
    ):
        with raises(ValueError, match="Expected uint16"):
            get_histograms("file.tiff")


def test_get_dataset_histograms_sums_files() -> None:
    with (
        patch("geoprocessor_gdal.gdal.gdal_scale.gdal_info", return_value=rgb_gdalinfo(2, 2, alpha=False)),
        patch(
            "geoprocessor_gdal.gdal.gdal_scale.run_gdal",
            side_effect=sample_writer(np.full((3, 2, 2), 100, dtype=np.uint16)),
        ),
    ):
        total = get_dataset_histograms(["a.tiff", "b.tiff", "c.tiff"], concurrency=2)

    assert total[:, 100].tolist() == [12, 12, 12]


def test_histogram_file_round_trip() -> None:
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[1, 100:200] = 5

    data = histograms_to_bytes("s3://bucket/a.tiff", histograms)

    assert len(data) < 10_000
    assert np.array_equal(histograms_from_bytes(data, "s3://bucket/a.tiff"), histograms)


def test_histograms_from_bytes_rejects_other_source() -> None:
    data = histograms_to_bytes("s3://bucket/a.tiff", np.zeros((1, 65536), dtype=np.int64))

    with raises(ValueError, match="Expected the histogram file of s3://bucket/b.tiff, got s3://bucket/a.tiff"):
        histograms_from_bytes(data, "s3://bucket/b.tiff")


def test_get_histogram_file_name(subtests: SubTests) -> None:
    with subtests.test(msg="starts with the source file name"):
        assert get_histogram_file_name("s3://bucket/a/CA09_1000_0808.tif").startswith("CA09_1000_0808.tif.")

    with subtests.test(msg="unique per full path"):
        assert get_histogram_file_name("s3://bucket/a/file.tiff") != get_histogram_file_name("s3://bucket/b/file.tiff")

    with subtests.test(msg="replaces characters unsafe in s3 keys"):
        assert get_histogram_file_name("s3://bucket/a?b é.tif").startswith("a_b__.tif.")

    with subtests.test(msg="fits a local file name"):
        assert len(get_histogram_file_name(f"s3://bucket/{'a' * 300}.tiff").encode()) <= 255


def test_sum_histograms(subtests: SubTests) -> None:
    rgb = np.ones((3, 65536), dtype=np.int64)

    with subtests.test(msg="sums"):
        assert sum_histograms([("a.tiff", rgb), ("b.tiff", rgb)])[:, 0].tolist() == [2, 2, 2]

    with subtests.test(msg="rejects mixed band counts"):
        with raises(ValueError, match="Expected 3 bands like the other sources, got 1: gray.tiff"):
            sum_histograms([("a.tiff", rgb), ("gray.tiff", np.ones((1, 65536), dtype=np.int64))])

    with subtests.test(msg="rejects no histograms"):
        with raises(ValueError, match="No histograms"):
            sum_histograms([])


def test_get_clip_percentiles() -> None:
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[0, 100:200] = 1
    histograms[1, 150:400] = 1
    histograms[2, 50:300] = 1

    assert get_clip_percentiles(histograms, ("red", "green", "blue"), [100, 0], max) == [
        {"percentile": 0, "value": 150, "bands": {"red": 100, "green": 150, "blue": 50}},
        {"percentile": 100, "value": 399, "bands": {"red": 199, "green": 399, "blue": 299}},
    ]
