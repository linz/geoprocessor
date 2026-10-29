from geoprocessor_raster.standardise_validate import get_args_parser
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests

REQUIRED_ARGS = [
    *["--preset", "webp", "--from-file", "input.json", "--source-epsg", "2193", "--target-epsg", "2193"],
    *["--gsd", "0.1", "--data-type", "uint16", "--create-footprints", "true", "--collection-id", "123"],
    *["--target", "/tmp/"],
]


def test_rescale_range_argument(subtests: SubTests, capsys: CaptureFixture[str]) -> None:
    parser = get_args_parser()

    for args, expected in [
        ([], None),
        (["--rescale-range", " "], None),
        (["--rescale-range", "1,10;2,20;3,30"], "1,10;2,20;3,30"),
    ]:
        with subtests.test(msg=" ".join(args) or "not provided"):
            rescale_range = parser.parse_args([*REQUIRED_ARGS, *args]).rescale_range
            assert (rescale_range if rescale_range is None else str(rescale_range)) == expected

    with subtests.test(msg="rejects an invalid range with its reason"):
        with raises(SystemExit):
            parser.parse_args([*REQUIRED_ARGS, "--rescale-range", "4012,301"])
        assert "--rescale-range: Invalid band range, expected 0 <= min < max <= 65535: 4012,301" in capsys.readouterr().err


def test_rescale_gamma_argument(subtests: SubTests) -> None:
    parser = get_args_parser()

    for args, expected in [([], 1.0), (["--rescale-gamma", " "], 1.0), (["--rescale-gamma", "1.3"], 1.3)]:
        with subtests.test(msg=" ".join(args) or "not provided"):
            assert parser.parse_args([*REQUIRED_ARGS, *args]).rescale_gamma == expected

    for value in ["0", "-1.3", "a", "nan", "inf"]:
        with subtests.test(msg=f"rejects {value}"):
            with raises(SystemExit):
                parser.parse_args([*REQUIRED_ARGS, "--rescale-gamma", value])
