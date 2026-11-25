# Changelog

## [1.1.0](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v1.0.0...geoprocessor-common-v1.1.0) (2026-11-25)


### Features

* add intensity_zstd preset for 16-bit single-band intensity TDE-2239 ([#1747](https://github.com/linz/geoprocessor/issues/1747)) ([e51d412](https://github.com/linz/geoprocessor/commit/e51d41228453fe4c4afda225c35f5ac6b4cceea0))

## [1.0.0](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.3.0...geoprocessor-common-v1.0.0) (2026-11-17)


### ⚠ BREAKING CHANGES

* Python 3.15 and GDAL 3.13.3 from LINZ base images TDE-2176 ([#1734](https://github.com/linz/geoprocessor/issues/1734))

### Features

* Python 3.15 and GDAL 3.13.3 from LINZ base images TDE-2176 ([#1734](https://github.com/linz/geoprocessor/issues/1734)) ([40837ff](https://github.com/linz/geoprocessor/commit/40837ffd333bc190e63c72831092680ad3d788f4))

## [0.3.0](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.2.0...geoprocessor-common-v0.3.0) (2026-11-04)


### Features

* scale 16-bit sources to 8-bit using dataset percentiles TDE-2075 ([#1710](https://github.com/linz/geoprocessor/issues/1710)) ([5a9c848](https://github.com/linz/geoprocessor/commit/5a9c84874830775d7d6b4d155e63e841ae86df98))

## [0.2.0](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.1.3...geoprocessor-common-v0.2.0) (2026-10-13)


### Features

* rescale 16-bit sources to 8-bit with the webp preset TDE-2106 ([#1683](https://github.com/linz/geoprocessor/issues/1683)) ([27293c7](https://github.com/linz/geoprocessor/commit/27293c71ec5009b2b0e8713166c9486ace0e8171))

## [0.1.3](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.1.2...geoprocessor-common-v0.1.3) (2026-09-30)


### Bug Fixes

* raise clear error when intermediate files disappear TDE-2099 ([#1665](https://github.com/linz/geoprocessor/issues/1665)) ([0fb3b3a](https://github.com/linz/geoprocessor/commit/0fb3b3aec7457b73e37978d83c3d447da839345d))


### Reverts

* "revert: "fix: stream file copies to allow outputs over 5GB TDE-2072" TDE-2090" ([#1663](https://github.com/linz/geoprocessor/issues/1663)) ([c546acd](https://github.com/linz/geoprocessor/commit/c546acde61d17b3eb5394e49fef4548c9cfff083))

## [0.1.2](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.1.1...geoprocessor-common-v0.1.2) (2026-09-25)


### Reverts

* "fix: stream file copies to allow outputs over 5GB TDE-2072" ([#1660](https://github.com/linz/geoprocessor/issues/1660)) ([ce6e399](https://github.com/linz/geoprocessor/commit/ce6e399e62527188932a3c134ef76725edff5127))

## [0.1.1](https://github.com/linz/geoprocessor/compare/geoprocessor-common-v0.1.0...geoprocessor-common-v0.1.1) (2026-09-23)


### Bug Fixes

* stream file copies to allow outputs over 5GB TDE-2072 ([#1653](https://github.com/linz/geoprocessor/issues/1653)) ([3a555d6](https://github.com/linz/geoprocessor/commit/3a555d6cc9dc1565c0d1c8f66ec1ced150bb2b1e))
