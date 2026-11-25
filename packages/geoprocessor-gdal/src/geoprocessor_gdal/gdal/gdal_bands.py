from geoprocessor_gdal.gdal.gdal_helper import gdal_info
from geoprocessor_gdal.gdal.gdal_presets import CompressionPreset
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo, GdalInfoBand
from linz_logger import get_log


def find_band(bands: list[GdalInfoBand], color: str) -> GdalInfoBand | None:
    """Look for a specific colorInterpretation inside of a `gdalinfo` band output.

    Args:
        bands: Bands to search
        color: Color to search, eg Red, Green, Gray

    Returns:
       Band if it exists, None otherwise
    """
    for band in bands:
        if band["colorInterpretation"] == color:
            return band
    return None


def get_gray_band_args(band: GdalInfoBand, preset: str | None = None) -> list[str]:
    """
    Return GDAL args for gray band (single DEM/DSM or converted to RGB).

    Args:
        band: Band to create gdal_translate args for
        preset: TIFF compression preset for the dataset

    Returns:
       List of GDAL args for gray band

    Examples:
        >>> get_gray_band_args({"band": 1, "colorInterpretation": "Gray"}, preset="dem_lerc")
        ['-b', '1']
        >>> get_gray_band_args({"band": 1, "colorInterpretation": "Gray"})
        ['-b', '1', '-b', '1', '-b', '1']
    """
    band_grey_index = str(band["band"])
    if preset in [
        CompressionPreset.DEM_LERC.value,
        CompressionPreset.DEM_ZSTD.value,
        CompressionPreset.INTENSITY_ZSTD.value,
    ]:
        # return single band if DEM/DSM or intensity
        return ["-b", band_grey_index]
    # Grey scale imagery, set R,G and B to just the grey_band
    return ["-b", band_grey_index, "-b", band_grey_index, "-b", band_grey_index]


# pylint: disable=line-too-long
def get_palette_band_args(band: GdalInfoBand, file: str) -> list[str]:
    """
    Return GDAL args for palette band (expand to rgb or rgba).

    Args:
        band: Band to create gdal_translate args for
        file: file to check

    Returns:
       List of GDAL args for palette band

    Examples:
        >>> get_palette_band_args({"band": 1, "colorInterpretation": "Palette", "colorTable": {"entries": [(1,2,3)]}}, "foo.tiff")
        ['-expand', 'rgb']
        >>> get_palette_band_args({"band": 1, "colorInterpretation": "Palette", "colorTable": {"entries": [(1,2,3,4)]}}, "foo.tiff")
        ['-expand', 'rgba']
        >>> get_palette_band_args({"band": 1, "colorInterpretation": "Palette", "colorTable": {"entries": [[1,2,3,4,5]]}}, "foo.tiff")
        Traceback (most recent call last):
        ...
        RuntimeError: unknown_palette_band_type
        >>> get_palette_band_args({"band": 1, "colorInterpretation": "Palette", "colorTable": None}, "foo.tiff")
        Traceback (most recent call last):
        ...
        RuntimeError: palette_band_missing_colorTable
    """
    if colour_table := band["colorTable"]:
        palette_channels = len(colour_table["entries"][0])
        if palette_channels in (3, 4):
            return ["-expand", "rgba" if palette_channels == 4 else "rgb"]
        get_log().error(
            "unknown_palette_band_type",
            palette_channels=palette_channels,
            first_entry=colour_table["entries"][0],
            path=file,
        )
        raise RuntimeError("unknown_palette_band_type")
    get_log().error("palette_band_missing_colorTable", path=file)
    raise RuntimeError("palette_band_missing_colorTable")


def get_rgb_bands_args(bands: list[GdalInfoBand]) -> list[str]:
    """Return GDAL args for RGB bands (bands 1,2,3).

    Args:
        bands: Bands to create gdal_translate args for

    Returns:
       List of GDAL args for RGB bands
    """
    band_red = find_band(bands, "Red")
    band_green = find_band(bands, "Green")
    band_blue = find_band(bands, "Blue")

    missing = [
        color_interp for color_interp, band in [("Red", band_red), ("Green", band_green), ("Blue", band_blue)] if band is None
    ]

    if band_red is None or band_green is None or band_blue is None:
        get_log().error(
            "gdal_info_bands_failed", band_red=band_red is None, band_green=band_green is None, band_blue=band_blue is None
        )
        raise RuntimeError(f"missing_expected_rgb_bands: {', '.join(missing)}")

    return ["-b", str(band_red["band"]), "-b", str(band_green["band"]), "-b", str(band_blue["band"])]


def get_gdal_band_offset(file: str, info: GdalInfo | None = None, preset: str | None = None) -> list[str]:
    """Get the banding parameters for a `gdal_translate` command.

    Args:
        file: file to check
        info: optional precomputed gdalinfo
        preset: TIFF compression preset for the dataset.
                "dem_lerc" preset used to differentiate single band elevation tiffs from
                single band historical imagery, "rgbnir_zstd" preset used to identify NIR

    Returns:
        list of band mappings eg "-b 1 -b 1 -b 1"
    """
    if info is None:
        info = gdal_info(file)

    bands = info["bands"]

    band_alpha_arg: list[str] = []
    band_nir_arg: list[str] = []

    if band_alpha := find_band(bands, "Alpha"):
        band_alpha_arg.extend(["-b", str(band_alpha["band"])])

    if band_grey := find_band(bands, "Gray"):
        return get_gray_band_args(band_grey, preset) + band_alpha_arg

    if band_palette := find_band(bands, "Palette"):
        return get_palette_band_args(band_palette, file)

    rgb_bands = get_rgb_bands_args(bands)

    # Add NIR band if required
    if preset == CompressionPreset.RGBNIR_ZSTD.value:
        for color_interp in ["NIR", "Undefined"]:
            if band := find_band(bands, color_interp):
                band_nir_arg.extend(["-b", str(band["band"])])
                if color_interp == "Undefined":
                    band_nir_arg.extend([f"-colorinterp_{str(band["band"])}", "nir"])

    return rgb_bands + band_nir_arg + band_alpha_arg
