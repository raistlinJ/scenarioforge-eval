import json
import os
import tempfile
import unittest

from scenarioforge_eval.reporter import Reporter


class ReporterPromptArtifactTests(unittest.TestCase):
    def test_ai_prompt_includes_available_phase_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = os.path.join(temp_dir, 'scenario.xml')
            preview_path = os.path.join(temp_dir, 'preview-plan.json')
            execute_log_path = os.path.join(temp_dir, 'execute.log')
            execute_report_path = os.path.join(temp_dir, 'scenario-report.md')
            execute_summary_path = os.path.join(temp_dir, 'scenario-summary.json')

            with open(xml_path, 'w', encoding='utf-8') as handle:
                handle.write('<Scenarios><CoreConnection ssh_password="pw123" ssh_username="corevm" /><Scenario name="spec-a"><ScenarioEditor><HardwareInLoop><CoreConnection ssh_password="pw123" ssh_username="corevm" /></HardwareInLoop></ScenarioEditor></Scenario></Scenarios>')
            with open(preview_path, 'w', encoding='utf-8') as handle:
                json.dump({'phase': 'preview-plan', 'ok': True}, handle)
            with open(execute_log_path, 'w', encoding='utf-8') as handle:
                handle.write('PHASE: execute\nRuntimeError: boom\n')
            with open(execute_report_path, 'w', encoding='utf-8') as handle:
                handle.write('# Scenario Report\n\nFailure details\n')
            with open(execute_summary_path, 'w', encoding='utf-8') as handle:
                json.dump({'status': 'failed'}, handle)

            reporter = Reporter(temp_dir)
            result = {
                'success': False,
                'stages': {'preview_plan': 'PASS', 'failed_at': 'boom'},
                'error': 'Traceback (most recent call last):\nRuntimeError: boom',
                'artifacts': {
                    'scenario_xml': xml_path,
                    'preview_plan_json': preview_path,
                    'execute_log': execute_log_path,
                    'execute_report': execute_report_path,
                    'execute_summary': execute_summary_path,
                },
            }

            reporter.log_result('spec-a', result)

            prompt_path = os.path.join(temp_dir, 'spec-a_ai_prompt.md')
            with open(prompt_path, 'r', encoding='utf-8') as handle:
                prompt_text = handle.read()
            self.assertIn('## Generated Scenario XML', prompt_text)
            self.assertIn('ssh_password="[REDACTED]"', prompt_text)
            self.assertNotIn('ssh_password="pw123"', prompt_text)
            self.assertIn('## Preview Plan JSON', prompt_text)
            self.assertIn('"phase": "preview-plan"', prompt_text)
            self.assertIn('## Execute Log', prompt_text)
            self.assertIn('PHASE: execute', prompt_text)
            self.assertIn('## Scenario Report', prompt_text)
            self.assertIn('# Scenario Report', prompt_text)
            self.assertIn('## Scenario Summary', prompt_text)
            self.assertIn('"status": "failed"', prompt_text)


if __name__ == '__main__':
    unittest.main()