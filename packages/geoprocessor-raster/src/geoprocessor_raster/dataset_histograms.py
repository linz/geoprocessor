import hashlib
import io
import json
import os
import re
from collections.abc import Iterable
from functools import partial
from multiprocessing import Pool

import numpy as np
from geoprocessor_common.aws.aws_helper import is_s3
from geoprocessor_common.files.fs import list_file_names, list_file_sizes, read, write
from geoprocessor_gdal.gdal.gdal_histograms import (
    BAND_NAMES,
    SAMPLE_CACHE_MIN_MB,
    SAMPLE_SIZE,
    Histograms,
    get_histograms,
)
from linz_logger import get_log

HISTOGRAM_FILE_VERSION = 1
HISTOGRAM_FILE_SUFFIX = ".npz"
HISTOGRAM_FILE_HASH_LENGTH = 12
# GDAL block cache shared by the workers
SAMPLE_CACHE_BUDGET_MB = 4096


def get_histogram_file_name(source: str) -> str:
    """Get the name of the histogram file of a source: its file name and a hash of its full path.

    Args:
        source: path to the source TIFF

    Returns:
        the histogram file name

    Examples:
        >>> get_histogram_file_name("s3://bucket/BQ25_1000_0101.tiff")
        'BQ25_1000_0101.tiff.5a82fdd96e42.npz'
    """
    digest = hashlib.sha256(source.encode()).hexdigest()[:HISTOGRAM_FILE_HASH_LENGTH]
    # Safe in s3 keys and within the 255 byte limit of local file names
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(source))[:200]
    return f"{name}.{digest}{HISTOGRAM_FILE_SUFFIX}"


def histograms_to_bytes(source: str, histograms: Histograms, sample_size: int = SAMPLE_SIZE) -> bytes:
    """Serialise the histograms of a source to a compressed `.npz` file.

    Args:
        source: path to the source TIFF
        histograms: value counts of the bands and of their luminance
        sample_size: maximum width and height the source was sampled at

    Returns:
        the `.npz` file content
    """
    metadata = {
        "version": HISTOGRAM_FILE_VERSION,
        "source": source,
        "bands": BAND_NAMES[len(histograms.bands)],
        "sampleSize": sample_size,
    }
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer, histograms=histograms.bands, luminance=histograms.luminance, metadata=np.array(json.dumps(metadata))
    )
    return buffer.getvalue()


def histograms_from_bytes(data: bytes, source: str) -> Histograms:
    """Read the histograms of a source from a `.npz` file.

    Args:
        data: the `.npz` file content
        source: path to the source TIFF the file must belong to

    Returns:
        value counts of the bands and of their luminance
    """
    with np.load(io.BytesIO(data), allow_pickle=False) as npz:
        metadata = json.loads(str(npz["metadata"]))
        histograms = Histograms(np.array(npz["histograms"], dtype=np.int64), np.array(npz["luminance"], dtype=np.int64))
    if metadata["version"] != HISTOGRAM_FILE_VERSION:
        raise ValueError(f"Expected histogram file version {HISTOGRAM_FILE_VERSION}, got {metadata['version']}: {source}")
    if metadata["source"] != source:
        raise ValueError(f"Expected the histogram file of {source}, got {metadata['source']}")
    return histograms


def get_source_histograms(
    source: str, histogram_dir: str, saved: bool, max_cache_mb: int = SAMPLE_CACHE_MIN_MB
) -> tuple[str, Histograms]:
    """Read the histograms of a source TIFF from its histogram file, or compute and save them.

    Args:
        source: path to the TIFF
        histogram_dir: directory of the histogram files
        saved: whether the histogram file of the source exists
        max_cache_mb: maximum GDAL block cache in MB to compute the histograms

    Returns:
        the source path and its value counts of the bands and of their luminance
    """
    path = os.path.join(histogram_dir, get_histogram_file_name(source))
    if saved:
        return source, histograms_from_bytes(read(path), source)
    histograms = get_histograms(source, max_cache_mb=max_cache_mb)
    write(path, histograms_to_bytes(source, histograms))
    return source, histograms


