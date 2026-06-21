import os
import tempfile
import textwrap
import unittest
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
            self.assertIn('ssh_password="pw123"', text)
            self.assertIn('ssh_username="corevm"', text)
            self.assertIn('name="ens19"', text)

    def test_run_uses_phase_based_cli_sequence(self):
        spec = {
            'name': 'eval-scenario',
            'topology': {'routers': 1, 'hosts': 2},
            'services': {'enabled': False, 'count': 0},
            'vulns': {'enabled': False, 'count': 0},
            'flows': {'enabled': True, 'chain_length': 3, 'allow_duplicates': False},
            'segmentation': {'enabled': False, 'density': 0.0},
            'hitl': {'use_env': True},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            executor = Executor(spec=spec, out_dir=temp_dir, sf_path='/Users/jcacosta/Documents/GitHub/scenarioforge')

            calls = []

            def _fake_generate_xml():
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write('<Scenarios><Scenario name="eval-scenario"><ScenarioEditor /></Scenario></Scenarios>')
                return xml_path

            def _fake_run_cli_phase(phase, xml_path, scenario_name, *, extra_args=None, json_output_name=None, log_name=None):
                calls.append({
                    'phase': phase,
                    'xml_path': xml_path,
                    'scenario_name': scenario_name,
                    'extra_args': list(extra_args or []),
                    'json_output_name': json_output_name,
                    'log_name': log_name,
                })
                return {}

            with mock.patch.object(executor, '_generate_xml', side_effect=_fake_generate_xml), \
                 mock.patch.object(executor, '_run_cli_phase', side_effect=_fake_run_cli_phase):
                result = executor.run()

            self.assertTrue(result['success'])
            self.assertTrue(result['artifacts']['scenario_xml'].endswith('scenario.xml'))
            self.assertTrue(result['artifacts']['preview_plan_json'].endswith('preview-plan.json'))
            self.assertTrue(result['artifacts']['flag_sequencing_json'].endswith('flag-sequencing.json'))
            self.assertTrue(result['artifacts']['execute_log'].endswith('execute.log'))
            self.assertEqual([call['phase'] for call in calls], ['preview-plan', 'flag-sequencing', 'execute'])
            self.assertEqual(calls[0]['json_output_name'], 'preview-plan.json')
            self.assertEqual(calls[1]['json_output_name'], 'flag-sequencing.json')
            self.assertIn('--flow-mode', calls[1]['extra_args'])
            self.assertEqual(calls[2]['log_name'], 'execute.log')


if __name__ == '__main__':
    unittest.main()