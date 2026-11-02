import json
from argparse import ArgumentTypeError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import numpy.typing as npt
from geoprocessor_gdal.gdal.gdal_histograms import Histograms
from geoprocessor_raster.compute_scale import main, str_to_fraction, str_to_percentile
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
    """Percentiles must be numbers from 0 to 100."""
    for value, expected in [("0", 0.0), ("1", 1.0), ("99.5", 99.5), ("100", 100.0)]:
        with subtests.test(msg=value):
            assert str_to_percentile(value) == expected

    for value in ["-1", "100.1", "a"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_percentile(value)


def test_str_to_fraction(subtests: SubTests) -> None:
    """Fractions must be numbers between 0 and 1, both excluded."""
    for value, expected in [("0.001", 0.001), ("0.4", 0.4), ("0.999", 0.999)]:
        with subtests.test(msg=value):
            assert str_to_fraction(value) == expected

    for value in ["0", "1", "-0.4", "a", "nan"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_fraction(value)


def test_should_write_rescale_range(tmp_path: Path) -> None:
    """compute-scale reads only the TIFF inputs and writes the range, pixel counts and clip percentiles table."""
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
    assert clip_percentiles["columns"] == ["red", "green", "blue"]
    expected_percentiles = [
        "0",
        "0.1",
        "0.2",
        "0.5",
        "1",
        "2",
        "3",
        "5",
        "95",
        "97",
        "98",
        "99",
        "99.5",
        "99.8",
        "99.9",
        "100",
    ]
    assert list(clip_percentiles["values"]) == expected_percentiles
    assert clip_percentiles["values"]["0"] == [100, 150, 50]
    assert clip_percentiles["values"]["100"] == [199, 399, 299]
    assert list(details["luminancePercentiles"]) == expected_percentiles
    assert [details["luminancePercentiles"][p] for p in ["0", "100"]] == [150, 399]


def test_should_write_per_band_rescale_range(tmp_path: Path) -> None:
    """`--rescale-per-band` writes one range per band."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 100:200] = 1

    run_main(tmp_path, bands, "--rescale-per-band", "true", "--rescale-clip-low-percentile", "0")

    assert (tmp_path / "rescale-range").read_text() == "100,199;100,199;100,199"


def test_should_write_rescale_gamma(tmp_path: Path, subtests: SubTests) -> None:
    """compute-scale writes the gamma that scales the median luminance to `--rescale-gamma-target`, 0.4 by default."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 1:1001] = 1

    for args, target, expected in [([], 0.4, "0.76"), (["--rescale-gamma-target", "0.5"], 0.5, "1")]:
        with subtests.test(msg=" ".join(args) or "defaults"):
            run_main(tmp_path, bands, "--rescale-clip-low-percentile", "0", "--rescale-clip-high-percentile", "100", *args)

            assert (tmp_path / "rescale-gamma").read_text() == expected
            details = read_details(tmp_path)
            assert details["rescaleGamma"] == float(expected)
            assert details["rescaleGammaTarget"] == target
            assert details["luminanceMedian"] == 500


def test_should_add_requested_percentiles_to_clip_percentiles(tmp_path: Path) -> None:
    """Clip percentiles not in the default table are added to it."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 1:1001] = 1

    run_main(tmp_path, bands, "--rescale-clip-low-percentile", "0.25", "--rescale-clip-high-percentile", "97.3")

    details = read_details(tmp_path)
    assert details["rescaleClipPercentiles"]["values"]["0.25"] == [3, 3, 3]
    assert details["rescaleClipPercentiles"]["values"]["97.3"] == [973, 973, 973]
    assert [details["luminancePercentiles"][p] for p in ["0.25", "97.3"]] == [3, 973]


def test_should_pass_options_to_get_dataset_histograms(tmp_path: Path, subtests: SubTests) -> None:
    """The histogram directory, force, concurrency and download budget options reach `get_dataset_histograms`."""
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
    """`--rescale-clip-low-percentile` must be lower than `--rescale-clip-high-percentile`."""
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
    """compute-scale fails without writing a range when both percentiles give the same pixel value."""
    bands = np.zeros((3, 65536), dtype=np.int64)
    bands[:, 1000] = 1

    with raises(SystemExit):
        run_main(tmp_path, bands)

    assert "both give 1000" in capsys.readouterr().out
    assert not (tmp_path / "rescale-range").exists()