def _get_source_histograms(task: tuple[str, str, bool], max_cache_mb: int) -> tuple[str, Histograms]:
    """Unpack the arguments of `get_source_histograms` for `Pool.imap_unordered`."""
    return get_source_histograms(*task, max_cache_mb=max_cache_mb)


def sum_histograms(source_histograms: Iterable[tuple[str, Histograms]]) -> Histograms:
    """Sum the histograms of all sources, which must have the same number of bands.

    Args:
        source_histograms: source path and value counts of the bands and of their luminance of each source

    Returns:
        value counts of the bands and of their luminance
    """
    total: Histograms | None = None
    for source, histograms in source_histograms:
        if total is None:
            total = Histograms(histograms.bands.copy(), histograms.luminance.copy())
        elif histograms.bands.shape != total.bands.shape:
            raise ValueError(
                f"Expected {len(total.bands)} bands like the other sources, got {len(histograms.bands)}: {source}"
            )
        else:
            total.bands[:] += histograms.bands
            total.luminance[:] += histograms.luminance
    if total is None:
        raise ValueError("No histograms to sum")
    return total


def get_worker_count(files: list[str], concurrency: int, max_download_bytes: int | None) -> int:
    """Get the number of workers so that one download of the largest file per worker fits in `max_download_bytes`.

    Args:
        files: paths of the TIFFs to download
        concurrency: maximum number of workers
        max_download_bytes: maximum size in bytes of the downloads at a time, no limit if None

    Returns:
        the number of workers, at least 1
    """
    if max_download_bytes is None or not files:
        return concurrency
    sizes: dict[str, int] = {}
    for directory in {os.path.join(os.path.dirname(file), "") for file in files}:
        sizes.update({os.path.join(directory, name): size for name, size in list_file_sizes(directory).items()})
    largest = max(sizes.get(file, 0) for file in files)
    if largest == 0:
        return concurrency
    workers = min(concurrency, max(1, max_download_bytes // largest))
    if workers < concurrency:
        get_log().info("compute_scale_concurrency_capped", concurrency=workers, largestFileSize=largest)
    return workers


def get_worker_cache_mb(workers: int) -> int:
    """Get the share of each worker of `SAMPLE_CACHE_BUDGET_MB`, at least `SAMPLE_CACHE_MIN_MB`.

    Args:
        workers: number of workers

    Returns:
        the maximum GDAL block cache of each worker in MB

    Examples:
        >>> get_worker_cache_mb(64)
        64
        >>> get_worker_cache_mb(256)
        32
    """
    return max(SAMPLE_CACHE_MIN_MB, SAMPLE_CACHE_BUDGET_MB // workers)


def get_dataset_histograms(
    files: list[str],
    histogram_dir: str,
    concurrency: int = 1,
    force: bool = False,
    max_download_bytes: int | None = None,
) -> Histograms:
    """Sum the colour band and luminance histograms of all TIFFs, reading the histogram files already in `histogram_dir`.

    Args:
        files: paths to the TIFFs
        histogram_dir: directory of the histogram file of each TIFF
        concurrency: number of TIFFs to read concurrently
        force: recompute the histogram files that already exist
        max_download_bytes: maximum size in bytes of the `s3` TIFFs downloaded at a time, no limit if None

    Returns:
        value counts of the bands and of their luminance
    """
    saved = set() if force else list_file_names(histogram_dir, HISTOGRAM_FILE_SUFFIX)
    tasks = [(file, histogram_dir, get_histogram_file_name(file) in saved) for file in files]
    downloads = [file for file, _, is_saved in tasks if not is_saved and is_s3(file)]
    workers = get_worker_count(downloads, concurrency, max_download_bytes)
    max_cache_mb = get_worker_cache_mb(workers)
    get_log().info(
        "dataset_histograms_start",
        fileCount=len(files),
        savedCount=sum(task[2] for task in tasks),
        workers=workers,
        maxCacheMb=max_cache_mb,
    )
    with Pool(workers) as p:
        return sum_histograms(p.imap_unordered(partial(_get_source_histograms, max_cache_mb=max_cache_mb), tasks))
