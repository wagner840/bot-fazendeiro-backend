"""Lightweight in-memory metrics registry for API observability."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Dict

_lock = Lock()
_counters: Dict[str, float] = defaultdict(float)
_hist_sum: Dict[str, float] = defaultdict(float)
_hist_count: Dict[str, float] = defaultdict(float)


def _build_key(name: str, labels: dict[str, str] | None = None) -> str:
    if not labels:
        return name
    label_expr = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{label_expr}}}"


def inc_counter(name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
    key = _build_key(name, labels)
    with _lock:
        _counters[key] += value


def observe_histogram(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    sum_key = _build_key(f"{name}_sum", labels)
    count_key = _build_key(f"{name}_count", labels)
    with _lock:
        _hist_sum[sum_key] += value
        _hist_count[count_key] += 1.0


def render_metrics() -> str:
    with _lock:
        lines = []
        for key, val in sorted(_counters.items()):
            lines.append(f"{key} {val}")
        for key, val in sorted(_hist_sum.items()):
            lines.append(f"{key} {val}")
        for key, val in sorted(_hist_count.items()):
            lines.append(f"{key} {val}")
    return "\n".join(lines) + ("\n" if lines else "")

