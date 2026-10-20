from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fake_gdalinfo import fake_gdalinfo
from geoprocessor_common.data_type import DataType
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from geoprocessor_gdal.gdal.gdal_scale import ScaleRange
from geoprocessor_gdal.standardising import StandardisingConfig, apply_gdal_transformation
from pytest import raises
from pytest_subtests import SubTests


def standardising_config(
    preset: str, data_type: str, scale_range: ScaleRange | None = None, scale_gamma: float = 1.0
) -> StandardisingConfig:
    return StandardisingConfig(
        gdal_preset=preset,
        source_epsg=EpsgNumber.NZTM_2000.value,
        target_epsg=EpsgNumber.NZTM_2000.value,
        gsd=Decimal("0.1"),
        create_footprints=False,
        simplify_footprints=False,
        cutline=None,
        data_type=data_type,
        scale_range=scale_range,
        scale_gamma=scale_gamma,
    )


def test_config_allows_high_bit_depth_rgbnir(subtests: SubTests) -> None:
    for data_type in [DataType.UINT8, DataType.UINT16]:
        with subtests.test(msg=f"{data_type.value} is valid with {CompressionPreset.RGBNIR_ZSTD.value}"):
            config = standardising_config(CompressionPreset.RGBNIR_ZSTD.value, data_type.value)

            assert config.data_type == data_type.value


def test_config_allows_uint8_for_any_preset(subtests: SubTests) -> None:
    for preset in CompressionPreset:
        with subtests.test(msg=f"{DataType.UINT8.value} is valid with {preset.value}"):
            config = standardising_config(preset.value, DataType.UINT8.value)

            assert config.data_type == DataType.UINT8.value


def test_config_allows_float32_for_dem_presets(subtests: SubTests) -> None:
    for preset in [CompressionPreset.DEM_LERC, CompressionPreset.DEM_ZSTD]:
        with subtests.test(msg=f"{DataType.FLOAT32.value} is valid with {preset.value}"):
            config = standardising_config(preset.value, DataType.FLOAT32.value)

            assert config.data_type == DataType.FLOAT32.value


def test_config_rejects_uint16_for_presets_other_than_rgbnir_or_webp(subtests: SubTests) -> None:
    for preset in [
        preset for preset in CompressionPreset if preset not in (CompressionPreset.RGBNIR_ZSTD, CompressionPreset.WEBP)
    ]:
        with subtests.test(msg=f"{DataType.UINT16.value} is invalid with {preset.value}"):
            with raises(
                ValueError,
                match=(
                    f"is only supported with the {CompressionPreset.RGBNIR_ZSTD.value} or "
                    f"{CompressionPreset.WEBP.value} presets"
                ),
            ):
                standardising_config(preset.value, DataType.UINT16.value)


def test_config_rejects_unknown_data_type() -> None:
    with raises(ValueError, match="Unsupported data type: int16"):
        standardising_config(CompressionPreset.RGBNIR_ZSTD.value, "int16")


def test_config_allows_scale_range_for_uint16_webp() -> None:
    config = standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, ScaleRange.parse("301,4012"))

    assert str(config.scale_range) == "301,4012"


def test_config_rejects_scale_range_without_uint16_webp(subtests: SubTests) -> None:
    for preset, data_type in [(CompressionPreset.WEBP, DataType.UINT8), (CompressionPreset.RGBNIR_ZSTD, DataType.UINT16)]:
        with subtests.test(msg=f"{preset.value} {data_type.value}"):
            with raises(ValueError, match="scale range is only supported"):
                standardising_config(preset.value, data_type.value, ScaleRange.parse("301,4012"))


def test_apply_gdal_transformation_scales_each_output_band(tmp_path: Path) -> None:
    config = standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, ScaleRange.parse("301,4012"))

    with (
        patch("geoprocessor_gdal.standardising.gdal_info", return_value=fake_gdalinfo()),
        patch(
            "geoprocessor_gdal.standardising.get_gdal_band_offset", return_value=["-b", "1", "-b", "2", "-b", "3", "-b", "4"]
        ),
        patch("geoprocessor_gdal.standardising.run_gdal") as run_gdal,
    ):
        apply_gdal_transformation("input.vrt", config, str(tmp_path), tile_name="CE16_5000_1001")

    command = run_gdal.call_args.args[0]
    assert command[command.index("-scale_3") : command.index("-scale_3") + 3] == ["-scale_3", "301", "4012"]
    assert command[command.index("-scale_4") : command.index("-scale_4") + 3] == ["-scale_4", "0", "65535"]
    assert "LINZ_SCALE_SOURCE_RANGE=301,4012" in command


def test_config_allows_scale_gamma_with_scale_range() -> None:
    config = standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, ScaleRange.parse("301,4012"), 1.3)

    assert config.scale_gamma == 1.3


def test_config_rejects_invalid_scale_gamma(subtests: SubTests) -> None:
    with subtests.test(msg="without scale range"):
        with raises(ValueError, match="scale gamma requires a scale range"):
            standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, scale_gamma=1.3)

    for gamma in [0, -1.3]:
        with subtests.test(msg=f"gamma {gamma}"):
            with raises(ValueError, match="positive scale gamma"):
                standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, ScaleRange.parse("301,4012"), gamma)


def test_apply_gdal_transformation_applies_scale_gamma(tmp_path: Path) -> None:
    config = standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, ScaleRange.parse("301,4012"), 1.3)

    with (
        patch("geoprocessor_gdal.standardising.gdal_info", return_value=fake_gdalinfo()),
        patch(
            "geoprocessor_gdal.standardising.get_gdal_band_offset", return_value=["-b", "1", "-b", "2", "-b", "3", "-b", "4"]
        ),
        patch("geoprocessor_gdal.standardising.run_gdal") as run_gdal,
    ):
        apply_gdal_transformation("input.vrt", config, str(tmp_path), tile_name="CE16_5000_1001")

    command = run_gdal.call_args.args[0]
    assert command[command.index("-exponent_1") : command.index("-exponent_1") + 2] == ["-exponent_1", "0.769231"]
    assert "-exponent_4" not in command
    assert "LINZ_SCALE_GAMMA=1.3" in command
