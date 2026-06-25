import argparse
import contextlib
import io
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


if __name__ == '__main__':
    unittest.main()
