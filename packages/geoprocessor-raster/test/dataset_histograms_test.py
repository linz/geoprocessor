from pathlib import Path
from unittest.mock import patch

import numpy as np
from geoprocessor_gdal.gdal.gdal_histograms import Histograms
from geoprocessor_raster.dataset_histograms import (
    get_dataset_histograms,
    get_histogram_file_name,
    get_worker_count,
    histograms_from_bytes,
    histograms_to_bytes,
    sum_histograms,
)
from pytest import raises
from pytest_subtests import SubTests


def empty_histograms(band_count: int = 3) -> Histograms:
    """Histograms with no counted pixels."""
    return Histograms(np.zeros((band_count, 65536), dtype=np.int64), np.zeros(65536, dtype=np.int64))


def source_histograms() -> Histograms:
    """Histograms of a source with 4 pixels of 100 in every band."""
    histograms = empty_histograms()
    histograms.bands[:, 100] = histograms.luminance[100] = 4
    return histograms


def test_get_dataset_histograms(tmp_path: Path, subtests: SubTests) -> None:
    """Source histograms are summed and saved per source, and a rerun reads the saved ones unless forced."""
    computing = patch("geoprocessor_raster.dataset_histograms.get_histograms", side_effect=lambda _: source_histograms())

    with subtests.test(msg="sums the sources and saves a histogram file per source"):
        directory = tmp_path / "sums"
        with computing:
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
        with computing:
            total = get_dataset_histograms(["a.tiff", "b.tiff"], str(directory))
        assert total.bands[:, 7].tolist() == [1000, 1000, 1000]
        assert total.bands[:, 100].tolist() == [4, 4, 4]
        assert total.luminance[[7, 100]].tolist() == [1000, 4]

    with subtests.test(msg="force recomputes all sources"):
        with computing:
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
        with computing, patch("geoprocessor_raster.dataset_histograms.get_worker_count", return_value=1) as worker_count:
            get_dataset_histograms(
                ["s3://bucket/saved.tif", "s3://bucket/new.tif", "local.tif"], str(directory), 4, max_download_bytes=1000
            )
        worker_count.assert_called_once_with(["s3://bucket/new.tif"], 4, 1000)


def test_histogram_file(subtests: SubTests) -> None:
    """A histogram file reads back unchanged, but only for the source it was written for."""
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
    """Histogram file names start with the source file name and are unique, S3-safe and short enough for local files."""
    with subtests.test(msg="starts with the source file name"):
        assert get_histogram_file_name("s3://bucket/a/CA09_1000_0808.tif").startswith("CA09_1000_0808.tif.")

    with subtests.test(msg="unique per full path"):
        assert get_histogram_file_name("s3://bucket/a/file.tiff") != get_histogram_file_name("s3://bucket/b/file.tiff")

    with subtests.test(msg="replaces characters unsafe in s3 keys"):
        assert get_histogram_file_name("s3://bucket/a?b é.tif").startswith("a_b__.tif.")

    with subtests.test(msg="fits a local file name"):
        assert len(get_histogram_file_name(f"s3://bucket/{'a' * 300}.tiff").encode()) <= 255


def test_sum_histograms(subtests: SubTests) -> None:
    """Source histograms are summed without changing them, and must all have the same band count."""
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
    """Workers are capped so that one download per worker of the largest S3 source fits the download budget."""
    sizes = {"s3://bucket/a/": {"1.tif": 100, "2.tif": 300, "other.tif": 10_000}, "s3://bucket/b/": {"3.tif": 200}}
    files = ["s3://bucket/a/1.tif", "s3://bucket/a/2.tif", "s3://bucket/b/3.tif"]

    with patch(
        "geoprocessor_raster.dataset_histograms.list_file_sizes", side_effect=lambda directory: sizes[directory]
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
