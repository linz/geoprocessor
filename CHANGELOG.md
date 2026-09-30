# Changelog

## [9.0.2](https://github.com/linz/geoprocessor/compare/v9.0.1...v9.0.2) (2026-09-25)


### Reverts

* "fix: stream file copies to allow outputs over 5GB TDE-2072" ([#1660](https://github.com/linz/geoprocessor/issues/1660)) ([ce6e399](https://github.com/linz/geoprocessor/commit/ce6e399e62527188932a3c134ef76725edff5127))

## [9.0.1](https://github.com/linz/geoprocessor/compare/v9.0.0...v9.0.1) (2026-09-23)


### Bug Fixes

* stream file copies to allow outputs over 5GB TDE-2072 ([#1653](https://github.com/linz/geoprocessor/issues/1653)) ([3a555d6](https://github.com/linz/geoprocessor/commit/3a555d6cc9dc1565c0d1c8f66ec1ced150bb2b1e))

## [9.0.0](https://github.com/linz/topo-imagery/compare/v8.0.0...v9.0.0) (2026-09-16)


### ⚠ BREAKING CHANGES

* move top level scripts and add to project.scripts TDE-1981 ([#1622](https://github.com/linz/topo-imagery/issues/1622))

### Features

* publish pointcloud and raster container TDE-1921 ([#1637](https://github.com/linz/topo-imagery/issues/1637)) ([b745a5c](https://github.com/linz/topo-imagery/commit/b745a5c794ba078673476c367504d8056d69e805))
* tini init container entrypoint ([#1651](https://github.com/linz/topo-imagery/issues/1651)) ([2c976e4](https://github.com/linz/topo-imagery/commit/2c976e41bb6a3719a9f5ecaa062a2d3d53e2d56c))


### Bug Fixes

* use NoSuchFileError consistently TDE-2057 ([#1638](https://github.com/linz/topo-imagery/issues/1638)) ([11cdf06](https://github.com/linz/topo-imagery/commit/11cdf0601aef1ae378758d9cd8b6ceb63d8a78aa))


### Code Refactoring

* move top level scripts and add to project.scripts TDE-1981 ([#1622](https://github.com/linz/topo-imagery/issues/1622)) ([06a0f6c](https://github.com/linz/topo-imagery/commit/06a0f6c418213abb97eded0d5faae7f4a5707243))

## [8.0.0](https://github.com/linz/topo-imagery/compare/v7.24.0...v8.0.0) (2026-09-14)


### ⚠ BREAKING CHANGES

* add data type to STAC collection metadata TDE-2004 ([#1643](https://github.com/linz/topo-imagery/issues/1643))
* use data-type parameter to determine BIGTIFF option TDE-2034 ([#1641](https://github.com/linz/topo-imagery/issues/1641))

### Features

* add data type to STAC collection metadata TDE-2004 ([#1643](https://github.com/linz/topo-imagery/issues/1643)) ([5b3c7cb](https://github.com/linz/topo-imagery/commit/5b3c7cbd8197dcb1006b4d9889b43d30a27d7148))
* topo imagery write bigtiff for 16 32 bit rgbnir imagery TDE-2005 ([#1607](https://github.com/linz/topo-imagery/issues/1607)) ([ea4a6bc](https://github.com/linz/topo-imagery/commit/ea4a6bc464d8d3ea67f6b53625a2a37ce8869b25))
* use data-type parameter to determine BIGTIFF option TDE-2034 ([#1641](https://github.com/linz/topo-imagery/issues/1641)) ([2f72bf4](https://github.com/linz/topo-imagery/commit/2f72bf4ca95eab2064cd13af24d178c0dc572c50))

## [7.24.0](https://github.com/linz/topo-imagery/compare/v7.23.0...v7.24.0) (2026-08-18)


### Features

* support Chatham Islands EPSG:3793 TDE-1990 ([#1588](https://github.com/linz/topo-imagery/issues/1588)) ([09ce5c4](https://github.com/linz/topo-imagery/commit/09ce5c4d3e886398fad94a6b2905dbab25b1eef2))

## [7.23.0](https://github.com/linz/topo-imagery/compare/v7.22.0...v7.23.0) (2026-08-09)


### Features

* title generation needs to consistently account for event names TDE-2010 ([#1603](https://github.com/linz/topo-imagery/issues/1603)) ([590a38b](https://github.com/linz/topo-imagery/commit/590a38bd85833c6fdd2877ff9df6da330f440d3d))

## [7.22.0](https://github.com/linz/topo-imagery/compare/v7.21.1...v7.22.0) (2026-07-08)


### Features

* Added Chatham Islands to the list of regions TDE-1971 ([#1585](https://github.com/linz/topo-imagery/issues/1585)) ([4e642d4](https://github.com/linz/topo-imagery/commit/4e642d45d9fc2b59db6d210e665f1939f7f5032b))
* change aerial photos to ancillary aerial photos TDE-1924 ([#1568](https://github.com/linz/topo-imagery/issues/1568)) ([4ac5259](https://github.com/linz/topo-imagery/commit/4ac525992eea5c965478cbe38ea9f3b255c2e3f3))

## [7.21.1](https://github.com/linz/topo-imagery/compare/v7.21.0...v7.21.1) (2026-04-22)


### Bug Fixes

* filter non-polygons artifacts from capture-area TDE-1857 ([#1495](https://github.com/linz/topo-imagery/issues/1495)) ([a1aef65](https://github.com/linz/topo-imagery/commit/a1aef6592b819d5b19f0d4cdea0da6e31fe9326a))

## [7.21.0](https://github.com/linz/topo-imagery/compare/v7.20.1...v7.21.0) (2026-03-23)


### Features

* do not generate hillshade footprints TDE-1839 ([#1481](https://github.com/linz/topo-imagery/issues/1481)) ([4da88fe](https://github.com/linz/topo-imagery/commit/4da88fe4a3b62e859259a983a8180360212cdc04))

## [7.20.1](https://github.com/linz/topo-imagery/compare/v7.20.0...v7.20.1) (2026-03-23)


### Bug Fixes

* use only supplied capture area if provided TDE-1857 ([#1491](https://github.com/linz/topo-imagery/issues/1491)) ([6e26508](https://github.com/linz/topo-imagery/commit/6e265087339dcafec765e833d7ed60c61def0232))

## [7.20.0](https://github.com/linz/topo-imagery/compare/v7.19.1...v7.20.0) (2026-03-20)


### Features

* standardise_validate allow custom concurrency TDE-1832 ([#1488](https://github.com/linz/topo-imagery/issues/1488)) ([8c22b24](https://github.com/linz/topo-imagery/commit/8c22b244a35b9bb1bcbd7cf2f97fb06a584ca721))

## [7.19.1](https://github.com/linz/topo-imagery/compare/v7.19.0...v7.19.1) (2026-03-19)


### Bug Fixes

* accept single feature geojson TDE-1858 ([#1486](https://github.com/linz/topo-imagery/issues/1486)) ([da33c12](https://github.com/linz/topo-imagery/commit/da33c1283234b7fc74c868ed06e8cd62fa3189c6))


### Reverts

* "build: stop publishing containers to ECR" TDE-1861 ([#1485](https://github.com/linz/topo-imagery/issues/1485)) ([d84a3ba](https://github.com/linz/topo-imagery/commit/d84a3ba18979dc41d5e079c4ebb3854cef45fe47))

## [7.19.0](https://github.com/linz/topo-imagery/compare/v7.18.1...v7.19.0) (2026-03-17)


### Features

* create capture area from capture dates file TDE-1839 ([#1478](https://github.com/linz/topo-imagery/issues/1478)) ([25ae5dc](https://github.com/linz/topo-imagery/commit/25ae5dcd891052e1c53dec9b11f4f078983d0fc5))


### Documentation

* add Testing section in Coding Guidelines TDE-1446 ([#1474](https://github.com/linz/topo-imagery/issues/1474)) ([727bd5a](https://github.com/linz/topo-imagery/commit/727bd5a4adad22e0883e7fa93f8bd5ae2de67e6d))

## [7.18.1](https://github.com/linz/topo-imagery/compare/v7.18.0...v7.18.1) (2026-03-16)


### Bug Fixes

* add gsd and linz:security_classification fields to collection when re-standardised TDE-1842 ([#1482](https://github.com/linz/topo-imagery/issues/1482)) ([b3f468d](https://github.com/linz/topo-imagery/commit/b3f468de004c2c2516ffb5df175795652d9d56e7))

## [7.18.0](https://github.com/linz/topo-imagery/compare/v7.17.0...v7.18.0) (2026-03-09)


### Features

* add `--force` option for standardise_validate.py ([#1477](https://github.com/linz/topo-imagery/issues/1477)) ([567be7b](https://github.com/linz/topo-imagery/commit/567be7b6a818cbfb5ae8c9deae0f899d1fca8204))


### Bug Fixes

* ZSTD hillshades should be treated as DEMs TDE-1835 ([#1479](https://github.com/linz/topo-imagery/issues/1479)) ([30de692](https://github.com/linz/topo-imagery/commit/30de692b07608e6f3684d37a231453209d91d0c9))


### Documentation

* update AWS tests instructions ([#1475](https://github.com/linz/topo-imagery/issues/1475)) ([2a5014d](https://github.com/linz/topo-imagery/commit/2a5014d0e922dfc404d336e5088152bff73121cc))

## [7.17.0](https://github.com/linz/topo-imagery/compare/v7.16.1...v7.17.0) (2026-02-26)


### Features

* change hillshade COG compression to ZSTD TDE-1817 ([#1471](https://github.com/linz/topo-imagery/issues/1471)) ([c71fe2c](https://github.com/linz/topo-imagery/commit/c71fe2c9217f46d365844856d15e0e5e8f2df63e))


### Documentation

* init CONTRIBUTING coding guidelines TDE-1446 ([#1472](https://github.com/linz/topo-imagery/issues/1472)) ([c9aa7bd](https://github.com/linz/topo-imagery/commit/c9aa7bdf237fd964526b89acb2e048afc46b8092))

## [7.16.1](https://github.com/linz/topo-imagery/compare/v7.16.0...v7.16.1) (2026-02-08)


### Bug Fixes

* force RGBNIR Band 4 to NIR if labelled Alpha TDE-1810 ([#1469](https://github.com/linz/topo-imagery/issues/1469)) ([397c67c](https://github.com/linz/topo-imagery/commit/397c67c0daf1003208655ec31942b7fda1ffc905))

## [7.16.0](https://github.com/linz/topo-imagery/compare/v7.15.0...v7.16.0) (2026-01-26)


### Features

* standardise RGBN imagery TDE-693 ([#1460](https://github.com/linz/topo-imagery/issues/1460)) ([e99d791](https://github.com/linz/topo-imagery/commit/e99d791f74c9091bff607ddd8087a1145cddf8a2))

## [7.15.0](https://github.com/linz/topo-imagery/compare/v7.14.0...v7.15.0) (2026-01-19)


### Features

* add an option to simplify footprints TDE-1772 ([#1463](https://github.com/linz/topo-imagery/issues/1463)) ([d3a222d](https://github.com/linz/topo-imagery/commit/d3a222d6282920465a8e67cb8cc240222c309ba4))
* add description for simplified capture-area TDE-1773 ([#1464](https://github.com/linz/topo-imagery/issues/1464)) ([bbb9817](https://github.com/linz/topo-imagery/commit/bbb9817c23dd695ab32043659b8d96332dcc2d33))

## [7.14.0](https://github.com/linz/topo-imagery/compare/v7.13.1...v7.14.0) (2025-12-17)


### Features

* add RGBNIR metadata tde-1741 ([#1456](https://github.com/linz/topo-imagery/issues/1456)) ([d6a9e92](https://github.com/linz/topo-imagery/commit/d6a9e92fab87b6e83a01416072c1984627035b93))
* support RGBNA imagery in Non-Visual QA TDE-1757 ([#1459](https://github.com/linz/topo-imagery/issues/1459)) ([e0d23fe](https://github.com/linz/topo-imagery/commit/e0d23fe937872884555ff496a4124e7bcf632e21))

## [7.13.1](https://github.com/linz/topo-imagery/compare/v7.13.0...v7.13.1) (2025-11-30)


### Bug Fixes

* gdalbuildvrt - specify EPSG code to prevent complex VRT cutline geometry ([#1454](https://github.com/linz/topo-imagery/issues/1454)) ([db54175](https://github.com/linz/topo-imagery/commit/db54175d9baaa04d6b7442ecbca93a197e748f6e))

## [7.13.0](https://github.com/linz/topo-imagery/compare/v7.12.2...v7.13.0) (2025-11-17)


### Features

* remove Argo Workflows environment variables usage TDE-1693 ([#1452](https://github.com/linz/topo-imagery/issues/1452)) ([a817c33](https://github.com/linz/topo-imagery/commit/a817c33286e211082c336173fa89d5aa4eee92a1))

## [7.12.2](https://github.com/linz/topo-imagery/compare/v7.12.1...v7.12.2) (2025-10-30)


### Bug Fixes

* convert temporal extent to NZ time for title and description TDE-1661 ([#1433](https://github.com/linz/topo-imagery/issues/1433)) ([5ca0421](https://github.com/linz/topo-imagery/commit/5ca0421ba3848d9d7e04ca83492c895bd02d3983))

## [7.12.1](https://github.com/linz/topo-imagery/compare/v7.12.0...v7.12.1) (2025-10-27)


### Bug Fixes

* ensure hillshade has been fully processed when skipping TDE-1701 ([#1442](https://github.com/linz/topo-imagery/issues/1442)) ([13c9c27](https://github.com/linz/topo-imagery/commit/13c9c2758828e664f304bd516edcb662ae8d3d47))

## [7.12.0](https://github.com/linz/topo-imagery/compare/v7.11.0...v7.12.0) (2025-10-20)


### Features

* Add script to fix LAZ headers TDE-1649 ([#1419](https://github.com/linz/topo-imagery/issues/1419)) ([018f9e0](https://github.com/linz/topo-imagery/commit/018f9e0ba7f8c8588b49dcd8c0af918b884a2d3b))

## [7.11.0](https://github.com/linz/topo-imagery/compare/v7.10.0...v7.11.0) (2025-09-21)


### Features

* add GSD metadata to collection.json TDE-1657 ([#1407](https://github.com/linz/topo-imagery/issues/1407)) ([02c43fd](https://github.com/linz/topo-imagery/commit/02c43fd6220a4bb598383643c7b4f3a29672f5fd))


### Bug Fixes

* accept aerial-photos as a category TDE-1650 ([#1402](https://github.com/linz/topo-imagery/issues/1402)) ([7c954d6](https://github.com/linz/topo-imagery/commit/7c954d6fe999076fbcd3a177e0cc0a78b7b641c8))

## [7.10.0](https://github.com/linz/topo-imagery/compare/v7.9.1...v7.10.0) (2025-09-02)


### Features

* use supplied capture area TDE-1604 ([#1374](https://github.com/linz/topo-imagery/issues/1374)) ([9f45051](https://github.com/linz/topo-imagery/commit/9f45051917e9ec3e0f0a62ebe714faffbfffd41f))

## [7.9.1](https://github.com/linz/topo-imagery/compare/v7.9.0...v7.9.1) (2025-08-24)


### Bug Fixes

* orient the capture area after making geometry valid TDE-1618 ([#1377](https://github.com/linz/topo-imagery/issues/1377)) ([b813f4a](https://github.com/linz/topo-imagery/commit/b813f4a53dc3e8428ffe3a27c52651228dc37df3))

## [7.9.0](https://github.com/linz/topo-imagery/compare/v7.8.0...v7.9.0) (2025-07-22)


### Features

* better logging for empty features TDE-1585 ([#1347](https://github.com/linz/topo-imagery/issues/1347)) ([cfdc507](https://github.com/linz/topo-imagery/commit/cfdc507c77c4ef88511b3a16177c32b1b1e5152d))

## [7.8.0](https://github.com/linz/topo-imagery/compare/v7.7.0...v7.8.0) (2025-07-16)


### Features

* keep existing collection description TDE-1498 ([#1338](https://github.com/linz/topo-imagery/issues/1338)) ([04efd8c](https://github.com/linz/topo-imagery/commit/04efd8c95d2d86f8a12358ff6df8fbfc8ac1b28e))

## [7.7.0](https://github.com/linz/topo-imagery/compare/v7.6.1...v7.7.0) (2025-06-12)


### Features

* add dataset domain TDE-1542 ([#1326](https://github.com/linz/topo-imagery/issues/1326)) ([f80c4df](https://github.com/linz/topo-imagery/commit/f80c4df902a369aa346bd9a7f4c9d4d44bc90361))


### Bug Fixes

* Collection title should always be set when no odr url is provided TDE-1539 ([#1325](https://github.com/linz/topo-imagery/issues/1325)) ([061e312](https://github.com/linz/topo-imagery/commit/061e3124334a959a25eef5230b05fd59374e8d0f))


### Documentation

* cleanup collection.update() docstring ([#1322](https://github.com/linz/topo-imagery/issues/1322)) ([c55de37](https://github.com/linz/topo-imagery/commit/c55de373d22b5fd4db48e2707fa457d154d97729))

## [7.6.1](https://github.com/linz/topo-imagery/compare/v7.6.0...v7.6.1) (2025-04-27)


### Bug Fixes

* title and description years should match temporal extent TDE-1464 ([#1317](https://github.com/linz/topo-imagery/issues/1317)) ([5a6c0b9](https://github.com/linz/topo-imagery/commit/5a6c0b9b5305c49d66f6376c0353d1370eb00fde))

## [7.6.0](https://github.com/linz/topo-imagery/compare/v7.5.0...v7.6.0) (2025-04-23)


### Features

* support national DSM hillshades TDE-1455 ([#1319](https://github.com/linz/topo-imagery/issues/1319)) ([62c4260](https://github.com/linz/topo-imagery/commit/62c4260b63f62a6a7f653e8ed177e7ffe63601f9))

## [7.5.0](https://github.com/linz/topo-imagery/compare/v7.4.2...v7.5.0) (2025-04-17)


### Features

* --delete-all-existing-items TDE-1443 ([#1306](https://github.com/linz/topo-imagery/issues/1306)) ([caca74b](https://github.com/linz/topo-imagery/commit/caca74b63efce2dc8f6de27257e27d57cde8c124))

## [7.4.2](https://github.com/linz/topo-imagery/compare/v7.4.1...v7.4.2) (2025-04-14)


### Bug Fixes

* existing collection is not updated with new metadata TDE-1444 ([#1313](https://github.com/linz/topo-imagery/issues/1313)) ([b0c7bcd](https://github.com/linz/topo-imagery/commit/b0c7bcd4be1b90638b048bab11d2f24fa6378533))

## [7.4.1](https://github.com/linz/topo-imagery/compare/v7.4.0...v7.4.1) (2025-03-31)


### Bug Fixes

* allow to pass ODR URL to `generate_hillshade.py` TDE-1452 ([#1310](https://github.com/linz/topo-imagery/issues/1310)) ([6802113](https://github.com/linz/topo-imagery/commit/68021134c005fa3312923eb1a32e714063bdf056))

## [7.4.0](https://github.com/linz/topo-imagery/compare/v7.3.0...v7.4.0) (2025-03-23)


### Features

* compute and store stats into hillshade TIFFs TDE-1439 ([#1300](https://github.com/linz/topo-imagery/issues/1300)) ([1e6d45b](https://github.com/linz/topo-imagery/commit/1e6d45b179e376a97250f86e09384a7edaf8d0eb))
* create hillshade footprints TDE-1441 ([#1301](https://github.com/linz/topo-imagery/issues/1301)) ([6ce42f1](https://github.com/linz/topo-imagery/commit/6ce42f15a7b5694e2d55413c144f855400720b8c))
* create STAC Items for hillshade TIFFs TDE-1438 ([#1298](https://github.com/linz/topo-imagery/issues/1298)) ([d31966a](https://github.com/linz/topo-imagery/commit/d31966a4df864c69be70607ad52f1ae3d4f614a6))


### Bug Fixes

* hillshade STAC is not created when TIFF already exists TDE-1445 ([#1302](https://github.com/linz/topo-imagery/issues/1302)) ([44dfa0d](https://github.com/linz/topo-imagery/commit/44dfa0d06dd9e29e6af95134faf2f97beb312854))


### Documentation

* update test_should_not_add_capture_area comment ([#1297](https://github.com/linz/topo-imagery/issues/1297)) ([67e56d5](https://github.com/linz/topo-imagery/commit/67e56d5e67f3a9f7878a2e00d58614cc950a904c))

## [7.3.0](https://github.com/linz/topo-imagery/compare/v7.2.0...v7.3.0) (2025-03-10)


### Features

* update existing Collection TDE-1359 ([#1224](https://github.com/linz/topo-imagery/issues/1224)) ([f8cdfba](https://github.com/linz/topo-imagery/commit/f8cdfba898c5b8ef8f2f38961ce9744b10fc70ee))


### Bug Fixes

* update hillshade preset enum values TDE-1371 ([#1294](https://github.com/linz/topo-imagery/issues/1294)) ([841bef8](https://github.com/linz/topo-imagery/commit/841bef8d2db8fff491c59f776d6aab702f1d1ba0))

## [7.2.0](https://github.com/linz/topo-imagery/compare/v7.1.1...v7.2.0) (2025-03-05)


### Features

* add resolution argument to gdalbuildvrt TDE-1383 ([#1269](https://github.com/linz/topo-imagery/issues/1269)) ([78dfc31](https://github.com/linz/topo-imagery/commit/78dfc31049a4a271cb875ff9982db752131571e1))
* generate hillshade TDE-1369 ([#1253](https://github.com/linz/topo-imagery/issues/1253)) ([e4f2bc4](https://github.com/linz/topo-imagery/commit/e4f2bc40bb4c41fa9b8b99918c996384a5cd9198))
* normalize capture-area geometry TDE-1359 ([#1288](https://github.com/linz/topo-imagery/issues/1288)) ([0a061ba](https://github.com/linz/topo-imagery/commit/0a061ba3910a2ed60aecf8b9ad1ec5ebc5cf80df))
* reset Collection extents TDE-1359 ([#1290](https://github.com/linz/topo-imagery/issues/1290)) ([e3bd9aa](https://github.com/linz/topo-imagery/commit/e3bd9aa3dc0e18be08c77310976a7820fb23a960))
* titles and descriptions for hillshade products TDE-1378 ([#1274](https://github.com/linz/topo-imagery/issues/1274)) ([7415614](https://github.com/linz/topo-imagery/commit/7415614e062de9dcf8ca5ff032d076fc8d314c9f))


### Bug Fixes

* deprecated artifact action TDE-1379 ([#1258](https://github.com/linz/topo-imagery/issues/1258)) ([7b0f43a](https://github.com/linz/topo-imagery/commit/7b0f43aec1340b4ac877d6a2983cc452faa90cc5))
* handle optional flags from Argo TDE-1346 ([#1287](https://github.com/linz/topo-imagery/issues/1287)) ([fea38b6](https://github.com/linz/topo-imagery/commit/fea38b6e87383c434aee7b3f294afa32693c1cb1))
* should not raise error when cutline is empty TDE-1392 ([#1284](https://github.com/linz/topo-imagery/issues/1284)) ([0b021e4](https://github.com/linz/topo-imagery/commit/0b021e47e970e8e4148d569adeae8330668bc57e))
* **standardise-validate:** allow empty string from Argo for start and end dates TDE-1346 ([#1286](https://github.com/linz/topo-imagery/issues/1286)) ([b96c851](https://github.com/linz/topo-imagery/commit/b96c85155db7970d97002cc5896a5a0f50382ffc))


### Reverts

* normalize capture-area geometry TDE-1359 ([#1288](https://github.com/linz/topo-imagery/issues/1288)) TDE-1423 ([#1292](https://github.com/linz/topo-imagery/issues/1292)) ([5bcf748](https://github.com/linz/topo-imagery/commit/5bcf748b800488400f5834bd5388704025552727))


### Documentation

* update cog-quality link ([#1256](https://github.com/linz/topo-imagery/issues/1256)) ([fbf92be](https://github.com/linz/topo-imagery/commit/fbf92be5d1fc47a5056360a802467f3fcefd26c8))

## [7.1.1](https://github.com/linz/topo-imagery/compare/v7.1.0...v7.1.1) (2024-12-18)


### Bug Fixes

* handle existing derived_from links when Item is updated TDE-1356 ([#1220](https://github.com/linz/topo-imagery/issues/1220)) ([7dfa7e7](https://github.com/linz/topo-imagery/commit/7dfa7e7066b6ccaf664af8067645284076cd0edd))

## [7.1.0](https://github.com/linz/topo-imagery/compare/v7.0.0...v7.1.0) (2024-11-28)


### Features

* set default current-date for collection_from_items script TDE-1298 ([#1196](https://github.com/linz/topo-imagery/issues/1196)) ([e22bb66](https://github.com/linz/topo-imagery/commit/e22bb66e9767d8a45cecca4443f2dbcd8459a084))


### Bug Fixes

* Use client syntax for getting file contents ([#1194](https://github.com/linz/topo-imagery/issues/1194)) ([ab83041](https://github.com/linz/topo-imagery/commit/ab830416703245b6c45b543dfb2037619ba31e42))

## [7.0.0](https://github.com/linz/topo-imagery/compare/v6.0.0...v7.0.0) (2024-11-27)


### ⚠ BREAKING CHANGES

* set update-dates on STAC item TDE-1298 ([#1180](https://github.com/linz/topo-imagery/issues/1180))

### Features

* defaults for current-datetime argument TDE-1298 ([#1193](https://github.com/linz/topo-imagery/issues/1193)) ([fa003f8](https://github.com/linz/topo-imagery/commit/fa003f8cf1d794f9e109e787fb96d1520e2de3b1))
* keep Collection properties.created date when resupplying ([#1160](https://github.com/linz/topo-imagery/issues/1160)) ([8af3e21](https://github.com/linz/topo-imagery/commit/8af3e2162a8d152c7fb8c8c29a4a0c5c468a4dfa))
* set update-dates on STAC item TDE-1298 ([#1180](https://github.com/linz/topo-imagery/issues/1180)) ([9d95b02](https://github.com/linz/topo-imagery/commit/9d95b02f5adad033dfbc83b93a8d538bedef7686))

## [6.0.0](https://github.com/linz/topo-imagery/compare/v5.2.0...v6.0.0) (2024-11-12)


### ⚠ BREAKING CHANGES

* add linz:slug to Collection TDE-1305 ([#1152](https://github.com/linz/topo-imagery/issues/1152))

### Features

* add linz:slug to Collection TDE-1305 ([#1152](https://github.com/linz/topo-imagery/issues/1152)) ([df5a746](https://github.com/linz/topo-imagery/commit/df5a746b6a0fac5c4d241ea948b376947f07332d))


### Bug Fixes

* Avoid deprecated stage name "commit" ([#1135](https://github.com/linz/topo-imagery/issues/1135)) ([e2d9e3d](https://github.com/linz/topo-imagery/commit/e2d9e3d161aa4267c74fd91dcd739af638964c4f))

## [5.2.0](https://github.com/linz/topo-imagery/compare/v5.1.0...v5.2.0) (2024-10-17)


### Features

* add description field for assets in collection TDE-1294 ([#1132](https://github.com/linz/topo-imagery/issues/1132)) ([4d6c030](https://github.com/linz/topo-imagery/commit/4d6c030d9da64f04d647ad116c6f478bbf2437f0))

## [5.1.0](https://github.com/linz/topo-imagery/compare/v5.0.2...v5.1.0) (2024-10-10)


### Features

* allow forcing Collection title to not have suffix TDE-1289 ([#1120](https://github.com/linz/topo-imagery/issues/1120)) ([7ca3c43](https://github.com/linz/topo-imagery/commit/7ca3c4329a46cc282e4bc9ba474eeb254c00667e))

## [5.0.2](https://github.com/linz/topo-imagery/compare/v5.0.1...v5.0.2) (2024-10-09)


### Bug Fixes

* capture area rounding TDE-1237 ([#1116](https://github.com/linz/topo-imagery/issues/1116)) ([d055f49](https://github.com/linz/topo-imagery/commit/d055f49f59ca1d64c5b19babcbcd91f9bfd657e0))
* providers should not be duplicated when having different roles TDE-1286 ([#1115](https://github.com/linz/topo-imagery/issues/1115)) ([46303cb](https://github.com/linz/topo-imagery/commit/46303cb6dd00b5c66802340d087d1f85848dbfb1))

## [5.0.1](https://github.com/linz/topo-imagery/compare/v5.0.0...v5.0.1) (2024-10-03)


### Bug Fixes

* round footprints to 8 decimal places TDE-1237 ([#1088](https://github.com/linz/topo-imagery/issues/1088)) ([fbb0930](https://github.com/linz/topo-imagery/commit/fbb09307048b8c0c1ed160f584074359366dcb3b))

## [5.0.0](https://github.com/linz/topo-imagery/compare/v4.11.2...v5.0.0) (2024-09-29)


### ⚠ BREAKING CHANGES

* dates from item TDE-1258 ([#1099](https://github.com/linz/topo-imagery/issues/1099))
* Auto-fill GSD unit TDE-1211 ([#1089](https://github.com/linz/topo-imagery/issues/1089))

### Features

* Add topo-imagery version information to STAC TDE-1265 ([#1080](https://github.com/linz/topo-imagery/issues/1080)) ([2039606](https://github.com/linz/topo-imagery/commit/20396060cdc5218f4ccd66a182195fb70f896837))
* Auto-fill GSD unit TDE-1211 ([#1089](https://github.com/linz/topo-imagery/issues/1089)) ([df257c9](https://github.com/linz/topo-imagery/commit/df257c9b6c81224df5626097c4a906b353aed4aa))
* dates from item TDE-1258 ([#1099](https://github.com/linz/topo-imagery/issues/1099)) ([8aabe64](https://github.com/linz/topo-imagery/commit/8aabe6488de8382a953d5d3fd1c7d1b8ae69415b))

## [4.11.2](https://github.com/linz/topo-imagery/compare/v4.11.1...v4.11.2) (2024-09-24)


### Bug Fixes

* Use GeoJSON media type for item links TDE-1254 ([#1086](https://github.com/linz/topo-imagery/issues/1086)) ([57dd0a8](https://github.com/linz/topo-imagery/commit/57dd0a86566e739a16c124be6ef24aca99565b79))

## [4.11.1](https://github.com/linz/topo-imagery/compare/v4.11.0...v4.11.1) (2024-09-19)


### Bug Fixes

* Don't attempt to install project inside virtualenv ([#1074](https://github.com/linz/topo-imagery/issues/1074)) ([dd989d0](https://github.com/linz/topo-imagery/commit/dd989d0500c3edc8eb847be86848a4ae9d54c8e2))
* start_datetime and end_datetime must be init if derived_from TDE-1258 ([#1079](https://github.com/linz/topo-imagery/issues/1079)) ([f0c8a4e](https://github.com/linz/topo-imagery/commit/f0c8a4e634ceb1359a1167368d69a955b04481bb))

## [4.11.0](https://github.com/linz/topo-imagery/compare/v4.10.0...v4.11.0) (2024-09-15)


### Features

* add capture dates asset link to collection TDE-1256 ([#1069](https://github.com/linz/topo-imagery/issues/1069)) ([d4b391a](https://github.com/linz/topo-imagery/commit/d4b391a60f27159be14d9074e4545a863aed57fc))

## [4.10.0](https://github.com/linz/topo-imagery/compare/v4.9.0...v4.10.0) (2024-09-12)


### Features

* add derived_from links to item TDE-1251 ([#1043](https://github.com/linz/topo-imagery/issues/1043)) ([077f14f](https://github.com/linz/topo-imagery/commit/077f14f3ab158ef47525b44b7929ddff593ff80e))
* determine start and end datetimes when item include derived TDE-1258 ([#1052](https://github.com/linz/topo-imagery/issues/1052)) ([62d571a](https://github.com/linz/topo-imagery/commit/62d571a6fdd196d4eef584b0c91aab7f3c4afa4a))
* make start_datetime and end_datetime optional when includeDerived is True TDE-1258 ([#1065](https://github.com/linz/topo-imagery/issues/1065)) ([57f088c](https://github.com/linz/topo-imagery/commit/57f088c1adc7c204f8338493a467eee1fe77df54))
* More types ([#989](https://github.com/linz/topo-imagery/issues/989)) ([3f7cd57](https://github.com/linz/topo-imagery/commit/3f7cd571e837ce3d8a8528f181b181d41549dd14))


### Bug Fixes

* capture area winding order TDE-1205 ([#1008](https://github.com/linz/topo-imagery/issues/1008)) ([61be096](https://github.com/linz/topo-imagery/commit/61be096bc9af997933ef6bee6cd72d441d350bc7))
* error on collection with no items TDE-1216 ([#1000](https://github.com/linz/topo-imagery/issues/1000)) ([d351d85](https://github.com/linz/topo-imagery/commit/d351d85f42fd096628b65629f8be30a5f617d920))

## [4.9.0](https://github.com/linz/topo-imagery/compare/v4.8.0...v4.9.0) (2024-07-16)


### Features

* Add Shapely type library TDE-1205 ([#988](https://github.com/linz/topo-imagery/issues/988)) ([f5e97e7](https://github.com/linz/topo-imagery/commit/f5e97e779c61246aadf99bbb4cf9538ffcb5a981))
* use new pull request template ([#999](https://github.com/linz/topo-imagery/issues/999)) ([9a6a0b2](https://github.com/linz/topo-imagery/commit/9a6a0b2971934a03607876c51feb8435ec985e00))


### Bug Fixes

* concurrency file order TDE-1213 ([#998](https://github.com/linz/topo-imagery/issues/998)) ([37dcb8b](https://github.com/linz/topo-imagery/commit/37dcb8b49d9a0cf45dcc6d0ce3011a4d6016e9e7))
* Treat item as `dict` TDE-1209 ([#993](https://github.com/linz/topo-imagery/issues/993)) ([384d0fc](https://github.com/linz/topo-imagery/commit/384d0fc674ce8fe4f1ff8726362881887a68522f))


### Reverts

* Pull Requests [#993](https://github.com/linz/topo-imagery/issues/993) and [#985](https://github.com/linz/topo-imagery/issues/985) ([#997](https://github.com/linz/topo-imagery/issues/997)) ([289880c](https://github.com/linz/topo-imagery/commit/289880c6886a2bbe6908feb2924aa68f1a7750a8))

## [4.8.0](https://github.com/linz/topo-imagery/compare/v4.7.1...v4.8.0) (2024-06-09)


### Features

* Add created/updated properties to collections TDE-1147 ([#981](https://github.com/linz/topo-imagery/issues/981)) ([00f4570](https://github.com/linz/topo-imagery/commit/00f457028ea4512419a1fe40344802cb89541729))
* Set created/updated item properties TDE-1147 ([#980](https://github.com/linz/topo-imagery/issues/980)) ([37ee07f](https://github.com/linz/topo-imagery/commit/37ee07f413f93ab831e8bec4b656d29d31d78dbc))

## [4.7.1](https://github.com/linz/topo-imagery/compare/v4.7.0...v4.7.1) (2024-05-27)


### Bug Fixes

* Make build compatible with new GDAL container TDE-1179 ([#977](https://github.com/linz/topo-imagery/issues/977)) ([f377d61](https://github.com/linz/topo-imagery/commit/f377d61f6c9471d9458b01db19aa62d2c4abd278))


### Reverts

* "fix: Make build compatible with new GDAL container TDE-1179 ([#971](https://github.com/linz/topo-imagery/issues/971))" ([#975](https://github.com/linz/topo-imagery/issues/975)) ([3990bf9](https://github.com/linz/topo-imagery/commit/3990bf967e4da461b3e1de7d079aa3f14ed0046c))

## [4.7.0](https://github.com/linz/topo-imagery/compare/v4.6.0...v4.7.0) (2024-05-23)


### Features

* timestamps when created TDE-1147 ([#956](https://github.com/linz/topo-imagery/issues/956)) ([2828f14](https://github.com/linz/topo-imagery/commit/2828f14bc2bfb1bc03963a31a2c2b64ba24f6f75))


### Bug Fixes

* add draft lifecycle tag TDE-1161 ([#964](https://github.com/linz/topo-imagery/issues/964)) ([64040d8](https://github.com/linz/topo-imagery/commit/64040d8a1a0a74b1a42ffd99d6379f4995573c98))
* Make build compatible with new GDAL container TDE-1179 ([#971](https://github.com/linz/topo-imagery/issues/971)) ([719d96e](https://github.com/linz/topo-imagery/commit/719d96e1ff1133c351bbee7a1d93fa359cc702e4))
* should use unique file names when copying files to standardise TDE-1186 ([#974](https://github.com/linz/topo-imagery/issues/974)) ([8b783dc](https://github.com/linz/topo-imagery/commit/8b783dce9870ff2bb5331552ff730218419f247c))

## [4.6.0](https://github.com/linz/topo-imagery/compare/v4.5.0...v4.6.0) (2024-05-07)


### Features

* add checksum to item links in collections TDE-1138 ([#953](https://github.com/linz/topo-imagery/issues/953)) ([afea8f0](https://github.com/linz/topo-imagery/commit/afea8f0f9722d0980657385e420f040e93085eef))
* add option to create footprints ([#959](https://github.com/linz/topo-imagery/issues/959)) ([ea5c98b](https://github.com/linz/topo-imagery/commit/ea5c98baa584c5445dcbedf159d409dfeeddf7ce))


### Bug Fixes

* Make compatible with latest moto ([#949](https://github.com/linz/topo-imagery/issues/949)) ([5902df0](https://github.com/linz/topo-imagery/commit/5902df0fec6dd15bb3a89ec616a2c27136a6aec5))
* Use correct types for S3 client ([#954](https://github.com/linz/topo-imagery/issues/954)) ([2c96c13](https://github.com/linz/topo-imagery/commit/2c96c1382d521d641e2b167e4096759af9b13dce))

## [4.5.0](https://github.com/linz/topo-imagery/compare/v4.4.0...v4.5.0) (2024-03-24)


### Features

* Use subtests for multi-assert tests ([#896](https://github.com/linz/topo-imagery/issues/896)) ([eb92bd2](https://github.com/linz/topo-imagery/commit/eb92bd2d550013f41538f2beb69e69abf0e6fd5d))


### Bug Fixes

* Treat "no data" value as a decimal number TDE-1077 ([#893](https://github.com/linz/topo-imagery/issues/893)) ([a9b4a84](https://github.com/linz/topo-imagery/commit/a9b4a84cbfa84ea48dd3e970c9fabe6175058001))
* update gdal version to 3.8.4 to fix footprints bug TDE-1106 ([#923](https://github.com/linz/topo-imagery/issues/923)) ([7a3367e](https://github.com/linz/topo-imagery/commit/7a3367ed9edebae49ebc50044ebe03a9e6fe63a6))
* Use integer coordinates TDE-1077 ([#895](https://github.com/linz/topo-imagery/issues/895)) ([b381bb6](https://github.com/linz/topo-imagery/commit/b381bb690d7bef68d15194b147568bcd1b8561f1))
* wrong vsis3 path logged ([#906](https://github.com/linz/topo-imagery/issues/906)) ([f491eb1](https://github.com/linz/topo-imagery/commit/f491eb1578ef3462170b79edb5f7775596ca2481))


### Documentation

* Document default "no data" value TDE-1077 ([#901](https://github.com/linz/topo-imagery/issues/901)) ([d15919f](https://github.com/linz/topo-imagery/commit/d15919ffc81309d0767ae13e5e7ab00b37136235))

## [4.4.0](https://github.com/linz/topo-imagery/compare/v4.3.0...v4.4.0) (2024-03-06)


### Features

* log capture-area generation duration TDE-1080 ([#889](https://github.com/linz/topo-imagery/issues/889)) ([5fd8f65](https://github.com/linz/topo-imagery/commit/5fd8f652aef1ce8c24a93a1a1816a9aa7164d880))


### Bug Fixes

* footprint should exists if tiff already exists ([#890](https://github.com/linz/topo-imagery/issues/890)) ([9868072](https://github.com/linz/topo-imagery/commit/9868072acbcf95ef58e1ad9b209f7b4a4a647011))

## [4.3.0](https://github.com/linz/topo-imagery/compare/v4.2.4...v4.3.0) (2024-03-06)


### Features

* simplify footprint geometry tde-1080 ([#891](https://github.com/linz/topo-imagery/issues/891)) ([a932a17](https://github.com/linz/topo-imagery/commit/a932a17125560d9e7007dec733f378d56799256e))

## [4.2.4](https://github.com/linz/topo-imagery/compare/v4.2.3...v4.2.4) (2024-02-27)


### Bug Fixes

* handle percent-encoded urls TDE-1054 ([#881](https://github.com/linz/topo-imagery/issues/881)) ([eacc453](https://github.com/linz/topo-imagery/commit/eacc4532407129cae02dfb209ac9293a3294584e))

## [4.2.3](https://github.com/linz/topo-imagery/compare/v4.2.2...v4.2.3) (2024-02-27)


### Bug Fixes

* update wording for release ([#878](https://github.com/linz/topo-imagery/issues/878)) ([dcc7972](https://github.com/linz/topo-imagery/commit/dcc7972195e685b5865c20b0bb15acac9ed51319))

## [4.2.2](https://github.com/linz/topo-imagery/compare/v4.2.1...v4.2.2) (2024-02-26)


### Bug Fixes

* allow unlimited footprint points and increase buffer size for simplifying capture area json ([#872](https://github.com/linz/topo-imagery/issues/872)) ([c733f1e](https://github.com/linz/topo-imagery/commit/c733f1e5dceb40244c8a35452f8bbd59bdd8f50c))

## [4.2.1](https://github.com/linz/topo-imagery/compare/v4.2.0...v4.2.1) (2024-02-19)


### Bug Fixes

* always ignore existing overviews TDE-1046 ([#862](https://github.com/linz/topo-imagery/issues/862)) ([900907f](https://github.com/linz/topo-imagery/commit/900907f96066564eac4cc7830616f6ed31ee60d4))

## [4.2.0](https://github.com/linz/topo-imagery/compare/v4.1.0...v4.2.0) (2024-02-19)


### Features

* save a copy of capture-area.geojson as an artifact for Argo Workflows TDE-1045 ([#860](https://github.com/linz/topo-imagery/issues/860)) ([a303c05](https://github.com/linz/topo-imagery/commit/a303c05448445281c8168a0614ea150b891221b9))

## [4.1.0](https://github.com/linz/topo-imagery/compare/v4.0.1...v4.1.0) (2024-02-14)


### Features

* add capture-area.geojson to the STAC Collection TDE-965 ([#758](https://github.com/linz/topo-imagery/issues/758)) ([75df081](https://github.com/linz/topo-imagery/commit/75df081ac23e340cce1479a2e2de76b6c1e40e73))


### Bug Fixes

* gdal should try reading file before getting credentials TDE-929 ([#852](https://github.com/linz/topo-imagery/issues/852)) ([83c9a68](https://github.com/linz/topo-imagery/commit/83c9a680868649bf458636d2727889a3eaf27c41))


### Documentation

* clarify readme ([#854](https://github.com/linz/topo-imagery/issues/854)) ([f0f742d](https://github.com/linz/topo-imagery/commit/f0f742dedcdbaf91f7fa3eb696ccc319b48a3bbe))

## [4.0.1](https://github.com/linz/topo-imagery/compare/v4.0.0...v4.0.1) (2024-02-12)


### Bug Fixes

* handle 50k imagery filenames TDE-1014 ([#845](https://github.com/linz/topo-imagery/issues/845)) ([07a7af5](https://github.com/linz/topo-imagery/commit/07a7af50c915a39e0108e87b66eb8837fd8a6e77))

## [4.0.0](https://github.com/linz/topo-imagery/compare/v3.6.0...v4.0.0) (2024-02-08)


### ⚠ BREAKING CHANGES

* add new fields to the Collection TDE-985 ([#765](https://github.com/linz/topo-imagery/issues/765))

### Features

* accept only hyphen named categories TDE-985 ([#830](https://github.com/linz/topo-imagery/issues/830)) ([26682c8](https://github.com/linz/topo-imagery/commit/26682c83565fa400b61378caedc15b50cbe3aabc))
* add new fields to the Collection TDE-985 ([#765](https://github.com/linz/topo-imagery/issues/765)) ([78016f6](https://github.com/linz/topo-imagery/commit/78016f6b6e01de1b3132e12ebeaf431da61537c2))


### Bug Fixes

* Disable duplicate code test ([#817](https://github.com/linz/topo-imagery/issues/817)) ([cde875d](https://github.com/linz/topo-imagery/commit/cde875dc730011165b73848338a700394eccdb4b))
* NoSuchFileError is stopping multiprocessing sidecar files TDE-1007 ([#832](https://github.com/linz/topo-imagery/issues/832)) ([dea3189](https://github.com/linz/topo-imagery/commit/dea3189b9afbb198e02888ed6ef9ebb17687a000))
* sidecars download permissions TDE-1007 ([#806](https://github.com/linz/topo-imagery/issues/806)) ([16b5b04](https://github.com/linz/topo-imagery/commit/16b5b0472d10f0ec9f0a3a6689af9e1edfcb7fda))
* write_file was not handling exception correctly TDE-1007 ([#836](https://github.com/linz/topo-imagery/issues/836)) ([caa289b](https://github.com/linz/topo-imagery/commit/caa289b240989f860f66412c0d028752ec1a17d9))

## [3.6.0](https://github.com/linz/topo-imagery/compare/v3.5.2...v3.6.0) (2024-01-09)


### Features

* Remove empty TIFFs after standardising TDE-964 ([#767](https://github.com/linz/topo-imagery/issues/767)) ([70d79b3](https://github.com/linz/topo-imagery/commit/70d79b3d55678fd0a6fc6145005094eab27962b2))

## [3.5.2](https://github.com/linz/topo-imagery/compare/v3.5.1...v3.5.2) (2023-12-21)


### Bug Fixes

* minor changes to be consistent with current data ([#790](https://github.com/linz/topo-imagery/issues/790)) ([4892b6b](https://github.com/linz/topo-imagery/commit/4892b6b30dfc5cb7cc3a00a5eef52b6fde8447ee))

## [3.5.1](https://github.com/linz/topo-imagery/compare/v3.5.0...v3.5.1) (2023-12-19)


### Bug Fixes

* typo in prod ([#788](https://github.com/linz/topo-imagery/issues/788)) ([275a665](https://github.com/linz/topo-imagery/commit/275a6658f2144f2a4cf2a690a2ea2b701aafc44b))

## [3.5.0](https://github.com/linz/topo-imagery/compare/v3.4.0...v3.5.0) (2023-12-19)


### Features

* Dependabot for Docker TDE-963 ([#746](https://github.com/linz/topo-imagery/issues/746)) ([250b82c](https://github.com/linz/topo-imagery/commit/250b82c196c1f3db601e9712d6834d6da28e6952))
* Pin Docker image TDE-958 ([#744](https://github.com/linz/topo-imagery/issues/744)) ([de8a129](https://github.com/linz/topo-imagery/commit/de8a129d60bb7fc16f7872542ee93bc3ce3c9570))
* title and description by arguments TDE-960 ([#757](https://github.com/linz/topo-imagery/issues/757)) ([dd3e282](https://github.com/linz/topo-imagery/commit/dd3e282660cc0e652667adf54fe3e5ad3b0b0bea))


### Documentation

* add explaination about collection provider tests ([#764](https://github.com/linz/topo-imagery/issues/764)) ([4e84901](https://github.com/linz/topo-imagery/commit/4e84901abe30ca0294ae570caef7fba511fe0ce5))

## [3.4.0](https://github.com/linz/topo-imagery/compare/v3.3.1...v3.4.0) (2023-11-23)


### Features

* force LERC overview max Z error threshold to 0.1 (10cm) TDE-873 ([#740](https://github.com/linz/topo-imagery/issues/740)) ([0924c13](https://github.com/linz/topo-imagery/commit/0924c132fd01221cb0467cba2126dbc8ba80b269))
* lint GitHub Actions workflows TDE-919 ([#720](https://github.com/linz/topo-imagery/issues/720)) ([1d32588](https://github.com/linz/topo-imagery/commit/1d325881607c69022dec6c93e178f85e9e05705e))
* Pin actions to hashes ([#729](https://github.com/linz/topo-imagery/issues/729)) ([e2343d5](https://github.com/linz/topo-imagery/commit/e2343d5f1959e71d3634f134cd7d61c1447ab261))

## [3.3.1](https://github.com/linz/topo-imagery/compare/v3.3.0...v3.3.1) (2023-10-04)


### Bug Fixes

* typo in readme ([#682](https://github.com/linz/topo-imagery/issues/682)) ([544d271](https://github.com/linz/topo-imagery/commit/544d271cf48120574ac43edc40d5ef91e34b49c7))
* upgrade gdal to 3.7.2 for webp fix ([#677](https://github.com/linz/topo-imagery/issues/677)) ([bdb4802](https://github.com/linz/topo-imagery/commit/bdb48021c7e3b66d85840a23c688b4737298e949))

## [3.3.0](https://github.com/linz/topo-imagery/compare/v3.2.1...v3.3.0) (2023-09-26)


### Features

* script to convert ascii files TDE-814 ([#595](https://github.com/linz/topo-imagery/issues/595)) ([5875d53](https://github.com/linz/topo-imagery/commit/5875d53c2b68f9d661a42f012deb7bbdb639ffe3))

## [3.2.1](https://github.com/linz/topo-imagery/compare/v3.2.0...v3.2.1) (2023-09-14)


### Bug Fixes

* recreate webp overviews TDE-869 ([#650](https://github.com/linz/topo-imagery/issues/650)) ([c1f265a](https://github.com/linz/topo-imagery/commit/c1f265a451ed495874bc7cc70c5cca7182a896ad))

## [3.2.0](https://github.com/linz/topo-imagery/compare/v3.1.0...v3.2.0) (2023-09-08)


### Features

* provide content type to S3 objects TDE-859 ([#642](https://github.com/linz/topo-imagery/issues/642)) ([bbbd653](https://github.com/linz/topo-imagery/commit/bbbd653de36bd8105ec11a9a01314adad60f8f05))


### Bug Fixes

* gdal should not create bigtiff TDE-805 ([#632](https://github.com/linz/topo-imagery/issues/632)) ([b33825f](https://github.com/linz/topo-imagery/commit/b33825fdaecebe64500bac74c96adf3e07a1f302))
* re-standardising TileByteCounts error TDE-850 ([#644](https://github.com/linz/topo-imagery/issues/644)) ([c762202](https://github.com/linz/topo-imagery/commit/c762202d49b09e1b8c538b0aa3fd7c6fed485e3c))
* storing count is not used TDE-842 ([#633](https://github.com/linz/topo-imagery/issues/633)) ([8cfc405](https://github.com/linz/topo-imagery/commit/8cfc405a712d54273f90ec223cc7c7ffc22bce68))

## [3.1.0](https://github.com/linz/topo-imagery/compare/v3.0.1...v3.1.0) (2023-08-29)


### Features

* download files using multithreading TDE-822 ([#580](https://github.com/linz/topo-imagery/issues/580)) ([8ab269d](https://github.com/linz/topo-imagery/commit/8ab269de0a06f735039029e53318552341a487ad))
* thumbnails creation TDE-839 ([#616](https://github.com/linz/topo-imagery/issues/616)) ([8e2028f](https://github.com/linz/topo-imagery/commit/8e2028f1ea340b9712ac6d00ed8b56980589def5))

## [3.0.1](https://github.com/linz/topo-imagery/compare/v3.0.0...v3.0.1) (2023-08-10)


### Bug Fixes

* gdalbuildvrt fails when coordinate system description is different TDE-818 ([#596](https://github.com/linz/topo-imagery/issues/596)) ([5758400](https://github.com/linz/topo-imagery/commit/575840018ced624ba8e4b179c7068b59461f975b))
* non-visual QA greyscale TDE-832 ([#593](https://github.com/linz/topo-imagery/issues/593)) ([afe25f3](https://github.com/linz/topo-imagery/commit/afe25f38c61ea671fa1942c1a1cdab9be3dba6f0))
* standardised path is not logged when non_visual_qa_passed ([#591](https://github.com/linz/topo-imagery/issues/591)) ([0c19104](https://github.com/linz/topo-imagery/commit/0c1910493a2952f21abe19d7d8df5ae5d43bcccf))
* stats are not written when retiling TDE-829 ([#599](https://github.com/linz/topo-imagery/issues/599)) ([c4bf5f2](https://github.com/linz/topo-imagery/commit/c4bf5f2fc78e66177b459b1e9482bc830b45a59a))


### Documentation

* comment to explain why extent is specified ([#584](https://github.com/linz/topo-imagery/issues/584)) ([1971bc2](https://github.com/linz/topo-imagery/commit/1971bc2a5d1cd85c7f26b6b424b01249686888b4))

## [3.0.0](https://github.com/linz/topo-imagery/compare/v2.2.1...v3.0.0) (2023-07-25)


### ⚠ BREAKING CHANGES

* standardise_validate should allow 1 output from multiple inputs TDE-784 ([#557](https://github.com/linz/topo-imagery/issues/557))

### Features

* standardise_validate allows passing a json file as input TDE-823 ([#564](https://github.com/linz/topo-imagery/issues/564)) ([ebd3e8e](https://github.com/linz/topo-imagery/commit/ebd3e8e00098d145371d8be240e9a97a7cffe2c1))
* standardise_validate should allow 1 output from multiple inputs TDE-784 ([#557](https://github.com/linz/topo-imagery/issues/557)) ([d0ddbbb](https://github.com/linz/topo-imagery/commit/d0ddbbba3d161f3e9249f45eaadd072d8b3810b8))


### Bug Fixes

* AREA_OR_POINT should be forced to AREA for DEMs TDE-787 ([#537](https://github.com/linz/topo-imagery/issues/537)) ([3b92a21](https://github.com/linz/topo-imagery/commit/3b92a21d070b9aabb77c6bbd27b7a9b646e97897))


### Reverts

* "revert: "chore: upgrade gdal from 3.6.1 to 3.7.0 ([#479](https://github.com/linz/topo-imagery/issues/479))" ([#536](https://github.com/linz/topo-imagery/issues/536))" ([#544](https://github.com/linz/topo-imagery/issues/544)) ([ca824f9](https://github.com/linz/topo-imagery/commit/ca824f91b57f4f245c9813928d4845f63fd9c1c6))

## [2.2.1](https://github.com/linz/topo-imagery/compare/v2.2.0...v2.2.1) (2023-07-12)


### Bug Fixes

* create a new release please PR to fix bug ([#548](https://github.com/linz/topo-imagery/issues/548)) ([c809721](https://github.com/linz/topo-imagery/commit/c8097217c318a04875d5918ce474552a4e4a3e93))

## [2.2.0](https://github.com/linz/topo-imagery/compare/v2.1.0...v2.2.0) (2023-07-12)


### Features

* handle standardising paletted tiffs ([#547](https://github.com/linz/topo-imagery/issues/547)) ([aa6ce05](https://github.com/linz/topo-imagery/commit/aa6ce05a7737f34bbaf5287e47e39e34474a01e7))


### Reverts

* "chore: upgrade gdal from 3.6.1 to 3.7.0 ([#479](https://github.com/linz/topo-imagery/issues/479))" ([#536](https://github.com/linz/topo-imagery/issues/536)) ([810b73c](https://github.com/linz/topo-imagery/commit/810b73c566e482b3caf29a73c1ffaccc32a6a1b4))

## [2.1.0](https://github.com/linz/topo-imagery/compare/v2.0.0...v2.1.0) (2023-07-04)


### Features

* add --producer-list to allow multiple producers TDE-781 ([#531](https://github.com/linz/topo-imagery/issues/531)) ([0a28d6f](https://github.com/linz/topo-imagery/commit/0a28d6f6f00deae2841d088f9b6a99bfdb437b14))
* add dem_lerc  preset TDE-779 ([#522](https://github.com/linz/topo-imagery/issues/522)) ([3e7378d](https://github.com/linz/topo-imagery/commit/3e7378d1506a5884b7151a29f6dd3a7281c3650a))


### Bug Fixes

* handle already existing collection JSON ([#532](https://github.com/linz/topo-imagery/issues/532)) ([7a26bae](https://github.com/linz/topo-imagery/commit/7a26bae03d8b2d9090cfb8dfb24d42473a0b2b62))
* standardising_validate.py fails when scale is 'None' ([#480](https://github.com/linz/topo-imagery/issues/480)) ([17296f1](https://github.com/linz/topo-imagery/commit/17296f1e0ffbb46d5160814ca6096d4c5893c996))


### Documentation

* add missing docstring ([#487](https://github.com/linz/topo-imagery/issues/487)) ([dd27c7c](https://github.com/linz/topo-imagery/commit/dd27c7c3f7209e58416e5e517498b0b68e7b3ca5))
* update docstring for tile_index.py ([#473](https://github.com/linz/topo-imagery/issues/473)) ([38ef275](https://github.com/linz/topo-imagery/commit/38ef275c304164c990675837cbba83076f80e512))
* update README release please instructions ([#496](https://github.com/linz/topo-imagery/issues/496)) ([d7369e0](https://github.com/linz/topo-imagery/commit/d7369e096b7d782e8f97bca10b6b384b70f33f89))
* update README.md ([#481](https://github.com/linz/topo-imagery/issues/481)) ([79add3c](https://github.com/linz/topo-imagery/commit/79add3cd3cd3fb8f5d75ba7a8ca2029145fd0b5a))

## [2.0.0](https://github.com/linz/topo-imagery/compare/v1.3.0...v2.0.0) (2023-04-18)


### ⚠ BREAKING CHANGES

* resume standardise validate TDE-710 ([#444](https://github.com/linz/topo-imagery/issues/444))

### Features

* fs.exists() checks if path exists TDE-710 ([#441](https://github.com/linz/topo-imagery/issues/441)) ([f79bd7a](https://github.com/linz/topo-imagery/commit/f79bd7a8b1ea7ef950479a3638595662f3417ed6))
* resume standardise validate TDE-710 ([#444](https://github.com/linz/topo-imagery/issues/444)) ([b4022a5](https://github.com/linz/topo-imagery/commit/b4022a509dc7d92e8d10eb384fa1b3408c45463e))


### Bug Fixes

* fs_local.write() fails when directory does not exist ([#445](https://github.com/linz/topo-imagery/issues/445)) ([935a041](https://github.com/linz/topo-imagery/commit/935a0419ee7c550793088c279e060d315bf8dad9))
* fs_s3.read() exceptions are not caught properly ([#432](https://github.com/linz/topo-imagery/issues/432)) ([3a855d5](https://github.com/linz/topo-imagery/commit/3a855d55f9a59bfe2d081835663b18b574380faa))
* unescaped bracket ([#426](https://github.com/linz/topo-imagery/issues/426)) ([f579638](https://github.com/linz/topo-imagery/commit/f57963854d0d3f61585055d2fbc5e3174f7948ea))

## [1.3.0](https://github.com/linz/topo-imagery/compare/v1.2.1...v1.3.0) (2023-03-29)


### Features

* deploy containers to ecr TDE-689 ([#408](https://github.com/linz/topo-imagery/issues/408)) ([31c713c](https://github.com/linz/topo-imagery/commit/31c713c9d5b7336f6af408e8a3bd6d592db9f831))


### Bug Fixes

* add latest to tag ([#416](https://github.com/linz/topo-imagery/issues/416)) ([82645ec](https://github.com/linz/topo-imagery/commit/82645ec3432b7f141a9f3af672b4d1aef2a46e68))
* add permissions ([#414](https://github.com/linz/topo-imagery/issues/414)) ([d05aa10](https://github.com/linz/topo-imagery/commit/d05aa1008eb51b8646f74fee675d56d4cbbfc9e9))
* update permissions ([#415](https://github.com/linz/topo-imagery/issues/415)) ([71c3fe9](https://github.com/linz/topo-imagery/commit/71c3fe9434209c2f87c333fe2323569a9d24d6a9))
* use multithreading for gdalwarp when creating COGS TDE-696 ([#399](https://github.com/linz/topo-imagery/issues/399)) ([061d3d6](https://github.com/linz/topo-imagery/commit/061d3d67bdb7a7385ffd84b0d060edde0010bd8c))

## [1.2.1](https://github.com/linz/topo-imagery/compare/v1.2.0...v1.2.1) (2023-03-08)


### Bug Fixes

* trailing char in local path is removed ([#389](https://github.com/linz/topo-imagery/issues/389)) ([604e591](https://github.com/linz/topo-imagery/commit/604e5911a7821d299cd6a2b5dc92176e4559a5eb))


### Documentation

* improve documentation about release process ([#362](https://github.com/linz/topo-imagery/issues/362)) ([d85653e](https://github.com/linz/topo-imagery/commit/d85653eec0ab254db15a86b1d3aad72a41e13083))

## [1.2.0](https://github.com/linz/topo-imagery/compare/v1.1.0...v1.2.0) (2023-03-01)


### Features

* make scale optional ([#372](https://github.com/linz/topo-imagery/issues/372)) ([20218bd](https://github.com/linz/topo-imagery/commit/20218bd3edc1af6113be1a917e6a7080525a5891))
* take source and target epsg, if not the same transform TDE-699 ([#375](https://github.com/linz/topo-imagery/issues/375)) ([547ec88](https://github.com/linz/topo-imagery/commit/547ec88871236c3df674d08a3f75c37c6c0e14c5))


### Bug Fixes

* be specific about nodata being None ([#363](https://github.com/linz/topo-imagery/issues/363)) ([8fe8211](https://github.com/linz/topo-imagery/commit/8fe82113d3f027e46364ecf33cd0ede5271c70ba))
* remove no data value (255) ensure is not none ([#360](https://github.com/linz/topo-imagery/issues/360)) ([a1154e8](https://github.com/linz/topo-imagery/commit/a1154e892053a6f15ef6b5c030d69ca261d95e39))

## [1.1.0](https://github.com/linz/topo-imagery/compare/v1.0.0...v1.1.0) (2023-02-15)


### Features

* add multiple STAC licensors TDE-643 ([#355](https://github.com/linz/topo-imagery/issues/355)) ([001b9fc](https://github.com/linz/topo-imagery/commit/001b9fc39264d062b302fe9cb15a89d1668066ca))

## [1.0.0](https://github.com/linz/topo-imagery/compare/v0.4.1...v1.0.0) (2023-02-13)


### ⚠ BREAKING CHANGES

* stac providers TDE-623 ([#348](https://github.com/linz/topo-imagery/issues/348))

### Features

* stac providers TDE-623 ([#348](https://github.com/linz/topo-imagery/issues/348)) ([9bc71a4](https://github.com/linz/topo-imagery/commit/9bc71a47492b9387acf337f738cad594f0c7586b))

## [0.4.1](https://github.com/linz/topo-imagery/compare/v0.4.0...v0.4.1) (2023-02-09)


### Features

* convert nodata to alpha TDE-625 ([#342](https://github.com/linz/topo-imagery/issues/342)) ([6710aea](https://github.com/linz/topo-imagery/commit/6710aea24306f5e651480e96215fdb447fe9aab8))


### Bug Fixes

* gdal info reference wrong file ([#347](https://github.com/linz/topo-imagery/issues/347)) ([52a2ee7](https://github.com/linz/topo-imagery/commit/52a2ee7354e939ed93b44f3b3d1d537e1d337d92))
* log wrong vsis3 path non visual qa TDE-563 ([#343](https://github.com/linz/topo-imagery/issues/343)) ([388ae19](https://github.com/linz/topo-imagery/commit/388ae1936782c6bf71b980efce9a739f2671c519))

## [0.4.0](https://github.com/linz/topo-imagery/compare/v0.3.0...v0.4.0) (2023-02-07)


### Features

* standardising 16bits TIFF TDE-628 ([#333](https://github.com/linz/topo-imagery/issues/333)) ([1a07683](https://github.com/linz/topo-imagery/commit/1a07683ece05da6dbafc46c03ca32f666e0e9627))


### Bug Fixes

* non visual qa errors logged twice TDE-563 ([#320](https://github.com/linz/topo-imagery/issues/320)) ([41c4c98](https://github.com/linz/topo-imagery/commit/41c4c98aa5ef0cfbf4bf28632bb07c1b5d398e9d))


### Documentation

* add versioning release section in readme ([#334](https://github.com/linz/topo-imagery/issues/334)) ([7ad502c](https://github.com/linz/topo-imagery/commit/7ad502c11c0ef8130beef3719fb0fb87852a16d8))

## [0.3.0](https://github.com/linz/topo-imagery/compare/v0.2.0...v0.3.0) (2023-01-19)


### Features

* add gray_webp preset TDE-482 ([#149](https://github.com/linz/topo-imagery/issues/149)) ([396dc16](https://github.com/linz/topo-imagery/commit/396dc16a5c6baf282c5f9c45ba994e7920b20a78))
* add standardising script (TDE-303) ([#23](https://github.com/linz/topo-imagery/issues/23)) ([fd60e53](https://github.com/linz/topo-imagery/commit/fd60e53eb8748c47cb27bf15270602562b7a8cf0))
* allow Create Polygons script to run with multiple files ([#48](https://github.com/linz/topo-imagery/issues/48)) ([8372cc7](https://github.com/linz/topo-imagery/commit/8372cc713d1cdd6d03cd629cc5c608d9bda24ba2))
* apply a cutline if supplied ([#240](https://github.com/linz/topo-imagery/issues/240)) ([13688d8](https://github.com/linz/topo-imagery/commit/13688d81e35ec86f267863f0b8619f75cb99e6f8))
* automatically refresh role assumptions ([#106](https://github.com/linz/topo-imagery/issues/106)) ([40e4b52](https://github.com/linz/topo-imagery/commit/40e4b52d303e693bfedb846e7d9e572609345926))
* cog output ([#60](https://github.com/linz/topo-imagery/issues/60)) ([38ef527](https://github.com/linz/topo-imagery/commit/38ef527b04061fb202985c9fedfe6eb73e47ac6e))
* create collection TDE-453 ([#177](https://github.com/linz/topo-imagery/issues/177)) ([20f5f34](https://github.com/linz/topo-imagery/commit/20f5f348222119e92cff2f45e7756ae668957688))
* create polygon script return temporary file path ([#47](https://github.com/linz/topo-imagery/issues/47)) ([34c210a](https://github.com/linz/topo-imagery/commit/34c210a6a1dc97d940998271dfe5f37f15d5d52b))
* create stac items TDE-452 ([#133](https://github.com/linz/topo-imagery/issues/133)) ([47e966a](https://github.com/linz/topo-imagery/commit/47e966a675f40a9da578fbbabb612f9dc0e672f1))
* create_polygons destination can be a full s3 path ([#15](https://github.com/linz/topo-imagery/issues/15)) ([d276baa](https://github.com/linz/topo-imagery/commit/d276baac6c204f65d1d06c27d5cd00b52091b58f))
* enable list source TDE-411 ([#36](https://github.com/linz/topo-imagery/issues/36)) ([c676b20](https://github.com/linz/topo-imagery/commit/c676b2031d080411ca66880b6811a135e1358497))
* File System Abstraction local/AWS TDE-407 ([#69](https://github.com/linz/topo-imagery/issues/69)) ([b4f035e](https://github.com/linz/topo-imagery/commit/b4f035e99bfe12ba8d72af6125ff2e05072dcf11))
* gdal concurrency TDE-457 ([#96](https://github.com/linz/topo-imagery/issues/96)) ([3f4a3be](https://github.com/linz/topo-imagery/commit/3f4a3bed092acee463cbdfed2efbc64d1c583cff))
* initialise collection stac TDE-453 ([#132](https://github.com/linz/topo-imagery/issues/132)) ([8c542d5](https://github.com/linz/topo-imagery/commit/8c542d547a0258115f886d5e7b38818f99e6850e))
* log pretty formatted gdalinfo in non visual qa logs TDE-563 ([#214](https://github.com/linz/topo-imagery/issues/214)) ([58d4cd2](https://github.com/linz/topo-imagery/commit/58d4cd27ea6348507fbf98a460dc43545a2ad9e2))
* log standardised image gdal virtual path when non visual qa error TDE-563 ([#239](https://github.com/linz/topo-imagery/issues/239)) ([e121df8](https://github.com/linz/topo-imagery/commit/e121df83acf044c80de5f945d030ff70eb8166eb))
* log the gdal version when run standardising TDE-559 ([#210](https://github.com/linz/topo-imagery/issues/210)) ([d458732](https://github.com/linz/topo-imagery/commit/d458732a5bc891d82568c483081e3dca5e94cbba))
* logs hostname and execution time TDE-431 ([#77](https://github.com/linz/topo-imagery/issues/77)) ([abb6634](https://github.com/linz/topo-imagery/commit/abb663435c670c2e3e7d87dccbf348366925806c))
* non visual qa log original tiff path TDE-563 ([#241](https://github.com/linz/topo-imagery/issues/241)) ([6320cc9](https://github.com/linz/topo-imagery/commit/6320cc94d8ee9ae6c86a18a5986233e27187575a))
* Non Visual QA script (TDE-309) ([#40](https://github.com/linz/topo-imagery/issues/40)) ([8411779](https://github.com/linz/topo-imagery/commit/8411779a6bb8875e3c17268587cfbe1ee264af4c))
* optimise cutline handling by only using the cutline if required ([#258](https://github.com/linz/topo-imagery/issues/258)) ([5000a65](https://github.com/linz/topo-imagery/commit/5000a65f7516a9a934fdd0937a71d1f5aeebf2b4))
* rename tiff file if not aligned with its tile name TDE-497 ([#209](https://github.com/linz/topo-imagery/issues/209)) ([7e547d6](https://github.com/linz/topo-imagery/commit/7e547d6deee18355f64703f39026087e8401b9f3))
* run standardising step on a list of files (TDE-412) ([#35](https://github.com/linz/topo-imagery/issues/35)) ([c119a56](https://github.com/linz/topo-imagery/commit/c119a561ed1cb1830f85f67a4152d37df963dd5e))
* standardise following by non visual QA check TDE-450 ([#90](https://github.com/linz/topo-imagery/issues/90)) ([ee8227d](https://github.com/linz/topo-imagery/commit/ee8227d074c87981e2b3c776364e7c79824f1ad0))
* switch between two gdal presets "lzw" or "webp" ([#108](https://github.com/linz/topo-imagery/issues/108)) ([9483f51](https://github.com/linz/topo-imagery/commit/9483f51ac81fcae3e2d57dd5278c3f3ae7141e4f))
* tde-421 remove destination arguments ([#61](https://github.com/linz/topo-imagery/issues/61)) ([ba69fea](https://github.com/linz/topo-imagery/commit/ba69fea3df9cafe01c57a7564f0e4c16f6d2fc08))
* update stac collection TDE-453 ([#134](https://github.com/linz/topo-imagery/issues/134)) ([9127002](https://github.com/linz/topo-imagery/commit/9127002151b664235de548aa87492849b798187b))
* upgrade to stable GDAL v3.6 TDE-565 ([#217](https://github.com/linz/topo-imagery/issues/217)) ([786b11e](https://github.com/linz/topo-imagery/commit/786b11e6e53eba821fd2a1e1375153a595e059ee))
* use a fixed version of osgeo/gdal container TDE-555 ([#204](https://github.com/linz/topo-imagery/issues/204)) ([e6837ec](https://github.com/linz/topo-imagery/commit/e6837ec7de37239585c39d6b1b7a17d9dffe588b))
* write processed file paths in tmp/file_list.json ([#50](https://github.com/linz/topo-imagery/issues/50)) ([5387093](https://github.com/linz/topo-imagery/commit/5387093c3707ed3601ef7a135a105259634a121b))


### Bug Fixes

* --cutline is not required ([#244](https://github.com/linz/topo-imagery/issues/244)) ([9fcb901](https://github.com/linz/topo-imagery/commit/9fcb9011774a09014cc7cc3ed76db88f39d992d5))
* a couple of bugs in get_session_credentials ([#120](https://github.com/linz/topo-imagery/issues/120)) ([d6372e7](https://github.com/linz/topo-imagery/commit/d6372e7bd6ede4a178e598cf4ef97e11c1803a54))
* accept preset arg standardise-validate ([#119](https://github.com/linz/topo-imagery/issues/119)) ([aa86be8](https://github.com/linz/topo-imagery/commit/aa86be85b82583cd5c337b24f6be2f80f0e37d06))
* add 'certifi' lib to temporary fix poetry install issue TDE-451 ([#88](https://github.com/linz/topo-imagery/issues/88)) ([0dd3ea7](https://github.com/linz/topo-imagery/commit/0dd3ea77e0f8b40e19010b50b65476b1c653814e))
* append to a temporary command list ([#110](https://github.com/linz/topo-imagery/issues/110)) ([6527603](https://github.com/linz/topo-imagery/commit/6527603c2a780f2c7fe3248be13a497062bc3b88))
* argument source was not correctly set ([#49](https://github.com/linz/topo-imagery/issues/49)) ([44ff66f](https://github.com/linz/topo-imagery/commit/44ff66f62586d3c3beb99360e17908a386e596e9))
* boto3 sessions need to create resources not clients ([#245](https://github.com/linz/topo-imagery/issues/245)) ([3cee053](https://github.com/linz/topo-imagery/commit/3cee053667de9659d2297429ea588fed6ef1c7f0))
* collection title escaped unicode TDE-594 ([#288](https://github.com/linz/topo-imagery/issues/288)) ([a679042](https://github.com/linz/topo-imagery/commit/a679042707511e4e2fdd656a91ebc49d92a16093))
* correct type imports ([#261](https://github.com/linz/topo-imagery/issues/261)) ([78e55eb](https://github.com/linz/topo-imagery/commit/78e55ebef8515881c37090b53079569c0d34fafc))
* download sidecar files like tfw and prj ([#246](https://github.com/linz/topo-imagery/issues/246)) ([b8bb95a](https://github.com/linz/topo-imagery/commit/b8bb95adc0ed18c25bebe1aaac1146b88e12aba0))
* Elastic Search is expecting an object in 'source' ([#156](https://github.com/linz/topo-imagery/issues/156)) ([8b9503b](https://github.com/linz/topo-imagery/commit/8b9503b10527b64074ef7ff28f7378a47bac0c5d))
* force a alpha band on all imagery if a cutline is present ([#264](https://github.com/linz/topo-imagery/issues/264)) ([dab4565](https://github.com/linz/topo-imagery/commit/dab4565ca058a857865f96bf88eff83bb10b63cb))
* GDAL error was not logged when command run fails ([#52](https://github.com/linz/topo-imagery/issues/52)) ([01d941e](https://github.com/linz/topo-imagery/commit/01d941e0895f47b20560c4b1b8b69f5a007822c7))
* geometry, bbox and asset type TDE-502 TDE-520 ([#185](https://github.com/linz/topo-imagery/issues/185)) ([0229df8](https://github.com/linz/topo-imagery/commit/0229df85f81714407cbbc15727b856de612f23b1))
* keep temporary files so they are pushed to the artifact bucket ([#66](https://github.com/linz/topo-imagery/issues/66)) ([86b8c3a](https://github.com/linz/topo-imagery/commit/86b8c3ae49de908a16e7e8907bd78729b354326f))
* log gdal stderr instead of raising an exception TDE-557 ([#203](https://github.com/linz/topo-imagery/issues/203)) ([4032145](https://github.com/linz/topo-imagery/commit/4032145b32b1bacceb721d9ad336ed678e6094af))
* log Non Visual QA error report in a JSON format ([#55](https://github.com/linz/topo-imagery/issues/55)) ([ed4d623](https://github.com/linz/topo-imagery/commit/ed4d623ad3894722f4e6a27455e8af3451efdde2))
* make cutline value optional TDE-602 ([#292](https://github.com/linz/topo-imagery/issues/292)) ([cfa20cf](https://github.com/linz/topo-imagery/commit/cfa20cff9a70baf2713518a5f3781aa18e8db995))
* not logging source as a list of string ([#116](https://github.com/linz/topo-imagery/issues/116)) ([a871935](https://github.com/linz/topo-imagery/commit/a8719359a874f2f654d1ed09d7e1b4c69dbf10c2))
* release-please.yml fails prettier ([#307](https://github.com/linz/topo-imagery/issues/307)) ([330fa04](https://github.com/linz/topo-imagery/commit/330fa04c609f4996bac1c77701aaca5305ed1f45))
* retry upto 3 times when InvalidIdentityTokenException happens ([#115](https://github.com/linz/topo-imagery/issues/115)) ([e27f2d0](https://github.com/linz/topo-imagery/commit/e27f2d0db836caf1cd8fc2c24f435f5fd766adc0))
* skip files which are not tiff ([#53](https://github.com/linz/topo-imagery/issues/53)) ([90396a6](https://github.com/linz/topo-imagery/commit/90396a6347d931f1f5e1c3abd16ae1ff6f86ea28))
* skip non visual qa if no file has been standardised ([#97](https://github.com/linz/topo-imagery/issues/97)) ([25a85c1](https://github.com/linz/topo-imagery/commit/25a85c1fbc8794bc410760577af051cc285ef079))
* specify and check bands TDE-533 ([#196](https://github.com/linz/topo-imagery/issues/196)) ([d4e512f](https://github.com/linz/topo-imagery/commit/d4e512fa3e91c7daaacd4348763d494933c5c6d3))
* support 1 band palleted grey scale TDE-601 ([#269](https://github.com/linz/topo-imagery/issues/269)) ([d2327a0](https://github.com/linz/topo-imagery/commit/d2327a0c8507d044c962c34b87b3ea33168941e2))
* suppress aux xml file creation ([#121](https://github.com/linz/topo-imagery/issues/121)) ([c674366](https://github.com/linz/topo-imagery/commit/c674366a7062c81271830975cc3b750b2fafa82d))
* TDE-454 remove `standardise` from file name ([#92](https://github.com/linz/topo-imagery/issues/92)) ([099df34](https://github.com/linz/topo-imagery/commit/099df340ce6bb00ae199524893f5f3ef8a62350d))
* tidy up geometry and bbox TDE-522 ([#227](https://github.com/linz/topo-imagery/issues/227)) ([02b06b5](https://github.com/linz/topo-imagery/commit/02b06b51a58650ffbe1a18a4bedd4996251c6c16))
* use $AWS_ROLE_CONFIG_PATH to be consistent ([#109](https://github.com/linz/topo-imagery/issues/109)) ([d1fff0d](https://github.com/linz/topo-imagery/commit/d1fff0d7be08a5475f99d7fa85e3489fe69469a2))
