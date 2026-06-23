import fcntl
import hashlib
import ipaddress
import json
import os
import random
import re
import socket
import subprocess
import sys
import tempfile
import traceback
import xml.etree.ElementTree as ET
from contextlib import contextmanager, nullcontext
from copy import deepcopy


class PhaseExecutionError(RuntimeError):
    def __init__(self, message: str, phase_result: dict):
        super().__init__(message)
        self.phase_result = phase_result

class Executor:
    DEFAULT_VM_SAFE_SERVICES = ("SSH", "HTTP")
    ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
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
    VALIDATION_WARNING_FIELDS = (
        'extra_nodes',
        'extra_docker_nodes',
        'docker_start_pending',
        'injects_missing',
        'generator_injects_missing',
    )

    def __init__(self, spec: dict, out_dir: str, sf_path: str, target_phase: str = "execute", verbose: bool = False):
        self.spec = spec
        self.out_dir = os.path.abspath(os.path.expanduser(out_dir))
        self.sf_path = os.path.abspath(os.path.expanduser(sf_path))
        self.target_phase = target_phase
        self.verbose = verbose
        self.seed = self._resolve_seed(self.spec.get('seed'))
        self._rng = random.Random(self.seed)
        self.phase_timeout_s = self._resolve_phase_timeout()
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
        existing = str(env.get('PYTHONPATH') or '').strip()
        pieces = [self.sf_path]
        if existing:
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
            '[validate]',
            'CORE daemon runtime hint:',
            'Scenario report written to',
            'Scenario summary written to',
            'WARNING',
            'ERROR',
            'Traceback',
            'FATAL',
        )
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self.verbose or any(pattern in line for pattern in progress_patterns):
                print(f"  {line}")

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

    def _phase_result(self, phase: str, returncode: int | None, combined: str, log_path: str, plan_payload: dict | None, *, timed_out: bool = False) -> dict:
        result = {
            'phase': phase,
            'returncode': returncode,
            'combined_output': combined,
            'log_path': log_path,
            'plan_payload': plan_payload,
            'session_id': None,
            'validation_summary': None,
            'report_path': None,
            'summary_path': None,
            'timed_out': timed_out,
        }
        if phase == 'execute':
            result['session_id'] = self._extract_last_marker_value(combined, 'CORE_SESSION_ID:')
            result['validation_summary'] = self._extract_last_json_marker(combined, 'VALIDATION_SUMMARY_JSON:')
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
            'report_path': phase_result.get('report_path'),
            'summary_path': phase_result.get('summary_path'),
            'timed_out': bool(phase_result.get('timed_out')),
        }
        result.setdefault('phase_results', {})[phase_result['phase']] = metadata

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
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield {'key': lock_key, 'path': lock_path}
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

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
    ) -> dict:
        self._ensure_scenarioforge_repo_dirs()

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
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.sf_path,
                env=self._cli_env(),
                capture_output=True,
                text=True,
                check=False,
                timeout=self.phase_timeout_s,
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

        self._stream_cli_output(combined)

        plan_payload = None
        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as handle:
                    plan_payload = json.load(handle)
            except Exception:
                plan_payload = None

        phase_result = self._phase_result(phase, returncode, combined, log_path, plan_payload, timed_out=timed_out)

        if timed_out:
            last_line = self._last_output_line(combined)
            message = f"scenarioforge.cli {phase} timed out after {self.phase_timeout_s} seconds."
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
        return phase_result

    def _build_topology_payload(self, topo_spec: dict) -> dict:
        try:
            host_count = max(0, int(topo_spec.get('hosts', 0) or 0))
        except Exception:
            host_count = 0
        try:
            router_count = max(0, int(topo_spec.get('routers', 0) or 0))
        except Exception:
            router_count = 0

        sections = {
            'Node Information': {
                'items': [{'selected': 'Workstation', 'factor': 1.0}],
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

    def _generate_xml(self) -> str:
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
            count = vulns_spec.get('count', 1)
            density = min(1.0, count / 10.0)
            scen_payload['sections']['Vulnerabilities'] = {
                'density': density,
                'items': [{'selected': 'Random', 'v_metric': 'Weight', 'factor': 1.0}]
            }
            
        # Inject services count into sections
        services_spec = self.spec.get('services', {})
        if services_spec.get('enabled', services_spec.get('randomize')):
                service_items = self._build_service_items(services_spec)
                if service_items:
                    scen_payload['sections']['Services'] = {
                        'density': services_spec.get('density', 1.0),
                        'items': service_items,
                    }
            
        # Inject flow_state
        flows_spec = self.spec.get('flows', {})
        if flows_spec.get('enabled', flows_spec.get('randomize')):
            scen_payload['flow_state'] = {
                'auto_chain': True,
                'chain_length': flows_spec.get('chain_length', 3),
                'allow_node_duplicates': flows_spec.get('allow_duplicates', False)
            }
            
        # Inject Segmentation
        seg_spec = self.spec.get('segmentation', {})
        if seg_spec.get('enabled', seg_spec.get('randomize')):
            scen_payload['sections']['Segmentation'] = {
                'density_input': seg_spec.get('density', 0.5)
            }
            
        core_defaults = deepcopy(backend._core_backend_defaults(include_password=True))
        if core_defaults:
            scen_payload['hitl'] = dict(scen_payload.get('hitl') or {})
            scen_payload['hitl'].setdefault('core', deepcopy(core_defaults))
        
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
            
        scenarios_inline = [scen_payload]
        
        # Build XML
        tree = backend._build_scenarios_xml({'scenarios': scenarios_inline, 'core': core_defaults})
        xml_path = os.path.join(self.out_dir, 'scenario.xml')
        backend._write_xml_tree_atomic(tree, xml_path)
        return xml_path

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
        result = {
            'success': False,
            'stages': {},
            'error': None,
            'phase_results': {},
            'metadata': {
                'seed': self.seed,
                'validation_policy': self._validation_policy(),
            },
            'artifacts': {
                'output_dir': self.out_dir,
            },
        }
        
        try:
            # ── Phase 1: Scenario XML generation ──
            print(">> Phase: scenario-xml")
            result['artifacts']['seed_txt'] = self._persist_seed_artifact()
            xml_path = self._generate_xml()
            scenario_name = self._resolve_xml_scenario_name(xml_path)
            result['artifacts']['scenario_xml'] = xml_path
            result['stages']['scenario_xml'] = 'PASS'
            
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
                    extra_args=['--post-execution-validation'],
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
                passed, warnings, failure_message = self._execute_success(execute_phase)
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
            
        return result
