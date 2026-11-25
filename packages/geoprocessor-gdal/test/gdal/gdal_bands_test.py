from fake_gdalinfo import add_band, add_palette_band, fake_gdalinfo
from geoprocessor_gdal.gdal.gdal_bands import get_gdal_band_offset
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from pytest import raises


def test_gdal_grey_bands() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-b 1 -b 1 -b 1"


def test_gdal_grey_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Alpha")
    add_band(gdalinfo, color_interpretation="Gray")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-b 2 -b 2 -b 2 -b 1"


def test_gdal_grey_bands_dem_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.DEM_LERC.value)

    assert " ".join(bands) == "-b 1"


def test_gdal_rgba_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Alpha")
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-b 2 -b 3 -b 4 -b 1"


def test_gdal_rgb_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-b 1 -b 2 -b 3"


def test_gdal_rgb_undefined_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="Undefined")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.RGBNIR_ZSTD.value)

    assert " ".join(bands) == "-b 1 -b 2 -b 3 -b 4 -colorinterp_4 nir"


def test_gdal_rgb_undefined_alpha_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="Undefined")
    add_band(gdalinfo, color_interpretation="Alpha")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.RGBNIR_ZSTD.value)

    assert " ".join(bands) == "-b 1 -b 2 -b 3 -b 4 -colorinterp_4 nir -b 5"


def test_gdal_rgbnir_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="NIR")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.RGBNIR_ZSTD.value)

    assert " ".join(bands) == "-b 1 -b 2 -b 3 -b 4"


def test_gdal_rgbnira_bands_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")
    add_band(gdalinfo, color_interpretation="Blue")
    add_band(gdalinfo, color_interpretation="NIR")
    add_band(gdalinfo, color_interpretation="Alpha")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.RGBNIR_ZSTD.value)

    assert " ".join(bands) == "-b 1 -b 2 -b 3 -b 4 -b 5"


def test_gdal_rgba_palette_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_palette_band(gdalinfo, colour_table_entries=[[x, x, x, 255] for x in reversed(range(256))])

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-expand rgba"


def test_gdal_rgb_palette_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_palette_band(gdalinfo, colour_table_entries=[[x, x, x] for x in reversed(range(256))])

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-expand rgb"


# Older greyscale historical scanned imagery was standardised as 4 band GGGA from paletted source TIFFs
def test_gdal_ggga() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")
    add_band(gdalinfo, color_interpretation="Gray")
    add_band(gdalinfo, color_interpretation="Gray")
    add_band(gdalinfo, color_interpretation="Alpha")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo)

    assert " ".join(bands) == "-b 1 -b 1 -b 1 -b 4"


def test_gdal_default_rg_missing_b() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Red")
    add_band(gdalinfo, color_interpretation="Green")

    with raises(RuntimeError) as excinfo:
        get_gdal_band_offset("some_file.tiff", gdalinfo)
    assert "missing_expected_rgb_bands: Blue" in str(excinfo.value)


def test_gdal_grey_bands_intensity_detection() -> None:
    gdalinfo = fake_gdalinfo()
    add_band(gdalinfo, color_interpretation="Gray")

    bands = get_gdal_band_offset("some_file.tiff", gdalinfo, CompressionPreset.INTENSITY_ZSTD.value)
    assert " ".join(bands) == "-b 1"
