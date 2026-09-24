import argparse
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple

import shapely.geometry
from geoprocessor_common.datetimes import parse_rfc_3339_date
from geoprocessor_common.files.fs import read
from linz_logger import get_log


class InputParameterError(Exception):
    pass


class TileFiles(NamedTuple):
    output: str
    """ The tile name of the output file that will be created """

    inputs: list[str]
    """ The list of input files to be used to create the output file """

    includeDerived: bool = False
    """ Whether the STAC Item should include the derived_from links """


def get_tile_files(source: str) -> list[TileFiles]:
    """Transform a JSON string representing a list of input file paths and output tile name created
    by `argo-tasks` (see examples) to a list of `TileFiles`

    Args:
        source: JSON string containing representing a list of input file paths and output tile name

    Raises:
        InputParameterError: for any parsing error

    Returns:
        a list of `TileFiles` namedtuple

    Example:
        >>> get_tile_files('[{"output": "CE16_5000_1001", "input": ["s3://bucket/SN9457_CE16_10k_0501.tif"]}]')
        [TileFiles(output='CE16_5000_1001', inputs=['s3://bucket/SN9457_CE16_10k_0501.tif'], includeDerived=False)]
    """
    try:
        source_json: list[TileFiles] = json.loads(
            source,
            object_hook=lambda d: TileFiles(
                inputs=d["input"], output=d["output"], includeDerived=d.get("includeDerived", False)
            ),
        )
    except (json.decoder.JSONDecodeError, KeyError) as e:
        get_log().error(type(e).__name__, error=str(e))
        raise InputParameterError("An error occurred while parsing the input file") from e

    return source_json


def load_input_files(path: str) -> list[TileFiles]:
    """Load the TileFiles from a JSON input file containing a list of output and input files.
    Args:
        path: path to a JSON file listing output name and input files

    Returns:
        a list of `TileFiles` namedtuple
    """
    source = json.dumps(json.loads(read(path)))

    try:
        tile_files: list[TileFiles] = get_tile_files(source)
        return tile_files
    except InputParameterError as e:
        get_log().error("An error occurred while getting tile_files", error=str(e))
        raise e


def valid_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return parse_rfc_3339_date(s)
    except ValueError as e:
        msg = f"not a valid date: {s}"
        raise argparse.ArgumentTypeError(msg) from e


def parse_list(list_s: str, separator: str | None = ";") -> list[str]:
    """Transform a string representing a list to a list of strings
    example: "foo; bar; foo bar" -> ["foo", "bar", "foo bar"]

    Args:
        list_s: string representing a list to transform
        separator: separator of the list

    Returns:
        a list of strings
    """
    if list_s:
        return [s.strip() for s in list_s.split(separator) if s != ""]
    return []


def coalesce_multi_single(multi_items: str | None, single_item: str | None) -> list[str]:
    """Coalesce strings containing either semicolon delimited values or a single
    value into a list. `single_item` is used only if `multi_items` is falsy.
    If both are falsy, an empty list is returned.

    Args:
        multi_items: string with semicolon delimited values
        single_item: string with a single value

    Returns:
        a list of values
    """
    output = []
    if multi_items:
        output.extend(parse_list(multi_items))
    elif single_item:
        output.append(single_item)
    return output


def str_to_gsd(value: str) -> Decimal:
    return Decimal(value)


def str_to_bool(value: str) -> bool:
    """Transform a string to a boolean value

    Example:
        >>> str_to_bool("true")
        True

    Args:
        str: string representing a boolean value

    Raises:
        ArgumentTypeError: if the string is not "true" or "false"

    Returns:
        bool: True if "true", False if "false"
    """
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean (must be exactly 'true' or 'false'): {value}")


def empty_str_to_false(value: str) -> str | bool:
    """Transform an empty string to False. Returns value if not empty.

    Example:
        >>> empty_str_to_false("")
        False
        >>> empty_str_to_false("foo")
        'foo'

    Args:
        str: string representing a capture area or an empty string

    Returns:
        str | bool: False if value is an empty string else returns value
    """
    return value or False


def str_to_list_or_none(values: str) -> list[Decimal] | None:
    """Transform a string to an empty list of list with 2 values. Return None if the string is empty.

    Example:
        >>> str_to_list_or_none('2,4')
        [Decimal('2'), Decimal('4')]
        >>> str_to_list_or_none('') is None
        True

    Args:
        str: string representing a list or an empty string

    Raises:
        ArgumentTypeError: if the string is not empty and does not contain exactly 2 values

    Returns:
        None or a list of 2 values
    """
    if not values:
        return None
    result = [Decimal(value) for value in values.split(",")]
    if len(result) != 2:
        raise argparse.ArgumentTypeError(f"Invalid list - must be blank or exactly 2 values x,y. Received: {values}")
    return result


def str_to_positive_int(value: str) -> int:
    """Transform a string to a positive integer

    Example:
        >>> str_to_positive_int("5")
        5

    Args:
        value: string representing a positive integer

    Raises:
        ArgumentTypeError: if the string is not a positive integer

    Returns:
        int: the positive integer value
    """
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def str_to_positive_int_or_none(value: str) -> int | None:
    """Transform a string to a positive integer. Return None if the string is empty.

    Argo passes unset workflow parameters as an empty string, so an optional integer
    argument has to accept one.

    Example:
        >>> str_to_positive_int_or_none("5")
        5
        >>> str_to_positive_int_or_none('') is None
        True

    Args:
        value: string representing a positive integer, or an empty string

    Raises:
        ArgumentTypeError: if the string is not empty and not a positive integer

    Returns:
        the positive integer value, or None if the string is empty
    """
    if not value:
        return None
    return str_to_positive_int(value)


def get_geometry_from_geojson_feature(feature: Any, file_path: str) -> shapely.geometry.base.BaseGeometry:
    """Extracts a geometry from a GeoJSON feature and logs errors if the geometry is invalid.

    :param feature: A feature from the GeoJSON file.
    :param file_path: Path to the GeoJSON file for logging.
    :return: A Shapely BaseGeometry object if successful, otherwise raises an exception.
    """
    get_log().debug(f"importing geometry from {file_path}")
    try:
        return shapely.geometry.shape(feature["geometry"])
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        error_message = f"The supplied GeoJSON feature does not contain a valid geometry: {file_path}"
        get_log().error(error_message, error=str(e))
        raise ValueError(error_message) from e


def get_non_empty_features(content: dict[str, Any], file_path: str) -> list[Any]:
    """Return a non-empty feature list from a supplied GeoJSON file.

    :param content: The content of the GeoJSON.
    :param file_path: The path to the GeoJSON file for logging purposes.
    :return: A list of features, otherwise raises an exception.
    """
    if content.get("type") == "Feature":
        return [content]

    features = content.get("features")
    if not isinstance(features, list) or len(features) == 0:
        error_message = f"Supplied GeoJSON has no features: {file_path}"
        get_log().error(error_message)
        raise ValueError(error_message)
    return features
