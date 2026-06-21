import argparse
import unittest

from scenarioforge_eval.main import resolve_target_phase


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


if __name__ == '__main__':
    unittest.main()