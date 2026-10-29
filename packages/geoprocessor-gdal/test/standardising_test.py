from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fake_gdalinfo import fake_gdalinfo
from geoprocessor_common.data_type import DataType
from geoprocessor_common.epsg import EpsgNumber
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from geoprocessor_gdal.gdal.gdal_rescale import RescaleRange
from geoprocessor_gdal.standardising import StandardisingConfig, apply_gdal_transformation
from pytest import CaptureFixture, raises
from pytest_subtests import SubTests


def standardising_config(
    preset: str, data_type: str, rescale_range: RescaleRange | None = None, rescale_gamma: float = 1.0
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
        rescale_range=rescale_range,
        rescale_gamma=rescale_gamma,
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


def test_config_rescale(subtests: SubTests, capsys: CaptureFixture[str]) -> None:
    webp_uint16 = (CompressionPreset.WEBP.value, DataType.UINT16.value)
    rescale_range = RescaleRange.parse("301,4012")

    with subtests.test(msg="allows a rescale range and gamma for uint16 webp"):
        config = standardising_config(*webp_uint16, rescale_range, 1.3)
        assert (str(config.rescale_range), config.rescale_gamma) == ("301,4012", 1.3)
        assert "webp_rescale_full_range" not in capsys.readouterr().out

    with subtests.test(msg="warns about the full range without a rescale range"):
        standardising_config(*webp_uint16)
        assert "webp_rescale_full_range" in capsys.readouterr().out

    for preset, data_type in [(CompressionPreset.WEBP, DataType.UINT8), (CompressionPreset.RGBNIR_ZSTD, DataType.UINT16)]:
        with subtests.test(msg=f"rejects a rescale range for {preset.value} {data_type.value}"):
            with raises(ValueError, match="rescale range is only supported"):
                standardising_config(preset.value, data_type.value, rescale_range)

    with subtests.test(msg="rejects a gamma without a rescale range"):
        with raises(ValueError, match="rescale gamma requires a rescale range"):
            standardising_config(*webp_uint16, rescale_gamma=1.3)

    for gamma in [0, -1.3]:
        with subtests.test(msg=f"rejects gamma {gamma}"):
            with raises(ValueError, match="positive rescale gamma"):
                standardising_config(*webp_uint16, rescale_range, gamma)


def test_apply_gdal_transformation_rescales_each_output_band(tmp_path: Path) -> None:
    config = standardising_config(CompressionPreset.WEBP.value, DataType.UINT16.value, RescaleRange.parse("301,4012"), 1.3)

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
    assert command[command.index("-exponent_3") : command.index("-exponent_3") + 2] == ["-exponent_3", "0.769231"]
    assert command[command.index("-scale_4") : command.index("-scale_4") + 3] == ["-scale_4", "0", "65535"]
    assert "-exponent_4" not in command
    assert "LINZ_RESCALE_RANGE=301,4012" in command
    assert "LINZ_RESCALE_GAMMA=1.3" in command
