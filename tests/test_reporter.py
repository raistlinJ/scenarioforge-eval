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

            with open(xml_path, 'w', encoding='utf-8') as handle:
                handle.write('<Scenarios><Scenario name="spec-a" /></Scenarios>')
            with open(preview_path, 'w', encoding='utf-8') as handle:
                json.dump({'phase': 'preview-plan', 'ok': True}, handle)
            with open(execute_log_path, 'w', encoding='utf-8') as handle:
                handle.write('PHASE: execute\nRuntimeError: boom\n')

            reporter = Reporter(temp_dir)
            result = {
                'success': False,
                'stages': {'preview_plan': 'PASS', 'failed_at': 'boom'},
                'error': 'Traceback (most recent call last):\nRuntimeError: boom',
                'artifacts': {
                    'scenario_xml': xml_path,
                    'preview_plan_json': preview_path,
                    'execute_log': execute_log_path,
                },
            }

            reporter.log_result('spec-a', result)

            prompt_path = os.path.join(temp_dir, 'spec-a_ai_prompt.md')
            with open(prompt_path, 'r', encoding='utf-8') as handle:
                prompt_text = handle.read()
            self.assertIn('## Generated Scenario XML', prompt_text)
            self.assertIn('<Scenario name="spec-a" />', prompt_text)
            self.assertIn('## Preview Plan JSON', prompt_text)
            self.assertIn('"phase": "preview-plan"', prompt_text)
            self.assertIn('## Execute Log', prompt_text)
            self.assertIn('PHASE: execute', prompt_text)


if __name__ == '__main__':
    unittest.main()