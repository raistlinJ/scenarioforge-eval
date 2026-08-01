"""Solver-shaping flag-sequencing options must be reachable from a spec.

The evaluator passed four of ScenarioForge's thirteen flag-sequencing options.
Two of the missing ones shape the scenario rather than the plumbing:

- `--flow-dependency-level` (1-5) governs solver strictness, so every run
  silently used the default of 3 and the other four levels went unexercised
- `--flow-preset` reaches an alternative sequencing path entirely

`--flow-chain-ids` is the third: it pins an explicit chain instead of letting
the solver choose.
"""

import ast
import os
import tempfile
import unittest

from scenarioforge_eval.executor import Executor

HERE = os.path.dirname(os.path.abspath(__file__))
EXECUTOR_PATH = os.path.join(os.path.dirname(HERE), 'scenarioforge_eval', 'executor.py')


def _executor(spec=None):
    return Executor(spec=spec or {}, out_dir=tempfile.gettempdir(), sf_path='.')


class DependencyLevelTests(unittest.TestCase):
    def test_unset_leaves_scenarioforge_to_choose(self):
        """Not passing the flag is different from passing its default."""
        self.assertIsNone(_executor()._resolve_dependency_level({}))
        self.assertIsNone(_executor()._resolve_dependency_level({'dependency_level': None}))
        self.assertIsNone(_executor()._resolve_dependency_level({'dependency_level': ''}))

    def test_each_supported_level_is_accepted(self):
        executor = _executor()
        for level in range(1, 6):
            self.assertEqual(executor._resolve_dependency_level({'dependency_level': level}), level)

    def test_a_numeric_string_is_accepted(self):
        self.assertEqual(_executor()._resolve_dependency_level({'dependency_level': '4'}), 4)

    def test_out_of_range_is_rejected_rather_than_clamped(self):
        """Clamping would silently run a different solver strictness."""
        executor = _executor()
        for level in (0, 6, -1, 99):
            with self.assertRaises(ValueError) as ctx:
                executor._resolve_dependency_level({'dependency_level': level})
            self.assertIn('between 1 and 5', str(ctx.exception))

    def test_a_non_numeric_value_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _executor()._resolve_dependency_level({'dependency_level': 'strict'})
        self.assertIn('must be an integer', str(ctx.exception))

    def test_the_range_matches_what_scenarioforge_accepts(self):
        try:
            import scenarioforge.cli  # noqa: F401
        except Exception as exc:  # pragma: no cover - depends on sibling checkout
            self.skipTest(f'ScenarioForge not importable: {exc}')

        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(scenarioforge.cli.__file__))),
            'scenarioforge', 'cli.py',
        )
        with open(cli_path, encoding='utf-8', errors='ignore') as handle:
            source = handle.read()
        self.assertIn(
            'dependency strictness level (1-5)', source.lower(),
            'ScenarioForge changed the accepted range; update DEPENDENCY_LEVEL_RANGE',
        )


class FlowArgumentWiringTests(unittest.TestCase):
    """The args are built inside a long phase method, so read the real source
    rather than reimplementing the construction here."""

    @staticmethod
    def _flow_arg_block():
        with open(EXECUTOR_PATH, encoding='utf-8') as handle:
            source = handle.read()
        start = source.index("flow_args = [")
        end = source.index('self._run_cli_phase(', start)
        return source[start:end]

    def test_dependency_level_is_passed_when_resolved(self):
        block = self._flow_arg_block()
        self.assertIn("'--flow-dependency-level'", block)
        self.assertIn('_resolve_dependency_level(flows_spec)', block)
        self.assertIn('if dependency_level is not None', block)

    def test_preset_is_passed_only_when_set(self):
        block = self._flow_arg_block()
        self.assertIn("'--flow-preset'", block)
        self.assertIn('if preset:', block)

    def test_chain_ids_are_passed_as_a_csv_list(self):
        block = self._flow_arg_block()
        self.assertIn("'--flow-chain-ids'", block)
        self.assertIn("','.join(chain_ids)", block)

    def test_the_executor_still_parses(self):
        with open(EXECUTOR_PATH, encoding='utf-8') as handle:
            ast.parse(handle.read())

    def test_every_flag_passed_here_exists_in_scenarioforge(self):
        """A typo in a flag name would only surface as a failed run."""
        try:
            import scenarioforge.cli  # noqa: F401
        except Exception as exc:  # pragma: no cover - depends on sibling checkout
            self.skipTest(f'ScenarioForge not importable: {exc}')

        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(scenarioforge.cli.__file__))),
            'scenarioforge', 'cli.py',
        )
        with open(cli_path, encoding='utf-8', errors='ignore') as handle:
            cli_source = handle.read()

        import re

        for flag in sorted(set(re.findall(r"'(--flow-[a-z-]+)'", self._flow_arg_block()))):
            self.assertIn(f"'{flag}'", cli_source, f'{flag} is not a ScenarioForge option')


class SchemaTests(unittest.TestCase):
    def test_the_new_keys_are_declared(self):
        import json

        with open(os.path.join(os.path.dirname(HERE), 'scenarioforge_eval', 'schema.json')) as handle:
            schema = json.load(handle)
        flows = schema['properties']['flows']['properties']
        self.assertEqual(flows['dependency_level']['minimum'], 1)
        self.assertEqual(flows['dependency_level']['maximum'], 5)
        self.assertIn('preset', flows)
        self.assertIn('chain_ids', flows)


if __name__ == '__main__':
    unittest.main()
