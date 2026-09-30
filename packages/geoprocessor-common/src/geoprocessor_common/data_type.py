from enum import Enum


class DataType(str, Enum):
    """Enum for the data types a dataset can be standardised as.

    `UINT16` is valid with the `CompressionPreset.RGBNIR_ZSTD` preset and with `CompressionPreset.WEBP`
    when the imagery category is aerial-photo based.
    `UINT32` is only valid with the `CompressionPreset.RGBNIR_ZSTD` preset.
    """

    FLOAT32 = "float32"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
