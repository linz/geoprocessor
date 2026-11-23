from geoprocessor_gdal.rescale_range import RescaleRange
from pytest import raises
from pytest_subtests import SubTests


def test_rescale_range_parse(subtests: SubTests) -> None:
    """One range or one per RGB band round-trips through its string; malformed, reversed or non-uint16 ranges are rejected."""
    for value in ["301,4012", "301,4012;295,3980;310,4100", "0,65535"]:
        with subtests.test(msg=value):
            assert str(RescaleRange.parse(value)) == value

    for value in ["", "301", "301,4012,5000", "a,b", "4012,301", "301,301", "-1,4012", "301,65536", "1,2;3,4"]:
        with subtests.test(msg=f"rejects {value!r}"):
            with raises(ValueError):
                RescaleRange.parse(value)
