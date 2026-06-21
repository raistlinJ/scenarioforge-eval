import os
import sys
import random
import subprocess
import traceback
from copy import deepcopy
from pathlib import Path

class Executor:
    DEFAULT_VM_SAFE_SERVICES = ("SSH", "HTTP")

    def __init__(self, spec: dict, out_dir: str, sf_path: str, target_phase: str = "execute", verbose: bool = False):
        self.spec = spec
        self.out_dir = out_dir
        self.sf_path = os.path.abspath(sf_path)
        self.target_phase = target_phase
        self.verbose = verbose
        os.makedirs(self.out_dir, exist_ok=True)
        
        # Dynamically add scenarioforge to the path
        if self.sf_path not in sys.path:
            sys.path.insert(0, self.sf_path)

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
        return env

    def _artifact_path(self, file_name: str | None) -> str | None:
        if not file_name:
            return None
        return os.path.join(self.out_dir, file_name)

    def _stream_cli_output(self, text: str) -> None:
        if not text:
            return
        progress_patterns = (
            'PHASE:',
            'Delegating CLI',
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

    def _run_cli_phase(
        self,
        phase: str,
        xml_path: str,
        scenario_name: str,
        *,
        extra_args: list[str] | None = None,
        json_output_name: str | None = None,
        log_name: str | None = None,
    ) -> dict | None:
        cmd = [
            self._cli_python(),
            '-m',
            'scenarioforge.cli',
            phase,
            '--xml',
            xml_path,
            '--scenario',
            scenario_name,
        ]
        if self.verbose:
            cmd.append('--verbose')

        output_path = None
        if json_output_name:
            output_path = os.path.join(self.out_dir, json_output_name)
            cmd.extend(['--plan-output', output_path])
        if extra_args:
            cmd.extend(extra_args)

        proc = subprocess.run(
            cmd,
            cwd=self.sf_path,
            env=self._cli_env(),
            capture_output=True,
            text=True,
            check=False,
        )

        combined = (proc.stdout or '') + (("\n" + proc.stderr) if proc.stderr else '')
        log_path = os.path.join(self.out_dir, log_name or f'{phase}.log')
        with open(log_path, 'w', encoding='utf-8') as handle:
            handle.write(combined)

        self._stream_cli_output(combined)

        if proc.returncode != 0:
            raise RuntimeError(f"scenarioforge.cli {phase} failed with exit code {proc.returncode}. See {log_path}")

        if output_path and os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as handle:
                    return __import__('json').load(handle)
            except Exception:
                return None
        return None

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
            selected = random.choice(service_pool)
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
            
        # Enforce VM mode for scenarioforge-eval
        webui_mode = os.environ.get('CORETG_WEBUI_MODE', 'native').lower()
        if webui_mode != 'vm':
            raise RuntimeError(
                f"scenarioforge-eval only supports 'vm' mode. Your .scenarioforge.env "
                f"is currently set to CORETG_WEBUI_MODE='{webui_mode}'. Please update "
                f"it to 'vm' to run the evaluation."
            )

        vm_defaults = backend._webui_vm_mode_defaults(include_password=True)
        core_defaults = deepcopy(vm_defaults.get('core') if isinstance(vm_defaults.get('core'), dict) else {})
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
        tree.write(xml_path, encoding='utf-8', xml_declaration=True)
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
            'artifacts': {
                'output_dir': self.out_dir,
            },
        }
        
        try:
            # ── Phase 1: Scenario XML generation ──
            print(">> Phase: scenario-xml")
            xml_path = self._generate_xml()
            scenario_name = self._resolve_xml_scenario_name(xml_path)
            result['artifacts']['scenario_xml'] = xml_path
            result['stages']['scenario_xml'] = 'PASS'
            
            if self.target_phase == 'topology':
                print(">> Phase: topo")
                result['artifacts']['topo_json'] = self._artifact_path('topo.json')
                result['artifacts']['topo_log'] = self._artifact_path('topo.log')
                self._run_cli_phase('topo', xml_path, scenario_name, json_output_name='topo.json', log_name='topo.log')
                result['stages']['topology'] = 'PASS'
                result['success'] = True
                return result
            
            # ── Phase 2: Preview plan ──
            print(">> Phase: preview-plan")
            result['artifacts']['preview_plan_json'] = self._artifact_path('preview-plan.json')
            result['artifacts']['preview_plan_log'] = self._artifact_path('preview-plan.log')
            self._run_cli_phase('preview-plan', xml_path, scenario_name, json_output_name='preview-plan.json', log_name='preview-plan.log')
            result['stages']['preview_plan'] = 'PASS'

            # ── Phase 3: Flag sequencing ──
            flows_spec = self.spec.get('flows', {})
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
                self._run_cli_phase('flag-sequencing', xml_path, scenario_name, extra_args=flow_args, json_output_name='flag-sequencing.json', log_name='flag-sequencing.log')
                result['stages']['flag_sequencing'] = 'PASS'
            else:
                result['stages']['flag_sequencing'] = 'SKIP'

            if self.target_phase == 'flag-sequencing':
                result['success'] = True
                return result

            # ── Phase 4: Execute ──
            print(">> Phase: execute")
            result['artifacts']['execute_log'] = self._artifact_path('execute.log')
            self._run_cli_phase('execute', xml_path, scenario_name, log_name='execute.log')
            result['stages']['execute'] = 'PASS'
            result['success'] = True
                    
        except Exception as e:
            result['error'] = traceback.format_exc()
            result['stages']['failed_at'] = str(e)
            
        return result
