from fake_gdalinfo import add_band, add_palette_band, fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from geoprocessor_gdal.tiff.file_tiff import FileTiff, FileTiffErrorType


def test_check_band_count_valid_3() -> None:
    """
    tests check_band_count when the input layer has a valid band count
    which is 3 bands
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_band_count_valid_4() -> None:
    """
    tests check_band_count when the input layer has a valid band count
    which is 4 bands where the fourth band is Alpha
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_band_count_valid_5() -> None:
    """
    tests check_band_count when the input layer has a valid band count
    which is 5 bands where the fourth band is NIR and the fifth band is Alpha
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo, color_interpretation="NIR")
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_band_count_invalid_2() -> None:
    """
    tests check_band_count when the input layer has a invalid band count of 2
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert file_tiff.get_errors()


def test_check_band_count_invalid_4() -> None:
    """
    tests check_band_count when the input layer has a invalid
    band count of 4 where the 4th band is not Alpha
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert file_tiff.get_errors()


def test_check_band_count_invalid_5() -> None:
    """
    tests check_band_count when the input layer has a invalid
    band count of 5 where the 4th band is not NIR
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_band_count(gdalinfo)

    assert file_tiff.get_errors()


def test_check_band_count_valid_1_dem() -> None:
    """
    tests check_band_count when the input layer has a valid band count
    which is 1 bands and a DEM preset
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_band_count(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_band_count_invalid_alpha_dem() -> None:
    """
    tests check_band_count when the input layer has a valid band count
    which is 2 bands where the second band is Alpha and DEM preset
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_band_count(gdalinfo)

    assert file_tiff.get_errors()


def test_check_band_count_invalid_3_dem() -> None:
    """
    tests check_band_count when the input layer has an invalid band count
    which is 3 bands where the preset is DEM.
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)
    add_band(gdalinfo)
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_band_count(gdalinfo)

    assert file_tiff.get_errors()


def test_check_color_interpretation_valid_rgb() -> None:
    """
    tests check_color_interpretation with the correct RGB color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_color_interpretation_valid_rgbna() -> None:
    """
    tests check_color_interpretation with the correct RGBNA color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="NIR")
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_color_interpretation_valid_greyscale() -> None:
    """
    tests check_color_interpretation with the correct greyscale color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")
    add_band(gdalinfo, color_interpretation="Gray")
    add_band(gdalinfo, color_interpretation="Gray")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_color_interpretation_invalid() -> None:
    """
    tests check_color_interpretation with the incorrect color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="undefined")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert file_tiff.get_errors()


def test_check_color_interpretation_invalid_rgbna() -> None:
    """
    tests check_color_interpretation with incorrect RGBNA color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="undefined")
    add_band(gdalinfo, color_interpretation="NIR")
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert file_tiff.get_errors()


def test_check_color_interpretation_invalid_5_band() -> None:
    """
    tests check_color_interpretation with incorrect 5 band color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="undefined")
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_color_interpretation(gdalinfo)

    assert file_tiff.get_errors()


def test_check_color_interpretation_valid_dem() -> None:
    """
    tests check_color_interpretation with the correct color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_color_interpretation(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_color_interpretation_invalid_dem() -> None:
    """
    tests check_color_interpretation with the incorrect color interpretation
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_color_interpretation(gdalinfo)

    assert file_tiff.get_errors()


def test_check_no_data_valid() -> None:
    """
    tests check_no_data when the input layer has a valid no data value of 255
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, no_data_value=255)

    file_tiff = FileTiff(["test"])
    file_tiff.check_no_data(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_no_data_valid_alpha() -> None:
    """
    tests check_no_data when the input layer has no no_data value assigned and Alpha
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="red")
    add_band(gdalinfo, color_interpretation="green")
    add_band(gdalinfo, color_interpretation="blue")
    add_band(gdalinfo, color_interpretation="Alpha")

    file_tiff = FileTiff(["test"])
    file_tiff.check_no_data(gdalinfo)

    assert not file_tiff.get_errors()


def test_check_no_data_invalid_not_alpha() -> None:
    """
    tests check_no_data when the input layer has no no_data value assigned and invalid fourth band
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="red")
    add_band(gdalinfo, color_interpretation="green")
    add_band(gdalinfo, color_interpretation="blue")
    add_band(gdalinfo, color_interpretation="invalid")

    file_tiff = FileTiff(["test"])
    file_tiff.check_no_data(gdalinfo)

    assert file_tiff.get_errors()


def test_check_no_data_no_value() -> None:
    """
    tests check_no_data when the input layer has no no_data value assigned
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"])
    file_tiff.check_no_data(gdalinfo)

    assert file_tiff.get_errors()


def test_is_no_data_true_255() -> None:
    """
    tests is_no_data when the input layer that has 255 no_data value assigned
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, no_data_value=255)

    file_tiff = FileTiff(["test"])
    assert file_tiff.is_no_data(gdalinfo)


def test_is_no_data_true_0() -> None:
    """
    tests is_no_data when the input layer that has 0 no_data value assigned
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, no_data_value=0)

    file_tiff = FileTiff(["test"])
    assert file_tiff.is_no_data(gdalinfo)


def test_is_no_data_false() -> None:
    """
    tests is_no_data when the input layer that does not have no_data value assigned
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo)

    file_tiff = FileTiff(["test"])
    assert not file_tiff.is_no_data(gdalinfo)


def test_check_no_data_invalid_value() -> None:
    """
    tests check_no_data when the input layer has the wrong value of 0 assigned
    """
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, no_data_value=0)

    file_tiff = FileTiff(["test"])
    file_tiff.check_no_data(gdalinfo)

    assert file_tiff.get_errors()


def test_check_srs_valid() -> None:
    """
    tests check_srs with the same srs value
    """
    srs_to_test_against = b"SRS Test"
    srs_tif = b"SRS Test"

    file_tiff = FileTiff(["test"])
    file_tiff.set_srs(srs_to_test_against)
    file_tiff.check_srs(srs_tif)

    assert not file_tiff.get_errors()


def test_check_srs_invalid() -> None:
    """
    tests check_srs with a different srs value
    """
    srs_to_test_against = b"SRS Test"
    srs_tif = b"SRS Different"

    file_tiff = FileTiff(["test"])
    file_tiff.set_srs(srs_to_test_against)
    file_tiff.check_srs(srs_tif)

    assert file_tiff.get_errors()


def test_should_throw_when_encountering_non_integer_no_data_value() -> None:
    gdalinfo = fake_gdalinfo()
    add_palette_band(gdalinfo, colour_table_entries=[[x, x, x, 255] for x in reversed(range(256))], no_data_value="-9999.1")

    file_tiff = FileTiff(["test"], CompressionPreset.DEM_LERC.value)
    file_tiff.check_no_data(gdalinfo)

    assert file_tiff.get_errors() == [
        {"type": FileTiffErrorType.NO_DATA, "message": "noDataValue is not -9999", "current": "-9999.1"}
    ]


def test_checksum_is_not_set_by_default() -> None:
    file_tiff = FileTiff(["test.tiff"], CompressionPreset.WEBP.value)

    assert file_tiff.get_checksum() is None


def test_set_checksum() -> None:
    file_tiff = FileTiff(["test.tiff"], CompressionPreset.WEBP.value)

    file_tiff.set_checksum("12206ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72")

    assert file_tiff.get_checksum() == "12206ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
