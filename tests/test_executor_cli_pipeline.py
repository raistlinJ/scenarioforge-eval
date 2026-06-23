import os
import stat
import subprocess
import socket
import tempfile
import textwrap
import unittest
from contextlib import contextmanager
from unittest import mock

from scenarioforge_eval.executor import Executor


class ExecutorCliPipelineTests(unittest.TestCase):
    def test_generate_xml_embeds_vm_core_connection_defaults(self):
        spec = {
            'name': 'eval-scenario',
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            with mock.patch.object(executor, '_load_runtime_env', return_value=None), \
                 mock.patch.dict(os.environ, {
                     'CORETG_WEBUI_MODE': 'vm',
                     'CORE_HOST': '10.0.0.50',
                     'CORE_PORT': '50051',
                     'CORE_SSH_HOST': '10.0.0.50',
                     'CORE_SSH_PORT': '22',
                     'CORE_SSH_USERNAME': 'corevm',
                     'CORE_SSH_PASSWORD': 'pw123',
                     'CORETG_VM_MODE_HITL_ENABLED': 'true',
                     'CORETG_VM_MODE_HITL_CORE_IFX_NAME': 'ens19',
                     'CORETG_VM_MODE_HITL_CORE_IFX_ATTACHMENT': 'existing_router',
                 }, clear=False):
                xml_path = executor._generate_xml()

            with open(xml_path, 'r', encoding='utf-8') as handle:
                text = handle.read()
            self.assertGreaterEqual(text.count('<CoreConnection'), 2)
            self.assertIn('ssh_password="pw123"', text)
            self.assertIn('ssh_username="corevm"', text)
            self.assertIn('name="ens19"', text)
            self.assertEqual(stat.S_IMODE(os.stat(xml_path).st_mode), 0o600)

    def test_generate_xml_uses_mode_aware_core_defaults_in_native_mode(self):
        spec = {
            'name': 'eval-scenario',
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': False},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            with mock.patch.object(executor, '_load_runtime_env', return_value=None), \
                 mock.patch.dict(os.environ, {
                     'CORETG_WEBUI_MODE': 'native',
                     'CORE_HOST': '127.0.0.1',
                     'CORE_PORT': '50051',
                     'CORE_SSH_HOST': '127.0.0.1',
                     'CORE_SSH_PORT': '22',
                     'CORE_SSH_USERNAME': 'localuser',
                     'CORE_SSH_PASSWORD': '',
                     'CORETG_VM_MODE_HITL_ENABLED': 'false',
                 }, clear=False):
                xml_path = executor._generate_xml()

            with open(xml_path, 'r', encoding='utf-8') as handle:
                text = handle.read()
            self.assertIn('<CoreConnection host="127.0.0.1" port="50051"', text)
            self.assertIn('ssh_host="127.0.0.1"', text)
            self.assertIn('ssh_username="localuser"', text)

    def test_run_uses_phase_based_cli_sequence(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 12345,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': True, 'chain_length': 3, 'allow_duplicates': False},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            calls = []

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            def _fake_run_cli_phase(phase, xml_path, scenario_name, *, seed, extra_args=None, json_output_name=None, log_name=None, allow_nonzero=False):
                calls.append({
                    'phase': phase,
                    'xml_path': xml_path,
                    'scenario_name': scenario_name,
                    'seed': seed,
                    'extra_args': list(extra_args or []),
                    'json_output_name': json_output_name,
                    'log_name': log_name,
                    'allow_nonzero': allow_nonzero,
                })
                return {
                    'phase': phase,
                    'returncode': 0,
                    'combined_output': '',
                    'log_path': os.path.join(temp_dir, log_name or f'{phase}.log'),
                    'plan_payload': {},
                    'session_id': '42' if phase == 'execute' else None,
                    'validation_summary': {'ok': True} if phase == 'execute' else None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                }

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=_fake_run_cli_phase):
                result = executor.run()

            self.assertTrue(result['success'])
            self.assertTrue(result['artifacts']['scenario_xml'].endswith('scenario.xml'))
            self.assertTrue(result['artifacts']['preview_plan_json'].endswith('preview-plan.json'))
            self.assertTrue(result['artifacts']['flag_sequencing_json'].endswith('flag-sequencing.json'))
            self.assertTrue(result['artifacts']['execute_log'].endswith('execute.log'))
            self.assertTrue(result['artifacts']['execute_validation_json'].endswith('execute-validation.json'))
            self.assertEqual([call['phase'] for call in calls], ['preview-plan', 'flag-sequencing', 'execute'])
            self.assertEqual({call['seed'] for call in calls}, {12345})
            self.assertEqual(calls[0]['json_output_name'], 'preview-plan.json')
            self.assertEqual(calls[1]['json_output_name'], 'flag-sequencing.json')
            self.assertIn('--flow-mode', calls[1]['extra_args'])
            self.assertIn('--post-execution-validation', calls[2]['extra_args'])
            self.assertEqual(calls[2]['log_name'], 'execute.log')
            with open(result['artifacts']['seed_txt'], 'r', encoding='utf-8') as handle:
                self.assertEqual(handle.read().strip(), '12345')

    def test_run_cli_phase_parses_last_validation_marker_on_nonzero_exit(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 777,
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            proc = subprocess.CompletedProcess(
                args=['python'],
                returncode=1,
                stdout='CORE_SESSION_ID: 51\nVALIDATION_SUMMARY_JSON: {"ok": false, "missing_nodes": ["n1"]}\n',
                stderr='Scenario report written to /tmp/report.md\nVALIDATION_SUMMARY_JSON: {"ok": false, "docker_start_pending": ["n2"]}\nScenario summary written to /tmp/summary.json\n',
            )

            with mock.patch('scenarioforge_eval.executor.subprocess.run', return_value=proc):
                phase_result = executor._run_cli_phase(
                    'execute',
                    '/tmp/scenario.xml',
                    'eval-scenario',
                    seed=777,
                    extra_args=['--post-execution-validation'],
                    log_name='execute.log',
                    allow_nonzero=True,
                )

            self.assertEqual(phase_result['returncode'], 1)
            self.assertEqual(phase_result['session_id'], '51')
            self.assertEqual(phase_result['validation_summary'], {'ok': False, 'docker_start_pending': ['n2']})
            self.assertEqual(phase_result['report_path'], '/tmp/report.md')
            self.assertEqual(phase_result['summary_path'], '/tmp/summary.json')

    def test_warning_tolerant_policy_accepts_warning_only_validation(self):
        warning_summary = {'ok': False, 'extra_nodes': ['node-1']}

        def _fake_generate_xml(temp_dir):
            xml_path = os.path.join(temp_dir, 'scenario.xml')
            with open(xml_path, 'w', encoding='utf-8') as handle:
                handle.write('<Scenarios><CoreConnection host="10.0.0.50" port="50051" ssh_host="10.0.0.50" ssh_port="22" ssh_username="corevm" vmid="100" /><Scenario name="eval-scenario"><ScenarioEditor><HardwareInLoop><CoreConnection host="10.0.0.50" port="50051" ssh_host="10.0.0.50" ssh_port="22" ssh_username="corevm" vmid="100" /></HardwareInLoop></ScenarioEditor></Scenario></Scenarios>')
            return xml_path

        def _make_phase_result(phase, temp_dir, validation_summary=None):
            return {
                'phase': phase,
                'returncode': 0,
                'combined_output': '',
                'log_path': os.path.join(temp_dir, f'{phase}.log'),
                'plan_payload': {},
                'session_id': '99' if phase == 'execute' else None,
                'validation_summary': validation_summary,
                'report_path': None,
                'summary_path': None,
                'timed_out': False,
            }

        for policy, expected_success in [('strict', False), ('warning_tolerant', True)]:
            with self.subTest(policy=policy):
                spec = {
                    'name': 'eval-scenario',
                    'seed': 2024,
                    'topology': {'routers': 1, 'hosts': 2},
                    'services': {'enabled': False, 'count': 0},
                    'vulns': {'enabled': False, 'count': 0},
                    'flows': {'enabled': False, 'chain_length': 0},
                    'segmentation': {'enabled': False, 'density': 0.0},
                    'hitl': {'use_env': True},
                    'validation': {'policy': policy},
                }
                with tempfile.TemporaryDirectory() as temp_dir:
                    executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')
                    phase_map = {
                        'preview-plan': _make_phase_result('preview-plan', temp_dir),
                        'execute': _make_phase_result('execute', temp_dir, validation_summary=warning_summary),
                    }

                    with mock.patch.object(executor, '_generate_xml', side_effect=lambda: _fake_generate_xml(temp_dir)), \
                         mock.patch.object(executor, '_run_cli_phase', side_effect=lambda phase, *args, **kwargs: phase_map[phase]):
                        result = executor.run()

                    self.assertEqual(result['success'], expected_success)
                    if expected_success:
                        self.assertIn('extra_nodes=["node-1"]', result.get('warnings', []))
                    else:
                        self.assertIn('strict policy', result.get('error', ''))

    def test_execute_requires_core_session_marker(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 2025,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            phase_map = {
                'preview-plan': {
                    'phase': 'preview-plan',
                    'returncode': 0,
                    'combined_output': '',
                    'log_path': os.path.join(temp_dir, 'preview-plan.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                },
                'execute': {
                    'phase': 'execute',
                    'returncode': 0,
                    'combined_output': 'VALIDATION_SUMMARY_JSON: {"ok": true}\n',
                    'log_path': os.path.join(temp_dir, 'execute.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': {'ok': True},
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                },
            }

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=lambda phase, *args, **kwargs: phase_map[phase]):
                result = executor.run()

            self.assertFalse(result['success'])
            self.assertIn('CORE_SESSION_ID', result.get('error', ''))

    def test_execute_failure_without_validation_marker_preserves_cli_error(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 2026,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            phase_map = {
                'preview-plan': {
                    'phase': 'preview-plan',
                    'returncode': 0,
                    'combined_output': '',
                    'log_path': os.path.join(temp_dir, 'preview-plan.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                },
                'execute': {
                    'phase': 'execute',
                    'returncode': 1,
                    'combined_output': 'ERROR root - The execute phase requires CORE gRPC availability or successful remote delegation; no CORE session was started.\n',
                    'log_path': os.path.join(temp_dir, 'execute.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                },
            }

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=lambda phase, *args, **kwargs: phase_map[phase]):
                result = executor.run()

            self.assertFalse(result['success'])
            self.assertIn('exit code 1', result.get('error', ''))
            self.assertIn('no CORE session was started', result.get('error', ''))

    def test_execute_preflight_fails_early_for_unreachable_local_core(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 2027,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')
            phase_calls = []

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><CoreConnection host="127.0.0.1" port="50051" ssh_host="127.0.0.1" ssh_port="22" ssh_username="localuser" /><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            def _fake_run_cli_phase(phase, *args, **kwargs):
                phase_calls.append(phase)
                return {
                    'phase': phase,
                    'returncode': 0,
                    'combined_output': '',
                    'log_path': os.path.join(temp_dir, f'{phase}.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                }

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=_fake_run_cli_phase), \
                 mock.patch('scenarioforge_eval.executor.socket.create_connection', side_effect=OSError('Connection refused')):
                result = executor.run()

            self.assertFalse(result['success'])
            self.assertEqual(phase_calls, ['preview-plan'])
            self.assertIn('Local CORE gRPC preflight failed before execute', result.get('error', ''))
            self.assertIn('127.0.0.1:50051', result.get('error', ''))

    def test_execute_preflight_skips_when_xml_supports_remote_delegation(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 2028,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': False, 'chain_length': 0},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')
            phase_calls = []

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><CoreConnection host="127.0.0.1" port="50051" ssh_host="12.0.0.100" ssh_port="22" ssh_username="corevm" ssh_password="pw123" /><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            def _fake_run_cli_phase(phase, *args, **kwargs):
                phase_calls.append(phase)
                return {
                    'phase': phase,
                    'returncode': 1 if phase == 'execute' else 0,
                    'combined_output': 'remote failure\n' if phase == 'execute' else '',
                    'log_path': os.path.join(temp_dir, f'{phase}.log'),
                    'plan_payload': {},
                    'session_id': None,
                    'validation_summary': None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                }

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=_fake_run_cli_phase), \
                 mock.patch('scenarioforge_eval.executor.socket.create_connection', side_effect=AssertionError('preflight should skip delegated XML')):
                result = executor.run()

            self.assertFalse(result['success'])
            self.assertEqual(phase_calls, ['preview-plan', 'execute'])
            self.assertIn('exit code 1', result.get('error', ''))

    def test_run_uses_shared_vm_lock_for_runtime_phases(self):
        spec = {
            'name': 'eval-scenario',
            'seed': 999,
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': True, 'chain_length': 3, 'allow_duplicates': False},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
            'validation': {'policy': 'strict'},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')
            events = []

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><CoreConnection host="10.0.0.50" port="50051" ssh_host="10.0.0.50" ssh_port="22" ssh_username="corevm" vmid="100" /><Scenario name="eval-scenario"><ScenarioEditor><HardwareInLoop><CoreConnection host="10.0.0.50" port="50051" ssh_host="10.0.0.50" ssh_port="22" ssh_username="corevm" vmid="100" /></HardwareInLoop></ScenarioEditor></Scenario></Scenarios>')
                return xml_path

            def _fake_run_cli_phase(phase, *args, **kwargs):
                events.append(phase)
                return {
                    'phase': phase,
                    'returncode': 0,
                    'combined_output': '',
                    'log_path': os.path.join(temp_dir, f'{phase}.log'),
                    'plan_payload': {},
                    'session_id': '3' if phase == 'execute' else None,
                    'validation_summary': {'ok': True} if phase == 'execute' else None,
                    'report_path': None,
                    'summary_path': None,
                    'timed_out': False,
                }

            @contextmanager
            def _fake_lock(_xml_path):
                events.append('enter-lock')
                yield {'key': '10.0.0.50:22:corevm:100', 'path': os.path.join(temp_dir, 'vm.lock')}
                events.append('exit-lock')

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=_fake_run_cli_phase), \
                 mock.patch.object(executor, '_shared_vm_lock', side_effect=_fake_lock):
                result = executor.run()

            self.assertTrue(result['success'])
            self.assertEqual(events, ['preview-plan', 'enter-lock', 'flag-sequencing', 'execute', 'exit-lock'])


if __name__ == '__main__':
    unittest.main()