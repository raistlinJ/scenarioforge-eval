import argparse
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from scenarioforge_eval import main as main_module
from scenarioforge_eval.main import resolve_target_phase
from scenarioforge_eval.reporter import Reporter


class MainCliPhaseSelectionTests(unittest.TestCase):
    def test_defaults_to_execute_to_match_cli(self):
        args = argparse.Namespace(execute=False, flag_sequencing=False, topology=False)

        self.assertEqual(resolve_target_phase(args), 'execute')

    def test_explicit_flag_sequencing_is_preserved(self):
        args = argparse.Namespace(execute=False, flag_sequencing=True, topology=False)

        self.assertEqual(resolve_target_phase(args), 'flag-sequencing')

    def test_explicit_topology_is_preserved(self):
        args = argparse.Namespace(execute=False, flag_sequencing=False, topology=True)

        self.assertEqual(resolve_target_phase(args), 'topology')

    def test_reporter_normalizes_relative_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                reporter = Reporter('test-outs')
            finally:
                os.chdir(original_cwd)

            self.assertEqual(
                os.path.realpath(reporter.out_dir),
                os.path.realpath(os.path.join(temp_dir, 'test-outs')),
            )

    def test_status_footer_tracks_counts_and_uses_color(self):
        stream = io.StringIO()
        footer = main_module.BatchStatusFooter(
            total_iterations=3,
            target_phase='execute',
            output_root='/tmp/out',
            stream=stream,
            use_color=True,
        )

        footer.render('ready')
        footer.start_iteration('fake-spec_run1', 101)
        footer.finish_iteration('fake-spec_run1', {'success': True, 'stages': {'execute': 'PASS'}})
        footer.start_iteration('fake-spec_run2', 202)
        footer.finish_iteration('fake-spec_run2', {'success': False, 'stages': {'execute': 'FAIL'}})
        footer.stop()

        output = stream.getvalue()
        self.assertIn('\033[', output)
        self.assertIn('runs 2/3', output)
        self.assertIn('ok 1', output)
        self.assertIn('fail 1', output)
        self.assertIn('pending 1', output)
        self.assertIn('current fake-spec_run2 seed=202', output)
        self.assertIn('last failure fake-spec_run2 (execute)', output)

    def test_main_prints_status_footer_for_planned_iterations(self):
        executor_specs = []

        class _FakeSpec:
            spec = {'iterations': 2}

            def get_name(self):
                return 'fake-spec'

            def get_topology_spec(self, rng=None):
                return {'hosts': 1, 'routers': 0}

            def get_services_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_vulns_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_flows_spec(self, rng=None):
                return {'enabled': False, 'chain_length': 0}

            def get_segmentation_spec(self):
                return {'enabled': False, 'density': 0.0}

            def get_hitl_spec(self):
                return {'use_env': True}

            def get_validation_spec(self):
                return {'policy': 'strict'}

        class _FakeExecutor:
            def __init__(
                self,
                spec,
                out_dir,
                sf_path,
                target_phase='execute',
                verbose=False,
                dangerous_cleanup_between_runs=False,
            ):
                executor_specs.append(spec['name'])

            def run(self):
                return {'success': True, 'stages': {'execute': 'PASS'}, 'artifacts': {}}

        stdout = io.StringIO()
        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml') as spec_file, \
             tempfile.TemporaryDirectory() as out_dir, \
             contextlib.redirect_stdout(stdout), \
             mock.patch.object(main_module, 'SpecParser', return_value=_FakeSpec()), \
             mock.patch.object(main_module, 'Executor', _FakeExecutor), \
             mock.patch.object(main_module.Reporter, 'log_result', return_value=None), \
             mock.patch(
                 'sys.argv',
                 [
                     'scenarioforge-eval',
                     spec_file.name,
                     '--sf-path',
                     '/tmp/scenarioforge',
                     '--out',
                     out_dir,
                 ],
             ):
            main_module.main()

        output = stdout.getvalue()
        self.assertEqual(executor_specs, ['fake-spec_run1', 'fake-spec_run2'])
        self.assertIn('[READY] | runs 0/2', output)
        self.assertIn('current fake-spec_run1 seed=', output)
        self.assertIn('runs 1/2 | ok 1 | fail 0 | pending 1', output)
        self.assertIn('[DONE] | runs 2/2 | ok 2 | fail 0 | pending 0', output)

    def test_main_passes_dangerous_cleanup_flag_to_executor(self):
        captured = {}

        class _FakeSpec:
            spec = {'iterations': 1}

            def get_name(self):
                return 'fake-spec'

            def get_topology_spec(self, rng=None):
                return {'hosts': 1, 'routers': 0}

            def get_services_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_vulns_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_flows_spec(self, rng=None):
                return {'enabled': False, 'chain_length': 0}

            def get_segmentation_spec(self):
                return {'enabled': False, 'density': 0.0}

            def get_hitl_spec(self):
                return {'use_env': True}

            def get_validation_spec(self):
                return {'policy': 'strict'}

        class _FakeExecutor:
            def __init__(
                self,
                spec,
                out_dir,
                sf_path,
                target_phase='execute',
                verbose=False,
                dangerous_cleanup_between_runs=False,
            ):
                captured['dangerous_cleanup_between_runs'] = dangerous_cleanup_between_runs
                captured['target_phase'] = target_phase

            def run(self):
                return {'success': True, 'stages': {}, 'artifacts': {}}

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml') as spec_file, \
             tempfile.TemporaryDirectory() as out_dir, \
             mock.patch.object(main_module, 'SpecParser', return_value=_FakeSpec()), \
             mock.patch.object(main_module, 'Executor', _FakeExecutor), \
             mock.patch.object(main_module.Reporter, 'log_result', return_value=None), \
             mock.patch(
                 'sys.argv',
                 [
                     'scenarioforge-eval',
                     spec_file.name,
                     '--sf-path',
                     '/tmp/scenarioforge',
                     '--out',
                     out_dir,
                     '--dangerous-cleanup-between-runs',
                 ],
             ):
            main_module.main()

        self.assertTrue(captured['dangerous_cleanup_between_runs'])
        self.assertEqual(captured['target_phase'], 'execute')

    def test_error_report_includes_validation_diagnostics_and_generators(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            execute_log = os.path.join(temp_dir, 'execute.log')
            execute_summary = os.path.join(temp_dir, 'execute-summary.json')
            with open(execute_log, 'w', encoding='utf-8') as handle:
                handle.write(
                    "INFO scenarioforge.cli: ordinary progress\n"
                    "WARNING scenarioforge.parsers.node_info: defaulting values\n"
                    "remote error: container exited\n"
                    'VALIDATION_SUMMARY_JSON: {"ok": false, "error": "duplicated elsewhere"}\n'
                )
            with open(execute_summary, 'w', encoding='utf-8') as handle:
                json.dump({'generators_used': ['flag-gen-a']}, handle)

            report = main_module._build_error_report(
                'spec-a',
                {
                    'metadata': {'seed': 123},
                    'phase_results': {
                        'execute': {
                            'log_path': execute_log,
                            'validation_summary': {
                                'ok': False,
                                'missing_nodes': ['host-2'],
                                'docker_start_pending': ['host-3'],
                                'generator_validation_detail': [
                                    {
                                        'generator_id': 'node-gen-1',
                                        'generator_name': 'Node Generator One',
                                        'generator_type': 'flag-node-generator',
                                        'node_name': 'host-2',
                                    }
                                ],
                            },
                        }
                    },
                    'artifacts': {'execute_summary': execute_summary},
                },
                timestamp='2026-07-01T00:00:00',
            )

        self.assertIn('--- GENERATORS USED ---', report)
        self.assertIn('id=node-gen-1, name=Node Generator One, type=flag-node-generator, node=host-2', report)
        self.assertIn('- flag-gen-a', report)
        self.assertIn('--- VALIDATION RESULT ---', report)
        self.assertIn('"missing_nodes": [', report)
        self.assertIn('missing_nodes: ["host-2"]', report)
        self.assertIn('docker_start_pending: ["host-3"]', report)
        self.assertIn('WARNING scenarioforge.parsers.node_info: defaulting values', report)
        self.assertIn('remote error: container exited', report)
        self.assertNotIn('ordinary progress', report)
        self.assertNotIn('VALIDATION_SUMMARY_JSON:', report)

    def test_main_writes_latest_and_combined_error_files(self):
        class _FakeSpec:
            spec = {'iterations': 1}

            def get_name(self):
                return 'fake-spec'

            def get_topology_spec(self, rng=None):
                return {'hosts': 1, 'routers': 0}

            def get_services_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_vulns_spec(self, rng=None):
                return {'enabled': False, 'count': 0}

            def get_flows_spec(self, rng=None):
                return {'enabled': False, 'chain_length': 0}

            def get_segmentation_spec(self):
                return {'enabled': False, 'density': 0.0}

            def get_hitl_spec(self):
                return {'use_env': True}

            def get_validation_spec(self):
                return {'policy': 'strict'}

        class _FakeExecutor:
            VALIDATION_ERROR_FIELDS = ('missing_nodes',)
            VALIDATION_WARNING_FIELDS = ('docker_start_pending',)

            def __init__(
                self,
                spec,
                out_dir,
                sf_path,
                target_phase='execute',
                verbose=False,
                dangerous_cleanup_between_runs=False,
            ):
                self.out_dir = out_dir

            def run(self):
                os.makedirs(self.out_dir, exist_ok=True)
                execute_log = os.path.join(self.out_dir, 'execute.log')
                with open(execute_log, 'w', encoding='utf-8') as handle:
                    handle.write(
                        "INFO scenarioforge.cli: hidden progress\n"
                        "WARNING scenarioforge.cli: useful warning\n"
                        "worker error: useful failure\n"
                    )
                return {
                    'success': False,
                    'stages': {'execute': 'FAIL'},
                    'error': None,
                    'phase_results': {
                        'execute': {
                            'log_path': execute_log,
                            'validation_summary': {
                                'ok': False,
                                'missing_nodes': ['host-9'],
                            },
                        }
                    },
                    'artifacts': {},
                }

        stdout = io.StringIO()
        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml') as spec_file, \
             tempfile.TemporaryDirectory() as out_dir, \
             contextlib.redirect_stdout(stdout), \
             mock.patch.object(main_module, 'SpecParser', return_value=_FakeSpec()), \
             mock.patch.object(main_module, 'Executor', _FakeExecutor), \
             mock.patch.object(main_module.Reporter, 'log_result', return_value=None), \
             mock.patch.object(main_module.Reporter, 'write_batch_metrics', return_value=None), \
             mock.patch(
                 'sys.argv',
                 [
                     'scenarioforge-eval',
                     spec_file.name,
                     '--sf-path',
                     '/tmp/scenarioforge',
                     '--out',
                     out_dir,
                 ],
             ):
            main_module.main()

            latest_path = os.path.join(out_dir, 'latest.errors')
            combined_hyphen_path = os.path.join(out_dir, 'combined-latest.errors')
            combined_underscore_path = os.path.join(out_dir, 'combined_latest.errors')
            for path in (latest_path, combined_hyphen_path, combined_underscore_path):
                self.assertTrue(os.path.exists(path), path)
                with open(path, 'r', encoding='utf-8') as handle:
                    content = handle.read()
                self.assertIn('--- VALIDATION RESULT ---', content)
                self.assertIn('missing_nodes: ["host-9"]', content)
                self.assertIn('WARNING scenarioforge.cli: useful warning', content)
                self.assertIn('worker error: useful failure', content)
                self.assertNotIn('hidden progress', content)


if __name__ == '__main__':
    unittest.main()
