import re
from pathlib import Path
from unittest.mock import patch

import pytest
from geoprocessor_common.cli.cli_helper import TileFiles
from geoprocessor_pdal.pdal_commands import PDALExecutionException
from geoprocessor_pointcloud.standardise_copc import get_args_parser, pdal_standardise_copc


def test_get_args_parser_reads_the_concurrency() -> None:
    arguments = get_args_parser().parse_args(["--from-file", "files.json", "--concurrency", "3"])

    assert arguments.concurrency == 3


def test_get_args_parser_defaults_the_concurrency_to_1() -> None:
    arguments = get_args_parser().parse_args(["--from-file", "files.json"])

    assert arguments.concurrency == 1


@pytest.mark.parametrize("concurrency", ["0", "-1", "abc"])
def test_get_args_parser_rejects_a_concurrency_that_is_not_a_positive_integer(concurrency: str) -> None:
    with pytest.raises(SystemExit):
        get_args_parser().parse_args(["--from-file", "files.json", "--concurrency", concurrency])


def fake_pdal_merge_copc(input_files: list[str], output_file: str, crs: str | None = None) -> str:
    # pylint: disable=unused-argument
    Path(output_file).write_bytes(b"copc")
    return output_file


def test_pdal_standardise_copc_merges_the_tile_files_into_one_copc_file_named_after_the_tile(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "x").mkdir(parents=True)
    (source / "y").mkdir()
    (source / "x" / "a.laz").write_bytes(b"laz")
    (source / "y" / "a.laz").write_bytes(b"laz")
    target = tmp_path / "target"
    target.mkdir()
    tile = TileFiles(output="BY16_5000_0410", inputs=[str(source / "x" / "a.laz"), str(source / "y" / "a.laz")])

    with patch(
        "geoprocessor_pointcloud.standardise_copc.pdal_merge_copc", side_effect=fake_pdal_merge_copc
    ) as pdal_merge_copc:
        result = pdal_standardise_copc(tile, target=str(target))

    assert result == str(target / "BY16_5000_0410.copc.laz")
    assert (target / "BY16_5000_0410.copc.laz").read_bytes() == b"copc"
    pdal_merge_copc.assert_called_once()
    local_inputs = pdal_merge_copc.call_args.args[0]
    assert len(local_inputs) == 2
    assert len(set(local_inputs)) == 2, "inputs with the same file name must not overwrite each other"


def test_pdal_standardise_copc_assigns_the_given_source_crs(tmp_path: Path) -> None:
    source_file = tmp_path / "a.laz"
    source_file.write_bytes(b"laz")
    target = tmp_path / "target"
    target.mkdir()

    with patch(
        "geoprocessor_pointcloud.standardise_copc.pdal_merge_copc", side_effect=fake_pdal_merge_copc
    ) as pdal_merge_copc:
        pdal_standardise_copc(
            TileFiles(output="tile", inputs=[str(source_file)]), target=str(target), source_crs="EPSG:2193+4440"
        )

    assert pdal_merge_copc.call_args.args[2] == "EPSG:2193+4440"


def test_pdal_standardise_copc_skips_a_tile_that_has_already_been_processed(tmp_path: Path) -> None:
    target_file = tmp_path / "tile.copc.laz"
    target_file.write_bytes(b"already processed")

    with patch("geoprocessor_pointcloud.standardise_copc.pdal_merge_copc") as pdal_merge_copc:
        result = pdal_standardise_copc(TileFiles(output="tile", inputs=["s3://bucket/a.laz"]), target=str(tmp_path))

    assert result == str(target_file)
    assert target_file.read_bytes() == b"already processed"
    pdal_merge_copc.assert_not_called()


def test_pdal_standardise_copc_overwrites_an_existing_output_when_forced(tmp_path: Path) -> None:
    source_file = tmp_path / "a.laz"
    source_file.write_bytes(b"laz")
    target_file = tmp_path / "tile.copc.laz"
    target_file.write_bytes(b"already processed")

    with patch("geoprocessor_pointcloud.standardise_copc.pdal_merge_copc", side_effect=fake_pdal_merge_copc):
        result = pdal_standardise_copc(TileFiles(output="tile", inputs=[str(source_file)]), target=str(tmp_path), force=True)

    assert result == str(target_file)
    assert target_file.read_bytes() == b"copc"


@pytest.mark.parametrize("force", [False, True])
def test_pdal_standardise_copc_refuses_to_overwrite_a_source_file(tmp_path: Path, force: bool) -> None:
    """A COPC source named after the tile and processed into its own directory would be replaced by the output."""
    source_file = tmp_path / "tile.copc.laz"
    source_file.write_bytes(b"source")
    tile = TileFiles(output="tile", inputs=[str(tmp_path / "other.laz"), str(source_file)])

    with (
        patch("geoprocessor_pointcloud.standardise_copc.pdal_merge_copc") as pdal_merge_copc,
        pytest.raises(ValueError, match="would overwrite a source file"),
    ):
        pdal_standardise_copc(tile, target=f"{tmp_path}/./", force=force)

    assert source_file.read_bytes() == b"source"
    pdal_merge_copc.assert_not_called()


def test_pdal_standardise_copc_refuses_to_overwrite_a_source_file_on_s3() -> None:
    with (
        patch("geoprocessor_pointcloud.standardise_copc.pdal_merge_copc") as pdal_merge_copc,
        pytest.raises(ValueError, match="would overwrite a source file"),
    ):
        pdal_standardise_copc(
            TileFiles(output="tile", inputs=["s3://bucket/path/tile.copc.laz"]), target="s3://bucket/path", force=True
        )

    pdal_merge_copc.assert_not_called()


def test_pdal_standardise_copc_raises_when_pdal_writes_no_file(tmp_path: Path) -> None:
    """`writers.copc` writes nothing when the source files have no points and still exits 0."""
    source_file = tmp_path / "empty.laz"
    source_file.write_bytes(b"laz without points")
    target = tmp_path / "target"
    target.mkdir()

    with (
        patch("geoprocessor_pointcloud.standardise_copc.pdal_merge_copc"),
        pytest.raises(PDALExecutionException, match=re.escape(f"tile, its source files may have no points: {source_file}")),
    ):
        pdal_standardise_copc(TileFiles(output="tile", inputs=[str(source_file)]), target=str(target))

    assert not list(target.iterdir())
