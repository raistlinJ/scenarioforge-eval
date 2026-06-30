import datetime
import os
import re
import resource
import sys
import time
from typing import Any


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def rounded_seconds(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, float(value)), 6)


def estimate_text_tokens(text: str | None) -> int:
    if not text:
        return 0
    return len(TOKEN_RE.findall(text))


def text_metrics(text: str | None) -> dict[str, int]:
    value = text or ''
    return {
        'bytes': len(value.encode('utf-8', errors='replace')),
        'chars': len(value),
        'lines': value.count('\n') + (1 if value and not value.endswith('\n') else 0),
        'estimated_tokens': estimate_text_tokens(value),
    }


def _maxrss_to_bytes(value: int) -> int:
    # macOS reports bytes; Linux reports KiB. The evaluator primarily runs on
    # Unix-like helper VMs and developer machines.
    if sys.platform == 'darwin':
        return int(value)
    return int(value) * 1024


def _usage_snapshot(kind: str) -> dict[str, Any] | None:
    if kind == 'self':
        usage = resource.getrusage(resource.RUSAGE_SELF)
    elif kind == 'children':
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    elif kind == 'self_children':
        own = resource.getrusage(resource.RUSAGE_SELF)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        return {
            'cpu_user_s': own.ru_utime + children.ru_utime,
            'cpu_system_s': own.ru_stime + children.ru_stime,
            'max_rss_bytes': max(_maxrss_to_bytes(own.ru_maxrss), _maxrss_to_bytes(children.ru_maxrss)),
            'minor_page_faults': own.ru_minflt + children.ru_minflt,
            'major_page_faults': own.ru_majflt + children.ru_majflt,
            'input_blocks': own.ru_inblock + children.ru_inblock,
            'output_blocks': own.ru_oublock + children.ru_oublock,
            'voluntary_context_switches': own.ru_nvcsw + children.ru_nvcsw,
            'involuntary_context_switches': own.ru_nivcsw + children.ru_nivcsw,
        }
    else:
        raise ValueError(f"unknown resource usage kind: {kind}")

    return {
        'cpu_user_s': usage.ru_utime,
        'cpu_system_s': usage.ru_stime,
        'max_rss_bytes': _maxrss_to_bytes(usage.ru_maxrss),
        'minor_page_faults': usage.ru_minflt,
        'major_page_faults': usage.ru_majflt,
        'input_blocks': usage.ru_inblock,
        'output_blocks': usage.ru_oublock,
        'voluntary_context_switches': usage.ru_nvcsw,
        'involuntary_context_switches': usage.ru_nivcsw,
    }


def _usage_delta(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    if before is None or after is None:
        return {}

    metrics: dict[str, Any] = {
        'cpu_user_s': rounded_seconds(after['cpu_user_s'] - before['cpu_user_s']),
        'cpu_system_s': rounded_seconds(after['cpu_system_s'] - before['cpu_system_s']),
        'max_rss_bytes': after['max_rss_bytes'],
        'minor_page_faults': max(0, int(after['minor_page_faults'] - before['minor_page_faults'])),
        'major_page_faults': max(0, int(after['major_page_faults'] - before['major_page_faults'])),
        'input_blocks': max(0, int(after['input_blocks'] - before['input_blocks'])),
        'output_blocks': max(0, int(after['output_blocks'] - before['output_blocks'])),
        'voluntary_context_switches': max(0, int(after['voluntary_context_switches'] - before['voluntary_context_switches'])),
        'involuntary_context_switches': max(0, int(after['involuntary_context_switches'] - before['involuntary_context_switches'])),
    }
    metrics['cpu_total_s'] = rounded_seconds((metrics['cpu_user_s'] or 0.0) + (metrics['cpu_system_s'] or 0.0))
    return metrics


class MetricSpan:
    def __init__(self, resource_kind: str = 'self_children'):
        self.resource_kind = resource_kind
        self.started_at = ''
        self.ended_at = ''
        self._started_perf = 0.0
        self._before: dict[str, Any] | None = None
        self._metrics: dict[str, Any] | None = None

    def __enter__(self):
        self.started_at = utc_now_iso()
        self._started_perf = time.perf_counter()
        self._before = _usage_snapshot(self.resource_kind)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.finish()

    def finish(self) -> dict[str, Any]:
        if self._metrics is not None:
            return self._metrics

        ended_perf = time.perf_counter()
        after = _usage_snapshot(self.resource_kind)
        resources = _usage_delta(self._before, after)
        self.ended_at = utc_now_iso()
        self._metrics = {
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'duration_s': rounded_seconds(ended_perf - self._started_perf),
            'resources': resources,
        }
        return self._metrics


def file_metrics(path: str | None, *, token_sample_bytes: int = 2_000_000) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        'path': path,
        'exists': False,
        'size_bytes': 0,
        'estimated_tokens': 0,
        'lines': 0,
        'token_estimate_truncated': False,
    }
    if not path:
        return metrics
    try:
        if not os.path.isfile(path):
            return metrics
        size_bytes = os.path.getsize(path)
        metrics.update({
            'exists': True,
            'size_bytes': size_bytes,
        })
        with open(path, 'rb') as handle:
            raw = handle.read(token_sample_bytes + 1)
        if len(raw) > token_sample_bytes:
            raw = raw[:token_sample_bytes]
            metrics['token_estimate_truncated'] = True
        text = raw.decode('utf-8', errors='replace')
        text_stats = text_metrics(text)
        metrics['estimated_tokens'] = text_stats['estimated_tokens']
        metrics['lines'] = text_stats['lines']
    except OSError as exc:
        metrics['error'] = str(exc)
    return metrics


def directory_metrics(path: str | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        'path': path,
        'exists': False,
        'file_count': 0,
        'total_size_bytes': 0,
    }
    if not path:
        return metrics
    if not os.path.isdir(path):
        return metrics

    metrics['exists'] = True
    for root, _, files in os.walk(path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                metrics['file_count'] += 1
                metrics['total_size_bytes'] += os.path.getsize(file_path)
            except OSError:
                continue
    return metrics
