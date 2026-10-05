from decimal import Decimal

from geoprocessor_common.data_type import DataType
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_gdal.gdal.gdal_commands import (
    get_cutline_command,
    get_footprint_command,
    get_gdal_command,
)
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset, HillshadePreset
from pytest_subtests import SubTests


def test_preset_webp(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(CompressionPreset.WEBP.value, epsg=EpsgNumber.NZTM_2000, data_type=DataType.UINT8.value)

    # Basic cog creation
    with subtests.test():
        assert "COG" in gdal_command

    with subtests.test():
        assert "blocksize=512" in gdal_command

    with subtests.test():
        assert "num_threads=all_cpus" in gdal_command

    with subtests.test():
        assert "bigtiff=no" in gdal_command

    # Webp lossless
    with subtests.test():
        assert "compress=webp" in gdal_command

    with subtests.test():
        assert "quality=100" in gdal_command

    # Webp overviews
    with subtests.test():
        assert "overview_compress=webp" in gdal_command

    with subtests.test():
        assert "overview_resampling=lanczos" in gdal_command

    with subtests.test():
        assert "overview_quality=90" in gdal_command

    with subtests.test():
        assert "overviews=ignore_existing" in gdal_command

    with subtests.test():
        assert f"EPSG:{EpsgNumber.NZTM_2000.value}" in gdal_command


def test_preset_zstd(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(
        CompressionPreset.RGBNIR_ZSTD.value, epsg=EpsgNumber.NZTM_2000, data_type=DataType.FLOAT32.value
    )

    # Basic cog creation
    with subtests.test():
        assert "COG" in gdal_command

    with subtests.test():
        assert "blocksize=512" in gdal_command

    with subtests.test():
        assert "num_threads=all_cpus" in gdal_command

    with subtests.test():
        assert "bigtiff=no" in gdal_command

    with subtests.test():
        assert "compress=zstd" in gdal_command

    # ZSTD level 17
    with subtests.test():
        assert "level=17" in gdal_command

    # ZSTD overviews
    with subtests.test():
        assert "overview_compress=zstd" in gdal_command

    with subtests.test():
        assert "overview_resampling=lanczos" in gdal_command

    with subtests.test():
        assert "overviews=ignore_existing" in gdal_command

    with subtests.test():
        assert f"EPSG:{EpsgNumber.NZTM_2000.value}" in gdal_command


def test_preset_zstd_high_bit_depth_uses_bigtiff(subtests: SubTests) -> None:
    for data_type in (DataType.UINT16,):
        gdal_command = get_gdal_command(
            CompressionPreset.RGBNIR_ZSTD.value,
            epsg=EpsgNumber.NZTM_2000.value,
            data_type=data_type.value,
        )

        with subtests.test(msg=f"{data_type.value} uses bigtiff=yes"):
            assert "bigtiff=yes" in gdal_command

        with subtests.test(msg=f"{data_type.value} does not use bigtiff=no"):
            assert "bigtiff=no" not in gdal_command


def test_preset_zstd_rejects_uint32() -> None:
    try:
        get_gdal_command(
            CompressionPreset.RGBNIR_ZSTD.value,
            epsg=EpsgNumber.NZTM_2000.value,
            data_type=DataType.UINT32.value,
        )
    except ValueError as error:
        assert str(error) == "Unsupported data type: uint32"
    else:
        raise AssertionError("Expected get_gdal_command to reject uint32")


def test_preset_zstd_uint8_keeps_bigtiff_no(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(
        CompressionPreset.RGBNIR_ZSTD.value,
        epsg=EpsgNumber.NZTM_2000.value,
        data_type=DataType.UINT8.value,
    )

    with subtests.test():
        assert "bigtiff=no" in gdal_command

    with subtests.test():
        assert "bigtiff=yes" not in gdal_command


def test_preset_lzw(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(CompressionPreset.LZW.value, epsg=EpsgNumber.NZTM_2000, data_type=DataType.UINT8.value)

    # Basic cog creation
    with subtests.test():
        assert "COG" in gdal_command

    with subtests.test():
        assert "blocksize=512" in gdal_command

    with subtests.test():
        assert "num_threads=all_cpus" in gdal_command

    with subtests.test():
        assert "bigtiff=no" in gdal_command

    with subtests.test():
        assert "overviews=ignore_existing" in gdal_command

    # LZW compression
    with subtests.test():
        assert "compress=lzw" in gdal_command

    with subtests.test():
        assert "predictor=2" in gdal_command

    # Webp overviews
    with subtests.test():
        assert "overview_compress=webp" in gdal_command

    with subtests.test():
        assert "overview_resampling=lanczos" in gdal_command

    with subtests.test():
        assert "overview_quality=90" in gdal_command

    with subtests.test():
        assert f"EPSG:{EpsgNumber.NZTM_2000.value}" in gdal_command


def test_preset_dem_lerc(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(
        CompressionPreset.DEM_LERC.value, epsg=EpsgNumber.NZTM_2000, data_type=DataType.FLOAT32.value
    )
    # Basic cog creation
    with subtests.test():
        assert "COG" in gdal_command

    with subtests.test():
        assert "blocksize=512" in gdal_command

    with subtests.test():
        assert "num_threads=all_cpus" in gdal_command

    with subtests.test():
        assert "bigtiff=no" in gdal_command

    with subtests.test():
        assert "overviews=ignore_existing" in gdal_command

    # LERC compression
    with subtests.test():
        assert "compress=lerc" in gdal_command

    with subtests.test():
        assert "max_z_error=0.001" in gdal_command

    with subtests.test():
        assert "max_z_error_overview=0.1" in gdal_command

    # No webp overviews
    with subtests.test():
        assert "overview_compress=webp" not in gdal_command

    with subtests.test():
        assert "overview_resampling=lanczos" not in gdal_command

    with subtests.test():
        assert "overview_quality=90" not in gdal_command

    with subtests.test():
        assert f"EPSG:{EpsgNumber.NZTM_2000.value}" in gdal_command


def test_cutline_params(subtests: SubTests) -> None:
    gdal_command = get_cutline_command("cutline.fgb")

    with subtests.test():
        assert "-cutline" in gdal_command

    with subtests.test():
        assert "cutline.fgb" in gdal_command

    with subtests.test():
        assert "-dstalpha" in gdal_command


def test_footprint_preset_rgbnir_zstd(subtests: SubTests) -> None:
    gdal_command = get_footprint_command(Decimal(1), CompressionPreset.RGBNIR_ZSTD.value)

    with subtests.test():
        assert "-b 5" in " ".join(gdal_command)


def test_footprint_preset_hillshade_igor(subtests: SubTests) -> None:
    gdal_command = get_footprint_command(Decimal(1), HillshadePreset.IGOR.value)

    with subtests.test():
        assert "-b 5" not in " ".join(gdal_command)
