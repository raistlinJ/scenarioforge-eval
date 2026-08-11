"""Read-only dashboard for ScenarioForge evaluator result trees."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import webbrowser
from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock, Thread, Timer
from typing import Any, Iterable
from uuid import uuid4

from flask import Flask, Response, jsonify, request
from yaml import YAMLError

from .parser import SpecParser
from .reporter import Reporter


MAX_RESULT_BYTES = 50 * 1024 * 1024
DASHBOARD_SCHEMA_VERSION = 3
HTML_PATH = Path(__file__).with_name("templates") / "dashboard.html"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_EXECUTION_LOG_LINES = 5000
DASHBOARD_SETTINGS_ENV_VAR = "SCENARIOFORGE_EVAL_DASHBOARD_SETTINGS"
EXECUTION_SETTINGS_KEYS = (
    "spec_path",
    "sf_path",
    "phase",
    "reproduction_mode",
    "verbose",
    "stop_on_error",
    "dangerous_cleanup_between_runs",
)

EXECUTION_PROGRESS_PATTERN = re.compile(
    r"\bruns\s+(?P<completed>\d+)\s*/\s*(?P<total>\d+)"
    r"\s*\|\s*ok\s+(?P<passed>\d+)"
    r"\s*\|\s*fail\s+(?P<failed>\d+)\b",
    re.IGNORECASE,
)

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
EXECUTION_CURRENT_RUN_PATTERN = re.compile(r"\bcurrent\s+(?P<name>\S+)")
DISK_USAGE_SSH_TIMEOUT_S = 10.0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dashboard_settings_path() -> Path:
    override = os.environ.get(DASHBOARD_SETTINGS_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".scenarioforge_eval" / "dashboard_settings.json"


def _load_dashboard_settings() -> dict[str, Any]:
    try:
        raw = json.loads(_dashboard_settings_path().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_dashboard_settings(updates: dict[str, Any]) -> None:
    """Persist dashboard settings so the next launch can restore last-used values."""
    settings = _load_dashboard_settings()
    settings.update(updates)
    path = _dashboard_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def _save_execution_settings(config: dict[str, Any]) -> None:
    _save_dashboard_settings({
        "execution": {key: config[key] for key in EXECUTION_SETTINGS_KEYS if key in config}
    })


def _parse_execution_progress_line(text: str) -> dict[str, int] | None:
    """Extract the evaluator's authoritative batch counters from a status line."""
    match = EXECUTION_PROGRESS_PATTERN.search(str(text or ""))
    if match is None:
        return None
    progress = {name: int(value) for name, value in match.groupdict().items()}
    if progress["completed"] > progress["total"]:
        return None
    if progress["passed"] + progress["failed"] != progress["completed"]:
        return None
    return progress


def _strip_ansi(text: Any) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", str(text or ""))


def _parse_execution_current_run(text: Any) -> str | None:
    """Name of the run the evaluator currently has in flight, if any.

    The status line carries `current <spec_name>` only while an iteration is
    running, so a change in this value marks the batch starting a new run.
    """
    match = EXECUTION_CURRENT_RUN_PATTERN.search(_strip_ansi(text))
    if match is None:
        return None
    return match.group("name") or None


def _read_env_file(path: Path) -> dict[str, str]:
    """Minimal reader for ScenarioForge's .scenarioforge.env.

    Mirrors webapp/env_loader.py's rules (optional `export`, quoted values,
    trailing ` #` comments) rather than importing it: the dashboard should not
    need ScenarioForge importable, and must not mutate this process's
    environment the way `load_runtime_env_files` does.
    """
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return values
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] in {'"', "'"} and value[-1] == value[0]:
            value = value[1:-1]
        else:
            comment_index = value.find(" #")
            if comment_index >= 0:
                value = value[:comment_index].rstrip()
        values[key] = value
    return values


def _core_ssh_settings(sf_path: str) -> dict[str, Any] | None:
    """CORE VM SSH target, real environment first (env_loader's precedence)."""
    env_file = _read_env_file(Path(sf_path) / ".scenarioforge.env")

    def _setting(key: str, default: str = "") -> str:
        return str(os.environ.get(key) or env_file.get(key) or default).strip()

    host = _setting("CORE_SSH_HOST")
    username = _setting("CORE_SSH_USERNAME")
    if not host or not username:
        return None
    try:
        port = int(_setting("CORE_SSH_PORT", "22"))
    except ValueError:
        port = 22
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": _setting("CORE_SSH_PASSWORD"),
    }


def _parse_df_output(output: str) -> dict[str, Any]:
    """Pull totals from `df -P -k` output, which is one data row after a header."""
    rows = [line.split() for line in _strip_ansi(output).splitlines() if line.strip()]
    for fields in reversed(rows):
        if len(fields) < 4 or not fields[1].isdigit() or not fields[3].isdigit():
            continue
        return {
            "total_bytes": int(fields[1]) * 1024,
            "free_bytes": int(fields[3]) * 1024,
        }
    return {"error": "could not parse df output"}


def _local_disk_usage(path: str) -> dict[str, Any]:
    target = Path(path or ".").expanduser()
    # The output root may not exist yet on a first run; the filesystem that
    # will hold it is what matters, so walk up to the nearest existing parent.
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        usage = shutil.disk_usage(str(target))
    except OSError as exc:
        return {"error": str(exc)}
    return {"free_bytes": int(usage.free), "total_bytes": int(usage.total)}


def _core_vm_disk_usage(sf_path: str) -> dict[str, Any]:
    settings = _core_ssh_settings(sf_path)
    if settings is None:
        return {"error": "CORE VM SSH settings not found in .scenarioforge.env"}
    try:
        import paramiko
    except ImportError:
        return {"error": "paramiko is not installed"}

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=settings["host"],
            port=settings["port"],
            username=settings["username"],
            password=settings["password"] or None,
            look_for_keys=True,
            allow_agent=True,
            timeout=DISK_USAGE_SSH_TIMEOUT_S,
            banner_timeout=DISK_USAGE_SSH_TIMEOUT_S,
            auth_timeout=DISK_USAGE_SSH_TIMEOUT_S,
        )
        # Read-only, so this deliberately does not take the shared VM lock the
        # executor uses; it must never delay a run it is only reporting on.
        _stdin, stdout, _stderr = client.exec_command(
            "df -P -k /", timeout=DISK_USAGE_SSH_TIMEOUT_S
        )
        output = stdout.read().decode("utf-8", "replace")
    except Exception as exc:  # paramiko raises a wide range of socket/auth errors
        return {"error": f"{type(exc).__name__}: {exc}".strip()}
    finally:
        try:
            client.close()
        except Exception:
            pass

    usage = _parse_df_output(output)
    usage["label"] = settings["host"]
    return usage


