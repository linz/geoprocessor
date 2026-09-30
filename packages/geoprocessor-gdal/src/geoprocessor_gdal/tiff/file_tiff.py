import json
import os
from decimal import Decimal
from enum import Enum
from typing import Any
from urllib.parse import unquote

from geoprocessor_gdal.gdal.gdal_helper import GDALExecutionException, gdal_info, run_gdal
from geoprocessor_gdal.gdal.gdal_presets import DEFAULT_NO_DATA_VALUE, CompressionPreset
from geoprocessor_gdal.gdal.gdalinfo import GdalInfo


class FileTiffErrorType(str, Enum):
    GDAL_INFO = "gdalinfo"
    NO_DATA = "nodata"
    BANDS = "bands"
    SRS = "srs"
    COLOR = "color"


class FileTiffType(str, Enum):
    IMAGERY = "Imagery"
    DEM = "DEM"


class FileTiff:
    """Wrapper to carry information about the TIFF or list of TIFF within the same tile."""

    def __init__(
        self,
        paths: list[str],
        preset: str | None = None,
        include_derived: bool = False,
    ) -> None:
        paths_original = []
        for p in paths:
            # paths can be URL containing percent-encoded (like `%20` for space) sequences
            # which would make the process fail later TDE-1054
            # FIXME: we should use URLs in the code base
            paths_original.append(unquote(p))

        self._paths_original = paths_original
        self._derived_from_paths = None
        if include_derived:
            # Transform the TIFF paths to JSON path to point to STAC Items,
            # assuming the STAC Items are in the same directory as the TIFF files
            self._derived_from_paths = [f"{os.path.splitext(path)[0]}.json" for path in paths_original]

        self._path_standardised = ""
        self._errors: list[dict[str, Any]] = []
        self._gdalinfo: GdalInfo | None = None
        self._srs: bytes | None = None
        if preset in [
            CompressionPreset.DEM_LERC.value,
            CompressionPreset.DEM_ZSTD.value,
        ]:
            self._tiff_type = FileTiffType.DEM
        else:
            self._tiff_type = FileTiffType.IMAGERY

    def set_srs(self, srs: bytes) -> None:
        """Set the Spatial Reference System returned by `gdalsrsinfo` for the TIFF.

        Args:
            srs: the srs in bytes

        Example:
            ```
            $ gdalsrsinfo RGB_1000_CC16_4127_2013.tiff

            PROJ.4 : +proj=tmerc +lat_0=0 +lon_0=173 +k=0.9996 +x_0=1600000 +y_0=10000000 +ellps=GRS80
            +towgs84=0,0,0,0,0,0,0 +units=m +no_defs

            OGC WKT2:2018 :
            PROJCRS["NZGD2000 / New Zealand Transverse Mercator 2000",
                BASEGEOGCRS["NZGD2000",
                    DATUM["New Zealand Geodetic Datum 2000",
                        ELLIPSOID["GRS 1980",6378137,298.257222101,
                            LENGTHUNIT["metre",1]]],
                    PRIMEM["Greenwich",0,
                        ANGLEUNIT["degree",0.0174532925199433]],
                    ID["EPSG",4167]],
                CONVERSION["New Zealand Transverse Mercator 2000",
                    METHOD["Transverse Mercator",
                        ID["EPSG",9807]],
                    PARAMETER["Latitude of natural origin",0,
                        ANGLEUNIT["degree",0.0174532925199433],
                        ID["EPSG",8801]],
                    PARAMETER["Longitude of natural origin",173,
                        ANGLEUNIT["degree",0.0174532925199433],
                        ID["EPSG",8802]],
                    PARAMETER["Scale factor at natural origin",0.9996,
                        SCALEUNIT["unity",1],
                        ID["EPSG",8805]],
                    PARAMETER["False easting",1600000,
                        LENGTHUNIT["metre",1],
                        ID["EPSG",8806]],
                    PARAMETER["False northing",10000000,
                        LENGTHUNIT["metre",1],
                        ID["EPSG",8807]]],
                CS[Cartesian,2],
                    AXIS["northing (N)",north,
                        ORDER[1],
                        LENGTHUNIT["metre",1]],
                    AXIS["easting (E)",east,
                        ORDER[2],
                        LENGTHUNIT["metre",1]],
                USAGE[
                    SCOPE["Engineering survey, topographic mapping."],
                    AREA["New Zealand - North Island, South Island, Stewart Island - onshore."],
                    BBOX[-47.33,166.37,-34.1,178.63]],
                ID["EPSG",2193]
        ```
        """
        self._srs = srs

    def set_path_standardised(self, path: str) -> None:
        """Set the standardised file path.

        Args:
            path: the path to the standardised file
        """
        self._path_standardised = path

    def get_gdalinfo(self, path: str | None = None) -> GdalInfo | None:
        """Get the `gdalinfo` output for the file.
        Run gdalinfo if not already ran or if different path is specified.
        `path` is useful to specify a local file to avoid downloading from external source.

        Args:
            path: path to the file. Force the `gdalinfo` to be executed.

        Returns:
            the `gdalinfo` output
        """
        # FIXME: Should not return None but not try running `gdalinfo` if there has already been an error
        if self.is_error_type(FileTiffErrorType.GDAL_INFO):
            return None
        if path:
            file_path = path
        else:
            file_path = self._path_standardised
        if path or not self._gdalinfo:
            try:
                self._gdalinfo = gdal_info(file_path)
            except json.JSONDecodeError as jde:
                self.add_error(error_type=FileTiffErrorType.GDAL_INFO, error_message=f"parsing result issue: {str(jde)}")
            except GDALExecutionException as gee:
                self.add_error(error_type=FileTiffErrorType.GDAL_INFO, error_message=f"failed: {str(gee)}")
            except Exception as e:  # pylint: disable=broad-except
                self.add_error(error_type=FileTiffErrorType.GDAL_INFO, error_message=f"error(s): {str(e)}")
        return self._gdalinfo

    def get_errors(self) -> list[dict[str, Any]]:
        """Get the Non Visual QA errors.

        Returns:
            a list of errors
        """
        return self._errors

    def get_paths_original(self) -> list[str]:
        """Get the path(s) of the original (non standardised) file.
        It can be a list of path if the standardised file is a retiled image.

        Returns:
            a list of file path
        """
        return self._paths_original

    def get_derived_from_paths(self) -> list[str] | None:
        """Get the path(s) of the STAC Items associated to the TIFF files from which the final output is derived.

        Returns:
            a list of STAC Item JSON file paths or None if not derived from other files.
        """
        return self._derived_from_paths

    def get_path_standardised(self) -> str:
        """Get the path of the standardised file.

        Returns:
            a file path
        """
        return self._path_standardised

    def get_tiff_type(self) -> FileTiffType:
        """Get the TIFF type.

        Returns:
            an element of `FileTiffType`
        """
        return self._tiff_type

    def add_error(
        self, error_type: FileTiffErrorType, error_message: str, custom_fields: dict[str, str] | None = None
    ) -> None:
        """Add an error in Non Visual QA errors list.

        Args:
            error_type: the type of the error
            error_message: the message of the error
            custom_fields: some custom properties. Defaults to None.
        """
        if not custom_fields:
            custom_fields = {}
        self._errors.append({"type": error_type, "message": error_message, **custom_fields})

    def is_valid(self) -> bool:
        """Check if the file is set to valid or not.

        Returns:
            true if _errors is empty
        """
        if len(self._errors) == 0:
            return True
        return False

    def is_error_type(self, error_type: FileTiffErrorType) -> bool:
        """Check if the file has a Non Visual QA error of the type `error_type`.

        Args:
            error_type: one of the value of `FileTiffErrorType`

        Returns:
            True if the the `error_type` is found
        """
        for error in self._errors:
            if error["type"] == error_type:
                return True
        return False

    def check_no_data(self, gdalinfo: GdalInfo) -> None:
        """Add a Non Visual QA error if there is no "noDataValue" and no alpha band for non-DEMs,
        or the "noDataValue" is not equal to 255, or -9999 for DEM in the "bands".

        Args:
            gdalinfo: `gdalinfo` output
        """
        bands = gdalinfo["bands"]
        if self._tiff_type != "DEM" and len(bands) in (4, 5) and bands[-1]["colorInterpretation"] == "Alpha":
            return
        if "noDataValue" in bands[0]:
            current_nodata_val = bands[0]["noDataValue"]
            # Convert `gdalinfo -json` no data value string to decimal for numeric comparison
            if self._tiff_type == "DEM" and current_nodata_val and Decimal(current_nodata_val) != DEFAULT_NO_DATA_VALUE:
                self.add_error(
                    error_type=FileTiffErrorType.NO_DATA,
                    error_message=f"noDataValue is not {DEFAULT_NO_DATA_VALUE}",
                    custom_fields={"current": f"{current_nodata_val}"},
                )
            elif self._tiff_type == "Imagery" and current_nodata_val != 255:
                self.add_error(
                    error_type=FileTiffErrorType.NO_DATA,
                    error_message="noDataValue is not 255",
                    custom_fields={"current": f"{current_nodata_val}"},
                )

    def is_no_data(self, gdalinfo: GdalInfo) -> bool:
        """Check if the bands have a "noDataValue" set.

        Args:
            gdalinfo: `gdalinfo` output

        Returns:
            True if a `noDataValue` is found
        """
        bands = gdalinfo["bands"]
        # 0 in noDataValue can return false unless specific here about None
        if "noDataValue" in bands[0] and bands[0]["noDataValue"] is not None:
            return True
        return False

    def check_band_count(self, gdalinfo: GdalInfo) -> None:
        """Add a Non Visual QA error if there is not exactly 3, 4 or 5 bands found, or 1 band if DEM.

        Args:
            gdalinfo: `gdalinfo` output
        """
        bands_num = 3
        bands = gdalinfo["bands"]
        if len(bands) == bands_num + 1:
            if bands[bands_num]["colorInterpretation"] == "Alpha":
                bands_num += 1
        if len(bands) == bands_num + 2:
            if bands[bands_num]["colorInterpretation"] == "NIR" and bands[bands_num + 1]["colorInterpretation"] == "Alpha":
                bands_num += 2
        if self._tiff_type == "DEM":
            bands_num = 1
        if len(bands) != bands_num:
            self.add_error(
                error_type=FileTiffErrorType.BANDS,
                error_message=f"bands count is not {bands_num}",
                custom_fields={"count": f"{int(bands_num)}"},
            )

    def check_srs(self, gdalsrsinfo_tif: bytes) -> None:
        """Add a Non Visual QA error if gdalsrsinfo and gdalsrsinfo_tif values are different.

        Args:
            gdalsrsinfo_tif : value returned by gdalsrsinfo for the tif as a string
        """
        if self._srs:
            if gdalsrsinfo_tif != self._srs:
                self.add_error(error_type=FileTiffErrorType.SRS, error_message="different srs")
        else:
            self.add_error(error_type=FileTiffErrorType.SRS, error_message="srs not defined")

    def check_color_interpretation(self, gdalinfo: GdalInfo) -> None:
        """Add a Non Visual QA error if the colors don't match RGB(A), RGBNA, or greyscale.

        Args:
            gdalinfo: `gdalinfo` output
        """
        bands = gdalinfo["bands"]
        missing_bands = []
        band_colour_ints = {1: "Red", 2: "Green", 3: "Blue"}
        band_greyscale_ints = {1: "Gray", 2: "Gray", 3: "Gray"}
        band_rgbn_ints = {1: "Red", 2: "Green", 3: "Blue", 4: "NIR", 5: "Alpha"}
        optional_colour_ints = {4: "Alpha"}
        if self._tiff_type == "DEM":
            band_colour_ints = {1: "Gray"}
        if len(bands) == 5 and bands[3]["colorInterpretation"] == "NIR":
            n = 1
            for band in bands:
                colour_int = band["colorInterpretation"]
                if colour_int != band_rgbn_ints[n]:
                    missing_bands.append(f"band {n} {colour_int}")
                n += 1
        else:
            n = 1
            for band in bands:
                colour_int = band["colorInterpretation"]
                if n in band_colour_ints:
                    if colour_int not in (band_colour_ints[n], band_greyscale_ints[n]):
                        missing_bands.append(f"band {n} {colour_int}")
                elif n in optional_colour_ints:
                    if colour_int != optional_colour_ints[n]:
                        missing_bands.append(f"band {n} {colour_int}")
                else:
                    missing_bands.append(f"band {n} {colour_int}")
                n += 1
        if missing_bands:
            missing_bands.sort()
            self.add_error(
                error_type=FileTiffErrorType.COLOR,
                error_message="unexpected color interpretation bands",
                custom_fields={"missing": f"{', '.join(missing_bands)}"},
            )

    def validate(self) -> bool:
        """Run the Non Visual QA checks.

        Returns:
            True if there is no error
        """

        gdalinfo = self.get_gdalinfo()
        if gdalinfo:
            self.check_no_data(gdalinfo)
            self.check_band_count(gdalinfo)
            self.check_color_interpretation(gdalinfo)

            gdalsrsinfo_tif_command = ["gdalsrsinfo", "-o", "wkt"]
            try:
                gdalsrsinfo_tif_result = run_gdal(gdalsrsinfo_tif_command, self._path_standardised)
                self.check_srs(gdalsrsinfo_tif_result.stdout)
            except GDALExecutionException as gee:
                self.add_error(error_type=FileTiffErrorType.SRS, error_message=f"not checked: {str(gee)}")
        return self.is_valid()
