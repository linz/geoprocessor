import json
from argparse import ArgumentTypeError
from pathlib import Path
from unittest.mock import patch

import numpy as np
from geoprocessor_raster.compute_scale import main, str_to_percentile, str_to_positive_float
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests


def test_str_to_percentile(subtests: SubTests) -> None:
    for value, expected in [("0", 0.0), ("1", 1.0), ("99.5", 99.5), ("100", 100.0)]:
        with subtests.test(msg=value):
            assert str_to_percentile(value) == expected

    for value in ["-1", "100.1", "a"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_percentile(value)


def test_should_write_rescale_range(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["b.tif", "a.tiff", "a.tfw"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[0, 100:200] = 1
    histograms[1, 150:400] = 1
    histograms[2, 50:300] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms) as get_histograms:
        main(
            [
                "--from-file",
                str(from_file),
                "--target",
                str(tmp_path),
                "--rescale-clip-low-percentile",
                "0",
                "--rescale-clip-high-percentile",
                "100",
            ]
        )

    get_histograms.assert_called_once_with(["a.tiff", "b.tif"], str(tmp_path / "histograms"), 1, False, None)
    assert (tmp_path / "rescale-range").read_text() == "50,399"
    details = json.loads((tmp_path / "rescale-range.json").read_text())
    assert details["fileCount"] == 2
    assert details["pixelCount"] == {"red": 100, "green": 250, "blue": 250}
    clip_percentiles = details["rescaleClipPercentiles"]
    assert clip_percentiles["columns"] == ["all", "red", "green", "blue"]
    assert list(clip_percentiles["low"]) == ["0", "0.1", "0.2", "0.5", "1", "2", "3", "5"]
    assert list(clip_percentiles["high"]) == ["95", "97", "98", "99", "99.5", "99.8", "99.9", "100"]
    assert clip_percentiles["low"]["0"] == [50, 100, 150, 50]
    assert clip_percentiles["high"]["100"] == [399, 199, 399, 299]


def test_should_write_per_band_rescale_range(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        main(
            [
                "--from-file",
                str(from_file),
                "--target",
                str(tmp_path),
                "--rescale-per-band",
                "true",
                "--rescale-clip-low-percentile",
                "0",
            ]
        )

    assert (tmp_path / "rescale-range").read_text() == "100,199;100,199;100,199"


def test_should_add_requested_percentiles_to_clip_percentiles(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 1:1001] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        main(
            [
                "--from-file",
                str(from_file),
                "--target",
                str(tmp_path),
                "--rescale-clip-low-percentile",
                "0.25",
                "--rescale-clip-high-percentile",
                "97.3",
            ]
        )

    clip_percentiles = json.loads((tmp_path / "rescale-range.json").read_text())["rescaleClipPercentiles"]
    assert clip_percentiles["low"]["0.25"] == [3, 3, 3, 3]
    assert clip_percentiles["high"]["97.3"] == [973, 973, 973, 973]


def test_should_reject_low_percentile_above_high(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        main(
            [
                "--from-file",
                "input.json",
                "--target",
                str(tmp_path),
                "--rescale-clip-low-percentile",
                "99",
                "--rescale-clip-high-percentile",
                "1",
            ]
        )

    assert "--rescale-clip-low-percentile must be lower than --rescale-clip-high-percentile" in capsys.readouterr().err


def test_should_pass_histogram_dir_and_force(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms) as get_histograms:
        main(
            ["--from-file", str(from_file), "--target", str(tmp_path), "--histogram-dir", "s3://bucket/histograms/", "--force"]
        )

    get_histograms.assert_called_once_with(["a.tiff"], "s3://bucket/histograms/", 1, True, None)


def test_should_fail_when_percentiles_give_the_same_value(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 1000] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        with raises(SystemExit):
            main(["--from-file", str(from_file), "--target", str(tmp_path)])

    assert "both give 1000" in capsys.readouterr().out
    assert not (tmp_path / "rescale-range").exists()


def test_should_pass_max_download_size(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms) as get_histograms:
        main(["--from-file", str(from_file), "--target", str(tmp_path), "--concurrency", "64", "--max-download-gb", "10"])

    get_histograms.assert_called_once_with(["a.tiff"], str(tmp_path / "histograms"), 64, False, 10_000_000_000)


def test_str_to_positive_float(subtests: SubTests) -> None:
    with subtests.test(msg="positive"):
        assert str_to_positive_float("1.5") == 1.5

    for value in ["0", "-1", "a", "nan", "inf"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_positive_float(value)