def _resolve_execution_path(
    value: Any,
    *,
    label: str,
    base: Path,
    must_exist: bool,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if must_exist and not path.exists():
        raise ValueError(f"{label} was not found: {path}")
    return path


def _build_execution_command(payload: Any, *, cwd: Path) -> tuple[list[str], dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    spec_path = _resolve_execution_path(
        payload.get("spec_path"), label="spec path", base=cwd, must_exist=True
    )
    if not (spec_path.is_file() or spec_path.is_dir()):
        raise ValueError(f"spec path is not a file or directory: {spec_path}")
    sf_path = _resolve_execution_path(
        payload.get("sf_path"), label="ScenarioForge path", base=cwd, must_exist=True
    )
    if not sf_path.is_dir():
        raise ValueError(f"ScenarioForge path is not a directory: {sf_path}")
    out_path = _resolve_execution_path(
        payload.get("out_path"), label="output path", base=cwd, must_exist=False
    )
    if out_path == Path(out_path.anchor):
        raise ValueError("output path cannot be a filesystem root")
    if out_path.exists() and not out_path.is_dir():
        raise ValueError(f"output path is not a directory: {out_path}")

    phase = str(payload.get("phase") or "scenario-xml").strip().lower()
    phase_flags = {
        "scenario-xml": None,
        "topology": "--topology",
        "flag-sequencing": "--flag-sequencing",
        "execute": "--execute",
    }
    if phase not in phase_flags:
        raise ValueError(f"unsupported phase: {phase}")

    command = [
        sys.executable,
        "-m",
        "scenarioforge_eval.main",
        str(spec_path),
        "--sf-path",
        str(sf_path),
        "--out",
        str(out_path),
    ]
    phase_flag = phase_flags[phase]
    if phase_flag:
        command.append(phase_flag)
    if bool(payload.get("verbose")):
        command.append("--verbose")
    if bool(payload.get("stop_on_error")):
        command.append("--stop-on-error")
    if bool(payload.get("dangerous_cleanup_between_runs")):
        command.append("--dangerous-cleanup-between-runs")
    reproduction_mode = str(payload.get("reproduction_mode") or "xml").strip().lower()
    if reproduction_mode not in {"xml", "replay", "bundle"}:
        raise ValueError(f"unsupported reproduction mode: {reproduction_mode}")
    if reproduction_mode != "xml":
        command.extend(["--reproduction-mode", reproduction_mode])

    public_config = {
        "spec_path": str(spec_path),
        "sf_path": str(sf_path),
        "out_path": str(out_path),
        "phase": phase,
        "verbose": bool(payload.get("verbose")),
        "stop_on_error": bool(payload.get("stop_on_error")),
        "dangerous_cleanup_between_runs": bool(
            payload.get("dangerous_cleanup_between_runs")
        ),
        "reproduction_mode": reproduction_mode,
    }
    return command, public_config


def _execution_spec_files(spec_path: Path) -> list[Path]:
    if spec_path.is_file():
        return [spec_path]
    spec_files = sorted(spec_path.glob("*.spec.yaml"))
    if not spec_files:
        raise ValueError(f"no .spec.yaml files found in spec folder: {spec_path}")
    return spec_files


def _existing_result_status(
    result_path: Path,
    *,
    run_name: str,
    iteration_index: int,
    phase: str,
    reproduction_mode: str,
) -> tuple[bool, bool]:
    if not result_path.is_file():
        return False, False
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, False
    if not isinstance(result, dict):
        return False, False
    metadata = result.get("metadata") or {}
    if not isinstance(metadata, dict):
        return False, False
    if str(metadata.get("spec_name") or run_name) != run_name:
        return False, False
    if _integer(metadata.get("iteration_index"), iteration_index) != iteration_index:
        return False, False

    phase_rank = {"scenario-xml": 0, "topology": 1, "flag-sequencing": 2, "execute": 3}
    existing_phase = str(metadata.get("target_phase") or "scenario-xml").strip().lower()
    if phase_rank.get(existing_phase, -1) < phase_rank[phase]:
        return False, False
    reproduction_rank = {"xml": 0, "replay": 1, "bundle": 2}
    existing_reproduction = str(metadata.get("reproduction_mode") or "xml").strip().lower()
    completed = (
        reproduction_rank.get(existing_reproduction, -1)
        >= reproduction_rank[reproduction_mode]
    )
    return completed, completed and bool(result.get("success"))


_REPEATED_ITERATION_FLAGS = re.compile(r"--iteration-index \d+(?: --iteration-index \d+){2,}")


def _summarize_command_texts(command_texts: list[str]) -> str:
    """Collapse resume plans so the console header stays a single readable line."""
    summary = _REPEATED_ITERATION_FLAGS.sub(
        lambda match: f"--iteration-index x{match.group(0).count('--iteration-index')}",
        command_texts[0],
    )
    extra = len(command_texts) - 1
    if extra:
        summary += f" · +{extra} more command{'' if extra == 1 else 's'}"
    return summary


# How many existing runs the resume dialog lists by name. The rest are
# reported as a trailing count rather than dropped silently.
_EXISTING_RUN_LIST_LIMIT = 10


def _interrupted_run_completion_paths(output_root: Path, run_name: str) -> tuple[Path, ...]:
    """Artifacts that would make an interrupted run look finished.

    Only the completion markers, not the run's output directory: a stopped run
    is usually stopped because something looked wrong, so its logs and partial
    artifacts stay put for inspection. Resume clears the directory itself
    before re-running.
    """
    safe_name = Reporter._safe_metric_dir_name(run_name)
    candidates = (
        output_root / f"{run_name}_result.json",
        output_root / f"{run_name}_ai_prompt.md",
        output_root / "metrics" / "runs" / safe_name,
    )
    return tuple(
        path for path in candidates
        if _path_inside_root(output_root, str(path)) is not None
    )


def _execution_run_cleanup_paths(output_root: Path, run: dict[str, Any]) -> tuple[Path, ...]:
    run_name = run["run_name"]
    candidates = (
        run["output_dir"],
        run["result_path"],
        output_root / f"{run_name}_ai_prompt.md",
        output_root / "metrics" / "runs" / Reporter._safe_metric_dir_name(run_name),
        output_root / "webui-xml" / f"{Reporter._safe_metric_dir_name(run_name)}.xml",
    )
    return tuple(
        path for path in candidates
        if _path_inside_root(output_root, str(path)) is not None
    )


def _scan_execution_runs(payload: Any, *, cwd: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, config = _build_execution_command(payload, cwd=cwd)
    spec_path = Path(config["spec_path"])
    output_root = Path(config["out_path"])
    runs: list[dict[str, Any]] = []
    for spec_file in _execution_spec_files(spec_path):
        try:
            spec = SpecParser(str(spec_file))
            iterations = max(0, int(spec.spec.get("iterations", 1)))
        except (OSError, UnicodeError, AttributeError, TypeError, ValueError, YAMLError) as exc:
            raise ValueError(f"unable to read spec {spec_file}: {exc}") from exc
        base_name = str(spec.get_name())
        for iteration_index in range(1, iterations + 1):
            run_name = base_name if iterations == 1 else f"{base_name}_run{iteration_index}"
            result_path = output_root / f"{run_name}_result.json"
            output_dir = output_root / run_name
            completed, succeeded = _existing_result_status(
                result_path,
                run_name=run_name,
                iteration_index=iteration_index,
                phase=config["phase"],
                reproduction_mode=config["reproduction_mode"],
            )
            runs.append({
                "spec_file": spec_file,
                "iteration_index": iteration_index,
                "run_name": run_name,
                "result_path": result_path,
                "output_dir": output_dir,
                "completed": completed,
                "succeeded": succeeded,
                "existing": result_path.exists() or output_dir.exists(),
            })
    if not runs:
        raise ValueError("the selected spec path contains zero planned runs")

    completed = sum(1 for run in runs if run["completed"])
    passed = sum(1 for run in runs if run["completed"] and run["succeeded"])
    existing = [run for run in runs if run["existing"]]
    incomplete = sum(1 for run in existing if not run["completed"])
    # Incomplete first: the list shown in the dialog is capped, and an
    # incomplete run is the one the reader has to act on (Resume re-runs it,
    # Start from beginning discards it). Ordering by completion keeps those
    # visible instead of letting a long tail of finished runs bury them.
    # sorted() is stable, so runs stay in plan order within each group.
    listed = sorted(existing, key=lambda run: bool(run["completed"]))[:_EXISTING_RUN_LIST_LIMIT]
    preflight = {
        "planned": len(runs),
        "completed": completed,
        "passed": passed,
        "failed": completed - passed,
        "remaining": len(runs) - completed,
        "existing": len(existing),
        "incomplete": incomplete,
        "has_existing": bool(existing),
        "existing_runs": [
            {
                "name": run["run_name"],
                "completed": bool(run["completed"]),
                "succeeded": bool(run["succeeded"]),
            }
            for run in listed
        ],
        "existing_not_listed": len(existing) - len(listed),
    }
    return preflight, runs


def _build_execution_plan(
    payload: Any,
    *,
    cwd: Path,
) -> tuple[list[list[str]], dict[str, Any], tuple[Path, ...]]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    action = payload.get("existing_runs_action")
    if action not in {None, "resume", "restart"}:
        raise ValueError("existing_runs_action must be 'resume' or 'restart'")

    command, config = _build_execution_command(payload, cwd=cwd)
    preflight, runs = _scan_execution_runs(payload, cwd=cwd)
    if preflight["has_existing"] and action is None:
        raise RuntimeError("existing runs require choosing Resume or Start from beginning")

    cleanup_paths: tuple[Path, ...] = ()
    if action == "resume":
        remaining = [run for run in runs if not run["completed"]]
        if not remaining:
            raise ValueError(
                "all planned runs already have completed results; choose Start from beginning to run them again"
            )
        grouped: dict[Path, list[int]] = defaultdict(list)
        for run in remaining:
            grouped[run["spec_file"]].append(run["iteration_index"])
        commands = []
        for spec_file, iteration_indexes in grouped.items():
            resume_payload = {**payload, "spec_path": str(spec_file)}
            resume_command, _ = _build_execution_command(resume_payload, cwd=cwd)
            for iteration_index in iteration_indexes:
                resume_command.extend(["--iteration-index", str(iteration_index)])
            commands.append(resume_command)
        cleanup_paths = tuple(dict.fromkeys(
            path
            for run in remaining
            if run["existing"]
            for path in _execution_run_cleanup_paths(Path(config["out_path"]), run)
        ))
        config.update({
            "kind": "resume",
            "run_count": len(runs),
            "execution_run_count": len(remaining),
            "progress_completed_offset": preflight["completed"],
            "progress_passed_offset": preflight["passed"],
            "progress_failed_offset": preflight["failed"],
        })
    else:
        commands = [command]
        config.update({"kind": "execution", "run_count": len(runs)})
        if action == "restart":
            cleanup_paths = tuple(dict.fromkeys(
                path
                for run in runs
                for path in _execution_run_cleanup_paths(Path(config["out_path"]), run)
            ))
            config["kind"] = "restart"

    config.update({
        "existing_runs_action": action or "new",
        "planned_run_count": preflight["planned"],
        "previously_completed_run_count": preflight["completed"],
    })
    return commands, config, cleanup_paths


class EvaluationJobManager:
    """Run one evaluator subprocess at a time and retain bounded console output."""

    ACTIVE_STATUSES = {"starting", "running", "stopping"}

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self._lock = Lock()
        self._job: dict[str, Any] | None = None
        self._process: subprocess.Popen[str] | None = None

    def _disk_usage_worker(self, job_id: str) -> None:
        # Loops rather than returning after one reading: runs can start while a
        # reading is in flight, and the newest run is the one worth showing.
        while True:
            with self._lock:
                if self._job is None or self._job.get("id") != job_id:
                    return
                if not self._job.get("_disk_refresh_pending"):
                    self._job["_disk_refresh_active"] = False
                    return
                run_name = str(self._job.get("_disk_refresh_run_name") or "")
                self._job["_disk_refresh_pending"] = False
                config = dict(self._job.get("config") or {})

            local = _local_disk_usage(str(config.get("out_path") or self.cwd))
            core_vm = _core_vm_disk_usage(str(config.get("sf_path") or ""))

            with self._lock:
                if self._job is None or self._job.get("id") != job_id:
                    return
                self._job["disk_usage"] = {
                    "local": local,
                    "core_vm": core_vm,
                    "run_name": run_name,
                    "updated_at": _utc_now(),
                }

    def _request_disk_usage_refresh(self, run_name: str) -> str | None:
        """Queue a reading. Caller holds the lock; returns a job id to spawn on."""
        if self._job is None:
            return None
        self._job["_disk_refresh_run_name"] = run_name
        self._job["_disk_refresh_pending"] = True
        if self._job.get("_disk_refresh_active"):
            return None
        self._job["_disk_refresh_active"] = True
        return str(self._job.get("id") or "")

    def _schedule_disk_usage_refresh(self, job_id: str) -> None:
        Thread(target=self._disk_usage_worker, args=(job_id,), daemon=True).start()

    def _append_log(self, text: str, *, command_index: int | None = None) -> None:
        parsed_progress = _parse_execution_progress_line(text)
        current_run = _parse_execution_current_run(text)
        refresh_job_id: str | None = None
        with self._lock:
            if self._job is None:
                return
            # The evaluator names the run it has in flight only while that run
            # is executing, so a status line without one means the batch is
            # between runs and nothing would be lost to a stop right now.
            if parsed_progress is not None or current_run is not None:
                self._job["current_run"] = current_run
            # Sample free space as each run begins. An SSH round trip is far
            # too slow to do per log line, and the numbers only move
            # meaningfully between runs anyway.
            if current_run is not None and current_run != self._job.get("_disk_refresh_seen"):
                self._job["_disk_refresh_seen"] = current_run
                refresh_job_id = self._request_disk_usage_refresh(current_run)
            self._job["log_sequence"] += 1
            self._job["logs"].append((self._job["log_sequence"], text.rstrip("\r\n")))
            if parsed_progress is not None:
                command_progress = self._job["_command_progress"]
                command_progress[command_index or 1] = parsed_progress
                config = self._job.get("config", {})
                completed = _integer(config.get("progress_completed_offset")) + sum(
                    item["completed"] for item in command_progress.values()
                )
                passed = _integer(config.get("progress_passed_offset")) + sum(
                    item["passed"] for item in command_progress.values()
                )
                failed = _integer(config.get("progress_failed_offset")) + sum(
                    item["failed"] for item in command_progress.values()
                )
                configured_total = _integer(config.get("run_count"))
                discovered_total = _integer(config.get("progress_completed_offset")) + sum(
                    item["total"] for item in command_progress.values()
                )
                total = configured_total or discovered_total
                self._job["progress"] = {
                    "completed": min(completed, total),
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                }
        if refresh_job_id:
            self._schedule_disk_usage_refresh(refresh_job_id)

    def snapshot(self, *, after: int = 0) -> dict[str, Any]:
        with self._lock:
            if self._job is None:
                return {"status": "idle", "logs": [], "log_sequence": 0}
            public = {
                key: value
                for key, value in self._job.items()
                if key not in {
                    "logs",
                    "stop_requested",
                    "_command_count",
                    "_command_progress",
                    "_disk_refresh_active",
                    "_disk_refresh_pending",
                    "_disk_refresh_run_name",
                    "_disk_refresh_seen",
                }
            }
            public["logs"] = [
                {"sequence": sequence, "text": text}
                for sequence, text in self._job["logs"]
                if sequence > after
            ]
            return public

    def start(self, payload: Any) -> dict[str, Any]:
        command, config = _build_execution_command(payload, cwd=self.cwd)
        return self.start_commands([command], config=config)

    def start_commands(
        self,
        commands: list[list[str]],
        *,
        config: dict[str, Any],
        cleanup_paths: Iterable[Path] = (),
        rebuild_root: Path | None = None,
    ) -> dict[str, Any]:
        if not commands or any(not command for command in commands):
            raise ValueError("at least one evaluator command is required")
        with self._lock:
            if self._job and self._job.get("status") in self.ACTIVE_STATUSES:
                raise RuntimeError("an evaluator job is already running")
            job_id = uuid4().hex
            command_texts = [
                shlex.join(["scenarioforge-eval", *command[3:]])
                for command in commands
            ]
            self._job = {
                "id": job_id,
                "status": "starting",
                "command": " && ".join(command_texts),
                "command_display": _summarize_command_texts(command_texts),
                "config": config,
                "started_at": _utc_now(),
                "ended_at": "",
                "returncode": None,
                "pid": None,
                "error": "",
                "progress": {
                    "completed": _integer(config.get("progress_completed_offset")),
                    "total": _integer(config.get("run_count")),
                    "passed": _integer(config.get("progress_passed_offset")),
                    "failed": _integer(config.get("progress_failed_offset")),
                },
                "stop_requested": False,
                "log_sequence": 0,
                "logs": deque(maxlen=MAX_EXECUTION_LOG_LINES),
                "current_run": None,
                "disk_usage": {},
                "_command_count": len(commands),
                "_command_progress": {},
                # Seed a reading before the first run reports in, so the panel
                # is populated for the whole job, not just from run one onward.
                "_disk_refresh_active": True,
                "_disk_refresh_pending": True,
                "_disk_refresh_run_name": "",
                "_disk_refresh_seen": None,
            }
        self._schedule_disk_usage_refresh(job_id)
        Thread(
            target=self._run,
            args=(job_id, commands, tuple(cleanup_paths), rebuild_root),
            daemon=True,
        ).start()
        return self.snapshot()

    def _run(
        self,
        job_id: str,
        commands: list[list[str]],
        cleanup_paths: tuple[Path, ...] = (),
        rebuild_root: Path | None = None,
    ) -> None:
        try:
            _delete_rerun_paths(cleanup_paths)
        except OSError as exc:
            with self._lock:
                if self._job and self._job.get("id") == job_id:
                    self._job.update({
                        "status": "failed",
                        "ended_at": _utc_now(),
                        "error": f"unable to delete original run data: {exc}",
                    })
            return

        returncode = 0
        for index, command in enumerate(commands, start=1):
            with self._lock:
                if not self._job or self._job.get("id") != job_id:
                    return
                if self._job["stop_requested"]:
                    break
            if len(commands) > 1:
                self._append_log(
                    f"[rerun] Command {index}/{len(commands)}: "
                    f"{_summarize_command_texts([shlex.join(command)])}",
                    command_index=index,
                )
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(self.cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    start_new_session=os.name != "nt",
                )
            except OSError as exc:
                returncode = returncode or 1
                self._append_log(f"[rerun] Unable to start evaluator command: {exc}")
                continue

            with self._lock:
                if not self._job or self._job.get("id") != job_id:
                    process.terminate()
                    return
                self._process = process
                self._job["pid"] = process.pid
                should_stop = bool(self._job["stop_requested"])
                self._job["status"] = "stopping" if should_stop else "running"
            if should_stop:
                self._terminate(process)

            if process.stdout is not None:
                for line in process.stdout:
                    self._append_log(line, command_index=index)
            command_returncode = process.wait()
            if command_returncode and returncode == 0:
                returncode = command_returncode
            with self._lock:
                self._process = None
                if self._job and self._job.get("stop_requested"):
                    break
                stop_on_error = bool(
                    self._job and self._job.get("config", {}).get("stop_on_error")
                )
            if command_returncode and stop_on_error:
                break

        self._invalidate_interrupted_run(job_id)

        if rebuild_root is not None:
            try:
                _rebuild_batch_metrics(rebuild_root)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                returncode = returncode or 1
                self._append_log(f"[rerun] Failed to rebuild batch metrics: {exc}")
        with self._lock:
            if self._job and self._job.get("id") == job_id:
                stopped = bool(self._job["stop_requested"])
                self._job.update({
                    "status": "stopped" if stopped else ("succeeded" if returncode == 0 else "failed"),
                    "ended_at": _utc_now(),
                    "returncode": returncode,
                })
                self._process = None

    def _invalidate_interrupted_run(self, job_id: str) -> None:
        """Make the run that a stop cut short count as not completed.

        Killing the evaluator mid-run leaves no fresh result file, but a result
        file from an earlier attempt at the same run may still be sitting
        there. Preflight decides completion from that file alone, so leaving it
        would let Resume skip the very run the stop interrupted, and the run
        folder on disk would no longer be what the result claims.
        """
        with self._lock:
            if not self._job or self._job.get("id") != job_id:
                return
            if not self._job.get("stop_requested"):
                return
            run_name = str(self._job.get("current_run") or "").strip()
            output_root = str((self._job.get("config") or {}).get("out_path") or "").strip()
            self._job["current_run"] = None
        if not run_name or not output_root:
            return

        # Resolve before the containment check: on macOS the output root can be
        # reached through a symlink (/var -> /private/var), and comparing a
        # resolved path against an unresolved root rejects every candidate.
        root = Path(output_root).expanduser().resolve()
        paths = [
            path
            for path in _interrupted_run_completion_paths(root, run_name)
            if path.exists() or path.is_symlink()
        ]
        if not paths:
            self._append_log(
                f"[stop] {run_name} was interrupted; it has no completed result, "
                "so Resume will run it again."
            )
            return
        try:
            _delete_rerun_paths(paths)
        except OSError as exc:
            self._append_log(
                f"[stop] Unable to clear the interrupted run {run_name}: {exc}. "
                "Choose Start from beginning, or delete its result file by hand."
            )
            return
        self._append_log(
            f"[stop] {run_name} was interrupted; discarded its stale result so "
            "Resume will run it again."
        )

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        try:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        except (OSError, ProcessLookupError):
            pass

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if not self._job or self._job.get("status") not in self.ACTIVE_STATUSES:
                raise RuntimeError("no evaluator job is running")
            self._job["stop_requested"] = True
            self._job["status"] = "stopping"
            process = self._process
        if process is not None:
            self._terminate(process)
        return self.snapshot()


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


def _nested(data: Any, *keys: str, default: Any = None) -> Any:
    value = data
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _assignment_produces_pivot(assignment: Any) -> bool:
    if not isinstance(assignment, dict):
        return False
    outputs: list[Any] = []
    for key in ("declared_outputs", "actual_outputs", "outputs", "produces"):
        values = assignment.get(key)
        if isinstance(values, list):
            outputs.extend(values)
    return any(str(value or "").strip().lower().startswith("pivot(") for value in outputs)


def _flag_assignments(result: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _nested(
        result,
        "phase_results",
        "flag-sequencing",
        "plan_payload",
        default={},
    )
    assignments = payload.get("flag_assignments") if isinstance(payload, dict) else []
    if not isinstance(assignments, list):
        return []
    return [assignment for assignment in assignments if isinstance(assignment, dict)]


def _challenge_key(assignment: dict[str, Any]) -> str:
    generator_id = str(
        assignment.get("id")
        or assignment.get("generator_id")
        or ""
    ).strip()
    if not generator_id:
        generator_id = str(
            assignment.get("name")
            or assignment.get("generator_name")
            or ""
        ).strip()
    if not generator_id:
        return ""
    catalog = str(assignment.get("generator_catalog") or "flag_generators").strip()
    return f"{catalog.lower()}:{generator_id.lower()}"


def _assignment_catalog(assignment: dict[str, Any]) -> str:
    return str(assignment.get("generator_catalog") or "flag_generators").strip().lower().replace(
        "-", "_"
    )


def _selected_vulnerabilities(result: dict[str, Any]) -> list[dict[str, str]]:
    selected = _nested(result, "metadata", "vulnerability_selection", "selected", default=[])
    if not isinstance(selected, list):
        return []
    vulnerabilities = []
    for item in selected:
        if isinstance(item, str):
            identity = item.strip()
            name = identity
        elif isinstance(item, dict):
            identity = str(item.get("name") or item.get("id") or item.get("path") or "").strip()
            name = str(item.get("name") or item.get("id") or identity).strip()
        else:
            continue
        if identity:
            vulnerabilities.append({"id": identity, "name": name or identity})
    return vulnerabilities


def _record_inventory_item(
    inventory: dict[str, dict[str, Any]],
    *,
    key: str,
    item_id: str,
    name: str,
    catalog: str,
    run_id: str,
    spec_name: str,
) -> None:
    entry = inventory.setdefault(
        key,
        {
            "id": item_id,
            "name": name,
            "catalog": catalog,
            "count": 0,
            "_runs": {},
        },
    )
    entry["count"] += 1
    run_entry = entry["_runs"].setdefault(
        run_id,
        {"run_id": run_id, "spec_name": spec_name, "count": 0},
    )
    run_entry["count"] += 1


def _serialize_inventory(inventory: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in inventory.values():
        runs = sorted(
            entry["_runs"].values(),
            key=lambda row: (row["spec_name"], row["run_id"]),
        )
        rows.append({
            "id": entry["id"],
            "name": entry["name"],
            "catalog": entry["catalog"],
            "count": entry["count"],
            "run_count": len(runs),
            "runs": runs,
        })
    return sorted(rows, key=lambda row: (-row["count"], row["name"].lower(), row["id"]))


def _timing_breakdown(
    phases: list[dict[str, Any]],
    total_duration_s: float,
) -> dict[str, float]:
    buckets = {"create": 0.0, "test": 0.0, "run": 0.0}
    for phase in phases:
        phase_name = str(phase.get("phase") or "").strip().lower().replace("_", "-")
        duration_s = _number(phase.get("duration_s"))
        if phase_name == "scenario-xml":
            buckets["create"] += duration_s
        elif phase_name in {"preview-plan", "flag-sequencing"}:
            buckets["test"] += duration_s
        elif phase_name in {"execute", "topo", "topology"}:
            buckets["run"] += duration_s
    measured_phase_total = sum(buckets.values())
    return {
        "create_duration_s": round(buckets["create"], 6),
        "test_duration_s": round(buckets["test"], 6),
        "run_duration_s": round(buckets["run"], 6),
        "total_duration_s": round(max(total_duration_s, measured_phase_total), 6),
    }


def _content_counts(result: dict[str, Any], row: dict[str, Any]) -> dict[str, int | float]:
    """Recover generated-content counts from both flat and raw result shapes."""
    content = _nested(result, "metrics", "content", default={})
    flag_payload = _nested(
        result,
        "phase_results",
        "flag-sequencing",
        "plan_payload",
        default={},
    )
    assignments = _flag_assignments(result)
    chain = flag_payload.get("chain") if isinstance(flag_payload, dict) else []
    chain = chain if isinstance(chain, list) else []
    raw_chain_length = flag_payload.get("length") if isinstance(flag_payload, dict) else 0
    chain_length = max(_integer(raw_chain_length), len(chain), len(assignments))

    challenge_count = max(
        _integer(row.get("challenge_count")),
        _integer(_nested(content, "challenges", "count", default=0)),
        len(assignments),
        chain_length,
    )
    chain_count = max(
        _integer(row.get("chain_count")),
        _integer(_nested(content, "chains", "count", default=0)),
        1 if chain_length else 0,
    )
    average_chain_length = max(
        _number(row.get("average_chain_length")),
        _number(_nested(content, "chains", "average_length", default=0)),
        float(chain_length) if chain_count else 0.0,
    )
    pivot_count = max(
        _integer(row.get("pivot_count")),
        _integer(_nested(content, "challenges", "pivot_count", default=0)),
        sum(1 for assignment in assignments if _assignment_produces_pivot(assignment)),
    )
    pivot_provider_count = max(
        _integer(row.get("pivot_provider_count")),
        _integer(_nested(content, "topology", "pivot_provider_count", default=0)),
        _integer(
            _nested(
                result,
                "phase_results",
                "preview-plan",
                "plan_payload",
                "full_preview",
                "display_artifacts",
                "segmentation",
                "json",
                "metadata",
                "pivot_access",
                "provider_count",
                default=0,
            )
        ),
    )
    return {
        "challenge_count": challenge_count,
        "chain_count": chain_count,
        "average_chain_length": average_chain_length,
        "pivot_count": pivot_count,
        "pivot_provider_count": pivot_provider_count,
    }


def _result_file_for_run(root: Path, run_id: str) -> Path:
    if not run_id:
        raise ValueError("run_id must be a non-empty string")
    candidate = (root / run_id).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("result path is outside the dashboard root") from exc
    is_result_file = (
        candidate.name == "run_metrics_raw.json"
        or candidate.name.endswith("_result.json")
    )
    if not candidate.is_file() or not is_result_file:
        raise ValueError("result file was not found")
    return candidate


def _folder_for_run(root: Path, run_id: str | None) -> Path:
    if not run_id:
        return root
    return _result_file_for_run(root, run_id).parent


def _path_inside_root(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path != root else None


def _rerun_target(root: Path, run_id: str) -> dict[str, Any]:
    result_path = _result_file_for_run(root, run_id)
    if not result_path.name.endswith("_result.json"):
        raise ValueError(f"run cannot be re-run from fallback metrics: {run_id}")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read selected run {run_id}: {exc}") from exc
    if not isinstance(result, dict):
        raise ValueError(f"selected run is not a result object: {run_id}")

    metadata = result.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    raw_spec_file = metadata.get("spec_file")
    if not isinstance(raw_spec_file, str) or not raw_spec_file.strip():
        raise ValueError(f"selected run does not record its source spec: {run_id}")
    spec_file = Path(raw_spec_file).expanduser().resolve()
    if not spec_file.is_file() or not spec_file.name.endswith(".spec.yaml"):
        raise ValueError(f"source spec was not found for selected run: {spec_file}")

    iteration_index = _integer(metadata.get("iteration_index"))
    if iteration_index < 1:
        raise ValueError(f"selected run does not record a valid iteration index: {run_id}")
    target_phase = str(metadata.get("target_phase") or "execute").strip().lower()
    if target_phase not in {"scenario-xml", "topology", "flag-sequencing", "execute"}:
        raise ValueError(f"selected run has an unsupported target phase: {target_phase}")
    spec_name = str(metadata.get("spec_name") or result_path.name.removesuffix("_result.json"))

    cleanup_paths: list[Path] = [result_path]
    artifacts = result.get("artifacts") or {}
    if isinstance(artifacts, dict):
        for key in ("output_dir", "scenarioforge_webui_xml_collection"):
            artifact_path = _path_inside_root(root, artifacts.get(key))
            if artifact_path is not None:
                cleanup_paths.append(artifact_path)
    for path in (
        result_path.parent / f"{spec_name}_ai_prompt.md",
        result_path.parent / "metrics" / "runs" / Reporter._safe_metric_dir_name(spec_name),
    ):
        safe_path = _path_inside_root(root, str(path))
        if safe_path is not None:
            cleanup_paths.append(safe_path)

    return {
        "run_id": run_id,
        "result_path": result_path,
        "spec_file": spec_file,
        "iteration_index": iteration_index,
        "target_phase": target_phase,
        "cleanup_paths": cleanup_paths,
    }


def _build_rerun_plan(
    payload: Any,
    *,
    root: Path,
    cwd: Path,
) -> tuple[list[list[str]], dict[str, Any], tuple[Path, ...]]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    run_ids = payload.get("run_ids")
    if not isinstance(run_ids, list) or not run_ids:
        raise ValueError("select at least one run to re-run")
    if len(run_ids) > 100:
        raise ValueError("no more than 100 runs may be re-run at once")
    if any(not isinstance(run_id, str) or not run_id.strip() for run_id in run_ids):
        raise ValueError("run_ids must contain non-empty strings")
    unique_run_ids = list(dict.fromkeys(run_ids))
    replace_original = payload.get("replace_original", False)
    if not isinstance(replace_original, bool):
        raise ValueError("replace_original must be a boolean")

    sf_path = _resolve_execution_path(
        payload.get("sf_path"), label="ScenarioForge path", base=cwd, must_exist=True
    )
    if not sf_path.is_dir():
        raise ValueError(f"ScenarioForge path is not a directory: {sf_path}")

    targets = [_rerun_target(root, run_id) for run_id in unique_run_ids]
    if replace_original:
        preserved_output_root = None
    else:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        preserved_output_root = root / "reruns" / f"{stamp}-{uuid4().hex[:8]}"

    groups: dict[tuple[Path, str, Path], list[int]] = defaultdict(list)
    for target in targets:
        output_root = (
            target["result_path"].parent if replace_original else preserved_output_root
        )
        groups[(target["spec_file"], target["target_phase"], output_root)].append(
            target["iteration_index"]
        )

    commands: list[list[str]] = []
    for (spec_file, phase, output_root), iteration_indexes in groups.items():
        command, _ = _build_execution_command(
            {
                "spec_path": str(spec_file),
                "sf_path": str(sf_path),
                "out_path": str(output_root),
                "phase": phase,
                "verbose": bool(payload.get("verbose")),
                "dangerous_cleanup_between_runs": bool(
                    payload.get("dangerous_cleanup_between_runs")
                ),
                "reproduction_mode": str(
                    payload.get("reproduction_mode") or "xml"
                ),
            },
            cwd=cwd,
        )
        for iteration_index in sorted(set(iteration_indexes)):
            command.extend(["--iteration-index", str(iteration_index)])
        commands.append(command)

    cleanup_paths = tuple(
        dict.fromkeys(
            path
            for target in targets
            for path in target["cleanup_paths"]
        )
    ) if replace_original else ()
    phases = {target["target_phase"] for target in targets}
    config = {
        "kind": "rerun",
        "run_count": len(unique_run_ids),
        "run_ids": unique_run_ids,
        "replace_original": replace_original,
        "spec_path": (
            str(targets[0]["spec_file"])
            if len({target["spec_file"] for target in targets}) == 1
            else f"{len({target['spec_file'] for target in targets})} selected specs"
        ),
        "sf_path": str(sf_path),
        "out_path": (
            str(preserved_output_root)
            if preserved_output_root is not None
            else "Original result folders"
        ),
        "phase": next(iter(phases)) if len(phases) == 1 else "mixed",
        "verbose": bool(payload.get("verbose")),
        "stop_on_error": False,
        "dangerous_cleanup_between_runs": bool(
            payload.get("dangerous_cleanup_between_runs")
        ),
        "reproduction_mode": str(payload.get("reproduction_mode") or "xml"),
    }
    return commands, config, cleanup_paths


def _delete_rerun_paths(paths: Iterable[Path]) -> None:
    unique_paths = sorted(
        set(paths),
        key=lambda path: (len(path.parts), str(path)),
        reverse=True,
    )
    for path in unique_paths:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def _rebuild_batch_metrics(root: Path) -> None:
    results: list[dict[str, Any]] = []
    for result_path in sorted(root.rglob("*_result.json")):
        if not result_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(result, dict) and "success" in result:
            results.append(result)
    Reporter(str(root)).write_batch_metrics(results)


def _open_folder(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    else:
        command = ["xdg-open", str(path)]
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _picker_initial_folder(value: Any) -> Path:
    if isinstance(value, str) and value.strip():
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        candidate = candidate.resolve()
        if candidate.is_file():
            candidate = candidate.parent
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        if candidate.is_dir():
            return candidate
    return PROJECT_ROOT


def _select_path(kind: str, initial_path: Any = None) -> str | None:
    """Open a native picker on the dashboard host and return a selected path."""
    if kind not in {"file", "folder"}:
        raise ValueError("picker kind must be 'file' or 'folder'")
    initial_folder = _picker_initial_folder(initial_path)

    if sys.platform == "darwin":
        chooser = "choose file" if kind == "file" else "choose folder"
        prompt = "Select a ScenarioForge evaluator spec" if kind == "file" else "Select a folder"
        script = f"""
on run argv
  set initialLocation to POSIX file (item 1 of argv)
  try
    set selectedItem to {chooser} with prompt "{prompt}" default location initialLocation
    return POSIX path of selectedItem
  on error number -128
    return ""
  end try
end run
"""
        command = ["osascript", "-e", script, str(initial_folder)]
    else:
        dialog = "askopenfilename" if kind == "file" else "askdirectory"
        script = (
            "import sys, tkinter as tk; from tkinter import filedialog; "
            "root=tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
            f"value=filedialog.{dialog}(initialdir=sys.argv[1]); "
            "print(value); root.destroy()"
        )
        command = [sys.executable, "-c", script, str(initial_folder)]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise OSError(f"unable to open native path picker: {exc}") from exc
    selected = str(result.stdout or "").strip()
    if not selected:
        if result.returncode != 0:
            detail = str(result.stderr or "").strip()
            raise OSError(detail or "native path picker failed")
        return None
    path = Path(selected).expanduser().resolve()
    if kind == "file" and not path.is_file():
        raise OSError(f"selected file was not found: {path}")
    if kind == "folder" and not path.is_dir():
        raise OSError(f"selected folder was not found: {path}")
    return str(path)


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
    unique_challenge_keys: set[str] = set()
    identified_challenge_occurrences = 0
    identified_vulnerability_occurrences = 0
    inventory_maps: dict[str, dict[str, dict[str, Any]]] = {
        "challenges": {},
        "flag_node_generators": {},
        "flag_generators": {},
        "vulnerabilities": {},
    }

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
        content_counts = _content_counts(result, row)
        phase_rows = _phase_rows_from_result(reporter, index, result)
        run_id = relative_path
        metadata = result.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        spec_name = str(
            row.get("spec_name")
            or result.get("spec_name")
            or metadata.get("spec_name")
            or candidate.name.removesuffix("_result.json")
        )
        spec_file = str(metadata.get("spec_file") or "").strip()
        iteration_index = _integer(
            row.get("iteration_index") or metadata.get("iteration_index")
        )
        target_phase = str(
            row.get("target_phase") or metadata.get("target_phase") or "execute"
        ).strip().lower()
        source_spec = Path(spec_file).expanduser() if spec_file else None
        rerunnable = bool(
            candidate.name.endswith("_result.json")
            and spec_file
            and source_spec is not None
            and source_spec.is_file()
            and source_spec.name.endswith(".spec.yaml")
            and iteration_index >= 1
            and target_phase in {"scenario-xml", "topology", "flag-sequencing", "execute"}
        )
        if rerunnable:
            rerun_unavailable_reason = ""
        elif not candidate.name.endswith("_result.json"):
            rerun_unavailable_reason = "Fallback metrics do not identify a rerunnable result"
        elif not spec_file:
            rerun_unavailable_reason = "Result does not record its source spec"
        elif source_spec is None or not source_spec.is_file():
            rerun_unavailable_reason = "Source spec file is no longer available"
        elif not source_spec.name.endswith(".spec.yaml"):
            rerun_unavailable_reason = "Source spec is not a .spec.yaml file"
        elif target_phase not in {"scenario-xml", "topology", "flag-sequencing", "execute"}:
            rerun_unavailable_reason = "Result records an unsupported target phase"
        else:
            rerun_unavailable_reason = "Result does not record a valid iteration index"
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

        assignments = _flag_assignments(result)
        challenge_keys = [key for key in (_challenge_key(item) for item in assignments) if key]
        unique_challenge_keys.update(challenge_keys)
        identified_challenge_occurrences += len(challenge_keys)
        for assignment in assignments:
            key = _challenge_key(assignment)
            if not key:
                continue
            item_id = str(
                assignment.get("id")
                or assignment.get("generator_id")
                or assignment.get("name")
                or assignment.get("generator_name")
            ).strip()
            name = str(
                assignment.get("name")
                or assignment.get("generator_name")
                or item_id
            ).strip()
            catalog = _assignment_catalog(assignment)
            _record_inventory_item(
                inventory_maps["challenges"],
                key=key,
                item_id=item_id,
                name=name,
                catalog=catalog,
                run_id=run_id,
                spec_name=spec_name,
            )
            if catalog in {"flag_node_generators", "flag_generators"}:
                _record_inventory_item(
                    inventory_maps[catalog],
                    key=key,
                    item_id=item_id,
                    name=name,
                    catalog=catalog,
                    run_id=run_id,
                    spec_name=spec_name,
                )

        vulnerabilities = _selected_vulnerabilities(result)
        identified_vulnerability_occurrences += len(vulnerabilities)
        for vulnerability in vulnerabilities:
            key = vulnerability["id"].lower()
            _record_inventory_item(
                inventory_maps["vulnerabilities"],
                key=key,
                item_id=vulnerability["id"],
                name=vulnerability["name"],
                catalog="vulnerabilities",
                run_id=run_id,
                spec_name=spec_name,
            )
        timing = _timing_breakdown(normalized_phases, _number(row.get("duration_s")))

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
            "target_phase": target_phase,
            "spec_file": spec_file,
            "seed": row.get("seed", ""),
            "iteration_index": iteration_index or "",
            "iteration_count": row.get("iteration_count", ""),
            "rerunnable": rerunnable,
            "rerun_unavailable_reason": rerun_unavailable_reason,
            "router_count": _integer(row.get("router_count")),
            "host_count": _integer(row.get("host_count")),
            "node_count": _integer(row.get("node_count")),
            "service_count": _integer(row.get("service_count")),
            "vulnerability_count": _integer(row.get("vulnerability_count")),
            "challenge_count": content_counts["challenge_count"],
            "unique_challenge_count": len(set(challenge_keys)),
            "unique_challenges_complete": (
                len(challenge_keys) >= content_counts["challenge_count"]
            ),
            "chain_count": content_counts["chain_count"],
            "average_chain_length": content_counts["average_chain_length"],
            "pivot_count": content_counts["pivot_count"],
            "pivot_provider_count": content_counts["pivot_provider_count"],
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
            **timing,
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

    inventories = {
        name: _serialize_inventory(items)
        for name, items in inventory_maps.items()
    }
    flag_node_generator_total = sum(
        row["count"] for row in inventories["flag_node_generators"]
    )
    flag_generator_total = sum(row["count"] for row in inventories["flag_generators"])
    vulnerability_total = sum(row["vulnerability_count"] for row in runs)

    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
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
            "unique_challenges": len(unique_challenge_keys),
            "unique_challenges_complete": identified_challenge_occurrences >= sum(
                row["challenge_count"] for row in runs
            ),
            "flag_node_generators_unique": len(inventories["flag_node_generators"]),
            "flag_node_generators_total": flag_node_generator_total,
            "flag_generators_unique": len(inventories["flag_generators"]),
            "flag_generators_total": flag_generator_total,
            "vulnerabilities_unique": len(inventories["vulnerabilities"]),
            "vulnerabilities_total": vulnerability_total,
            "vulnerabilities_complete": identified_vulnerability_occurrences >= vulnerability_total,
            "chains": sum(row["chain_count"] for row in runs),
            "pivot_challenges": sum(row["pivot_count"] for row in runs),
            "pivot_providers": sum(row["pivot_provider_count"] for row in runs),
            "pivots": sum(row["pivot_count"] for row in runs),
            "pivot_total": sum(
                row["pivot_count"] + row["pivot_provider_count"] for row in runs
            ),
        },
        "failure_stages": [
            {"stage": stage, "count": count}
            for stage, count in failure_stages.most_common()
        ],
        "phase_summary": phase_summary,
        "inventories": inventories,
        "runs": runs,
    }


def create_app(root_path: str | os.PathLike[str]) -> Flask:
    root = Path(root_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"dashboard root is not a directory: {root}")

    app = Flask(__name__)
    app.config["DASHBOARD_ROOT"] = str(root)
    execution_manager = EvaluationJobManager(PROJECT_ROOT)
    app.extensions["evaluation_job_manager"] = execution_manager

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

    @app.get("/api/execution")
    def execution_status():
        try:
            after = max(0, int(request.args.get("after", "0")))
        except ValueError:
            return jsonify({"ok": False, "error": "after must be an integer"}), 400
        snapshot = execution_manager.snapshot(after=after)
        settings = _load_dashboard_settings()
        execution_settings = settings.get("execution")
        if not isinstance(execution_settings, dict):
            execution_settings = {}
        snapshot["defaults"] = {
            "spec_path": execution_settings.get("spec_path") or str(PROJECT_ROOT / "test_specs"),
            "sf_path": execution_settings.get("sf_path")
            or str((PROJECT_ROOT.parent / "scenarioforge").resolve()),
            "out_path": app.config["DASHBOARD_ROOT"],
            "phase": execution_settings.get("phase") or "execute",
            "reproduction_mode": execution_settings.get("reproduction_mode") or "xml",
            "verbose": bool(execution_settings.get("verbose", False)),
            "stop_on_error": bool(execution_settings.get("stop_on_error", False)),
            "dangerous_cleanup_between_runs": bool(
                execution_settings.get("dangerous_cleanup_between_runs", False)
            ),
        }
        response = jsonify(snapshot)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/api/execution")
    def start_execution():
        try:
            commands, config, cleanup_paths = _build_execution_plan(
                request.get_json(silent=True),
                cwd=PROJECT_ROOT,
            )
            _save_execution_settings(config)
            snapshot = execution_manager.start_commands(
                commands,
                config=config,
                cleanup_paths=cleanup_paths,
                rebuild_root=Path(config["out_path"]),
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        return jsonify({"ok": True, **snapshot}), 202

    @app.post("/api/execution/preflight")
    def execution_preflight():
        try:
            preflight, _ = _scan_execution_runs(
                request.get_json(silent=True),
                cwd=PROJECT_ROOT,
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, **preflight})

    @app.post("/api/rerun")
    def rerun_selected():
        try:
            current_root = Path(app.config["DASHBOARD_ROOT"]).resolve()
            commands, config, cleanup_paths = _build_rerun_plan(
                request.get_json(silent=True),
                root=current_root,
                cwd=PROJECT_ROOT,
            )
            snapshot = execution_manager.start_commands(
                commands,
                config=config,
                cleanup_paths=cleanup_paths,
                rebuild_root=current_root,
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        return jsonify({"ok": True, **snapshot}), 202

    @app.post("/api/execution/stop")
    def stop_execution():
        try:
            snapshot = execution_manager.stop()
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        return jsonify({"ok": True, **snapshot})

    @app.post("/api/data-source")
    def set_data_source():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "request body must be a JSON object"}), 400
        raw_path = payload.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return jsonify({"ok": False, "error": "path must be a non-empty string"}), 400
        data_root = Path(raw_path).expanduser().resolve()
        if not data_root.is_dir():
            return jsonify({"ok": False, "error": f"folder was not found: {data_root}"}), 400
        app.config["DASHBOARD_ROOT"] = str(data_root)
        _save_dashboard_settings({"root": str(data_root)})
        return jsonify({"ok": True, "root": str(data_root)})

    @app.post("/api/select-path")
    def select_path():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "request body must be a JSON object"}), 400
        kind = payload.get("kind")
        if kind not in {"file", "folder"}:
            return jsonify({"ok": False, "error": "kind must be 'file' or 'folder'"}), 400
        try:
            selected = _select_path(kind, payload.get("initial_path"))
        except (OSError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500
        if selected is None:
            return jsonify({"ok": True, "cancelled": True})
        return jsonify({"ok": True, "cancelled": False, "path": selected})

    @app.post("/api/open-folder")
    def open_folder():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "request body must be a JSON object"}), 400
        run_id = payload.get("run_id")
        if run_id is not None and not isinstance(run_id, str):
            return jsonify({"ok": False, "error": "run_id must be a string"}), 400
        try:
            current_root = Path(app.config["DASHBOARD_ROOT"])
            folder = _folder_for_run(current_root, run_id)
            _open_folder(folder)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except OSError as exc:
            return jsonify({"ok": False, "error": f"unable to open folder: {exc}"}), 500
        return jsonify({"ok": True, "folder": str(folder)})

    @app.get("/healthz")
    def health():
        return {
            "ok": True,
            "root": app.config["DASHBOARD_ROOT"],
            "schema_version": DASHBOARD_SCHEMA_VERSION,
        }

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Browse ScenarioForge evaluator run metrics")
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help=(
            "Parent folder containing *_result.json files "
            "(defaults to the last folder used by the dashboard)"
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", default=8088, type=int, help="Bind port (default: 8088)")
    parser.add_argument("--open", action="store_true", help="Open the dashboard in the default browser")
    args = parser.parse_args(argv)

    settings = _load_dashboard_settings()
    if args.root:
        root = Path(args.root).expanduser().resolve()
    elif settings.get("root"):
        root = Path(str(settings["root"])).expanduser().resolve()
    else:
        parser.error("root is required on first run (no previously used folder is saved yet)")
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    _save_dashboard_settings({"root": str(root)})

    url_host = "localhost" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{url_host}:{args.port}"
    print(f"ScenarioForge Eval dashboard: {url}")
    print(f"Scanning: {root}")
    if args.open:
        Timer(0.75, lambda: webbrowser.open(url)).start()
    create_app(root).run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
