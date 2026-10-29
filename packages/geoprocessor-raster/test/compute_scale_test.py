import json
from argparse import ArgumentTypeError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import numpy.typing as npt
from geoprocessor_gdal.gdal.gdal_rescale import Histograms
from geoprocessor_raster.compute_scale import main, str_to_percentile, str_to_positive_float
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests


def run_main(tmp_path: Path, bands: npt.NDArray[np.int64], *args: str, inputs: list[str] | None = None) -> MagicMock:
    """Run compute-scale with `bands` as the dataset histograms and the green band as luminance.

    Returns:
        the mocked `get_dataset_histograms`
    """
    from_file = tmp_path / "input.json"
    from_file.write_text(json.dumps([{"output": "BQ25_1000_0101", "input": inputs or ["a.tiff"]}]))
    with patch(
        "geoprocessor_raster.compute_scale.get_dataset_histograms", return_value=Histograms(bands, bands[1])
    ) as get_histograms:
        main(["--from-file", str(from_file), "--target", str(tmp_path), *args])
    return get_histograms


def read_details(tmp_path: Path) -> Any:
    """Read the `rescale-range.json` written by compute-scale."""
    return json.loads((tmp_path / "rescale-range.json").read_text())


def test_str_to_percentile(subtests: SubTests) -> None:
    for value, expected in [("0", 0.0), ("1", 1.0), ("99.5", 99.5), ("100", 100.0)]:
        with subtests.test(msg=value):
            assert str_to_percentile(value) == expected

    for value in ["-1", "100.1", "a"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_percentile(value)


def test_str_to_positive_float(subtests: SubTests) -> None:
    with subtests.test(msg="positive"):
        assert str_to_positive_float("1.5") == 1.5

    for value in ["0", "-1", "a", "nan", "inf"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_positive_float(value)


def test_should_write_rescale_range(tmp_path: Path) -> None:
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[0, 100:200] = bands[1, 150:400] = bands[2, 50:300] = 1

    get_histograms = run_main(
        tmp_path,
        bands,
        "--rescale-clip-low-percentile",
        "0",
        "--rescale-clip-high-percentile",
        "100",
        inputs=["b.tif", "a.tiff", "a.tfw"],
    )

    assert get_histograms.call_args.args[0] == ["a.tiff", "b.tif"]
    assert (tmp_path / "rescale-range").read_text() == "50,399"
    details = read_details(tmp_path)
    assert details["fileCount"] == 2
    assert details["pixelCount"] == {"red": 100, "green": 250, "blue": 250, "luminance": 250}
    clip_percentiles = details["rescaleClipPercentiles"]
    assert clip_percentiles["columns"] == ["all", "red", "green", "blue", "luminance"]
    assert list(clip_percentiles["low"]) == ["0", "0.1", "0.2", "0.5", "1", "2", "3", "5"]
    assert list(clip_percentiles["high"]) == ["95", "97", "98", "99", "99.5", "99.8", "99.9", "100"]
    assert clip_percentiles["low"]["0"] == [50, 100, 150, 50, 150]
    assert clip_percentiles["high"]["100"] == [399, 199, 399, 299, 399]


def test_should_write_per_band_rescale_range(tmp_path: Path) -> None:
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 100:200] = 1

    run_main(tmp_path, bands, "--rescale-per-band", "true", "--rescale-clip-low-percentile", "0")

    assert (tmp_path / "rescale-range").read_text() == "100,199;100,199;100,199"


def test_should_add_requested_percentiles_to_clip_percentiles(tmp_path: Path) -> None:
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 1:1001] = 1

    run_main(tmp_path, bands, "--rescale-clip-low-percentile", "0.25", "--rescale-clip-high-percentile", "97.3")

    clip_percentiles = read_details(tmp_path)["rescaleClipPercentiles"]
    assert clip_percentiles["low"]["0.25"] == [3, 3, 3, 3, 3]
    assert clip_percentiles["high"]["97.3"] == [973, 973, 973, 973, 973]


def test_should_pass_options_to_get_dataset_histograms(tmp_path: Path, subtests: SubTests) -> None:
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 100:200] = 1
    default_dir = str(tmp_path / "histograms")

    for args, expected in [
        ([], (default_dir, 1, False, None)),
        (["--histogram-dir", "s3://bucket/histograms/", "--force"], ("s3://bucket/histograms/", 1, True, None)),
        (["--concurrency", "64", "--max-download-gb", "10"], (default_dir, 64, False, 10_000_000_000)),
    ]:
        with subtests.test(msg=" ".join(args) or "defaults"):
            run_main(tmp_path, bands, *args).assert_called_once_with(["a.tiff"], *expected)


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


def test_should_fail_when_percentiles_give_the_same_value(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 1000] = 1

    with raises(SystemExit):
        run_main(tmp_path, bands)

    assert "both give 1000" in capsys.readouterr().out
    assert not (tmp_path / "rescale-range").exists()
