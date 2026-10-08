import json
from pathlib import Path
from unittest.mock import patch

from geoprocessor_pdal.pdal_commands import pdal_translate_copc_command
from geoprocessor_pointcloud.standardise_copc import (
    flatten,
    get_copc_file_name,
    json_file_loader,
    manifest_loader,
    non_empty_str,
    pdal_standardise_copc,
)


def fake_run_pdal(command: list[str], input_file: str, output_file: str) -> None:  # pylint: disable=unused-argument
    Path(output_file).write_bytes(b"copc")


def test_flatten_returns_a_flat_list_unchanged() -> None:
    assert list(flatten(["a", "b"])) == ["a", "b"]


def test_flatten_flattens_nesting_at_any_depth() -> None:
    """`--from-file` accepts a nested list, which is what the workflows that generate it produce."""
    assert list(flatten([["a"], ["b", ["c", ["d"]]]])) == ["a", "b", "c", "d"]


def test_flatten_returns_nothing_for_an_empty_list() -> None:
    assert not list(flatten([]))


def test_non_empty_str_wraps_a_value_in_a_list() -> None:
    assert non_empty_str("a/file.laz") == ["a/file.laz"]


def test_non_empty_str_discards_blank_values() -> None:
    """Argo passes an empty string for an unset parameter, which must not become a file to process."""
    for blank in ["", " ", "\t\n"]:
        assert not non_empty_str(blank)


def test_json_file_loader_flattens_the_file_it_reads(tmp_path: Path) -> None:
    from_file = tmp_path / "files.json"
    from_file.write_text(json.dumps([["a.laz"], ["b.laz", "c.laz"]]))

    assert json_file_loader(str(from_file)) == ["a.laz", "b.laz", "c.laz"]


def test_json_file_loader_returns_nothing_for_a_missing_file(tmp_path: Path) -> None:
    """Regression: `read()` raises `NoSuchFileError`, not `FileNotFoundError`."""
    assert not json_file_loader(str(tmp_path / "absent.json"))


def test_json_file_loader_returns_nothing_for_an_empty_path() -> None:
    assert not json_file_loader("")


def test_manifest_loader_returns_the_sources(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"parameters": {"manifest": [{"source": "a.laz", "target": "x"}, {"source": "b.laz", "target": "y"}]}})
    )

    assert manifest_loader(str(manifest)) == ["a.laz", "b.laz"]


def test_manifest_loader_returns_nothing_for_a_manifest_without_entries(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"parameters": {}}))

    assert not manifest_loader(str(manifest))


def test_manifest_loader_returns_nothing_for_a_missing_file(tmp_path: Path) -> None:
    """Regression: `read()` raises `NoSuchFileError`, not `FileNotFoundError`."""
    assert not manifest_loader(str(tmp_path / "absent.json"))


def test_get_copc_file_name_replaces_the_extension() -> None:
    assert get_copc_file_name("s3://bucket/path/BQ31_1000_0101.laz") == "BQ31_1000_0101.copc.laz"
    assert get_copc_file_name("/local/path/BQ31_1000_0101.las") == "BQ31_1000_0101.copc.laz"


def test_get_copc_file_name_does_not_repeat_the_copc_extension() -> None:
    assert get_copc_file_name("s3://bucket/BQ31_1000_0101.copc.laz") == "BQ31_1000_0101.copc.laz"
    assert get_copc_file_name("s3://bucket/BQ31_1000_0101.COPC.LAZ") == "BQ31_1000_0101.copc.laz"


def test_pdal_standardise_copc_writes_a_copc_file_to_the_target(tmp_path: Path) -> None:
    source_file = tmp_path / "a.laz"
    source_file.write_bytes(b"laz")
    target = tmp_path / "target"
    target.mkdir()

    with patch("geoprocessor_pointcloud.standardise_copc.run_pdal", side_effect=fake_run_pdal) as run_pdal:
        result = pdal_standardise_copc(str(source_file), target=str(target))

    assert result == str(target / "a.copc.laz")
    assert (target / "a.copc.laz").read_bytes() == b"copc"
    run_pdal.assert_called_once()
    assert run_pdal.call_args.args == (pdal_translate_copc_command,)


def test_pdal_standardise_copc_skips_a_file_that_has_already_been_processed(tmp_path: Path) -> None:
    target_file = tmp_path / "a.copc.laz"
    target_file.write_bytes(b"already processed")

    with patch("geoprocessor_pointcloud.standardise_copc.run_pdal") as run_pdal:
        result = pdal_standardise_copc("s3://bucket/a.laz", target=str(tmp_path))

    assert result == str(target_file)
    assert target_file.read_bytes() == b"already processed"
    run_pdal.assert_not_called()


def test_pdal_standardise_copc_overwrites_an_existing_output_when_forced(tmp_path: Path) -> None:
    source_file = tmp_path / "a.laz"
    source_file.write_bytes(b"laz")
    target_file = tmp_path / "a.copc.laz"
    target_file.write_bytes(b"already processed")

    with patch("geoprocessor_pointcloud.standardise_copc.run_pdal", side_effect=fake_run_pdal):
        result = pdal_standardise_copc(str(source_file), target=str(tmp_path), force=True)

    assert result == str(target_file)
    assert target_file.read_bytes() == b"copc"
