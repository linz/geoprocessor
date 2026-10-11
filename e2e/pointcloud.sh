#!/usr/bin/env bash
# End to end tests for the pointcloud entry points.
#
# Usage: e2e/pointcloud.sh <image> [output-directory]
#
# Runs each entry point against the fixtures in e2e/data and compares against expected files in e2e/data/output.
# FIXME: implement concurrency when adding test cases.
set -o errexit -o nounset -o pipefail

image=${1:?usage: $0 <image> [output-directory]}
output=${2:-$(mktemp --directory)}
repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "testing ${image}, writing to ${output}"

# The entry points are given paths like ./tests/data/pdal_bad_header_1.laz, relative to the image's
# WORKDIR of /app, so the fixtures are mounted there rather than taken from the image.
run() {
  docker run --rm \
    --volume "${repository_root}/e2e/data:/app/tests/data:ro" \
    --volume "${output}:/tmp/" \
    "${image}" "$@"
}

fixture() {
  echo "${repository_root}/e2e/data/$1"
}

echo "::group::Fix LAZ headers with pdal translate"
run fix-laz-header --files ./tests/data/pdal_bad_header_1.laz ./tests/data/pdal_good_header_1.laz --target /tmp/
cmp --silent "${output}/pdal_good_header_1.laz" "$(fixture pdal_good_header_1.laz)" && echo "good header retained, as expected"
cmp --silent "${output}/pdal_bad_header_1.laz" "$(fixture pdal_bad_header_1.laz)" && exit 1 || echo "bad header fixed, as expected"
echo "::endgroup::"

echo "all pointcloud end to end tests passed"
