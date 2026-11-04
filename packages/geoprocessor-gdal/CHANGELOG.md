# Changelog

## [0.3.0](https://github.com/linz/geoprocessor/compare/geoprocessor-gdal-v0.2.0...geoprocessor-gdal-v0.3.0) (2026-11-04)


### Features

* rescale 16-bit webp with a source range and gamma TDE-2199 ([#1731](https://github.com/linz/geoprocessor/issues/1731)) ([4dbf695](https://github.com/linz/geoprocessor/commit/4dbf6954d5fd6caa52c7090b694a51e563d8c91b))
* scale 16-bit sources to 8-bit using dataset percentiles TDE-2075 ([#1710](https://github.com/linz/geoprocessor/issues/1710)) ([5a9c848](https://github.com/linz/geoprocessor/commit/5a9c84874830775d7d6b4d155e63e841ae86df98))

## [0.2.0](https://github.com/linz/geoprocessor/compare/geoprocessor-gdal-v0.1.3...geoprocessor-gdal-v0.2.0) (2026-10-13)


### Features

* rescale 16-bit sources to 8-bit with the webp preset TDE-2106 ([#1683](https://github.com/linz/geoprocessor/issues/1683)) ([27293c7](https://github.com/linz/geoprocessor/commit/27293c71ec5009b2b0e8713166c9486ace0e8171))

## [0.1.3](https://github.com/linz/geoprocessor/compare/geoprocessor-gdal-v0.1.2...geoprocessor-gdal-v0.1.3) (2026-09-30)


### Bug Fixes

* raise clear error when intermediate files disappear TDE-2099 ([#1665](https://github.com/linz/geoprocessor/issues/1665)) ([0fb3b3a](https://github.com/linz/geoprocessor/commit/0fb3b3aec7457b73e37978d83c3d447da839345d))


### Reverts

* "revert: "fix: stream file copies to allow outputs over 5GB TDE-2072" TDE-2090" ([#1663](https://github.com/linz/geoprocessor/issues/1663)) ([c546acd](https://github.com/linz/geoprocessor/commit/c546acde61d17b3eb5394e49fef4548c9cfff083))

## [0.1.2](https://github.com/linz/geoprocessor/compare/geoprocessor-gdal-v0.1.1...geoprocessor-gdal-v0.1.2) (2026-09-25)


### Reverts

* "fix: stream file copies to allow outputs over 5GB TDE-2072" ([#1660](https://github.com/linz/geoprocessor/issues/1660)) ([ce6e399](https://github.com/linz/geoprocessor/commit/ce6e399e62527188932a3c134ef76725edff5127))

## [0.1.1](https://github.com/linz/geoprocessor/compare/geoprocessor-gdal-v0.1.0...geoprocessor-gdal-v0.1.1) (2026-09-23)


### Bug Fixes

* stream file copies to allow outputs over 5GB TDE-2072 ([#1653](https://github.com/linz/geoprocessor/issues/1653)) ([3a555d6](https://github.com/linz/geoprocessor/commit/3a555d6cc9dc1565c0d1c8f66ec1ced150bb2b1e))
