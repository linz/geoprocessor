from decimal import Decimal

from geoprocessor_common.data_type import DataType
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from geoprocessor_gdal.standardising import StandardisingConfig
from pytest import raises
from pytest_subtests import SubTests


def standardising_config(preset: str, data_type: str) -> StandardisingConfig:
    return StandardisingConfig(
        gdal_preset=preset,
        source_epsg=EpsgNumber.NZTM_2000.value,
        target_epsg=EpsgNumber.NZTM_2000.value,
        gsd=Decimal("0.1"),
        create_footprints=False,
        simplify_footprints=False,
        cutline=None,
        data_type=data_type,
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
