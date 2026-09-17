# geoprocessor

[![GitHub Actions Status](https://github.com/linz/geoprocessor/workflows/format-tests.yml/badge.svg)](https://github.com/linz/geoprocessor/actions)
[![Containers](https://github.com/linz/geoprocessor/actions/workflows/containers.yml/badge.svg)](https://github.com/linz/geoprocessor/actions/workflows/containers.yml)
[![Coverage: 100% branches](https://img.shields.io/badge/Coverage-100%25%20branches-brightgreen.svg)](https://pytest.org/)
[![Dependabot Status](https://badgen.net/badge/Dependabot/enabled?labelColor=2e3a44&color=blue)](https://github.com/linz/geoprocessor/network/updates)
[![License](https://badgen.net/github/license/linz/geoprocessor?labelColor=2e3a44&label=License)](https://github.com/linz/geoprocessor/blob/master/LICENSE)
[![Conventional Commits](https://badgen.net/badge/Commits/conventional?labelColor=2e3a44&color=EC5772)](https://conventionalcommits.org)
[![Code Style](https://badgen.net/badge/Code%20Style/black?labelColor=2e3a44&color=000000)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=2e3a44)](https://pycqa.github.io/isort/)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code Style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)

## Description

This is a collection of Python scripts used for processing geospatial data in and for the cloud (AWS).

Two Docker containers are provided to run the Python scripts:

| Container                 | Built from              | Package                   | Contains                  |
| ------------------------- | ----------------------- | ------------------------- | ------------------------- |
| `geoprocessor/raster`     | `Dockerfile.raster`     | `geoprocessor-raster`     | [GDAL](https://gdal.org/) |
| `geoprocessor/pointcloud` | `Dockerfile.pointcloud` | `geoprocessor-pointcloud` | [PDAL](https://pdal.io/)  |

The containers are available [in GitHub Packages](https://github.com/orgs/linz/packages?repo_name=geoprocessor).

### Usage

The scripts have been implemented to be run inside the Docker container only. This is mainly because of the `GDAL` dependency.

#### Local

- Build the `Docker` image:

```bash
docker build --file Dockerfile.raster --tag=geoprocessor/raster .
```

```bash
docker build --file Dockerfile.pointcloud --tag=geoprocessor/pointcloud .
```

- Example: running the `standardise-validate` command

This script standardises TIFF files to [COGs](https://www.cogeo.org/) with a creation of a [STAC](https://stacspec.org/) Item file per TIFF containing the metadata.
The input TIFF file paths have to be passed through a `json` file in the following format:

```json
[
  {
    "output": "tile_name",
    "input": ["./path/to/file.tiff"]
  }
]
```

where `output` is the desired output [tile name](https://github.com/linz/geoprocessor/blob/6aa0fb565696cb99fb66ca92b8c678ef3523d11a/scripts/tile/tests/tile_index_data.py#L3-L514) and input is the path to one or several TIFFs. If more than one TIFF, the system will try to retile them into one single output file.

Some test data are available in `/e2e/data/` along with the expected output.

Run `docker run geoprocessor/raster standardise-validate --help` to get the list of the expected arguments.

- Example of local execution. This example uses the test data available on this repo and create the output will be created in a `~/tmp/` on the local machine (volume share with `Docker`):

```bash
docker run -v ${HOME}/tmp/:/tmp/:rw geoprocessor/raster standardise-validate --preset webp --data-type uint8 --from-file ./tests/data/aerial.json --collection-id 123 --start-datetime 2023-01-01 --end-datetime 2023-01-01 --target /tmp/ --source-epsg 2193 --target-epsg 2193 --gsd 10 --create-footprints=true
```

To use an AWS test dataset (input located in an AWS S3 bucket), log into the AWS account and add the following arguments to the `docker run` command:

```bash
-v ${HOME}/.aws:/root/.aws/:ro -e AWS_PROFILE=your-profile
```

### In the cloud

This package is designed to be run in a [Kubernetes](https://kubernetes.io/) cluster using a workflow system. More information can be found in the [linz/topo-workflows](https://github.com/linz/topo-workflows) repository.

## Versioning

GitHub Actions automatically handles publishing a container to the GitHub Package Registry (`ghcr`) and in a private AWS Elastic Container Registry (ECR).

A new container is published every time a change is [merged to the `master` branch](https://github.com/linz/geoprocessor/blob/master/.github/workflows/containers.yml). This container will be tagged with the following:

- `latest`
- `github` version (example: `v1.1.0-2-ga1154e8`)

A new container is also published [when a release is merged to `master`](https://github.com/linz/geoprocessor/blob/master/.github/workflows/release-please.yml) (see section bellow). This container will be tagged with the following:

- `latest`
- `vX` (example: `v1`)
- `vX.Y` (example: `v1.2`)
- `vX.Y.Z` (example: `v1.2.4`)

You can see the tags in the [GitHub Packages page](https://github.com/linz/geoprocessor/pkgs/container/geoprocessor/raster).

## Releases

### Managing

[googleapis/release-please](https://github.com/googleapis/release-please) is used to support the release process.
Based on what has been merged to `master` (`fix`, `feat`, `feat!`, `fix!` or `refactor!`), the library generates a `changelog` based on the commit messages and creates a Pull Request. This is triggered by this [GitHub Action](https://github.com/linz/geoprocessor/blob/master/.github/workflows/release-please.yml).

The repository is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) and each of its packages is versioned on its own:

| Component                    | Version in                                       | Git tag                         | Changelog                                      |
| ---------------------------- | ------------------------------------------------ | ------------------------------- | ---------------------------------------------- |
| Repository (both containers) | `pyproject.toml`                                 | `vX.Y.Z`                        | `CHANGELOG.md`                                 |
| `geoprocessor-<package>`     | `packages/geoprocessor-<package>/pyproject.toml` | `geoprocessor-<package>-vX.Y.Z` | `packages/geoprocessor-<package>/CHANGELOG.md` |

The repository version takes every commit into account, so it bumps whenever any package does, and both containers keep sharing that single `vX.Y.Z` tag ([see above](#versioning)). A package version only bumps when a user facing commit touches that package's directory, which lets the packages move at their own pace.

All of these bumps are batched into one `release: X.Y.Z` Pull Request, `X.Y.Z` being the new repository version. Merging it tags every component that was released.

### Publishing

To publish a release, the Pull Request opened by `release-please` bot needs to be merged:

1. Open the PR and verify that the `CHANGELOG` contains what you expect in the release. If the latest change you expect is not there, double-check that a GitHub Actions is not currently running or failed.
2. Approve and merge the PR.
3. Once the Pull Request is merged to `master` a [GitHub Action](https://github.com/linz/geoprocessor/blob/master/.github/workflows/release-please.yml) it creates the release and publish a new container tagged for this release.
