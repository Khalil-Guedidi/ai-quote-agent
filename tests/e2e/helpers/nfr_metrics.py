"""NFR measurement utilities — timing, memory, and latency statistics for scale tests."""

from __future__ import annotations

import json
import logging
import resource
import statistics
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

# NFR targets from architecture.md
NFR1_PIPELINE_MAX_SECONDS = 120  # End-to-end pipeline < 2 minutes
NFR2_SEARCH_MAX_SECONDS = 3.0  # Search latency < 3 seconds
NFR6_CACHE_HIT_MAX_SECONDS = 1.0  # Cache hit < 1 second


@contextmanager
def measure_time() -> Generator[list[float], None, None]:
    """Context manager that captures elapsed wall-clock time.

    Usage::

        with measure_time() as elapsed:
            do_something()
        print(f"Took {elapsed[0]:.3f}s")

    The elapsed time (seconds) is stored in ``elapsed[0]`` after the block exits.
    """
    container: list[float] = [0.0]
    start = time.perf_counter()
    yield container
    container[0] = time.perf_counter() - start


def get_peak_rss_mb() -> float:
    """Return peak resident set size (RSS) in megabytes.

    Uses ``resource.getrusage`` — on Linux ``ru_maxrss`` is in kilobytes.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024.0  # KB → MB


def compute_percentiles(samples: list[float]) -> dict[str, float]:
    """Compute p50 and p95 from a list of latency samples."""
    if not samples:
        return {"p50": 0.0, "p95": 0.0}

    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)

    # Clamp to valid range
    p50_idx = min(p50_idx, n - 1)
    p95_idx = min(p95_idx, n - 1)

    return {
        "p50": round(sorted_samples[p50_idx], 4),
        "p95": round(sorted_samples[p95_idx], 4),
    }


def compute_stats(samples: list[float]) -> dict[str, float]:
    """Compute basic statistics from latency samples: mean, min, max, p50, p95."""
    if not samples:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "p50": 0.0, "p95": 0.0}

    percentiles = compute_percentiles(samples)
    return {
        "mean": round(statistics.mean(samples), 4),
        "min": round(min(samples), 4),
        "max": round(max(samples), 4),
        **percentiles,
    }


def log_nfr_report(report: dict[str, object]) -> None:
    """Log a structured NFR report as JSON."""
    logger.info(
        "NFR Report: %s",
        json.dumps(report, indent=2, default=str),
    )
