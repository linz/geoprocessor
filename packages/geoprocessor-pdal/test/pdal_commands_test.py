import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import patch

import pytest
from geoprocessor_pdal.pdal_commands import (
    COPC_WRITER_OPTIONS,
    PDALExecutionException,
    get_merge_copc_pipeline,
    get_pdal_command,
    get_pdal_version,
    pdal_merge_copc,
    pdal_pipeline_command,
)


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


def test_get_merge_copc_pipeline_reads_every_input_then_writes_one_copc_file() -> None:
    pipeline = get_merge_copc_pipeline(["a.laz", "b.laz"], "merged.copc.laz")

    assert pipeline == [
        "a.laz",
        "b.laz",
        {"type": "writers.copc", "filename": "merged.copc.laz", **COPC_WRITER_OPTIONS},
    ]


def test_get_merge_copc_pipeline_rejects_no_input_files() -> None:
    with pytest.raises(ValueError, match="At least one input file"):
        get_merge_copc_pipeline([], "merged.copc.laz")


@pytest.mark.parametrize(
    "input_files, output_file",
    [(["a.laz", "s3://bucket/b.laz"], "merged.copc.laz"), (["a.laz"], "s3://bucket/merged.copc.laz")],
)
def test_get_merge_copc_pipeline_rejects_s3_paths(input_files: list[str], output_file: str) -> None:
    """
    tests that S3 paths, which PDAL would receive untouched, raise a clear error instead
    """
    with pytest.raises(ValueError, match="must be local.*s3://bucket/"):
        get_merge_copc_pipeline(input_files, output_file)


def test_pdal_merge_copc_runs_the_pipeline_as_json() -> None:
    """
    tests that the pipeline is written to a JSON file and passed to `pdal pipeline`
    """
    pipelines: list[Any] = []

    def read_pipeline(command: list[str], input_file: str) -> None:
        assert command == pdal_pipeline_command
        pipelines.append(json.loads(Path(input_file).read_text(encoding="utf-8")))

    with patch("geoprocessor_pdal.pdal_commands.run_pdal", side_effect=read_pipeline):
        result = pdal_merge_copc(["a.laz", "b.laz"], "merged.copc.laz")

    assert result == "merged.copc.laz"
    assert pipelines == [get_merge_copc_pipeline(["a.laz", "b.laz"], "merged.copc.laz")]
