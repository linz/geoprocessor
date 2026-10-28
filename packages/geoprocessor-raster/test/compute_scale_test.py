import json
from argparse import ArgumentTypeError
from pathlib import Path
from unittest.mock import patch

import numpy as np
from geoprocessor_raster.compute_scale import main, str_to_percentile
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


def test_should_write_scale_range(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["b.tif", "a.tiff", "a.tfw"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[0, 100:200] = 1
    histograms[1, 150:400] = 1
    histograms[2, 50:300] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms) as get_histograms:
        main(["--from-file", str(from_file), "--target", str(tmp_path), "--low-percentile", "0", "--high-percentile", "100"])

    get_histograms.assert_called_once_with(["a.tiff", "b.tif"], str(tmp_path / "histograms"), 1, False)
    assert (tmp_path / "scale-range").read_text() == "50,399"
    details = json.loads((tmp_path / "scale-range.json").read_text())
    assert details["bands"][1] == {"name": "green", "low": 150, "high": 399, "pixelCount": 250}
    assert details["fileCount"] == 2
    low, high = details["clipPercentiles"]["low"], details["clipPercentiles"]["high"]
    assert [entry["percentile"] for entry in low] == [
        0,
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1,
        1.5,
        2,
        2.5,
        3,
        3.5,
        4,
        4.5,
        5,
    ]
    assert [entry["percentile"] for entry in high] == [
        95,
        95.5,
        96,
        96.5,
        97,
        97.5,
        98,
        98.5,
        99,
        99.1,
        99.2,
        99.3,
        99.4,
        99.5,
        99.6,
        99.7,
        99.8,
        99.9,
        100,
    ]
    assert low[0] == {"percentile": 0, "value": 50, "bands": {"red": 100, "green": 150, "blue": 50}}
    assert high[-1] == {"percentile": 100, "value": 399, "bands": {"red": 199, "green": 399, "blue": 299}}


def test_should_write_per_band_scale_range(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        main(["--from-file", str(from_file), "--target", str(tmp_path), "--per-band", "true", "--low-percentile", "0"])

    assert (tmp_path / "scale-range").read_text() == "100,198;100,198;100,198"


def test_should_add_requested_percentiles_to_clip_percentiles(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 1:1001] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        main(
            ["--from-file", str(from_file), "--target", str(tmp_path), "--low-percentile", "0.25", "--high-percentile", "97.3"]
        )

    clip_percentiles = json.loads((tmp_path / "scale-range.json").read_text())["clipPercentiles"]
    assert {"percentile": 0.25, "value": 3, "bands": {"red": 3, "green": 3, "blue": 3}} in clip_percentiles["low"]
    assert {"percentile": 97.3, "value": 973, "bands": {"red": 973, "green": 973, "blue": 973}} in clip_percentiles["high"]


def test_should_reject_low_percentile_above_high(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        main(["--from-file", "input.json", "--target", str(tmp_path), "--low-percentile", "99", "--high-percentile", "1"])

    assert "--low-percentile must be lower than --high-percentile" in capsys.readouterr().err


def test_should_pass_histogram_dir_and_force(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms) as get_histograms:
        main(
            ["--from-file", str(from_file), "--target", str(tmp_path), "--histogram-dir", "s3://bucket/histograms/", "--force"]
        )

    get_histograms.assert_called_once_with(["a.tiff"], "s3://bucket/histograms/", 1, True)


def test_should_fail_when_percentiles_give_the_same_value(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 1000] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        with raises(SystemExit):
            main(["--from-file", str(from_file), "--target", str(tmp_path)])

    assert "both give 1000" in capsys.readouterr().out
    assert not (tmp_path / "scale-range").exists()
