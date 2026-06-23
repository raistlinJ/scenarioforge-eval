import argparse
import os
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
