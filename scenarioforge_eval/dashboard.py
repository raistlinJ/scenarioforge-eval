"""Read-only dashboard for ScenarioForge evaluator result trees."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import webbrowser
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Timer
from typing import Any, Iterable

from flask import Flask, Response, jsonify

from .reporter import Reporter


MAX_RESULT_BYTES = 50 * 1024 * 1024
HTML_PATH = Path(__file__).with_name("templates") / "dashboard.html"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _first_failed_stage(result: dict[str, Any]) -> str:
    return Reporter._first_failed_stage(result) or str(
        (result.get("stages") or {}).get("failed_at") or "unknown"
    )


def _phase_rows_from_result(reporter: Reporter, index: int, result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = reporter._phase_metrics_rows(index, result)
    if rows or not isinstance(result.get("phases"), list):
        return rows
    return [dict(row) for row in result["phases"] if isinstance(row, dict)]


def _run_row_from_result(reporter: Reporter, index: int, result: dict[str, Any]) -> dict[str, Any]:
    if isinstance(result.get("run"), dict) and not result.get("phase_results"):
        return dict(result["run"])
    return reporter._run_metrics_row(index, result)


def _candidate_files(root: Path) -> tuple[list[Path], bool]:
    standard = sorted(
        path for path in root.rglob("*_result.json")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )
    if standard:
        return standard, False

    # A copied metrics tree may not contain the canonical result files. Support
    # its raw per-run payloads as a fallback, while deduplicating mirrored copies.
    fallback = sorted(
        path for path in root.rglob("run_metrics_raw.json")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )
    return fallback, True


def load_dashboard_data(root_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Recursively load evaluator results and return a browser-friendly model."""
    root = Path(root_path).expanduser().resolve()
    reporter = Reporter(str(root))
    candidates, using_fallback = _candidate_files(root)
    runs: list[dict[str, Any]] = []
    all_phase_rows: list[dict[str, Any]] = []
    load_errors: list[dict[str, str]] = []
    fallback_fingerprints: set[str] = set()

    for candidate in candidates:
        relative_path = candidate.relative_to(root).as_posix()
        try:
            size = candidate.stat().st_size
            if size > MAX_RESULT_BYTES:
                raise ValueError(f"file is larger than {MAX_RESULT_BYTES // (1024 * 1024)} MiB")
            with candidate.open("r", encoding="utf-8") as handle:
                result = json.load(handle)
            if not isinstance(result, dict):
                raise ValueError("top-level JSON value is not an object")
            if "success" not in result:
                raise ValueError("missing required 'success' field")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            load_errors.append({"file": relative_path, "error": str(exc)})
            continue

        if using_fallback:
            fingerprint = json.dumps(
                {"run": result.get("run"), "phases": result.get("phases")},
                sort_keys=True,
                default=str,
            )
            if fingerprint in fallback_fingerprints:
                continue
            fallback_fingerprints.add(fingerprint)

        index = len(runs) + 1
        row = _run_row_from_result(reporter, index, result)
        phase_rows = _phase_rows_from_result(reporter, index, result)
        run_id = relative_path
        spec_name = str(
            row.get("spec_name")
            or result.get("spec_name")
            or (result.get("metadata") or {}).get("spec_name")
            or candidate.name.removesuffix("_result.json")
        )
        success = bool(result.get("success"))
        warnings = result.get("warnings") or []
        stages = result.get("stages") or {}

        normalized_phases = []
        for phase_row in phase_rows:
            phase = {
                "phase": str(phase_row.get("phase") or "unknown"),
                "duration_s": _number(phase_row.get("duration_s")),
                "returncode": phase_row.get("returncode", ""),
                "timed_out": bool(phase_row.get("timed_out")),
                "estimated_output_tokens": _integer(phase_row.get("estimated_output_tokens")),
                "log_size_bytes": _integer(phase_row.get("log_size_bytes")),
                "cpu_total_s": _number(phase_row.get("cpu_total_s")),
                "max_rss_bytes": _integer(phase_row.get("max_rss_bytes")),
                "validation_ok": phase_row.get("validation_ok", ""),
            }
            normalized_phases.append(phase)
            all_phase_rows.append({**phase, "run_id": run_id, "spec_name": spec_name})

        runs.append({
            "id": run_id,
            "spec_name": spec_name,
            "source_file": relative_path,
            "success": success,
            "failed_stage": "" if success else _first_failed_stage(result),
            "failed_at": str(row.get("failed_at") or ""),
            "started_at": str(row.get("started_at") or ""),
            "ended_at": str(row.get("ended_at") or ""),
            "duration_s": _number(row.get("duration_s")),
            "target_phase": str(row.get("target_phase") or ""),
            "seed": row.get("seed", ""),
            "iteration_index": row.get("iteration_index", ""),
            "iteration_count": row.get("iteration_count", ""),
            "router_count": _integer(row.get("router_count")),
            "host_count": _integer(row.get("host_count")),
            "node_count": _integer(row.get("node_count")),
            "service_count": _integer(row.get("service_count")),
            "vulnerability_count": _integer(row.get("vulnerability_count")),
            "challenge_count": _integer(row.get("challenge_count")),
            "chain_count": _integer(row.get("chain_count")),
            "average_chain_length": _number(row.get("average_chain_length")),
            "pivot_count": _integer(row.get("pivot_count")),
            "flag_node_generator_count": _integer(row.get("flag_node_generator_count")),
            "estimated_output_tokens": _integer(row.get("estimated_output_tokens")),
            "artifact_total_size_bytes": _integer(row.get("artifact_total_size_bytes")),
            "artifact_file_count": _integer(row.get("artifact_file_count")),
            "cpu_total_s": _number(row.get("cpu_total_s")),
            "max_rss_bytes": _integer(row.get("max_rss_bytes")),
            "validation_ok": row.get("validation_ok", ""),
            "check_artifacts_ok": row.get("check_artifacts_ok", ""),
            "check_artifacts_overall": row.get("check_artifacts_overall", ""),
            "warnings": [str(item) for item in warnings],
            "warning_count": len(warnings),
            "stages": stages,
            "error": str(result.get("error") or ""),
            "phases": normalized_phases,
        })

    runs.sort(key=lambda row: (row["started_at"], row["spec_name"], row["id"]))
    durations = [row["duration_s"] for row in runs]
    successes = sum(1 for row in runs if row["success"])
    failures = len(runs) - successes
    failure_stages = Counter(row["failed_stage"] for row in runs if not row["success"])

    phase_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_phase_rows:
        phase_buckets[row["phase"]].append(row)
    phase_summary = []
    for phase, rows in sorted(phase_buckets.items()):
        phase_durations = [row["duration_s"] for row in rows]
        phase_summary.append({
            "phase": phase,
            "count": len(rows),
            "failures": sum(
                1 for row in rows
                if row["timed_out"] or row["returncode"] not in ("", None, 0, "0")
            ),
            "timeouts": sum(1 for row in rows if row["timed_out"]),
            "avg_duration_s": round(statistics.fmean(phase_durations), 6) if phase_durations else 0.0,
            "p95_duration_s": _percentile(phase_durations, 0.95),
            "estimated_output_tokens": sum(row["estimated_output_tokens"] for row in rows),
            "log_size_bytes": sum(row["log_size_bytes"] for row in rows),
            "cpu_total_s": round(sum(row["cpu_total_s"] for row in rows), 6),
            "max_rss_bytes": max((row["max_rss_bytes"] for row in rows), default=0),
        })

    return {
        "schema_version": 1,
        "meta": {
            "root": str(root),
            "scanned_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "candidate_files": len(candidates),
            "loaded_runs": len(runs),
            "load_errors": load_errors,
            "source_mode": "metrics-fallback" if using_fallback else "result-json",
        },
        "summary": {
            "total_runs": len(runs),
            "successes": successes,
            "failures": failures,
            "pass_rate": round(successes / len(runs), 6) if runs else 0.0,
            "total_duration_s": round(sum(durations), 6),
            "avg_duration_s": round(statistics.fmean(durations), 6) if durations else 0.0,
            "median_duration_s": round(statistics.median(durations), 6) if durations else 0.0,
            "p95_duration_s": _percentile(durations, 0.95),
            "estimated_output_tokens": sum(row["estimated_output_tokens"] for row in runs),
            "artifact_total_size_bytes": sum(row["artifact_total_size_bytes"] for row in runs),
            "cpu_total_s": round(sum(row["cpu_total_s"] for row in runs), 6),
            "max_rss_bytes": max((row["max_rss_bytes"] for row in runs), default=0),
            "challenges": sum(row["challenge_count"] for row in runs),
            "chains": sum(row["chain_count"] for row in runs),
            "pivots": sum(row["pivot_count"] for row in runs),
        },
        "failure_stages": [
            {"stage": stage, "count": count}
            for stage, count in failure_stages.most_common()
        ],
        "phase_summary": phase_summary,
        "runs": runs,
    }


def create_app(root_path: str | os.PathLike[str]) -> Flask:
    root = Path(root_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"dashboard root is not a directory: {root}")

    app = Flask(__name__)
    app.config["DASHBOARD_ROOT"] = str(root)

    @app.get("/")
    def index() -> Response:
        response = Response(HTML_PATH.read_text(encoding="utf-8"), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/dashboard")
    def dashboard_data():
        response = jsonify(load_dashboard_data(app.config["DASHBOARD_ROOT"]))
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz")
    def health():
        return {"ok": True, "root": app.config["DASHBOARD_ROOT"]}

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Browse ScenarioForge evaluator run metrics")
    parser.add_argument("root", help="Parent folder containing *_result.json files")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", default=8088, type=int, help="Bind port (default: 8088)")
    parser.add_argument("--open", action="store_true", help="Open the dashboard in the default browser")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    url_host = "localhost" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{url_host}:{args.port}"
    print(f"ScenarioForge Eval dashboard: {url}")
    print(f"Scanning: {root}")
    if args.open:
        Timer(0.75, lambda: webbrowser.open(url)).start()
    create_app(root).run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
