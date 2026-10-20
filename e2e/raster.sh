#!/usr/bin/env bash
# End to end tests for the raster entry points.
#
# Usage: e2e/raster.sh <image> [output-directory]
#
# Runs each entry point against the fixtures in e2e/data and compares against expected files in e2e/data/output.
# Cases run concurrently.
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
  # `directory` is what run() mounts and the case compares against
  local directory
  directory=$(case_directory "${name}")
  mkdir -p "${directory}"
  "${function}" >"${directory}.log" 2>&1 &
  names+=("${name}")
  pids+=("$!")
}
# The entry points are given paths like ./tests/data/aerial.json, relative to the image's
# WORKDIR of /app, so the fixtures are mounted there rather than taken from the image.
run() {
  docker run --rm \
    --volume "${repository_root}/e2e/data:/app/tests/data:ro" \
    --volume "${directory}:/tmp/" \
    "${image}" "$@"
}

expected() {
  echo "${repository_root}/e2e/data/output/$1"
}

aerial_imagery() {
  run standardise-validate --from-file ./tests/data/aerial.json --preset webp --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BG35_1000_4829.tiff" "$(expected BG35_1000_4829.tiff)"
}

elevation() {
  run standardise-validate --from-file ./tests/data/dem.json --preset dem_lerc --data-type float32 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 30 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BK39_10000_0102.tiff" "$(expected BK39_10000_0102.tiff)"
  cmp --silent "${directory}/BK39_10000_0101.tiff" "$(expected BK39_10000_0101.tiff)"
}

hillshade_default() {
  run generate-hillshade --from-file ./tests/data/hillshade.json --preset hillshade --target /tmp/ --force
  cmp --silent "${directory}/BK39_10000_0101.tiff" "$(expected BK39_10000_0101_default.tiff)"
}

hillshade_igor() {
  run generate-hillshade --from-file ./tests/data/hillshade.json --preset hillshade-igor --target /tmp/ --force
  cmp --silent "${directory}/BK39_10000_0101.tiff" "$(expected BK39_10000_0101_igor.tiff)"
}

historical_aerial_imagery() {
  run standardise-validate --from-file ./tests/data/hi.json --preset webp --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 60 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BQ31_5000_0608.tiff" "$(expected BQ31_5000_0608.tiff)"
}

dem_zstd() {
  run standardise-validate --from-file ./tests/data/dem_zstd.json --preset dem_zstd --data-type float32 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z --force
  cmp --silent "${directory}/BK39_10000_0101.tiff" "$(expected BK39_10000_0101_zstd.tiff)"
}

near_infrared_aerial_imagery() {
  run standardise-validate --from-file ./tests/data/nir.json --preset rgbnir_zstd --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BR33_500_040034.tiff" "$(expected BR33_500_040034.tiff)"
}

compute_scale() {
  run compute-scale --from-file ./tests/data/aerial_uint16.json --target /tmp/
  [[ "$(cat "${directory}/scale-range")" == "1240,4648" ]]
}

aerial_imagery_uint16() {
  run standardise-validate --from-file ./tests/data/aerial_uint16.json --preset webp --data-type uint16 --scale-range 1240,4648 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BG35_1000_4829.tiff" "$(expected BG35_1000_4829_uint16.tiff)"
}

aerial_imagery_uint16_gamma() {
  run standardise-validate --from-file ./tests/data/aerial_uint16.json --preset webp --data-type uint16 --scale-range 1240,4648 --scale-gamma 1.3 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/BG35_1000_4829.tiff" "$(expected BG35_1000_4829_uint16_gamma.tiff)"
}

cutline_aerial_imagery() {
  run standardise-validate --from-file ./tests/data/aerial.json --preset webp --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/cutline/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --cutline ./tests/data/cutline_aerial.fgb --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/cutline/BG35_1000_4829.tiff" "$(expected BG35_1000_4829_cut.tiff)"
}

footprint() {
  run standardise-validate --from-file ./tests/data/aerial.json --preset webp --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  jq 'select(.xy_coordinate_resolution == 1E-8) // error("Wrong or missing X/Y coordinate resolution")' "${directory}/BG35_1000_4829_footprint.geojson"
  cmp --silent \
    <(jq "del(.features[0].properties.location, .xy_coordinate_resolution)" "${directory}/BG35_1000_4829_footprint.geojson") \
    <(jq "del(.features[0].properties.location, .xy_coordinate_resolution)" "$(expected BG35_1000_4829_footprint.geojson)")
}

footprint_simplification() {
  run standardise-validate --from-file ./tests/data/footprint.json --preset dem_lerc --data-type float32 --target-epsg 2193 --source-epsg 2193 --target /tmp/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z --simplify-footprints=true
  cmp --silent \
    <(jq -S '.features[].geometry' "$(expected AX31_10000_0502_footprint_simplified.geojson)") \
    <(jq -S '.features[].geometry' "${directory}/AX31_10000_0502_footprint.geojson")
}

thumbnails_topo50_topo250() {
  run thumbnails --from-file ./tests/data/thumbnails.json --target /tmp/
  cmp --silent "${directory}/CB07_GeoTifv1-02-thumbnail.jpg" "$(expected CB07_GeoTifv1-02-thumbnail.jpg)"
  cmp --silent "${directory}/CB07_TIFFv1-02-thumbnail.jpg" "$(expected CB07_TIFFv1-02-thumbnail.jpg)"
}

restandardise_aerial_imagery() {
  run standardise-validate --from-file ./tests/data/restandardise.json --preset webp --data-type uint8 --target-epsg 2193 --source-epsg 2193 --target /tmp/restandardise/ --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --gsd 10 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  cmp --silent "${directory}/restandardise/BG35_1000_4829.tiff" "$(expected BG35_1000_4829.tiff)"
}

translate_ascii_files_elevation() {
  run translate-ascii --from-file ./tests/data/elevation_ascii.json --target /tmp/
  cmp --silent "${directory}/elevation_ascii.tiff" "$(expected elevation_ascii.tiff)"
}

remove_empty_files() {
  run standardise-validate --from-file=./tests/data/empty.json --preset=webp --data-type=uint8 --target-epsg=2193 --source-epsg=2193 --target=/tmp --collection-id=123 --start-datetime=2023-01-01 --end-datetime=2023-01-01 --gsd 60 --create-footprints=true --current-datetime=2010-09-18T12:34:56Z
  [[ -n "$(find "${directory}" -maxdepth 0 -type d -empty)" ]]
}

start "Aerial Imagery" aerial_imagery
start "Elevation" elevation
start "Hillshade Default" hillshade_default
start "Hillshade Igor" hillshade_igor
start "Historical Aerial Imagery" historical_aerial_imagery
start "DEM ZSTD" dem_zstd
start "Near Infrared Aerial Imagery" near_infrared_aerial_imagery
start "Compute Scale" compute_scale
start "Aerial Imagery (uint16)" aerial_imagery_uint16
start "Aerial Imagery (uint16, gamma)" aerial_imagery_uint16_gamma
start "Cutline (Aerial Imagery)" cutline_aerial_imagery
start "Footprint" footprint
start "Footprint simplification" footprint_simplification
start "Thumbnails (Topo50/Topo250)" thumbnails_topo50_topo250
start "Restandardise Aerial Imagery" restandardise_aerial_imagery
start "Translate Ascii Files (Elevation)" translate_ascii_files_elevation
start "Remove empty files" remove_empty_files

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
