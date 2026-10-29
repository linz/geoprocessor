from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import numpy as np
import numpy.typing as npt
import tifffile
from fake_gdalinfo import add_band, fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_rescale import (
    BandRange,
    Histograms,
    RescaleRange,
    get_clip_percentiles,
    get_dataset_histograms,
    get_histogram_file_name,
    get_histograms,
    get_sample_command,
    get_worker_count,
    histogram_from_pixels,
    histograms_from_bytes,
    histograms_to_bytes,
    luminance_from_pixels,
    percentile_from_histogram,
    rescale_range_from_histograms,
    sum_histograms,
)
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo
from pytest import raises
from pytest_subtests import SubTests


def staggered_bands() -> npt.NDArray[np.int64]:
    """Histograms of three bands with one pixel per value: red 100-199, green 150-399, blue 50-299."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[0, 100:200] = bands[1, 150:400] = bands[2, 50:300] = 1
    return bands


def empty_histograms(band_count: int = 3) -> Histograms:
    """Histograms with no counted pixels."""
    return Histograms(np.zeros((band_count, 65536), dtype=np.int64), np.zeros(65536, dtype=np.int64))


def rgb_gdalinfo(width: int, height: int, alpha: bool = True, no_data_value: int | None = None) -> GdalInfo:
    gdalinfo: GdalInfo = fake_gdalinfo()
    gdalinfo["size"] = [width, height]
    for color in ["Red", "Green", "Blue"] + (["Alpha"] if alpha else []):
        add_band(gdalinfo, color, no_data_value)
    return gdalinfo


def sample_writer(pixels: npt.NDArray[Any]) -> Callable[..., None]:
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
        patch("geoprocessor_gdal.gdal.gdal_rescale.download") as download,
        patch(
            "geoprocessor_gdal.gdal.gdal_rescale.gdal_info", return_value=gdalinfo or rgb_gdalinfo(2, 2, alpha=False)
        ) as info,
        patch("geoprocessor_gdal.gdal.gdal_rescale.run_gdal", side_effect=sample_writer(pixels)) as run,
    ):
        yield download, info, run


def test_rescale_range_parse(subtests: SubTests) -> None:
    for value in ["301,4012", "301,4012;295,3980;310,4100", "0,65535"]:
        with subtests.test(msg=value):
            assert str(RescaleRange.parse(value)) == value

    for value in ["", "301", "301,4012,5000", "a,b", "4012,301", "301,301", "-1,4012", "301,65536", "1,2;3,4"]:
        with subtests.test(msg=f"rejects {value!r}"):
            with raises(ValueError):
                RescaleRange.parse(value)


def test_histogram_from_pixels(subtests: SubTests) -> None:
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


def test_luminance_from_pixels(subtests: SubTests) -> None:
    pixels = np.array([[[1000, 0, 7, 1000]], [[2000, 0, 7, 2000]], [[3000, 0, 7, 3000]]], dtype=np.uint16)

    with subtests.test(msg="weighted sum of red, green and blue, without all-zero and nodata pixels"):
        assert np.flatnonzero(luminance_from_pixels(pixels, nodata=7)).tolist() == [1860]
        assert luminance_from_pixels(pixels, nodata=7)[1860] == 2

    with subtests.test(msg="without transparent pixels"):
        alpha = np.array([[65535, 65535, 65535, 0]], dtype=np.uint16)
        assert luminance_from_pixels(pixels, alpha=alpha, nodata=7)[1860] == 1

    with subtests.test(msg="gray is its own luminance"):
        assert np.flatnonzero(luminance_from_pixels(pixels[:1])).tolist() == [7, 1000]


def test_percentile_from_histogram(subtests: SubTests) -> None:
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


def test_get_histograms(subtests: SubTests) -> None:
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

    with subtests.test(msg="rejects non-uint16 sources"):
        with sampling(np.ones((3, 2, 2), dtype=np.uint8)):
            with raises(ValueError, match="Expected uint16"):
                get_histograms("file.tiff")


def test_get_dataset_histograms(tmp_path: Path, subtests: SubTests) -> None:
    pixels = np.full((3, 2, 2), 100, dtype=np.uint16)

    with subtests.test(msg="sums the sources and saves a histogram file per source"):
        directory = tmp_path / "sums"
        with sampling(pixels):
            total = get_dataset_histograms(["a.tiff", "b.tiff", "c.tiff"], str(directory), concurrency=2)
        assert total.bands[:, 100].tolist() == [12, 12, 12]
        assert total.luminance[100] == 12
        assert {path.name for path in directory.iterdir()} == {
            get_histogram_file_name(f) for f in ["a.tiff", "b.tiff", "c.tiff"]
        }

    directory = tmp_path / "saved"
    directory.mkdir()
    saved = empty_histograms()
    saved.bands[:, 7] = saved.luminance[7] = 1000
    (directory / get_histogram_file_name("a.tiff")).write_bytes(histograms_to_bytes("a.tiff", saved))

    with subtests.test(msg="reads the sources that have a histogram file"):
        with sampling(pixels):
            total = get_dataset_histograms(["a.tiff", "b.tiff"], str(directory))
        assert total.bands[:, 7].tolist() == [1000, 1000, 1000]
        assert total.bands[:, 100].tolist() == [4, 4, 4]
        assert total.luminance[[7, 100]].tolist() == [1000, 4]

    with subtests.test(msg="force recomputes all sources"):
        with sampling(pixels):
            total = get_dataset_histograms(["a.tiff", "b.tiff"], str(directory), force=True)
        assert total.bands[:, 7].tolist() == [0, 0, 0]
        assert total.bands[:, 100].tolist() == [8, 8, 8]
        saved_file = histograms_from_bytes((directory / get_histogram_file_name("a.tiff")).read_bytes(), "a.tiff")
        assert saved_file.bands[:, 100].tolist() == [4, 4, 4]

    with subtests.test(msg="caps the workers by the s3 sources left to download"):
        directory = tmp_path / "downloads"
        directory.mkdir()
        (directory / get_histogram_file_name("s3://bucket/saved.tif")).write_bytes(
            histograms_to_bytes("s3://bucket/saved.tif", empty_histograms())
        )
        with sampling(pixels), patch("geoprocessor_gdal.gdal.gdal_rescale.get_worker_count", return_value=1) as worker_count:
            get_dataset_histograms(
                ["s3://bucket/saved.tif", "s3://bucket/new.tif", "local.tif"], str(directory), 4, max_download_bytes=1000
            )
        worker_count.assert_called_once_with(["s3://bucket/new.tif"], 4, 1000)


def test_histogram_file(subtests: SubTests) -> None:
    histograms = empty_histograms()
    histograms.bands[1, 100:200] = 5
    histograms.luminance[150:250] = 3
    data = histograms_to_bytes("s3://bucket/a.tiff", histograms)

    with subtests.test(msg="round trip"):
        assert len(data) < 10_000
        read = histograms_from_bytes(data, "s3://bucket/a.tiff")
        assert np.array_equal(read.bands, histograms.bands)
        assert np.array_equal(read.luminance, histograms.luminance)

    with subtests.test(msg="rejects the file of another source"):
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
    rgb = Histograms(np.ones((3, 65536), dtype=np.int64), np.ones(65536, dtype=np.int64))

    with subtests.test(msg="sums"):
        total = sum_histograms([("a.tiff", rgb), ("b.tiff", rgb)])
        assert total.bands[:, 0].tolist() == [2, 2, 2]
        assert total.luminance[0] == 2
        assert rgb.bands[0, 0] == 1

    with subtests.test(msg="rejects mixed band counts"):
        with raises(ValueError, match="Expected 3 bands like the other sources, got 1: gray.tiff"):
            sum_histograms([("a.tiff", rgb), ("gray.tiff", empty_histograms(1))])

    with subtests.test(msg="rejects no histograms"):
        with raises(ValueError, match="No histograms"):
            sum_histograms([])


def test_get_worker_count(subtests: SubTests) -> None:
    sizes = {"s3://bucket/a/": {"1.tif": 100, "2.tif": 300, "other.tif": 10_000}, "s3://bucket/b/": {"3.tif": 200}}
    files = ["s3://bucket/a/1.tif", "s3://bucket/a/2.tif", "s3://bucket/b/3.tif"]

    with patch(
        "geoprocessor_gdal.gdal.gdal_rescale.list_file_sizes", side_effect=lambda directory: sizes[directory]
    ) as listing:
        with subtests.test(msg="caps to fit the largest file"):
            assert get_worker_count(files, 16, 1000) == 3
            assert sorted(call.args[0] for call in listing.call_args_list) == ["s3://bucket/a/", "s3://bucket/b/"]

        for files_, concurrency, max_download_bytes, expected, msg in [
            (files, 2, 1000, 2, "keeps the concurrency when the files fit"),
            (files, 16, 10, 1, "at least one worker"),
            (files, 16, None, 16, "no limit"),
            ([], 16, 1000, 16, "no downloads"),
        ]:
            with subtests.test(msg=msg):
                assert get_worker_count(files_, concurrency, max_download_bytes) == expected


def test_get_clip_percentiles() -> None:
    bands = staggered_bands()

    assert get_clip_percentiles(Histograms(bands, bands[1]), [100, 0, 2.5], max) == {
        "0": [150, 100, 150, 50, 150],
        "2.5": [156, 102, 156, 56, 156],
        "100": [399, 199, 399, 299, 399],
    }
