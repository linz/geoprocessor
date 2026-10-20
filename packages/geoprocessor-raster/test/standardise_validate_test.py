from argparse import ArgumentTypeError

from geoprocessor_raster.standardise_validate import get_args_parser, str_to_gamma, str_to_scale_range
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests

REQUIRED_ARGS = [
    *["--preset", "webp", "--from-file", "input.json", "--source-epsg", "2193", "--target-epsg", "2193"],
    *["--gsd", "0.1", "--data-type", "uint16", "--create-footprints", "true", "--collection-id", "123"],
    *["--target", "/tmp/"],
]


def test_str_to_scale_range(subtests: SubTests) -> None:
    with subtests.test(msg="blank"):
        assert str_to_scale_range(" ") is None

    with subtests.test(msg="range"):
        assert str(str_to_scale_range("301,4012")) == "301,4012"


def test_scale_range_argument(subtests: SubTests) -> None:
    parser = get_args_parser()

    with subtests.test(msg="not provided"):
        assert parser.parse_args(REQUIRED_ARGS).scale_range is None

    with subtests.test(msg="empty"):
        assert parser.parse_args([*REQUIRED_ARGS, "--scale-range", ""]).scale_range is None

    with subtests.test(msg="per band"):
        scale_range = parser.parse_args([*REQUIRED_ARGS, "--scale-range", "1,10;2,20;3,30"]).scale_range
        assert str(scale_range) == "1,10;2,20;3,30"


def test_scale_range_argument_rejects_invalid(capsys: CaptureFixture[str]) -> None:
    with raises(SystemExit):
        get_args_parser().parse_args([*REQUIRED_ARGS, "--scale-range", "4012,301"])

    assert "--scale-range" in capsys.readouterr().err


def test_str_to_gamma(subtests: SubTests) -> None:
    for value, expected in [("", 1.0), (" ", 1.0), ("1", 1.0), ("1.3", 1.3)]:
        with subtests.test(msg=repr(value)):
            assert str_to_gamma(value) == expected

    for value in ["0", "-1.3", "a"]:
        with subtests.test(msg=value):
            with raises(ArgumentTypeError):
                str_to_gamma(value)


def test_scale_gamma_argument(subtests: SubTests) -> None:
    parser = get_args_parser()

    with subtests.test(msg="not provided"):
        assert parser.parse_args(REQUIRED_ARGS).scale_gamma == 1.0

    with subtests.test(msg="provided"):
        assert parser.parse_args([*REQUIRED_ARGS, "--scale-gamma", "1.3"]).scale_gamma == 1.3
