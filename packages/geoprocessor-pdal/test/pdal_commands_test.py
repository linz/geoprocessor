from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from geoprocessor_pdal.pdal_commands import PDALExecutionException, get_pdal_command, get_pdal_version


def test_check_pdal_command() -> None:
    """
    tests that the pdal command is built correctly
    """
    pdal_command = get_pdal_command("info", ["--option1", "value1", "--option2", "value2"])
    assert pdal_command == ["info", "--option1", "value1", "--option2", "value2"]


def test_check_pdal_command_invalid() -> None:
    """
    tests that the pdal command raises an error when an invalid command is provided
    """
    try:
        get_pdal_command("invalid_command", ["--option1", "value1"])
    except ValueError as e:
        assert str(e) == "Unsupported PDAL command: invalid_command"
    else:
        assert False, "ValueError was not raised for an invalid PDAL command"


def test_get_pdal_version_strips_the_surrounding_rules() -> None:
    """
    tests that the dashes are dropped from `pdal --version`
    """
    rule = "-" * 80
    output = f"{rule}\npdal 2.10.2 (git-version: 27008f)\n{rule}\n"
    get_pdal_version.cache_clear()
    with patch("geoprocessor_pdal.pdal_commands.subprocess.run", return_value=CompletedProcess([], 0, output.encode(), b"")):
        assert get_pdal_version() == "pdal 2.10.2 (git-version: 27008f)"


def test_get_pdal_version_keeps_every_line_that_is_not_a_rule() -> None:
    """
    tests that additional lines / changed layouts will be preserved as a single line rather than dropped
    """
    rule = "-" * 80
    output = f"{rule}\npdal 2.11.0\nbuilt with GDAL 3.10.3\n{rule}\n"
    get_pdal_version.cache_clear()
    with patch("geoprocessor_pdal.pdal_commands.subprocess.run", return_value=CompletedProcess([], 0, output.encode(), b"")):
        assert get_pdal_version() == "pdal 2.11.0 built with GDAL 3.10.3"


def test_get_pdal_version_rejects_a_successful_run_that_reports_nothing() -> None:
    """
    tests that an empty version is an error rather than an empty string in logs and STAC metadata
    """
    get_pdal_version.cache_clear()
    with patch("geoprocessor_pdal.pdal_commands.subprocess.run", return_value=CompletedProcess([], 0, b"-" * 80, b"")):
        with pytest.raises(PDALExecutionException, match="reported no version"):
            get_pdal_version()


def test_get_pdal_version_reports_a_missing_executable() -> None:
    """
    tests that a missing `pdal` binary raises
    """
    get_pdal_version.cache_clear()
    with patch("geoprocessor_pdal.pdal_commands.subprocess.run", side_effect=FileNotFoundError("pdal")):
        with pytest.raises(PDALExecutionException, match="Could not determine the PDAL version"):
            get_pdal_version()
