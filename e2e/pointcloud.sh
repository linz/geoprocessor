#!/usr/bin/env bash
# End to end tests for the pointcloud entry points.
#
# Usage: e2e/pointcloud.sh <image> [output-directory]
#
# Runs each entry point against the fixtures in e2e/data and checks the files it writes. Cases run concurrently, each
# in its own directory of the output directory. Needs jq.
set -o errexit -o nounset -o pipefail

image=${1:?usage: $0 <image> [output-directory]}
output=${2:-$(mktemp --directory)}
repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "testing ${image}, writing to ${output}"

names=()
pids=()

case_directory() {
  echo "${output}/${1//[^A-Za-z0-9]/_}"
}

start() {
  local name=$1 function=$2
  # `directory` is what run() mounts and the case checks
  local directory
  directory=$(case_directory "${name}")
  mkdir -p "${directory}"
  "${function}" >"${directory}.log" 2>&1 &
  names+=("${name}")
  pids+=("$!")
}

# The entry points are given paths like ./tests/data/pdal_bad_header_1.laz, relative to the image's
# WORKDIR of /app, so the fixtures are mounted there rather than taken from the image.
# Files a case writes to /tmp/ are in its directory.
run() {
  docker run --rm \
    --volume "${repository_root}/e2e/data:/app/tests/data:ro" \
    --volume "${directory}:/tmp/" \
    "${image}" "$@"
}

fixture() {
  echo "${repository_root}/e2e/data/$1"
}

# The header and CRS of a point cloud file, as JSON
metadata() {
  run pdal info "$1" --metadata
}

# Fails unless the jq filter (the last argument, after any jq options) is true for the JSON on standard input
check() {
  jq --exit-status "$@" >/dev/null
}

fix_laz_headers() {
  run fix-laz-header --files ./tests/data/pdal_bad_header_1.laz ./tests/data/pdal_good_header_1.laz --target /tmp/
  # A good header is kept as it is, a bad one is rewritten. `cmp` exits 1 when the files differ, and 2 when one is
  # missing, which must fail the case too.
  cmp --silent "${directory}/pdal_good_header_1.laz" "$(fixture pdal_good_header_1.laz)"
  local status=0
  cmp --silent "${directory}/pdal_bad_header_1.laz" "$(fixture pdal_bad_header_1.laz)" || status=$?
  ((status == 1))
}

standardise_copc() {
  # A source whose header differs from the writer's defaults, to check which values are kept and which are replaced
  run pdal translate ./tests/data/pdal_good_header_1.laz /tmp/custom_header.laz --writers.las.forward=all \
    --writers.las.global_encoding=1 --writers.las.filesource_id=42 --writers.las.creation_year=2024 \
    --writers.las.system_id=CUSTOM --writers.las.project_id=01234567-89ab-cdef-0123-456789abcdef \
    --writers.las.scale_x=0.001 --writers.las.scale_y=0.001 --writers.las.scale_z=0.001 \
    --writers.las.offset_x=1700000 --writers.las.offset_y=5600000 --writers.las.offset_z=0
  check '.metadata | .global_encoding == 1 and .filesource_id == 42 and .creation_year == 2024 and .system_id == "CUSTOM"' \
    <<<"$(metadata /tmp/custom_header.laz)"

  # The day the run starts, as year and day of year (1 for 1 January), to check the COPC file's creation date
  local start_year start_doy
  read -r start_year start_doy < <(date --utc '+%Y %-j')
  run standardise-copc --from-file ./tests/data/copc.json --target /tmp/

  # A COPC file per tile, with every point of the tile's source files
  check '. == ["/tmp/pdal_bad_header_1.copc.laz", "/tmp/pdal_good_header_1.copc.laz", "/tmp/custom_header.copc.laz", "/tmp/merged.copc.laz"]' \
    <"${directory}/processed.json"
  local good bad custom merged
  good=$(metadata /tmp/pdal_good_header_1.copc.laz)
  bad=$(metadata /tmp/pdal_bad_header_1.copc.laz)
  custom=$(metadata /tmp/custom_header.copc.laz)
  merged=$(metadata /tmp/merged.copc.laz)
  check '.metadata | .copc and .count == 10' <<<"${good}"
  check '.metadata | .copc and .count == 367' <<<"${bad}"
  check '.metadata | .copc and .count == 377' <<<"${merged}"

  # The bad header's malformed CRS is replaced, so both get NZTM2000 + NZVD2016. Not compared with the good source's
  # CRS, which PDAL reads as the registered compound EPSG:11460: the same CRS, but its WKT has another top-level code.
  [[ "$(jq --raw-output .metadata.srs.compoundwkt <<<"${bad}")" == "$(jq --raw-output .metadata.srs.compoundwkt <<<"${good}")" ]]
  check '.metadata.srs.compoundwkt | contains("AUTHORITY[\"EPSG\",\"2193\"]") and contains("AUTHORITY[\"EPSG\",\"7839\"]")' \
    <<<"${good}"

  # Kept: the GPS time type (PDAL also sets the WKT bit, 16), scale and offsets
  check '.metadata | .global_encoding == 17 and .scale_x == 0.001 and .scale_y == 0.001 and .scale_z == 0.001
    and .offset_x == 1700000 and .offset_y == 5600000 and .offset_z == 0' <<<"${custom}"
  # Replaced, to describe the COPC file. The source's creation date is 2024, day 0.
  [[ "$(run pdal --version)" =~ pdal\ ([0-9.]+) ]]
  check --arg version "${BASH_REMATCH[1]}" --argjson start_year "${start_year}" --argjson start_doy "${start_doy}" '.metadata |
    .filesource_id == 0 and .system_id == "TRANSFORMATION" and .project_id == "00000000-0000-0000-0000-000000000000"
    and [.creation_year, .creation_doy] >= [$start_year, $start_doy] and (.software_id | startswith("PDAL \($version) "))' \
    <<<"${custom}"
}

