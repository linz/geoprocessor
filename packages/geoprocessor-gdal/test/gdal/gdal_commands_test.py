from decimal import Decimal

from geoprocessor_common.data_type import DataType
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_gdal.gdal.gdal_commands import (
    get_build_vrt_command,
    get_cutline_command,
    get_footprint_command,
    get_gdal_command,
    get_webp_rescaled,
)
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset, HillshadePreset
from geoprocessor_gdal.gdal.gdal_scale import ScaleRange
from pytest import raises
from pytest_subtests import SubTests


def test_get_webp_rescaled() -> None:
    assert get_webp_rescaled(DataType.UINT16.value) == [
        "-scale",
        "0",
        "65535",
        "0",
        "255",
        "-ot",
        "Byte",
    ]


def test_get_webp_rescaled_with_scale_range(subtests: SubTests) -> None:
    with subtests.test(msg="single range with alpha"):
        assert get_webp_rescaled(DataType.UINT16.value, ScaleRange.parse("301,4012"), band_count=4) == [
            *["-scale_1", "301", "4012", "0", "255"],
            *["-scale_2", "301", "4012", "0", "255"],
            *["-scale_3", "301", "4012", "0", "255"],
            *["-scale_4", "0", "65535", "0", "255"],
            *["-ot", "Byte"],
            *["-mo", "LINZ_SCALE_SOURCE_RANGE=301,4012"],
        ]

    with subtests.test(msg="per band without alpha"):
        assert get_webp_rescaled(DataType.UINT16.value, ScaleRange.parse("1,10;2,20;3,30"), band_count=3) == [
            *["-scale_1", "1", "10", "0", "255"],
            *["-scale_2", "2", "20", "0", "255"],
            *["-scale_3", "3", "30", "0", "255"],
            *["-ot", "Byte"],
            *["-mo", "LINZ_SCALE_SOURCE_RANGE=1,10;2,20;3,30"],
        ]

    for band_count in [None, 2]:
        with subtests.test(msg=f"rejects band count {band_count}"):
            with raises(ValueError, match="output bands"):
                get_webp_rescaled(DataType.UINT16.value, ScaleRange.parse("301,4012"), band_count=band_count)


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

    with subtests.test(msg=f"{DataType.UINT8.value} is not rescaled"):
        assert "-scale" not in gdal_command


def test_preset_webp_uint16_is_rescaled(subtests: SubTests) -> None:
    gdal_command = get_gdal_command(CompressionPreset.WEBP.value, epsg=EpsgNumber.NZTM_2000, data_type=DataType.UINT16.value)

    with subtests.test(msg=f"{DataType.UINT16.value} is rescaled to 8-bit"):
        assert "-scale" in gdal_command

    with subtests.test():
        assert "Byte" in gdal_command

    with subtests.test():
        assert "compress=webp" in gdal_command


def test_preset_webp_uint16_applies_scale_range() -> None:
    gdal_command = get_gdal_command(
        CompressionPreset.WEBP.value,
        epsg=EpsgNumber.NZTM_2000,
        data_type=DataType.UINT16.value,
        scale_range=ScaleRange.parse("301,4012"),
        band_count=4,
    )

    assert "-scale" not in gdal_command
    assert gdal_command[gdal_command.index("-scale_1") : gdal_command.index("-scale_1") + 5] == [
        "-scale_1",
        "301",
        "4012",
        "0",
        "255",
    ]


def test_scale_range_is_rejected_without_rescaling(subtests: SubTests) -> None:
    for preset, data_type in [
        (CompressionPreset.WEBP, DataType.UINT8),
        (CompressionPreset.RGBNIR_ZSTD, DataType.UINT16),
        (CompressionPreset.LZW, DataType.UINT8),
    ]:
        with subtests.test(msg=f"{preset.value} {data_type.value}"):
            with raises(ValueError, match="only supported when rescaling to 8-bit"):
                get_gdal_command(
                    preset.value,
                    epsg=EpsgNumber.NZTM_2000,
                    data_type=data_type.value,
                    scale_range=ScaleRange.parse("301,4012"),
                    band_count=4,
                )


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
    gdal_command = get_gdal_command(
        CompressionPreset.RGBNIR_ZSTD.value,
        epsg=EpsgNumber.NZTM_2000.value,
        data_type=DataType.UINT16.value,
    )

    with subtests.test(msg=f"{DataType.UINT16.value} uses bigtiff=yes"):
        assert "bigtiff=yes" in gdal_command

    with subtests.test(msg=f"{DataType.UINT16.value} does not use bigtiff=no"):
        assert "bigtiff=no" not in gdal_command


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


def test_get_build_vrt_command_keeps_input_order(subtests: SubTests) -> None:
    """`gdalbuildvrt` draws later inputs over earlier ones."""
    files = ["/tmp/source/z.tiff", "/tmp/source/a.tiff", "/tmp/source/m.tiff"]

    command = get_build_vrt_command(files=files, output="/tmp/source.vrt")

    with subtests.test(msg="inputs are last, in the order given"):
        assert command[-3:] == files

    with subtests.test(msg="output precedes the inputs"):
        assert command[-4] == "/tmp/source.vrt"
