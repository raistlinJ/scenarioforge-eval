import fnmatch
import hashlib
import ipaddress
import json
import os
import queue
import random
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import traceback
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager, nullcontext
from copy import deepcopy

try:
    import fcntl
    msvcrt = None
except ImportError:
    # Windows: _lock_file_exclusive falls back to msvcrt byte-range locking.
    import msvcrt
    fcntl = None

try:
    from .metrics import MetricSpan, directory_metrics, file_metrics, rounded_seconds, text_metrics
    from .parser import AI_TIMEOUT_CEILING_S
    from .reproduction import (
        REPRODUCTION_MODES,
        artifact_source_paths,
        create_reproduction_bundle,
        local_artifact_source,
    )
except ImportError:
    from metrics import MetricSpan, directory_metrics, file_metrics, rounded_seconds, text_metrics
    from parser import AI_TIMEOUT_CEILING_S
    from reproduction import (
        REPRODUCTION_MODES,
        artifact_source_paths,
        create_reproduction_bundle,
        local_artifact_source,
    )


def _lock_file_exclusive(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return
    # msvcrt.locking gives up after ~10s of contention, so retry until the
    # byte range is ours to match flock's block-until-acquired behaviour.
    handle.seek(0)
    while True:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            return
        except OSError:
            continue


def _unlock_file(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


class PhaseExecutionError(RuntimeError):
    def __init__(self, message: str, phase_result: dict):
        super().__init__(message)
        self.phase_result = phase_result

class Executor:
    DEFAULT_VM_SAFE_SERVICES = ("SSH", "HTTP")
    ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    ARTIFACT_CHECK_STEP_RE = re.compile(
        r"\[check-artifacts\]\s+Step\s+(\d+)(?:/(\d+))?:\s*(.*)",
        re.IGNORECASE,
    )
    ARTIFACT_CHECK_STEP_LABELS = (
        "Containers running on correct nodes",
        "Services running",
        "Ports open",
        "Inject files placed",
        "Firewall/segmentation rules in place",
        "Required traffic agents running",
        "Required traffic reaches its destination",
        "Flow pivot paths traversable (source → target)",
        "Pivot providers reachable from the participant",
    )
    VALIDATION_ERROR_FIELDS = (
        'missing_nodes',
        'missing_docker_nodes',
        'missing_vuln_nodes',
        'docker_missing',
        'docker_not_running',
        'generator_outputs_missing',
        'flow_live_paths_missing',
        'validation_unavailable',
        'error',
        'flow_artifact_copy_error',
    )
    # Wall-clock the ai phase gets beyond the provider's own timeout, to cover
    # the bridge's tool-call round-trips.
    AI_PHASE_TIMEOUT_HEADROOM_S = 300
    AI_RETRYABLE_ERROR_RE = re.compile(
        r"tim(?:ed\s*out|eout)|read\s+timed\s+out|deadline\s+exceeded",
        re.IGNORECASE,
    )
    VALIDATION_WARNING_FIELDS = (
        'extra_nodes',
        'extra_docker_nodes',
        'docker_start_pending',
        'injects_missing',
        'generator_injects_missing',
    )

    def __init__(
        self,
        spec: dict,
        out_dir: str,
        sf_path: str,
        target_phase: str = "execute",
        verbose: bool = False,
        dangerous_cleanup_between_runs: bool = False,
        stream_execute_output: bool = False,
        reproduction_mode: str = "xml",
    ):
        self.spec = spec
        self.out_dir = os.path.abspath(os.path.expanduser(out_dir))
        self.sf_path = os.path.abspath(os.path.expanduser(sf_path))
        self.target_phase = target_phase
        self.verbose = verbose
        self.dangerous_cleanup_between_runs = bool(dangerous_cleanup_between_runs)
        self.stream_execute_output = bool(stream_execute_output)
        self.reproduction_mode = str(reproduction_mode or "xml").strip().lower()
        if self.reproduction_mode not in REPRODUCTION_MODES:
            raise ValueError(
                f"reproduction_mode must be one of {', '.join(REPRODUCTION_MODES)}"
            )
        self.seed = self._resolve_seed(self.spec.get('seed'))
        self._rng = random.Random(self.seed)
        self._vulnerability_selection: dict | None = None
        self._flag_node_generator_selection: dict | None = None
        self._ai_generation: dict | None = None
        self._ai_phase_results: list[dict] = []
        self._ai_warnings: list[str] = []
        self._artifact_check_progress_active = False
        self._artifact_check_last_step = 0
        self._artifact_check_total_steps = 0
        self.phase_timeout_s = self._resolve_phase_timeout()
        self.cleanup_timeout_s = self._resolve_cleanup_timeout()
        os.makedirs(self.out_dir, exist_ok=True)
        try:
            os.chmod(self.out_dir, 0o700)
        except OSError:
            pass
        
        # Dynamically add scenarioforge to the path
        if self.sf_path not in sys.path:
            sys.path.insert(0, self.sf_path)

    def _resolve_seed(self, raw_seed) -> int:
        try:
            return int(raw_seed)
        except Exception:
            return random.SystemRandom().randint(0, 2**31 - 1)

    def _resolve_phase_timeout(self) -> int:
        raw_timeout = str(os.environ.get('SCENARIOFORGE_EVAL_PHASE_TIMEOUT_S') or '1200').strip()
        try:
            timeout_s = int(raw_timeout)
        except Exception:
            timeout_s = 1200
        return max(timeout_s, 1)

    def _resolve_cleanup_timeout(self) -> int:
        raw_timeout = str(os.environ.get('SCENARIOFORGE_EVAL_CLEANUP_TIMEOUT_S') or '900').strip()
        try:
            timeout_s = int(raw_timeout)
        except Exception:
            timeout_s = 900
        return max(timeout_s, 1)

    def _load_runtime_env(self) -> None:
        from pathlib import Path
        from webapp.env_loader import load_runtime_env_files

        load_runtime_env_files(base_dir=Path(self.sf_path), include_example=False)

    def _cli_python(self) -> str:
        override = str(os.environ.get('SCENARIOFORGE_EVAL_SCENARIOFORGE_PYTHON') or '').strip()
        if override:
            return override
        repo_python = os.path.join(self.sf_path, '.venv', 'bin', 'python')
        if os.path.exists(repo_python):
            return repo_python
        return sys.executable

    def _cli_env(self) -> dict[str, str]:
        env = dict(os.environ)
        pieces = [self.sf_path]
        preserve_pythonpath = str(env.get('SCENARIOFORGE_EVAL_PRESERVE_PYTHONPATH') or '').strip().lower() in {
            '1',
            'true',
            'yes',
            'y',
            'on',
        }
        existing = str(env.get('PYTHONPATH') or '').strip()
        if preserve_pythonpath and existing:
            pieces.append(existing)
        env['PYTHONPATH'] = os.pathsep.join(pieces)
        env['NO_COLOR'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        return env

    def _artifact_path(self, file_name: str | None) -> str | None:
        if not file_name:
            return None
        return os.path.join(self.out_dir, file_name)

    def _scenarioforge_repo_write_error(self, directory: str, exc: OSError) -> RuntimeError:
        repo_root = self.sf_path
        outputs_root = os.path.join(repo_root, 'outputs')
        uploads_root = os.path.join(repo_root, 'uploads')
        return RuntimeError(
            "ScenarioForge CLI needs a writable sibling repo checkout for runtime artifacts. "
            f"Failed to create or access {directory!r}: {exc}. "
            f"Ensure the evaluator user can write under {outputs_root!r} and {uploads_root!r}."
        )

    def _ensure_scenarioforge_repo_dirs(self) -> None:
        outputs_root = os.path.join(self.sf_path, 'outputs')
        candidate_dirs = {
            outputs_root,
            os.path.join(self.sf_path, 'uploads'),
        }

        for directory in sorted(candidate_dirs):
            try:
                os.makedirs(directory, exist_ok=True)
            except PermissionError as exc:
                raise self._scenarioforge_repo_write_error(directory, exc) from exc

    def _write_json_artifact(self, file_name: str, payload: dict) -> str:
        artifact_path = os.path.join(self.out_dir, file_name)
        with open(artifact_path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        return artifact_path

    def _snapshot_webui_xml(self, result: dict) -> str | None:
        """Preserve the final, phase-mutated XML as an explicit WebUI import artifact."""
        artifacts = result.setdefault('artifacts', {})
        source_path = artifacts.get('scenario_xml')
        if not isinstance(source_path, str) or not os.path.isfile(source_path):
            return None

        snapshot_path = os.path.join(self.out_dir, 'scenarioforge-webui.xml')
        if os.path.abspath(source_path) != os.path.abspath(snapshot_path):
            shutil.copy2(source_path, snapshot_path)
        try:
            os.chmod(snapshot_path, 0o600)
        except OSError:
            pass
        artifacts['scenarioforge_webui_xml'] = snapshot_path
        return snapshot_path

    def _snapshot_reproduction_bundle(self, result: dict, xml_path: str | None) -> str | None:
        """Package the final XML and replay/artifact data requested by the caller."""
        result.setdefault('metadata', {})['reproduction_mode'] = self.reproduction_mode
        if self.reproduction_mode == 'xml' or not xml_path:
            return None
        artifact_overrides: dict[str, str] = {}
        staging_dir = None
        if self.reproduction_mode == 'bundle':
            artifact_overrides, staging_dir = self._download_remote_reproduction_artifacts(
                xml_path,
                result,
            )
        try:
            bundle_path, manifest = create_reproduction_bundle(
                xml_path=xml_path,
                output_dir=self.out_dir,
                mode=self.reproduction_mode,
                seed=self.seed,
                sf_path=self.sf_path,
                eval_repo=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                artifact_overrides=artifact_overrides,
                ai_generation=self._ai_generation,
            )
        finally:
            if staging_dir:
                shutil.rmtree(staging_dir, ignore_errors=True)
        result.setdefault('artifacts', {})['scenarioforge_reproduction_bundle'] = bundle_path
        result['metadata']['reproduction_fidelity'] = manifest.get('fidelity')
        result['metadata']['reproduction_artifact_sources'] = len(
            manifest.get('artifact_sources') or []
        )
        result['metadata']['reproduction_artifact_sources_bundled'] = sum(
            1 for item in (manifest.get('artifact_sources') or []) if item.get('bundled')
        )
        return bundle_path

    def _download_remote_reproduction_artifacts(
        self,
        xml_path: str,
        result: dict,
    ) -> tuple[dict[str, str], str | None]:
        """Fetch remote-only generated Flow payloads for a portable bundle."""
        remote_sources = [
            source
            for source in artifact_source_paths(xml_path)
            if source.startswith('/tmp/vulns/')
            and not local_artifact_source(source, self.sf_path)
        ]
        if not remote_sources:
            return {}, None

        staging_dir = tempfile.mkdtemp(prefix='.reproduction-remote-', dir=self.out_dir)
        client = None
        sftp = None
        overrides: dict[str, str] = {}
        try:
            from webapp import app_backend as backend

            scenario_name = self._resolve_xml_scenario_name(xml_path)
            scenario_norm = backend._normalize_scenario_label(scenario_name)
            core_cfg = backend._core_config_from_xml_path(
                xml_path,
                scenario_norm,
                include_password=True,
            )
            try:
                runtime_cfg = backend._select_core_config_for_page(
                    scenario_norm,
                    include_password=True,
                )
            except Exception:
                runtime_cfg = None
            if isinstance(runtime_cfg, dict) and runtime_cfg:
                if isinstance(core_cfg, dict) and core_cfg:
                    core_cfg = backend._merge_core_configs(
                        runtime_cfg,
                        core_cfg,
                        include_password=True,
                    )
                else:
                    core_cfg = runtime_cfg
            if isinstance(core_cfg, dict):
                core_cfg = backend._apply_core_secret_to_config(core_cfg, scenario_norm)
            core_cfg = backend._require_core_ssh_credentials(core_cfg)
            client = backend._open_ssh_client(core_cfg)
            sftp = client.open_sftp()

            def download_dir(remote_root: str, local_root: str) -> None:
                os.makedirs(local_root, exist_ok=True)
                for item in sftp.listdir_attr(remote_root):
                    remote_child = backend._remote_path_join(remote_root, item.filename)
                    local_child = os.path.join(local_root, item.filename)
                    if stat.S_ISDIR(item.st_mode):
                        download_dir(remote_child, local_child)
                    elif stat.S_ISREG(item.st_mode):
                        sftp.get(remote_child, local_child)
                        try:
                            os.chmod(local_child, stat.S_IMODE(item.st_mode))
                        except OSError:
                            pass

            for index, source in enumerate(remote_sources, start=1):
                local_root = os.path.join(staging_dir, f'{index:03d}')
                try:
                    download_dir(source, local_root)
                except Exception:
                    shutil.rmtree(local_root, ignore_errors=True)
                    continue
                overrides[source] = local_root
        except Exception as exc:
            result.setdefault('metadata', {})['reproduction_remote_fetch_error'] = str(exc)
        finally:
            try:
                if sftp:
                    sftp.close()
            except Exception:
                pass
            try:
                if client:
                    client.close()
            except Exception:
                pass
        if not overrides:
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {}, None
        return overrides, staging_dir

    def _persist_seed_artifact(self) -> str:
        seed_path = os.path.join(self.out_dir, 'seed.txt')
        with open(seed_path, 'w', encoding='utf-8') as handle:
            handle.write(f"{self.seed}\n")
        return seed_path

    def _stream_cli_output(self, text: str) -> None:
        if not text:
            return
        progress_patterns = (
            'PHASE:',
            'Delegating CLI',
            'CORE_SESSION_ID:',
            'CORE_SESSION_VALIDATION_JSON:',
            'Post-execution validation:',
            'VALIDATION_SUMMARY_JSON:',
            'CHECK_ARTIFACTS_SUMMARY_JSON:',
            '[check-artifacts]',
            '[validate]',
            'CORE daemon runtime hint:',
            'Scenario report written to',
            'Scenario summary written to',
            'WARNING',
            'ERROR',
            'Traceback',
            'FATAL',
            '[cleanup]',
            '[images]',
        )
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if '[check-artifacts] Running checks against session' in line:
                self._artifact_check_progress_active = True
                self._artifact_check_last_step = 0
                self._artifact_check_total_steps = 0

            step_match = self.ARTIFACT_CHECK_STEP_RE.search(line)
            if step_match and self._artifact_check_progress_active:
                step = int(step_match.group(1))
                total = int(step_match.group(2) or 0)
                if total > 0:
                    self._artifact_check_total_steps = total
                self._print_missing_artifact_check_steps(step)

            if (
                'CHECK_ARTIFACTS_SUMMARY_JSON:' in line
                and self._artifact_check_progress_active
            ):
                self._complete_artifact_check_progress(line)

            if self.verbose or any(pattern in line for pattern in progress_patterns):
                print(f"  {line}")

            if step_match and self._artifact_check_progress_active:
                self._artifact_check_last_step = max(
                    self._artifact_check_last_step,
                    int(step_match.group(1)),
                )

    def _artifact_check_step_label(self, step: int) -> str:
        if 1 <= step <= len(self.ARTIFACT_CHECK_STEP_LABELS):
            return self.ARTIFACT_CHECK_STEP_LABELS[step - 1]
        return "Running"

    def _print_missing_artifact_check_steps(self, next_step: int) -> None:
        total = self._artifact_check_total_steps or len(self.ARTIFACT_CHECK_STEP_LABELS)
        for step in range(self._artifact_check_last_step + 1, next_step):
            label = self._artifact_check_step_label(step)
            print(f"  [check-artifacts] Step {step}/{total}: {label}")
            self._artifact_check_last_step = step

    def _complete_artifact_check_progress(self, marker_line: str) -> None:
        marker = 'CHECK_ARTIFACTS_SUMMARY_JSON:'
        try:
            payload = json.loads(marker_line.split(marker, 1)[1].strip())
        except (IndexError, json.JSONDecodeError, TypeError):
            payload = {}
        checks = payload.get('checks') if isinstance(payload, dict) else []
        completed_step = self._artifact_check_last_step
        if isinstance(checks, list) and checks:
            self._artifact_check_total_steps = len(checks)
            completed_step = max(
                [
                    index
                    for index, check in enumerate(checks, start=1)
                    if isinstance(check, dict)
                    and str(check.get('status') or '').strip().lower()
                    in {'pass', 'warn', 'fail', 'skip', 'error', 'running'}
                ]
                or [completed_step]
            )
        self._print_missing_artifact_check_steps(completed_step + 1)
        self._artifact_check_progress_active = False

    def _run_streaming_cli_command(self, cmd: list[str]) -> tuple[int | None, str, bool]:
        """Run a CLI command while forwarding selected output lines as they arrive."""
        proc = subprocess.Popen(
            cmd,
            cwd=self.sf_path,
            env=self._cli_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        output_lines: list[str] = []
        output_queue: queue.Queue[str | None] = queue.Queue()

        def _read_output() -> None:
            try:
                if proc.stdout is not None:
                    for line in proc.stdout:
                        output_queue.put(line)
            except (OSError, ValueError):
                # The timeout path may close the pipe to release this reader.
                pass
            finally:
                output_queue.put(None)

        def _stop_process() -> None:
            if proc.poll() is not None:
                return
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        reader = threading.Thread(target=_read_output, name='scenarioforge-eval-output', daemon=True)
        reader.start()
        deadline = time.monotonic() + self.phase_timeout_s
        timed_out = False
        reader_done = False

        while not reader_done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                line = output_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                continue
            if line is None:
                reader_done = True
                continue
            output_lines.append(line)
            self._stream_cli_output(line)

        if timed_out:
            _stop_process()
        else:
            remaining = max(0.001, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
                _stop_process()

        reader.join(timeout=1)
        if proc.stdout is not None:
            proc.stdout.close()
        reader.join(timeout=1)
        while True:
            try:
                line = output_queue.get_nowait()
            except queue.Empty:
                break
            if line is not None:
                output_lines.append(line)
                self._stream_cli_output(line)

        return proc.returncode, ''.join(output_lines), timed_out

    @classmethod
    def _clean_output(cls, text: str) -> str:
        return cls.ANSI_RE.sub('', text or '')

    @staticmethod
    def _coerce_subprocess_text(value) -> str:
        if value is None:
            return ''
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return str(value)

    @classmethod
    def _extract_last_json_marker(cls, text: str, marker: str) -> dict | None:
        clean = cls._clean_output(text)
        for line in reversed(clean.splitlines()):
            if marker not in line:
                continue
            try:
                return json.loads(line.split(marker, 1)[1].strip())
            except Exception:
                return None
        return None

    @classmethod
    def _extract_last_marker_value(cls, text: str, marker: str) -> str | None:
        clean = cls._clean_output(text)
        for line in reversed(clean.splitlines()):
            if marker not in line:
                continue
            value = line.split(marker, 1)[1].strip()
            return value or None
        return None

    def _phase_result(
        self,
        phase: str,
        returncode: int | None,
        combined: str,
        log_path: str | None,
        plan_payload: dict | None,
        *,
        timed_out: bool = False,
        stderr_output: str = '',
        metrics: dict | None = None,
    ) -> dict:
        result = {
            'phase': phase,
            'returncode': returncode,
            'combined_output': combined,
            'stderr_output': stderr_output,
            'log_path': log_path,
            'plan_payload': plan_payload,
            'session_id': None,
            'validation_summary': None,
            'check_artifacts_summary': None,
            'report_path': None,
            'summary_path': None,
            'timed_out': timed_out,
            'metrics': metrics or {},
        }
        if phase == 'execute':
            result['session_id'] = self._extract_last_marker_value(combined, 'CORE_SESSION_ID:')
            result['validation_summary'] = self._extract_last_json_marker(combined, 'VALIDATION_SUMMARY_JSON:')
            result['check_artifacts_summary'] = self._extract_last_json_marker(
                combined, 'CHECK_ARTIFACTS_SUMMARY_JSON:'
            )
            result['report_path'] = self._extract_last_marker_value(combined, 'Scenario report written to')
            result['summary_path'] = self._extract_last_marker_value(combined, 'Scenario summary written to')
        return result

    def _record_phase_result(self, result: dict, phase_result: dict) -> None:
        metadata = {
            'returncode': phase_result.get('returncode'),
            'log_path': phase_result.get('log_path'),
            'plan_payload': phase_result.get('plan_payload'),
            'session_id': phase_result.get('session_id'),
            'validation_summary': phase_result.get('validation_summary'),
            'check_artifacts_summary': phase_result.get('check_artifacts_summary'),
            'report_path': phase_result.get('report_path'),
            'summary_path': phase_result.get('summary_path'),
            'timed_out': bool(phase_result.get('timed_out')),
            'stderr_output': phase_result.get('stderr_output') or '',
            'metrics': phase_result.get('metrics') or {},
        }
        result.setdefault('phase_results', {})[phase_result['phase']] = metadata

    def _record_ai_generation(self, result: dict) -> None:
        """Attach prompt-generation provenance and its phase artifacts."""
        for phase_result in self._ai_phase_results:
            self._record_phase_result(result, phase_result)
            log_path = phase_result.get('log_path')
            if log_path:
                result.setdefault('artifacts', {})['ai_log'] = log_path
        if self._ai_warnings:
            warnings = result.setdefault('warnings', [])
            for warning in self._ai_warnings:
                if warning not in warnings:
                    warnings.append(warning)
        if not self._ai_generation:
            return
        result.setdefault('metadata', {})['ai_generation'] = self._ai_generation
        ai_json = self._artifact_path('ai.json')
        if ai_json and os.path.exists(ai_json):
            result.setdefault('artifacts', {})['ai_json'] = ai_json

    def _record_internal_phase_result(self, result: dict, phase: str, metrics: dict) -> None:
        self._record_phase_result(
            result,
            {
                'phase': phase,
                'returncode': None,
                'combined_output': '',
                'stderr_output': '',
                'log_path': None,
                'plan_payload': None,
                'session_id': None,
                'validation_summary': None,
                'report_path': None,
                'summary_path': None,
                'timed_out': False,
                'metrics': metrics,
            },
        )

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _nested(data: dict, *keys, default=None):
        value = data
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return default if value is None else value

    def _spec_metrics(self) -> dict:
        topology = self.spec.get('topology') or {}
        services = self.spec.get('services') or {}
        traffic = self.spec.get('traffic') or {}
        vulns = self.spec.get('vulns') or {}
        flag_node_generators = self.spec.get('flag_node_generators') or {}
        flows = self.spec.get('flows') or {}
        segmentation = self.spec.get('segmentation') or {}

        router_count = max(0, self._safe_int(topology.get('routers')))
        host_count = max(0, self._safe_int(topology.get('hosts')))
        service_count = max(0, self._safe_int(services.get('count'))) if services.get('enabled', services.get('randomize')) else 0
        traffic_count = sum(
            max(0, self._safe_int(item.get('v_count')))
            for item in (traffic.get('items') or [])
            if isinstance(item, dict)
        ) if traffic.get('enabled', traffic.get('randomize')) else 0
        vulnerability_count = max(0, self._safe_int(vulns.get('count'))) if vulns.get('enabled', vulns.get('randomize')) else 0
        flag_node_generator_count = (
            max(0, self._safe_int(flag_node_generators.get('count')))
            if flag_node_generators.get('enabled', flag_node_generators.get('randomize'))
            else 0
        )
        flow_enabled = bool(flows.get('enabled', flows.get('randomize')))
        flow_chain_length = max(0, self._safe_int(flows.get('chain_length'))) if flow_enabled else 0

        return {
            'name': self.spec.get('name', 'eval'),
            'seed': self.seed,
            'target_phase': self.target_phase,
            'validation_policy': self._validation_policy(),
            'topology': {
                'routers': router_count,
                'hosts': host_count,
                'nodes': router_count + host_count,
            },
            'services': {
                'enabled': bool(services.get('enabled', services.get('randomize'))),
                'count': service_count,
            },
            'traffic': {
                'enabled': bool(traffic.get('enabled', traffic.get('randomize'))),
                'profile': traffic.get('profile'),
                'payload_types': list(traffic.get('payload_types') or []),
                'density': traffic.get('density'),
                'count': traffic_count,
            },
            'vulnerabilities': {
                'enabled': bool(vulns.get('enabled', vulns.get('randomize'))),
                'count': vulnerability_count,
            },
            'flag_node_generators': {
                'enabled': bool(flag_node_generators.get('enabled', flag_node_generators.get('randomize'))),
                'count': flag_node_generator_count,
            },
            'flows': {
                'enabled': flow_enabled,
                'chain_length': flow_chain_length,
                'allow_duplicates': bool(flows.get('allow_duplicates', False)),
                'include_all_topology_pivots': bool(flows.get('include_all_topology_pivots', False)),
            },
            'segmentation': {
                'enabled': bool(segmentation.get('enabled', segmentation.get('randomize'))),
                'density': segmentation.get('density'),
                'items': list(segmentation.get('items') or []),
            },
        }

    def _artifact_metrics(self, artifacts: dict) -> dict:
        metrics = {}
        for artifact_key, artifact_path in sorted((artifacts or {}).items()):
            if not isinstance(artifact_path, str):
                continue
            if artifact_key == 'output_dir':
                metrics[artifact_key] = directory_metrics(artifact_path)
            else:
                metrics[artifact_key] = file_metrics(artifact_path)
        return metrics

    @staticmethod
    def _assignment_produces_pivot(assignment: dict) -> bool:
        if not isinstance(assignment, dict):
            return False
        output_values = []
        for key in ('declared_outputs', 'actual_outputs', 'outputs', 'produces'):
            values = assignment.get(key)
            if isinstance(values, list):
                output_values.extend(values)
        return any(str(value or '').strip().lower().startswith('pivot(') for value in output_values)

    def _content_metrics(self, result: dict) -> dict:
        """Summarize concrete generated challenges, chains, pivots, and FNGs."""
        phase_results = result.get('phase_results') or {}
        flag_payload = (phase_results.get('flag-sequencing') or {}).get('plan_payload') or {}
        preview_payload = (phase_results.get('preview-plan') or {}).get('plan_payload') or {}

        assignments = flag_payload.get('flag_assignments') if isinstance(flag_payload, dict) else []
        assignments = assignments if isinstance(assignments, list) else []
        chain = flag_payload.get('chain') if isinstance(flag_payload, dict) else []
        chain = chain if isinstance(chain, list) else []

        challenge_count = len(assignments)
        chain_length = max(0, self._safe_int(flag_payload.get('length'))) if isinstance(flag_payload, dict) else 0
        if chain_length == 0:
            chain_length = len(chain) or challenge_count
        if challenge_count == 0 and chain_length:
            challenge_count = chain_length
        chain_count = 1 if chain_length > 0 else 0

        pivot_count = sum(
            1 for assignment in assignments if self._assignment_produces_pivot(assignment)
        )
        flag_node_generator_count = sum(
            1
            for assignment in assignments
            if isinstance(assignment, dict)
            and str(assignment.get('generator_catalog') or '').strip().lower()
            in {'flag_node_generators', 'flag-node-generators'}
        )

        stats = flag_payload.get('stats') if isinstance(flag_payload, dict) else {}
        stats = stats if isinstance(stats, dict) else {}
        spec_fng_metrics = self._spec_metrics().get('flag_node_generators') or {}
        topology_fng_count = self._safe_int(
            stats.get('topology_flag_node_generator_total'),
            self._safe_int(spec_fng_metrics.get('count')),
        )

        pivot_access = self._nested(
            preview_payload,
            'full_preview',
            'display_artifacts',
            'segmentation',
            'json',
            'metadata',
            'pivot_access',
            default={},
        )
        if not isinstance(pivot_access, dict):
            pivot_access = {}

        return {
            'challenges': {
                'count': challenge_count,
                'pivot_count': pivot_count,
                'flag_node_generator_count': flag_node_generator_count,
            },
            'chains': {
                'count': chain_count,
                'length': chain_length,
                'length_gt_1_count': 1 if chain_length > 1 else 0,
                'average_length': float(chain_length) if chain_count else 0.0,
            },
            'topology': {
                'flag_node_generator_count': max(0, topology_fng_count),
                'pivot_provider_count': max(0, self._safe_int(pivot_access.get('provider_count'))),
            },
        }

    def _finalize_result_metrics(self, result: dict, run_metrics: dict) -> None:
        phase_metrics = {}
        for phase, phase_result in (result.get('phase_results') or {}).items():
            metrics = phase_result.get('metrics')
            if metrics:
                phase_metrics[phase] = metrics

        artifact_metrics = self._artifact_metrics(result.get('artifacts') or {})
        result['metrics'] = {
            'schema_version': 1,
            'token_estimator': 'regex_word_or_punctuation',
            'run': run_metrics,
            'spec': self._spec_metrics(),
            'phases': phase_metrics,
            'artifacts': artifact_metrics,
            'content': self._content_metrics(result),
        }

    def _check_artifacts_config(self) -> dict:
        """Spec-driven settings for the ScenarioForge check-artifacts phase.

        validation:
          check_artifacts:
            enabled: true
            delay_seconds: 45   # let routing converge before probing
            strict: false       # warnings stay warnings unless true
        """
        validation = self.spec.get('validation') or {}
        raw = validation.get('check_artifacts')
        if isinstance(raw, bool):
            raw = {'enabled': raw}
        if not isinstance(raw, dict):
            raw = {}
        try:
            delay = float(raw.get('delay_seconds') or 0.0)
        except Exception:
            delay = 0.0
        return {
            'enabled': bool(raw.get('enabled')),
            'delay_seconds': max(0.0, delay),
            'strict': bool(raw.get('strict')),
        }

    def _check_artifacts_extra_args(self) -> list:
        config = self._check_artifacts_config()
        if not config['enabled']:
            return []
        args = ['--check-artifacts']
        if config['delay_seconds'] > 0:
            args += ['--check-artifacts-delay', str(config['delay_seconds'])]
        if config['strict']:
            args.append('--strict')
        return args

    @staticmethod
    def _check_artifacts_messages(summary: dict, statuses: tuple) -> list:
        """Human-readable '<label>: <summary>' lines for checks in the given states."""
        messages = []
        for check in (summary.get('checks') or []):
            if not isinstance(check, dict):
                continue
            if str(check.get('status') or '').strip().lower() not in statuses:
                continue
            label = str(check.get('label') or check.get('key') or 'check').strip()
            detail = str(check.get('summary') or '').strip()
            messages.append(f"{label}: {detail}" if detail else label)
        return messages

    def _check_artifacts_outcome(self, phase_result: dict) -> tuple:
        """Return (ok, warnings, failure_message) for the artifact checks.

        When the checks are not enabled this is a no-op. The CLI only emits the
        marker when --check-artifacts ran, so a missing marker while enabled is
        itself a failure.
        """
        config = self._check_artifacts_config()
        if not config['enabled']:
            return True, [], None
        summary = phase_result.get('check_artifacts_summary')
        if not isinstance(summary, dict):
            return (
                False,
                [],
                'artifact checks were requested but scenarioforge.cli execute did not emit '
                'CHECK_ARTIFACTS_SUMMARY_JSON. See execute.log',
            )

        failures = self._check_artifacts_messages(summary, ('fail', 'error'))
        warn_details = self._check_artifacts_messages(summary, ('warn',))
        warnings = [f'artifact check warning — {m}' for m in warn_details]
        error_text = str(summary.get('error') or '').strip()

        if failures or error_text:
            detail = '; '.join(failures) or error_text
            return False, warnings, f'artifact checks failed: {detail}. See execute-check-artifacts.json'
        if config['strict'] and warn_details:
            return (
                False,
                warnings,
                f"artifact checks reported warnings under strict mode: {'; '.join(warn_details)}",
            )
        return True, warnings, None

    def _validation_policy(self) -> str:
        validation = self.spec.get('validation') or {}
        raw_policy = str(validation.get('policy') or 'strict').strip().lower().replace('-', '_')
        if raw_policy == 'warning_tolerant':
            return 'warning_tolerant'
        return 'strict'

    @staticmethod
    def _is_populated(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def _validation_messages(self, summary: dict, fields: tuple[str, ...]) -> list[str]:
        messages = []
        for field in fields:
            value = summary.get(field)
            if not self._is_populated(value):
                continue
            try:
                rendered = json.dumps(value, sort_keys=True)
            except TypeError:
                rendered = str(value)
            messages.append(f"{field}={rendered}")
        return messages

    def _last_output_line(self, text: str) -> str | None:
        clean = self._clean_output(text)
        for raw_line in reversed(clean.splitlines()):
            line = raw_line.strip()
            if line:
                return line
        return None

    def _execute_success(self, phase_result: dict) -> tuple[bool, list[str], str | None]:
        validation_summary = phase_result.get('validation_summary')
        if validation_summary is None:
            if phase_result.get('returncode') not in (None, 0):
                message = (
                    f"scenarioforge.cli execute failed with exit code {phase_result.get('returncode')} "
                    "and did not emit VALIDATION_SUMMARY_JSON."
                )
                last_line = self._last_output_line(phase_result.get('combined_output') or '')
                if last_line:
                    message = f"{message} Last output: {last_line}"
                return False, [], f"{message} See execute.log"
            return False, [], 'scenarioforge.cli execute did not emit VALIDATION_SUMMARY_JSON. See execute.log'

        warnings = self._validation_messages(validation_summary, self.VALIDATION_WARNING_FIELDS)

        if phase_result.get('returncode') != 0:
            error_messages = self._validation_messages(
                validation_summary,
                self.VALIDATION_ERROR_FIELDS,
            )
            detail = f" Validation: {', '.join(error_messages)}." if error_messages else ''
            return (
                False,
                warnings,
                f"scenarioforge.cli execute failed with exit code "
                f"{phase_result.get('returncode')}.{detail} See execute.log",
            )

        if not str(phase_result.get('session_id') or '').strip():
            return False, warnings, 'scenarioforge.cli execute did not emit CORE_SESSION_ID. See execute.log'

        if self._validation_policy() == 'warning_tolerant':
            error_messages = self._validation_messages(validation_summary, self.VALIDATION_ERROR_FIELDS)
            if error_messages:
                return False, warnings, f"execute validation reported errors: {', '.join(error_messages)}"
            return True, warnings, None

        if validation_summary.get('ok') is True:
            return True, warnings, None
        return False, warnings, 'execute validation failed under strict policy. See execute-validation.json'

    def _core_connection_attrs(self, xml_path: str) -> dict[str, str]:
        try:
            root = ET.parse(xml_path).getroot()
        except Exception:
            return {}

        attrs: dict[str, str] = {}
        if root.tag == 'Scenarios':
            global_core = root.find('CoreConnection')
            if global_core is not None:
                attrs.update(global_core.attrib)
            scenario_el = root.find('Scenario')
            if scenario_el is not None:
                scenario_core = scenario_el.find('./ScenarioEditor/HardwareInLoop/CoreConnection')
                if scenario_core is not None:
                    attrs.update({key: value for key, value in scenario_core.attrib.items() if value not in (None, '')})
        elif root.tag == 'Scenario':
            scenario_core = root.find('./ScenarioEditor/HardwareInLoop/CoreConnection')
            if scenario_core is not None:
                attrs.update(scenario_core.attrib)
        elif root.tag == 'ScenarioEditor':
            scenario_core = root.find('./HardwareInLoop/CoreConnection')
            if scenario_core is not None:
                attrs.update(scenario_core.attrib)
        return attrs

    def _shared_vm_lock_key(self, xml_path: str) -> str | None:
        attrs = self._core_connection_attrs(xml_path)
        ssh_host = str(attrs.get('ssh_host') or attrs.get('host') or '').strip()
        ssh_port = str(attrs.get('ssh_port') or '').strip()
        ssh_username = str(attrs.get('ssh_username') or '').strip()
        vm_identifier = str(attrs.get('vmid') or attrs.get('vm_key') or '').strip()
        if not (ssh_host and ssh_port and ssh_username):
            return None
        parts = [ssh_host, ssh_port, ssh_username]
        if vm_identifier:
            parts.append(vm_identifier)
        return ':'.join(parts)

    @contextmanager
    def _shared_vm_lock(self, xml_path: str):
        lock_key = self._shared_vm_lock_key(xml_path)
        if not lock_key:
            yield None
            return

        digest = hashlib.sha256(lock_key.encode('utf-8')).hexdigest()[:16]
        lock_path = os.path.join(tempfile.gettempdir(), f'scenarioforge-eval-{digest}.lock')
        with open(lock_path, 'a+', encoding='utf-8') as handle:
            wait_started = time.perf_counter()
            _lock_file_exclusive(handle)
            wait_s = rounded_seconds(time.perf_counter() - wait_started)
            try:
                yield {'key': lock_key, 'path': lock_path, 'wait_s': wait_s}
            finally:
                _unlock_file(handle)

    @staticmethod
    def _is_loopback_host(host: str) -> bool:
        value = str(host or '').strip().strip('[]').lower()
        if not value:
            return False
        if value == 'localhost':
            return True
        try:
            return ipaddress.ip_address(value).is_loopback
        except ValueError:
            return False

    def _xml_supports_remote_delegation(self, xml_path: str) -> bool:
        attrs = self._core_connection_attrs(xml_path)
        ssh_host = str(attrs.get('ssh_host') or '').strip()
        ssh_username = str(attrs.get('ssh_username') or '').strip()
        ssh_password = str(attrs.get('ssh_password') or '').strip()
        target_host = str(attrs.get('host') or '').strip()
        if not ssh_host or not ssh_username or not ssh_password:
            return False
        return not (self._is_loopback_host(ssh_host) and self._is_loopback_host(target_host))

    def _local_core_preflight_error(self, xml_path: str, phase: str) -> str | None:
        if self._xml_supports_remote_delegation(xml_path):
            return None

        attrs = self._core_connection_attrs(xml_path)
        host = str(attrs.get('host') or '').strip()
        port_raw = attrs.get('port')
        try:
            port = int(port_raw) if port_raw not in (None, '') else 0
        except Exception:
            port = 0

        if not self._is_loopback_host(host) or port <= 0:
            return None

        try:
            with socket.create_connection((host, port), timeout=3):
                return None
        except OSError as exc:
            return (
                f"Local CORE gRPC preflight failed before {phase}: {host}:{port} is unreachable ({exc}). "
                f"Start a local CORE daemon or switch ScenarioForge to a VM-backed target before rerunning."
            )

    def _run_cli_phase(
        self,
        phase: str,
        xml_path: str,
        scenario_name: str,
        *,
        seed: int,
        extra_args: list[str] | None = None,
        json_output_name: str | None = None,
        log_name: str | None = None,
        allow_nonzero: bool = False,
        timeout_s: int | None = None,
    ) -> dict:
        self._ensure_scenarioforge_repo_dirs()
        phase_timeout_s = int(timeout_s or self.phase_timeout_s)

        cmd = [
            self._cli_python(),
            '-m',
            'scenarioforge.cli',
            phase,
            '--xml',
            xml_path,
            '--scenario',
            scenario_name,
            '--seed',
            str(seed),
        ]
        if self.verbose:
            cmd.append('--verbose')

        output_path = None
        if json_output_name:
            output_path = os.path.join(self.out_dir, json_output_name)
            cmd.extend(['--plan-output', output_path])
        if extra_args:
            cmd.extend(extra_args)

        returncode: int | None = None
        stdout_text = ''
        stderr_text = ''
        timed_out = False
        output_was_streamed = False
        with MetricSpan('children') as phase_span:
            try:
                if phase == 'execute' and self.stream_execute_output:
                    returncode, stdout_text, timed_out = self._run_streaming_cli_command(cmd)
                    output_was_streamed = True
                else:
                    proc = subprocess.run(
                        cmd,
                        cwd=self.sf_path,
                        env=self._cli_env(),
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=phase_timeout_s,
                    )
                    returncode = proc.returncode
                    stdout_text = proc.stdout or ''
                    stderr_text = proc.stderr or ''
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout_text = self._coerce_subprocess_text(exc.stdout)
                stderr_text = self._coerce_subprocess_text(exc.stderr)

        combined = stdout_text + (("\n" + stderr_text) if stderr_text else '')
        log_path = os.path.join(self.out_dir, log_name or f'{phase}.log')
        with open(log_path, 'w', encoding='utf-8') as handle:
            handle.write(combined)

        if not output_was_streamed:
            self._stream_cli_output(combined)

        plan_payload = None
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as handle:
                    plan_payload = json.load(handle)
            except Exception:
                plan_payload = None

        phase_metrics = phase_span.finish()
        phase_metrics.update({
            'command': {
                'argv': cmd,
                'cwd': self.sf_path,
                'timeout_s': phase_timeout_s,
            },
            'returncode': returncode,
            'timed_out': timed_out,
            'outputs': {
                'stdout': text_metrics(stdout_text),
                'stderr': text_metrics(stderr_text),
                'combined': text_metrics(combined),
            },
            'log': file_metrics(log_path),
        })
        if output_path:
            phase_metrics['plan_output'] = file_metrics(output_path)

        phase_result = self._phase_result(
            phase,
            returncode,
            combined,
            log_path,
            plan_payload,
            timed_out=timed_out,
            stderr_output=stderr_text,
            metrics=phase_metrics,
        )

        if timed_out:
            last_line = self._last_output_line(combined)
            message = f"scenarioforge.cli {phase} timed out after {phase_timeout_s} seconds."
            if last_line:
                message = f"{message} Last output: {last_line}"
            raise PhaseExecutionError(
                f"{message} See {log_path}",
                phase_result,
            )
        if returncode != 0 and not allow_nonzero:
            last_line = self._last_output_line(combined)
            message = f"scenarioforge.cli {phase} failed with exit code {returncode}."
            if last_line:
                message = f"{message} Last output: {last_line}"
            raise PhaseExecutionError(
                f"{message} See {log_path}",
                phase_result,
            )
        if (
            returncode == 0
            and isinstance(plan_payload, dict)
            and plan_payload.get('ok') is False
            and not allow_nonzero
        ):
            payload_error = str(
                plan_payload.get('error')
                or plan_payload.get('message')
                or 'the phase payload reported ok=false'
            ).strip()
            raise PhaseExecutionError(
                f"scenarioforge.cli {phase} reported failure despite exit code 0: "
                f"{payload_error}. See {output_path or log_path}",
                phase_result,
            )
        return phase_result

    def _run_dangerous_cleanup(self) -> dict:
        self._ensure_scenarioforge_repo_dirs()

        cmd = [
            self._cli_python(),
            '-m',
            'scenarioforge.cleanup_scenarioforge_docker',
            '--force',
            '--timeout',
            str(self.cleanup_timeout_s),
        ]

        returncode: int | None = None
        stdout_text = ''
        stderr_text = ''
        timed_out = False
        timeout_s = self.cleanup_timeout_s + 30
        with MetricSpan('children') as phase_span:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.sf_path,
                    env=self._cli_env(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout_s,
                )
                returncode = proc.returncode
                stdout_text = proc.stdout or ''
                stderr_text = proc.stderr or ''
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout_text = self._coerce_subprocess_text(exc.stdout)
                stderr_text = self._coerce_subprocess_text(exc.stderr)

        combined = stdout_text + (("\n" + stderr_text) if stderr_text else '')
        log_path = os.path.join(self.out_dir, 'dangerous-cleanup.log')
        with open(log_path, 'w', encoding='utf-8') as handle:
            handle.write(combined)

        self._stream_cli_output(combined)
        phase_metrics = phase_span.finish()
        phase_metrics.update({
            'command': {
                'argv': cmd,
                'cwd': self.sf_path,
                'timeout_s': timeout_s,
            },
            'returncode': returncode,
            'timed_out': timed_out,
            'outputs': {
                'stdout': text_metrics(stdout_text),
                'stderr': text_metrics(stderr_text),
                'combined': text_metrics(combined),
            },
            'log': file_metrics(log_path),
        })
        phase_result = self._phase_result(
            'dangerous-cleanup',
            returncode,
            combined,
            log_path,
            None,
            timed_out=timed_out,
            stderr_output=stderr_text,
            metrics=phase_metrics,
        )

        if timed_out:
            last_line = self._last_output_line(combined)
            message = f"cleanup-scenarioforge-docker timed out after {self.cleanup_timeout_s} seconds."
            if last_line:
                message = f"{message} Last output: {last_line}"
            raise PhaseExecutionError(
                f"{message} See {log_path}",
                phase_result,
            )
        if returncode != 0:
            last_line = self._last_output_line(combined)
            message = f"cleanup-scenarioforge-docker failed with exit code {returncode}."
            if last_line:
                message = f"{message} Last output: {last_line}"
            raise PhaseExecutionError(
                f"{message} See {log_path}",
                phase_result,
            )
        return phase_result

    def _run_dangerous_cleanup_if_requested(self, result: dict) -> None:
        if not self.dangerous_cleanup_between_runs:
            return

        print(">> Phase: dangerous-cleanup")
        result['artifacts']['dangerous_cleanup_log'] = self._artifact_path('dangerous-cleanup.log')
        try:
            cleanup_phase = self._run_dangerous_cleanup()
        except PhaseExecutionError as exc:
            self._record_phase_result(result, exc.phase_result)
            result['stages']['dangerous_cleanup'] = 'FAIL'
            raise
        self._record_phase_result(result, cleanup_phase)
        result['stages']['dangerous_cleanup'] = 'PASS'

    DEPENDENCY_LEVEL_RANGE = (1, 5)

    def _resolve_dependency_level(self, flows_spec: dict):
        """Return the flag-sequencing dependency level, or None to leave default.

        ScenarioForge accepts 1-5. A value outside that range is a spec error
        worth failing on rather than silently clamping, since the whole point of
        setting it is to pin solver strictness.
        """
        raw = flows_spec.get('dependency_level')
        if raw is None or raw == '':
            return None
        try:
            level = int(raw)
        except Exception:
            raise ValueError(f'flows.dependency_level must be an integer, got {raw!r}')
        low, high = self.DEPENDENCY_LEVEL_RANGE
        if not (low <= level <= high):
            raise ValueError(
                f'flows.dependency_level must be between {low} and {high}, got {level}'
            )
        return level

    def _resolve_topology_count(self, value) -> int:
        """Resolve a host-role count that may be a number or an inclusive range.

        The schema allows `[min, max]` for these the same way it does for
        hosts and routers; a range is drawn from the seeded RNG so a spec stays
        reproducible.
        """
        if value is None:
            return 0
        if isinstance(value, (list, tuple)):
            try:
                low, high = int(value[0]), int(value[1])
            except Exception:
                return 0
            if high < low:
                low, high = high, low
            return max(0, self._rng.randint(low, high))
        try:
            return max(0, int(value))
        except Exception:
            return 0

    def _build_topology_payload(self, topo_spec: dict) -> dict:
        try:
            host_count = max(0, int(topo_spec.get('hosts', 0) or 0))
        except Exception:
            host_count = 0
        try:
            router_count = max(0, int(topo_spec.get('routers', 0) or 0))
        except Exception:
            router_count = 0

        items = [{'selected': 'Workstation', 'factor': 1.0}]

        # Docker-backed host roles. `docker` rows accept either challenge kind;
        # a slot row is capacity reserved for one kind, materialised empty and
        # filled during flag-sequencing only if the requested chain reaches it.
        # Both slot kinds raise the challenge ceiling, so a spec that wants them
        # exercised has to ask for a chain long enough to need them.
        for spec_key, role in (
            ('docker', 'Docker'),
            ('vulnerability_slots', 'VulnerabilitySlot'),
            ('flag_gen_slots', 'FlagGenSlot'),
        ):
            role_count = self._resolve_topology_count(topo_spec.get(spec_key))
            if role_count > 0:
                items.append({
                    'selected': role,
                    'factor': 1.0,
                    'v_metric': 'Count',
                    'v_count': role_count,
                })

        sections = {
            'Node Information': {
                'items': items,
            }
        }
        if router_count > 0:
            sections['Routing'] = {
                'density': 0.0,
                'items': [],
                'node_count_min_enabled': True,
                'node_count_min': router_count,
                'node_count_max_enabled': True,
                'node_count_max': router_count,
            }

        return {
            'density_count': host_count,
            'sections': sections,
        }

    def _build_service_items(self, services_spec: dict) -> list[dict]:
        try:
            requested_count = max(0, int(services_spec.get('count', 3)))
        except Exception:
            requested_count = 0

        if requested_count == 0:
            return []

        include = [name for name in services_spec.get('include', []) if name]
        exclude = {name for name in services_spec.get('exclude', []) if name}

        if include:
            service_pool = [name for name in include if name not in exclude]
        else:
            service_pool = [name for name in self.DEFAULT_VM_SAFE_SERVICES if name not in exclude]

        if not service_pool:
            raise ValueError(
                "services configuration excludes every evaluator-supported VM service; "
                "set services.enabled=false, services.count=0, or provide services.include"
            )

        assigned_counts = {name: 0 for name in service_pool}
        for _ in range(requested_count):
            selected = self._rng.choice(service_pool)
            assigned_counts[selected] += 1

        items = []
        for service_name in service_pool:
            service_count = assigned_counts[service_name]
            if service_count <= 0:
                continue
            items.append({
                'selected': service_name,
                'factor': 1.0,
                'v_metric': 'Count',
                'v_count': service_count,
            })
        return items

    @staticmethod
    def _build_segmentation_section(seg_spec: dict) -> dict:
        """Build the XML-writer model without losing plan-shaping settings."""
        section = {
            'density': seg_spec.get('density', 0.5),
            'items': list(seg_spec.get('items') or []),
        }
        for key in (
            'nat_mode',
            'include_hosts',
            'dnat_probability',
            'allow_src_subnet_prob',
            'allow_dst_subnet_prob',
            'accessible_by_pivot',
        ):
            if key in seg_spec:
                section[key] = seg_spec[key]
        return section

    def _load_eligible_vulnerability_catalog(self) -> list[dict] | None:
        if not os.path.isdir(os.path.join(self.sf_path, 'webapp')):
            return None
        try:
            from webapp import app_backend as backend
        except Exception:
            return None

        loader = getattr(backend, '_load_backend_vuln_catalog_items', None)
        if not callable(loader):
            return None

        try:
            catalog_items = loader(selectable_only=True)
        except TypeError:
            try:
                catalog_items = loader()
            except Exception:
                return None
        except Exception:
            return None

        if not isinstance(catalog_items, list):
            return None

        eligible = []
        seen = set()
        for item in catalog_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get('Name') or item.get('name') or '').strip()
            path = str(item.get('Path') or item.get('path') or '').strip()
            if not name or not path:
                continue
            if not os.path.isfile(path):
                continue
            key = (name.lower(), os.path.abspath(path))
            if key in seen:
                continue
            seen.add(key)
            eligible.append({
                'name': name,
                'path': os.path.abspath(path),
                'validated_ok': item.get('validated_ok'),
                'validated_at': item.get('validated_at'),
                'eligible_for_selection': item.get('eligible_for_selection'),
            })
        return eligible

    def _vulnerability_matches_filter(self, entry: dict, filters: list[str]) -> bool:
        haystacks = [
            str(entry.get('name') or '').lower(),
            str(entry.get('path') or '').lower(),
        ]
        for raw_filter in filters:
            pattern = str(raw_filter or '').strip().lower()
            if not pattern:
                continue
            for value in haystacks:
                if fnmatch.fnmatch(value, pattern) or pattern in value:
                    return True
        return False

    def _load_eligible_flag_node_generator_catalog(self) -> list[dict]:
        """Load only enabled, installed topology flag-node-generators.

        This deliberately uses ScenarioForge's enabled-source loader so an
        uninstalled or disabled generator can never be selected by an eval run.
        """
        if not os.path.isdir(os.path.join(self.sf_path, 'webapp')):
            raise ValueError(
                "Unable to inspect ScenarioForge's enabled flag-node-generator catalog: "
                f"{self.sf_path!r} does not contain webapp."
            )
        try:
            from webapp import app_backend as backend
            loader = getattr(backend, '_flag_node_generators_from_enabled_sources', None)
            if not callable(loader):
                raise RuntimeError('enabled flag-node-generator catalog loader is unavailable')
            catalog_items, errors = loader()
        except Exception as exc:
            raise ValueError(
                "Unable to inspect ScenarioForge's enabled flag-node-generator catalog: "
                f"{exc}"
            ) from exc

        if errors:
            details = '; '.join(
                str(item.get('error') or item) if isinstance(item, dict) else str(item)
                for item in errors
            )
            raise ValueError(
                "ScenarioForge's flag-node-generator catalog contains manifest errors: "
                f"{details}"
            )

        eligible = []
        seen = set()
        for item in catalog_items or []:
            if not isinstance(item, dict):
                continue
            generator_id = str(item.get('id') or '').strip()
            name = str(item.get('name') or '').strip()
            if not generator_id or generator_id in seen:
                continue
            seen.add(generator_id)
            eligible.append({'id': generator_id, 'name': name or generator_id})
        return eligible

    @staticmethod
    def _flag_node_generator_matches_filter(entry: dict, filters: list[str]) -> bool:
        values = [
            str(entry.get('id') or '').lower(),
            str(entry.get('name') or '').lower(),
        ]
        for raw_filter in filters:
            pattern = str(raw_filter or '').strip().lower()
            if not pattern:
                continue
            if any(fnmatch.fnmatch(value, pattern) or pattern in value for value in values):
                return True
        return False

    def _build_flag_node_generator_section(self, generators_spec: dict) -> dict | None:
        specific_entries = generators_spec.get('specific') or []
        if specific_entries:
            catalog = {entry['id']: entry for entry in self._load_eligible_flag_node_generator_catalog()}
            selected = []
            for raw_entry in specific_entries:
                generator_id = str(raw_entry.get('id') or '').strip()
                expected_name = str(raw_entry.get('name') or '').strip()
                try:
                    count = max(0, int(raw_entry.get('count', 0)))
                except (TypeError, ValueError):
                    count = 0
                entry = catalog.get(generator_id)
                if not entry or entry['name'] != expected_name or count <= 0:
                    raise ValueError(
                        "flag_node_generators.specific contains an unavailable or changed enabled catalog "
                        f"entry: id={generator_id!r}, name={expected_name!r}. Regenerate dataset-resolved."
                    )
                selected.append({'id': generator_id, 'name': expected_name, 'count': count})
            self._flag_node_generator_selection = {
                'mode': 'specific_from_resolved_spec',
                'requested_count': sum(entry['count'] for entry in selected),
                'eligible_count_unfiltered': len(catalog),
                'eligible_count': len(catalog),
                'include': [],
                'exclude': [],
                'selected': selected,
            }
            return {
                'density': 0.0,
                'items': [
                    {
                        'selected': 'Specific',
                        'g_id': entry['id'],
                        'g_name': entry['name'],
                        'v_metric': 'Count',
                        'v_count': entry['count'],
                        'factor': 1.0,
                    }
                    for entry in selected
                ],
            }
        try:
            requested_count = max(0, int(generators_spec.get('count', 0) or 0))
        except Exception:
            requested_count = 0
        if requested_count <= 0:
            return None

        catalog = self._load_eligible_flag_node_generator_catalog()
        include_filters = [value for value in generators_spec.get('include', []) if value]
        exclude_filters = [value for value in generators_spec.get('exclude', []) if value]
        unfiltered_eligible_count = len(catalog)
        if include_filters:
            catalog = [
                entry for entry in catalog
                if self._flag_node_generator_matches_filter(entry, include_filters)
            ]
        if exclude_filters:
            catalog = [
                entry for entry in catalog
                if not self._flag_node_generator_matches_filter(entry, exclude_filters)
            ]
        if not catalog:
            filter_description = ''
            if include_filters or exclude_filters:
                filter_description = (
                    f" after applying include={include_filters!r} and exclude={exclude_filters!r}"
                )
            raise ValueError(
                f"flag_node_generators.count requested {requested_count} generator node(s), but no "
                f"enabled installed flag-node-generators are eligible{filter_description}."
            )

        selection_rng = random.Random(f"{self.seed}:flag-node-generators:{self.spec.get('name', 'eval')}")
        selected_entries = [selection_rng.choice(catalog) for _ in range(requested_count)]
        selected_counts: dict[str, int] = {}
        selected_by_id: dict[str, dict] = {}
        for entry in selected_entries:
            generator_id = entry['id']
            selected_counts[generator_id] = selected_counts.get(generator_id, 0) + 1
            selected_by_id[generator_id] = entry

        selected = [
            {
                'id': generator_id,
                'name': selected_by_id[generator_id]['name'],
                'count': count,
            }
            for generator_id, count in selected_counts.items()
        ]
        self._flag_node_generator_selection = {
            'mode': 'specific_from_enabled_catalog',
            'requested_count': requested_count,
            'eligible_count_unfiltered': unfiltered_eligible_count,
            'eligible_count': len(catalog),
            'include': include_filters,
            'exclude': exclude_filters,
            'selected': selected,
        }
        return {
            'density': 0.0,
            'items': [
                {
                    'selected': 'Specific',
                    'g_id': entry['id'],
                    'g_name': entry['name'],
                    'v_metric': 'Count',
                    'v_count': entry['count'],
                    'factor': 1.0,
                }
                for entry in selected
            ],
        }

    def _build_vulnerability_section(self, vulns_spec: dict) -> dict | None:
        specific_entries = vulns_spec.get('specific') or []
        if specific_entries:
            eligible_catalog = self._load_eligible_vulnerability_catalog()
            # Keyed by name alone, matching `_build_flag_node_generator_section`'s
            # own pattern (keyed by id). A resolved spec's stored `path` is an
            # absolute filesystem location baked in by materialize_catalog_selections.py
            # on whatever machine ran it -- under a catalog-install directory
            # name that is itself unique per install, so it cannot be expected
            # to match on a different machine, or even this one after a catalog
            # reinstall. `name` (e.g. "struts2/s2-009") is the portable
            # identifier; the path used below is always the one freshly
            # discovered on the machine actually running this eval.
            catalog = {entry['name']: entry for entry in (eligible_catalog or [])}
            selected = []
            for raw_entry in specific_entries:
                name = str(raw_entry.get('name') or '').strip()
                try:
                    count = max(0, int(raw_entry.get('count', 0)))
                except (TypeError, ValueError):
                    count = 0
                entry = catalog.get(name)
                if not entry or count <= 0:
                    raise ValueError(
                        "vulns.specific contains an unavailable or changed validated catalog entry: "
                        f"name={name!r}. Regenerate dataset-resolved."
                    )
                selected.append({'name': name, 'path': entry['path'], 'count': count, **{
                    key: entry.get(key) for key in ('validated_ok', 'validated_at')
                }})
            self._vulnerability_selection = {
                'mode': 'specific_from_resolved_spec',
                'requested_count': sum(entry['count'] for entry in selected),
                'eligible_count_unfiltered': len(catalog),
                'eligible_count': len(catalog),
                'include': [],
                'exclude': [],
                'selected': selected,
            }
            return {
                'density': 0.0,
                'flag_type': 'text',
                'items': [
                    {
                        'selected': 'Specific',
                        'v_name': entry['name'],
                        'v_path': entry['path'],
                        'v_metric': 'Count',
                        'v_count': entry['count'],
                        'factor': 1.0,
                    }
                    for entry in selected
                ],
            }
        try:
            requested_count = max(0, int(vulns_spec.get('count', 0) or 0))
        except Exception:
            requested_count = 0
        if requested_count <= 0:
            return None

        eligible_catalog = self._load_eligible_vulnerability_catalog()
        if eligible_catalog is not None:
            include_filters = [value for value in vulns_spec.get('include', []) if value]
            exclude_filters = [value for value in vulns_spec.get('exclude', []) if value]
            unfiltered_eligible_count = len(eligible_catalog)
            if include_filters:
                eligible_catalog = [
                    entry
                    for entry in eligible_catalog
                    if self._vulnerability_matches_filter(entry, include_filters)
                ]
            if exclude_filters:
                eligible_catalog = [
                    entry
                    for entry in eligible_catalog
                    if not self._vulnerability_matches_filter(entry, exclude_filters)
                ]

            if requested_count > len(eligible_catalog):
                filter_description = ''
                if include_filters or exclude_filters:
                    filter_description = (
                        f" after applying include={include_filters!r} and exclude={exclude_filters!r} "
                        f"to {unfiltered_eligible_count} catalog entries"
                    )
                raise ValueError(
                    f"vulns.count requested {requested_count} vulnerabilities, but only "
                    f"{len(eligible_catalog)} validated vulnerability catalog entries{filter_description} with existing "
                    "docker-compose files are eligible. Validate/install more catalog entries or reduce vulns.count."
                )

            selection_rng = random.Random(f"{self.seed}:vulnerabilities:{self.spec.get('name', 'eval')}")
            selected_entries = selection_rng.sample(eligible_catalog, requested_count)
            self._vulnerability_selection = {
                'mode': 'specific_from_eligible_catalog',
                'requested_count': requested_count,
                'eligible_count_unfiltered': unfiltered_eligible_count,
                'eligible_count': len(eligible_catalog),
                'include': include_filters,
                'exclude': exclude_filters,
                'selected': [
                    {
                        'name': entry['name'],
                        'path': entry['path'],
                        'validated_ok': entry.get('validated_ok'),
                        'validated_at': entry.get('validated_at'),
                    }
                    for entry in selected_entries
                ],
            }
            return {
                'density': 0.0,
                'flag_type': 'text',
                'items': [
                    {
                        'selected': 'Specific',
                        'v_name': entry['name'],
                        'v_path': entry['path'],
                        'v_metric': 'Count',
                        'v_count': 1,
                        'factor': 1.0,
                    }
                    for entry in selected_entries
                ],
            }

        self._vulnerability_selection = {
            'mode': 'random_catalog_fallback',
            'requested_count': requested_count,
            'eligible_count': 0,
            'selected': [],
            'warning': (
                "Unable to inspect ScenarioForge's selectable vulnerability catalog with existing compose files; "
                "falling back to upstream Random vulnerability selection."
            ),
        }
        return {
            'density': 0.0,
            'items': [{
                'selected': 'Random',
                'v_metric': 'Count',
                'v_count': requested_count,
                'factor': 1.0,
            }],
        }

    def _ai_spec(self) -> dict:
        ai_spec = self.spec.get('ai')
        return ai_spec if isinstance(ai_spec, dict) else {}

    def _ai_generation_requested(self) -> bool:
        ai_spec = self._ai_spec()
        return bool(ai_spec.get('enabled')) and bool(str(ai_spec.get('prompt') or '').strip())

    def _generate_xml(self) -> str:
        """Build the scenario XML, from a prompt when the spec asks for one.

        Both routes write the same XML in the same place, so every later phase
        is unaware of which one produced it.
        """
        if self._ai_generation_requested():
            return self._generate_xml_from_prompt()
        return self._generate_xml_from_spec()

    def _generate_xml_from_spec(self) -> str:
        """Uses the UI's XML generator to build a random topology XML."""
        from webapp import app_backend as backend
        self._load_runtime_env()
        # Translate spec to the payload expected by _build_scenarios_xml
        topo_spec = self.spec.get('topology', {})
        topology_payload = self._build_topology_payload(topo_spec)
        scen_payload = {
            'name': self.spec.get('name', 'eval'),
            'nodes': self._generate_nodes(topo_spec),
            'links': [], # Links will be auto-generated by cli.py if we just supply nodes
            'density_count': topology_payload['density_count'],
            'sections': dict(topology_payload['sections']),
        }
        
        # Inject vulnerabilities count into sections
        vulns_spec = self.spec.get('vulns', {})
        if vulns_spec.get('enabled', vulns_spec.get('randomize')):
            vulnerability_section = self._build_vulnerability_section(vulns_spec)
            if vulnerability_section:
                scen_payload['sections']['Vulnerabilities'] = vulnerability_section

        # Flag-node-generators are topology additions, like vulnerabilities.
        # Their IDs are selected from the enabled installed catalog and written
        # as Specific rows so the XML remains authoritative and reproducible.
        generators_spec = self.spec.get('flag_node_generators', {})
        if generators_spec.get('enabled', generators_spec.get('randomize')):
            generator_section = self._build_flag_node_generator_section(generators_spec)
            if generator_section:
                scen_payload['sections']['Flag Node Generators'] = generator_section
            
        # Inject services count into sections
        services_spec = self.spec.get('services', {})
        if services_spec.get('enabled', services_spec.get('randomize')):
                service_items = self._build_service_items(services_spec)
                if service_items:
                    scen_payload['sections']['Services'] = {
                        'density': services_spec.get('density', 1.0),
                        'items': service_items,
                    }

        # Traffic is an existing-node workload.  Profile shorthands are
        # resolved by SpecParser into concrete TCP/UDP rows before this point.
        traffic_spec = self.spec.get('traffic', {})
        if traffic_spec.get('enabled', traffic_spec.get('randomize')):
            scen_payload['sections']['Traffic'] = {
                'density': traffic_spec.get('density', 0.0),
                'items': list(traffic_spec.get('items') or []),
            }
            
        # Inject flow_state
        flows_spec = self.spec.get('flows', {})
        if flows_spec.get('enabled', flows_spec.get('randomize')):
            scen_payload['flow_state'] = {
                'auto_chain': True,
                'chain_length': flows_spec.get('chain_length', 3),
                'allow_node_duplicates': flows_spec.get('allow_duplicates', False),
                'include_all_topology_pivots': bool(flows_spec.get('include_all_topology_pivots', False)),
            }
            
        # Inject Segmentation
        seg_spec = self.spec.get('segmentation', {})
        if seg_spec.get('enabled', seg_spec.get('randomize')):
            scen_payload['sections']['Segmentation'] = self._build_segmentation_section(seg_spec)
            
        core_defaults = self._apply_core_and_hitl(backend, scen_payload)
        scenarios_inline = [scen_payload]
        
        # Build XML
        tree = backend._build_scenarios_xml({'scenarios': scenarios_inline, 'core': core_defaults})
        xml_path = os.path.join(self.out_dir, 'scenario.xml')
        backend._write_xml_tree_atomic(tree, xml_path)
        return xml_path

    def _apply_core_and_hitl(self, backend, scen_payload: dict) -> dict:
        """Attach the resolved CORE connection and HITL block to a scenario.

        Returns the CORE defaults for the document-level <CoreConnection>.  The
        embedded SSH password is what tells the evaluator a run can be delegated
        to the CORE VM, so a scenario missing it is treated as local-only and
        fails preflight.
        """
        core_defaults = deepcopy(backend._core_backend_defaults(include_password=True))
        if core_defaults:
            scen_payload['hitl'] = dict(scen_payload.get('hitl') or {})
            # Not setdefault: a scenario parsed back from XML carries an explicit
            # `core: None`, which setdefault would leave in place.
            if not scen_payload['hitl'].get('core'):
                scen_payload['hitl']['core'] = deepcopy(core_defaults)
        
        # Inject HITL
        hitl_spec = self.spec.get('hitl', {})
        if hitl_spec.get('use_env'):
            hitl_enabled = str(os.environ.get('CORETG_VM_MODE_HITL_ENABLED', '')).lower() in ('true', '1', 'yes')
            hitl_iface = os.environ.get('CORETG_VM_MODE_HITL_CORE_IFX_NAME')
            hitl_attachment = os.environ.get('CORETG_VM_MODE_HITL_CORE_IFX_ATTACHMENT')
                            
            if hitl_enabled and hitl_iface:
                scen_payload['hitl'] = {
                    'enabled': True,
                    'interfaces': [
                        {'name': hitl_iface, 'attachment': hitl_attachment or 'existing_router'}
                    ],
                    'core': deepcopy(core_defaults) if core_defaults else None,
                }
        return core_defaults

    def _ai_phase_extra_args(self, ai_spec: dict) -> list[str]:
        """Flags for the ai phase.  Omitted overrides inherit CORETG_AI_*."""
        extra_args = ['--prompt', str(ai_spec.get('prompt') or '').strip(), '--force']

        # Never --ai-skip-bridge: an eval run always wants tool-driven authoring.
        bridge_mode = str(ai_spec.get('bridge_mode') or '').strip()
        if bridge_mode:
            extra_args.extend(['--ai-bridge-mode', bridge_mode])

        for key, flag in (
            ('provider', '--ai-provider'),
            ('model', '--ai-model'),
            ('base_url', '--ai-base-url'),
        ):
            value = str(ai_spec.get(key) or '').strip()
            if value:
                extra_args.extend([flag, value])

        timeout_s = ai_spec.get('timeout_s')
        if isinstance(timeout_s, (int, float)) and not isinstance(timeout_s, bool):
            extra_args.extend(['--ai-timeout-seconds', str(float(timeout_s))])
        return extra_args

    def _ai_phase_timeout(self, ai_spec: dict) -> int:
        """Wall-clock budget for the ai phase.

        The provider timeout bounds a single request, but a bridged run makes
        several tool-call round-trips, so the evaluator's own ceiling has to sit
        well above it or it cuts off a generation that was still within budget.
        """
        provider_timeout = ai_spec.get('timeout_s')
        if not isinstance(provider_timeout, (int, float)) or isinstance(provider_timeout, bool):
            provider_timeout = AI_TIMEOUT_CEILING_S
        return max(self.phase_timeout_s, int(provider_timeout) + self.AI_PHASE_TIMEOUT_HEADROOM_S)

    def _ai_phase_error(self, phase_result: dict | None) -> str:
        """The provider's own error text, which the phase JSON carries.

        The exception message alone is not enough: the phase prints its envelope
        indented, so the last output line is a closing brace rather than a cause.
        """
        payload = (phase_result or {}).get('plan_payload')
        if not isinstance(payload, dict):
            return ''
        error = str(payload.get('error') or '').strip()
        status = payload.get('status')
        if error and status not in (None, ''):
            return f'{error} (status {status})'
        return error

    def _ai_error_is_retryable(self, phase_result: dict | None, message: str) -> bool:
        if (phase_result or {}).get('timed_out'):
            return True
        return bool(self.AI_RETRYABLE_ERROR_RE.search(f'{self._ai_phase_error(phase_result)} {message}'))

    def _generate_xml_from_prompt(self) -> str:
        """Generate the scenario XML through ScenarioForge's ai CLI phase.

        AI generation is not reproducible from a seed, so what gets recorded is
        the request and the XML it produced -- the XML stays the reproducible
        artifact that every later phase and any replay works from.
        """
        self._load_runtime_env()
        ai_spec = self._ai_spec()
        xml_path = os.path.join(self.out_dir, 'scenario.xml')
        scenario_name = self.spec.get('name', 'eval')
        extra_args = self._ai_phase_extra_args(ai_spec)
        attempts = max(1, self._safe_int(ai_spec.get('retries'), 0) + 1)
        phase_timeout_s = self._ai_phase_timeout(ai_spec)

        generation: dict = {
            'prompt': str(ai_spec.get('prompt') or '').strip(),
            'bridge_mode': str(ai_spec.get('bridge_mode') or ''),
            'retries': attempts - 1,
            'attempts': 0,
            'xml_path': xml_path,
            'command_args': list(extra_args),
        }
        for key in ('timeout_s', 'timeout_requested_s'):
            if ai_spec.get(key) is not None:
                generation[key] = ai_spec[key]
        for key in ('provider', 'model', 'base_url'):
            if str(ai_spec.get(key) or '').strip():
                generation.setdefault('overrides', {})[key] = str(ai_spec[key]).strip()
        self._ai_generation = generation

        if 'timeout_requested_s' in generation:
            self._ai_warnings.append(
                'ScenarioForge caps the AI provider timeout at '
                f'{AI_TIMEOUT_CEILING_S:.0f}s; ai.timeout_s '
                f"{generation['timeout_requested_s']:.0f}s was lowered to "
                f"{generation['timeout_s']:.0f}s."
            )

        last_error: PhaseExecutionError | None = None
        for attempt in range(1, attempts + 1):
            suffix = '' if attempt == 1 else f'-attempt{attempt}'
            generation['attempts'] = attempt
            try:
                phase_result = self._run_cli_phase(
                    'ai',
                    xml_path,
                    scenario_name,
                    seed=self.seed,
                    extra_args=extra_args,
                    json_output_name=f'ai{suffix}.json',
                    log_name=f'ai{suffix}.log',
                    timeout_s=phase_timeout_s,
                )
            except PhaseExecutionError as exc:
                self._ai_phase_results.append(exc.phase_result)
                provider_error = self._ai_phase_error(exc.phase_result)
                generation['error'] = provider_error or str(exc)
                self._record_ai_settings(generation, exc.phase_result)
                last_error = exc
                if attempt < attempts and self._ai_error_is_retryable(exc.phase_result, str(exc)):
                    print(
                        f'>> ai generation attempt {attempt}/{attempts} timed out; retrying'
                    )
                    continue
                break

            self._ai_phase_results.append(phase_result)
            generation.pop('error', None)
            self._record_ai_settings(generation, phase_result)
            self._apply_core_connection_to_generated_xml(xml_path)
            return xml_path

        message = self._ai_phase_error(getattr(last_error, 'phase_result', None))
        raise PhaseExecutionError(
            'scenarioforge.cli ai failed to generate a scenario from the prompt'
            + (f': {message}' if message else f'. {last_error}'),
            getattr(last_error, 'phase_result', {'phase': 'ai'}),
        )

    def _apply_core_connection_to_generated_xml(self, xml_path: str) -> None:
        """Embed this evaluator's CORE connection in a prompt-generated XML.

        The ai phase writes the scenario the model authored, but its CORE block
        comes from ScenarioForge's own defaults and carries no SSH password.
        Without one the evaluator cannot tell that the run is delegable to the
        CORE VM, so it preflights loopback gRPC and fails before topo.  Loading
        and re-emitting through the same backend helpers the deterministic route
        uses leaves the authored sections untouched and makes the two XMLs agree
        on the connection.
        """
        from webapp import app_backend as backend

        payload = backend._parse_scenarios_xml(xml_path)
        scenarios = (payload or {}).get('scenarios') or []
        if not scenarios:
            return
        core_defaults = None
        for scenario in scenarios:
            core_defaults = self._apply_core_and_hitl(backend, scenario)
        payload['core'] = core_defaults
        tree = backend._build_scenarios_xml(payload)
        backend._write_xml_tree_atomic(tree, xml_path)

    def _record_ai_settings(self, generation: dict, phase_result: dict | None) -> None:
        """Copy the resolved provider identity out of the phase JSON.

        The API key is dropped rather than carried in its redacted form: nothing
        downstream needs even a length, and run outputs get shared.
        """
        payload = (phase_result or {}).get('plan_payload')
        if not isinstance(payload, dict):
            return
        settings = payload.get('settings')
        if isinstance(settings, dict):
            resolved = {
                key: value
                for key, value in settings.items()
                if key not in {'api_key', 'api_key_source'}
            }
            generation['settings'] = resolved
            for key in ('provider', 'model', 'base_url'):
                if resolved.get(key):
                    generation[key] = resolved[key]
        for key in ('scenario', 'acting_user', 'applied_actions', 'written', 'overwritten'):
            if payload.get(key) is not None:
                generation[key] = payload[key]

    def _resolve_xml_scenario_name(self, xml_path: str) -> str:
        """Return the canonical scenario name written into the generated XML."""
        fallback = self.spec.get('name', 'eval-scen')
        try:
            import xml.etree.ElementTree as ET

            root = ET.parse(xml_path).getroot()
            scenario_el = root.find('.//Scenario')
            if scenario_el is None:
                return fallback
            scenario_name = str(scenario_el.get('name') or '').strip()
            return scenario_name or fallback
        except Exception:
            return fallback

    def _generate_nodes(self, topo_spec: dict) -> list:
        nodes = []
        node_id = 1
        num_routers = topo_spec.get('routers', 2)
        num_hosts = topo_spec.get('hosts', 5)
        
        for _ in range(num_routers):
            nodes.append({"id": node_id, "name": f"router-{node_id}", "type": "router"})
            node_id += 1
            
        for _ in range(num_hosts):
            nodes.append({"id": node_id, "name": f"host-{node_id}", "type": "docker"})
            node_id += 1
            
        return nodes

    def run(self):
        run_span = MetricSpan('self_children')
        run_span.__enter__()
        result = {
            'success': False,
            'stages': {},
            'error': None,
            'phase_results': {},
            'metadata': {
                'seed': self.seed,
                'validation_policy': self._validation_policy(),
                'dangerous_cleanup_between_runs': self.dangerous_cleanup_between_runs,
            },
            'artifacts': {
                'output_dir': self.out_dir,
            },
        }
        
        try:
            # ── Phase 1: Scenario XML generation ──
            print(">> Phase: scenario-xml")
            scenario_span = MetricSpan('self')
            scenario_span.__enter__()
            try:
                result['artifacts']['seed_txt'] = self._persist_seed_artifact()
                xml_path = self._generate_xml()
                scenario_name = self._resolve_xml_scenario_name(xml_path)
                if self._vulnerability_selection:
                    result['metadata']['vulnerability_selection'] = self._vulnerability_selection
                if self._flag_node_generator_selection:
                    result['metadata']['flag_node_generator_selection'] = self._flag_node_generator_selection
                result['artifacts']['scenario_xml'] = xml_path
                result['stages']['scenario_xml'] = 'PASS'
            finally:
                self._record_internal_phase_result(result, 'scenario-xml', scenario_span.finish())
                # Recorded in `finally` so a failed generation still reports the
                # prompt and the provider it was sent to.
                self._record_ai_generation(result)
            
            if self.target_phase == 'topology':
                print(">> Phase: topo")
                result['artifacts']['topo_json'] = self._artifact_path('topo.json')
                result['artifacts']['topo_log'] = self._artifact_path('topo.log')
                preflight_error = self._local_core_preflight_error(xml_path, 'topo')
                if preflight_error:
                    raise RuntimeError(preflight_error)
                with self._shared_vm_lock(xml_path) as lock_info:
                    if lock_info:
                        result['metadata']['shared_vm_lock'] = lock_info
                    self._run_dangerous_cleanup_if_requested(result)
                    try:
                        topo_phase = self._run_cli_phase('topo', xml_path, scenario_name, seed=self.seed, json_output_name='topo.json', log_name='topo.log')
                    except PhaseExecutionError as exc:
                        self._record_phase_result(result, exc.phase_result)
                        raise
                self._record_phase_result(result, topo_phase)
                result['stages']['topology'] = 'PASS'
                result['success'] = True
                return result
            
            # ── Phase 2: Preview plan ──
            print(">> Phase: preview-plan")
            result['artifacts']['preview_plan_json'] = self._artifact_path('preview-plan.json')
            result['artifacts']['preview_plan_log'] = self._artifact_path('preview-plan.log')
            try:
                preview_phase = self._run_cli_phase('preview-plan', xml_path, scenario_name, seed=self.seed, json_output_name='preview-plan.json', log_name='preview-plan.log')
            except PhaseExecutionError as exc:
                self._record_phase_result(result, exc.phase_result)
                raise
            self._record_phase_result(result, preview_phase)
            result['stages']['preview_plan'] = 'PASS'

            # ── Phase 3: Flag sequencing ──
            flows_spec = self.spec.get('flows', {})
            runtime_lock_context = self._shared_vm_lock(xml_path) if self.target_phase in {'execute', 'flag-sequencing'} else nullcontext(None)
            execute_phase = None
            with runtime_lock_context as lock_info:
                if lock_info:
                    result['metadata']['shared_vm_lock'] = lock_info

                self._run_dangerous_cleanup_if_requested(result)

                if flows_spec.get('enabled', flows_spec.get('randomize')):
                    print(">> Phase: flag-sequencing")
                    result['artifacts']['flag_sequencing_json'] = self._artifact_path('flag-sequencing.json')
                    result['artifacts']['flag_sequencing_log'] = self._artifact_path('flag-sequencing.log')
                    flow_args = [
                        '--flow-mode', 'resolve',
                        '--flow-length', str(flows_spec.get('chain_length', 3)),
                    ]
                    if flows_spec.get('allow_duplicates', False):
                        flow_args.append('--flow-allow-node-duplicates')
                    else:
                        flow_args.append('--flow-best-effort')
                    # Dependency strictness governs how the solver chains steps.
                    # Left unset every run used ScenarioForge's default of 3 and
                    # the other levels went unexercised.
                    dependency_level = self._resolve_dependency_level(flows_spec)
                    if dependency_level is not None:
                        flow_args.extend(['--flow-dependency-level', str(dependency_level)])
                    chain_ids = [
                        str(node_id).strip()
                        for node_id in (flows_spec.get('chain_ids') or [])
                        if str(node_id).strip()
                    ]
                    if chain_ids:
                        flow_args.extend(['--flow-chain-ids', ','.join(chain_ids)])
                    # Operational knob, overridable per-spec via flows.timeout_s.
                    #
                    # Always pass an explicit value here rather than leaving it
                    # unset. `--flow-best-effort` above is only about letting the
                    # solver clamp to available eligible nodes (see its CLI help
                    # text) -- it has nothing to do with timing. But
                    # ScenarioForge's own request handler
                    # (`_load_prepare_preview_request_context` in
                    # webapp/flow_prepare_preview_execute.py) has an unrelated,
                    # undocumented side effect: any request with best_effort=true
                    # and no explicit timeout_s silently gets a hardcoded 30s
                    # total budget for the whole generator-run phase. That's fine
                    # for a quick interactive hint/preview peek, but nowhere near
                    # enough for real generator execution -- each generator may
                    # need to build/pull a fresh Docker image, and this phase's
                    # own flag-sequencing.log has shown two ~5-15s cold builds
                    # alone. Once the budget is exhausted mid-chain, remaining
                    # generators are silently skipped (not failed) and the run
                    # only blows up much later, at `execute`, with a confusing
                    # "missing flag outputs" error disconnected from the real
                    # cause. ScenarioForge's own web UI never hits this: its
                    # "Resolve" action always sends best_effort=false plus an
                    # explicit timeout_s of max(600, chain_length*150 + 180)
                    # (see resolveTimeoutSeconds in webapp/templates/flow.html).
                    # Mirror that formula here so batch runs get the same
                    # generous, chain-length-scaled budget the UI always has.
                    timeout_s = flows_spec.get('timeout_s')
                    if timeout_s not in (None, ''):
                        try:
                            timeout_value = int(timeout_s)
                        except Exception:
                            raise ValueError(
                                f'flows.timeout_s must be an integer, got {timeout_s!r}'
                            )
                        if timeout_value <= 0:
                            raise ValueError(
                                f'flows.timeout_s must be positive, got {timeout_value}'
                            )
                    else:
                        chain_length_for_timeout = int(flows_spec.get('chain_length', 3) or 3)
                        timeout_value = max(600, chain_length_for_timeout * 150 + 180)
                    flow_args.extend(['--flow-timeout-s', str(timeout_value)])
                    if flows_spec.get('cleanup_generated_artifacts'):
                        flow_args.append('--flow-cleanup-generated-artifacts')
                    execution = str(flows_spec.get('execution') or '').strip().lower()
                    if execution == 'remote':
                        flow_args.append('--flow-run-remote')
                    elif execution == 'local':
                        flow_args.append('--flow-run-local')
                    elif execution:
                        raise ValueError(
                            f"flows.execution must be 'local' or 'remote', got {execution!r}"
                        )
                    try:
                        flag_phase = self._run_cli_phase(
                            'flag-sequencing',
                            xml_path,
                            scenario_name,
                            seed=self.seed,
                            extra_args=flow_args,
                            json_output_name='flag-sequencing.json',
                            log_name='flag-sequencing.log',
                        )
                    except PhaseExecutionError as exc:
                        self._record_phase_result(result, exc.phase_result)
                        raise
                    self._record_phase_result(result, flag_phase)
                    result['stages']['flag_sequencing'] = 'PASS'
                else:
                    result['stages']['flag_sequencing'] = 'SKIP'

                if self.target_phase == 'flag-sequencing':
                    result['success'] = True
                    return result

                # ── Phase 4: Execute ──
                print(">> Phase: execute")
                result['artifacts']['execute_log'] = self._artifact_path('execute.log')
                preflight_error = self._local_core_preflight_error(xml_path, 'execute')
                if preflight_error:
                    raise RuntimeError(preflight_error)
                execute_phase = self._run_cli_phase(
                    'execute',
                    xml_path,
                    scenario_name,
                    seed=self.seed,
                    extra_args=['--post-execution-validation'] + self._check_artifacts_extra_args(),
                    log_name='execute.log',
                    allow_nonzero=True,
                )

            if execute_phase is not None:
                self._record_phase_result(result, execute_phase)
                if execute_phase.get('report_path'):
                    result['artifacts']['execute_report'] = execute_phase['report_path']
                if execute_phase.get('summary_path'):
                    result['artifacts']['execute_summary'] = execute_phase['summary_path']
                if execute_phase.get('validation_summary') is not None:
                    result['artifacts']['execute_validation_json'] = self._write_json_artifact(
                        'execute-validation.json',
                        execute_phase['validation_summary'],
                    )
                if execute_phase.get('check_artifacts_summary') is not None:
                    result['artifacts']['execute_check_artifacts_json'] = self._write_json_artifact(
                        'execute-check-artifacts.json',
                        execute_phase['check_artifacts_summary'],
                    )
                passed, warnings, failure_message = self._execute_success(execute_phase)
                # Artifact checks run after execute validation, so they can only
                # add findings to an otherwise successful run.
                checks_ok, check_warnings, check_failure = self._check_artifacts_outcome(execute_phase)
                warnings = list(warnings) + list(check_warnings)
                if passed and not checks_ok:
                    passed, failure_message = False, check_failure
                if warnings:
                    result['warnings'] = warnings
                if not passed:
                    result['stages']['execute'] = 'FAIL'
                    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')

            result['stages']['execute'] = 'PASS'
            result['success'] = True
                    
        except Exception as e:
            result['error'] = traceback.format_exc()
            result['stages']['failed_at'] = str(e)
        finally:
            webui_xml = None
            try:
                webui_xml = self._snapshot_webui_xml(result)
            except OSError as exc:
                result.setdefault('warnings', []).append(
                    f'Unable to preserve the ScenarioForge WebUI XML artifact: {exc}'
                )
            try:
                self._snapshot_reproduction_bundle(result, webui_xml)
            except (OSError, ValueError, ET.ParseError) as exc:
                result.setdefault('warnings', []).append(
                    f'Unable to create the requested ScenarioForge reproduction bundle: {exc}'
                )
            self._finalize_result_metrics(result, run_span.finish())
            
        return result