standardise_copc_empty_tile() {
  run pdal translate ./tests/data/pdal_good_header_1.laz /tmp/empty.laz --filter filters.range \
    --filters.range.limits='Z[100000:100001]' --writers.las.forward=all
  check '.metadata.count == 0' <<<"$(metadata /tmp/empty.laz)"

  # `writers.copc` writes no file for a tile without points, which must fail the command
  local log status=0
  log=$(run standardise-copc --from-file ./tests/data/copc_empty.json --target /tmp/ 2>&1) || status=$?
  echo "${log}"
  ((status != 0))
  grep --quiet --fixed-strings "PDAL wrote no COPC file for empty, its source files may have no points: /tmp/empty.laz" <<<"${log}"
  [[ ! -e "${directory}/empty.copc.laz" ]]
}

standardise_copc_refuses_to_overwrite_a_source() {
  run standardise-copc --from-file ./tests/data/copc_good_header.json --target /tmp/
  local checksum
  checksum=$(sha256sum "${directory}/pdal_good_header_1.copc.laz")

  # That COPC file as the source of a tile with the same name, even with --force
  local log status=0
  log=$(run standardise-copc --force --from-file ./tests/data/copc_overwrite.json --target /tmp/ 2>&1) || status=$?
  echo "${log}"
  ((status != 0))
  grep --quiet --fixed-strings "would overwrite a source file" <<<"${log}"
  [[ "$(sha256sum "${directory}/pdal_good_header_1.copc.laz")" == "${checksum}" ]]
}

standardise_copc_source_crs() {
  run standardise-copc --from-file ./tests/data/copc_good_header.json --source-crs EPSG:2193+4440 --target /tmp/
  check '.metadata.srs.compoundwkt | contains("AUTHORITY[\"EPSG\",\"2193\"]") and contains("AUTHORITY[\"EPSG\",\"4440\"]")' \
    <<<"$(metadata /tmp/pdal_good_header_1.copc.laz)"
}

start "Fix LAZ headers" fix_laz_headers
start "Standardise COPC" standardise_copc
start "Standardise COPC (empty tile)" standardise_copc_empty_tile
start "Standardise COPC (refuse to overwrite a source)" standardise_copc_refuses_to_overwrite_a_source
start "Standardise COPC (source CRS)" standardise_copc_source_crs

failures=()
for index in "${!pids[@]}"; do
  name=${names[${index}]}
  # `wait` is needed to read the exit code of a backgrounded task
  if wait "${pids[${index}]}"; then
    echo "::group::PASS ${name}"
  else
    echo "::group::FAIL ${name}"
    failures+=("${name}")
  fi
  cat "$(case_directory "${name}").log"
  echo "::endgroup::"
done

if ((${#failures[@]})); then
  echo "::error::failed: ${failures[*]}"
  exit 1
fi
echo "all ${#names[@]} cases passed"
