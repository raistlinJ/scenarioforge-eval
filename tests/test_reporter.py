import contextlib
import csv
import io
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

    def test_write_batch_metrics_exports_summary_raw_and_csv_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_out_dir = os.path.join(temp_dir, 'spec-a')
            os.makedirs(run_out_dir)
            reporter = Reporter(temp_dir)
            result = {
                'success': True,
                'stages': {'scenario_xml': 'PASS', 'preview_plan': 'PASS'},
                'metadata': {
                    'spec_file': '/tmp/spec.spec.yaml',
                    'iteration_index': 1,
                    'iteration_count': 1,
                },
                'phase_results': {
                    'preview-plan': {
                        'returncode': 0,
                        'timed_out': False,
                        'session_id': None,
                        'validation_summary': None,
                        'metrics': {
                            'started_at': '2026-06-30T00:00:00Z',
                            'ended_at': '2026-06-30T00:00:01Z',
                            'duration_s': 1.0,
                            'outputs': {
                                'stdout': {'bytes': 10, 'chars': 10, 'lines': 1, 'estimated_tokens': 2},
                                'stderr': {'bytes': 0, 'chars': 0, 'lines': 0, 'estimated_tokens': 0},
                                'combined': {'bytes': 10, 'chars': 10, 'lines': 1, 'estimated_tokens': 2},
                            },
                            'log': {'path': '/tmp/preview-plan.log', 'size_bytes': 10},
                            'resources': {'cpu_user_s': 0.1, 'cpu_system_s': 0.2, 'cpu_total_s': 0.3, 'max_rss_bytes': 1024},
                        },
                    },
                },
                'metrics': {
                    'schema_version': 1,
                    'token_estimator': 'regex_word_or_punctuation',
                    'run': {
                        'started_at': '2026-06-30T00:00:00Z',
                        'ended_at': '2026-06-30T00:00:01Z',
                        'duration_s': 1.0,
                        'resources': {'cpu_user_s': 0.1, 'cpu_system_s': 0.2, 'cpu_total_s': 0.3, 'max_rss_bytes': 1024},
                    },
                    'spec': {
                        'name': 'spec-a',
                        'seed': 123,
                        'target_phase': 'execute',
                        'topology': {'routers': 1, 'hosts': 2, 'nodes': 3},
                        'services': {'count': 1},
                        'vulnerabilities': {'count': 0},
                        'flows': {'enabled': False, 'chain_length': 0},
                    },
                    'phases': {
                        'preview-plan': {
                            'duration_s': 1.0,
                            'outputs': {'combined': {'estimated_tokens': 2}},
                            'log': {'size_bytes': 10},
                            'resources': {'cpu_total_s': 0.3},
                        },
                    },
                    'artifacts': {
                        'output_dir': {'file_count': 3, 'total_size_bytes': 100},
                    },
                },
                'artifacts': {
                    'output_dir': run_out_dir,
                },
            }

            with contextlib.redirect_stdout(io.StringIO()):
                paths = reporter.write_batch_metrics([result])

            for path in paths.values():
                self.assertTrue(os.path.exists(path), path)

            with open(paths['summary_json'], 'r', encoding='utf-8') as handle:
                summary = json.load(handle)
            self.assertEqual(summary['runs']['total'], 1)
            self.assertEqual(summary['runs']['successes'], 1)
            self.assertEqual(summary['runs']['estimated_output_tokens'], 2)
            self.assertEqual(summary['phases']['preview-plan']['count'], 1)

            with open(paths['raw_jsonl'], 'r', encoding='utf-8') as handle:
                raw_lines = [line for line in handle.read().splitlines() if line]
            self.assertEqual(len(raw_lines), 1)

            with open(paths['runs_csv'], 'r', encoding='utf-8') as handle:
                run_rows = list(csv.DictReader(handle))
            self.assertEqual(run_rows[0]['spec_name'], 'spec-a')
            self.assertEqual(run_rows[0]['estimated_output_tokens'], '2')

            with open(paths['phases_csv'], 'r', encoding='utf-8') as handle:
                phase_rows = list(csv.DictReader(handle))
            self.assertEqual(phase_rows[0]['phase'], 'preview-plan')
            self.assertEqual(phase_rows[0]['estimated_output_tokens'], '2')

            root_metrics_dir = os.path.join(temp_dir, 'metrics')
            self.assertTrue(os.path.exists(os.path.join(root_metrics_dir, 'batch_metrics_summary.json')))
            self.assertTrue(os.path.exists(os.path.join(root_metrics_dir, 'batch_metrics_runs.csv')))
            self.assertTrue(os.path.exists(os.path.join(root_metrics_dir, 'batch_metrics_phases.csv')))

            root_run_metrics_dir = os.path.join(root_metrics_dir, 'runs', 'spec-a')
            self.assertTrue(os.path.exists(os.path.join(root_run_metrics_dir, 'run_metrics_summary.json')))
            self.assertTrue(os.path.exists(os.path.join(root_run_metrics_dir, 'run_metrics.csv')))
            self.assertTrue(os.path.exists(os.path.join(root_run_metrics_dir, 'phase_metrics.csv')))

            run_metrics_dir = os.path.join(run_out_dir, 'metrics')
            self.assertTrue(os.path.exists(os.path.join(run_metrics_dir, 'run_metrics_summary.json')))
            self.assertTrue(os.path.exists(os.path.join(run_metrics_dir, 'run_metrics.csv')))
            self.assertTrue(os.path.exists(os.path.join(run_metrics_dir, 'phase_metrics.csv')))


if __name__ == '__main__':
    unittest.main()
