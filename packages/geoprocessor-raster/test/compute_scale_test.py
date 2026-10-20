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

    get_histograms.assert_called_once_with(["a.tiff", "b.tif"], 1)
    assert (tmp_path / "scale-range").read_text() == "50,399"
    details = json.loads((tmp_path / "scale-range.json").read_text())
    assert details["bands"][1] == {"low": 150, "high": 399, "pixelCount": 250}
    assert details["fileCount"] == 2


def test_should_write_per_band_scale_range(tmp_path: Path) -> None:
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": ["a.tiff"]}]))
    histograms = np.zeros((3, 65536), dtype=np.int64)
    histograms[:, 100:200] = 1

    with patch("geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=histograms):
        main(["--from-file", str(from_file), "--target", str(tmp_path), "--per-band", "true", "--low-percentile", "0"])

    assert (tmp_path / "scale-range").read_text() == "100,198;100,198;100,198"


def test_should_reject_low_percentile_above_high(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        main(["--from-file", "input.json", "--target", str(tmp_path), "--low-percentile", "99", "--high-percentile", "1"])

    assert "--low-percentile must be lower than --high-percentile" in capsys.readouterr().err
