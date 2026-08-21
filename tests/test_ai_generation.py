"""Prompt-driven scenario generation: parsing, routing, and failure surface.

Every test here stubs the ScenarioForge CLI subprocess.  Generation is a live
model call in production, and an eval suite that made one would be slow, costly,
and non-deterministic.
"""

import argparse
import json
import os
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

import yaml

from scenarioforge_eval.executor import Executor, PhaseExecutionError
from scenarioforge_eval.main import _apply_ai_overrides
from scenarioforge_eval.parser import (
    AI_BRIDGE_TIMEOUT_CEILING_S,
    AI_TIMEOUT_CEILING_S,
    DEFAULT_AI_BRIDGE_MODE,
    SpecParser,
)
from scenarioforge_eval.reproduction import _generation_summary


def _parser_for(spec: dict) -> SpecParser:
    handle = tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False, encoding='utf-8')
    yaml.safe_dump(spec, handle)
    handle.close()
    return SpecParser(handle.name)


class AiSpecParsingTests(unittest.TestCase):
    def test_spec_without_prompt_keeps_generation_disabled(self):
        resolved = _parser_for({'name': 'plain', 'topology': {'routers': 1, 'hosts': 1}}).get_ai_spec()

        self.assertFalse(resolved['enabled'])
        self.assertEqual(resolved['prompt'], '')

    def test_bare_top_level_prompt_is_shorthand_for_ai_prompt(self):
        resolved = _parser_for({'name': 'short', 'prompt': '  two routers  '}).get_ai_spec()

        self.assertTrue(resolved['enabled'])
        self.assertEqual(resolved['prompt'], 'two routers')

    def test_ai_prompt_wins_over_the_top_level_shorthand(self):
        resolved = _parser_for({'prompt': 'shorthand', 'ai': {'prompt': 'explicit'}}).get_ai_spec()

        self.assertEqual(resolved['prompt'], 'explicit')

    def test_explicit_enabled_false_disables_a_prompted_spec(self):
        resolved = _parser_for({'ai': {'prompt': 'two routers', 'enabled': False}}).get_ai_spec()

        self.assertFalse(resolved['enabled'])

    def test_enabled_without_a_prompt_stays_disabled(self):
        resolved = _parser_for({'ai': {'enabled': True}}).get_ai_spec()

        self.assertFalse(resolved['enabled'])

    def test_bridged_timeout_is_clamped_to_the_lower_bridge_ceiling(self):
        """The bridge clamps harder than the direct path, and eval runs bridge.

        ScenarioForge applies min(max(t, 5), 480) on the direct JSON path but
        _normalize_bridge_timeout_seconds (high=240) on the MCP bridge. Since
        every eval run requests the bridge, reporting the 480 ceiling would
        promise a budget the run never gets -- observed live as a generation
        that failed at "timed out after 240s" while its settings said 480.
        """
        resolved = _parser_for({'ai': {'prompt': 'p', 'timeout_s': 900}}).get_ai_spec()

        self.assertEqual(resolved['timeout_s'], AI_BRIDGE_TIMEOUT_CEILING_S)
        self.assertEqual(resolved['timeout_ceiling_s'], AI_BRIDGE_TIMEOUT_CEILING_S)
        self.assertEqual(resolved['timeout_requested_s'], 900.0)
        self.assertLess(AI_BRIDGE_TIMEOUT_CEILING_S, AI_TIMEOUT_CEILING_S)

    def test_a_480s_request_is_reported_as_lowered_not_honoured(self):
        # Every shipped prompt spec asks for 480; each one is really getting 240.
        resolved = _parser_for({'ai': {'prompt': 'p', 'timeout_s': 480}}).get_ai_spec()

        self.assertEqual(resolved['timeout_s'], 240.0)
        self.assertEqual(resolved['timeout_requested_s'], 480.0)

    def test_timeout_within_the_ceiling_is_not_reported_as_clamped(self):
        resolved = _parser_for({'ai': {'prompt': 'p', 'timeout_s': 120}}).get_ai_spec()

        self.assertEqual(resolved['timeout_s'], 120.0)
        self.assertNotIn('timeout_requested_s', resolved)

    def test_range_form_resolves_through_the_shared_value_resolver(self):
        import random

        resolved = _parser_for({'ai': {'prompt': 'p', 'timeout_s': [60, 60]}}).get_ai_spec(
            rng=random.Random(1)
        )

        self.assertEqual(resolved['timeout_s'], 60.0)

    def test_bridge_mode_defaults_on_and_is_overridable(self):
        default = _parser_for({'ai': {'prompt': 'p'}}).get_ai_spec()
        override = _parser_for({'ai': {'prompt': 'p', 'bridge_mode': 'other'}}).get_ai_spec()

        self.assertEqual(default['bridge_mode'], DEFAULT_AI_BRIDGE_MODE)
        self.assertEqual(override['bridge_mode'], 'other')

    def test_omitted_overrides_are_absent_and_empty_ones_do_not_override(self):
        resolved = _parser_for({
            'ai': {'prompt': 'p', 'provider': 'openai', 'model': '', 'base_url': None},
        }).get_ai_spec()

        self.assertEqual(resolved['provider'], 'openai')
        self.assertNotIn('model', resolved)
        self.assertNotIn('base_url', resolved)

    def test_retries_default_to_zero_and_never_go_negative(self):
        self.assertEqual(_parser_for({'ai': {'prompt': 'p'}}).get_ai_spec()['retries'], 0)
        self.assertEqual(_parser_for({'ai': {'prompt': 'p', 'retries': -3}}).get_ai_spec()['retries'], 0)
        self.assertEqual(_parser_for({'ai': {'prompt': 'p', 'retries': 2}}).get_ai_spec()['retries'], 2)


class AiCliOverrideTests(unittest.TestCase):
    def test_prompt_flag_enables_generation_and_replaces_the_spec_prompt(self):
        ai_spec = {'enabled': False, 'prompt': 'from spec'}

        _apply_ai_overrides(ai_spec, argparse.Namespace(prompt='from cli', no_ai=False))

        self.assertTrue(ai_spec['enabled'])
        self.assertEqual(ai_spec['prompt'], 'from cli')

    def test_no_ai_forces_the_deterministic_path(self):
        ai_spec = {'enabled': True, 'prompt': 'from spec'}

        _apply_ai_overrides(ai_spec, argparse.Namespace(prompt=None, no_ai=True))

        self.assertFalse(ai_spec['enabled'])


def _ai_payload(**overrides) -> dict:
    payload = {
        'ok': True,
        'phase': 'ai',
        'xml_path': '/unused/scenario.xml',
        'scenario': 'ai-run',
        'written': True,
        'overwritten': True,
        'prompt': 'two routers',
        'acting_user': 'eval-operator',
        'applied_actions': [{'tool': 'set_node_info'}],
        'settings': {
            'provider': 'openai',
            'model': 'test-model',
            'base_url': 'https://example.invalid/v1',
            'bridge_mode': 'mcp-python-sdk',
            'api_key': '<set len=8>',
            'api_key_source': 'environment',
        },
    }
    payload.update(overrides)
    return payload


class AiExecutorRoutingTests(unittest.TestCase):
    def _executor(self, temp_dir, ai_spec):
        spec = {'name': 'ai-run', 'seed': 4242}
        if ai_spec is not None:
            spec['ai'] = ai_spec
        return Executor(spec=spec, out_dir=temp_dir, sf_path=temp_dir)

    def test_spec_without_ai_block_uses_the_deterministic_builder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, None)
            with mock.patch.object(
                executor, '_generate_xml_from_spec', return_value='/built/by/spec.xml'
            ) as built, mock.patch.object(executor, '_generate_xml_from_prompt') as prompted:
                self.assertEqual(executor._generate_xml(), '/built/by/spec.xml')

            built.assert_called_once_with()
            prompted.assert_not_called()
            self.assertIsNone(executor._ai_generation)

    def test_disabled_ai_block_still_uses_the_deterministic_builder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, {'enabled': False, 'prompt': 'two routers'})
            with mock.patch.object(
                executor, '_generate_xml_from_spec', return_value='/built/by/spec.xml'
            ) as built, mock.patch.object(executor, '_generate_xml_from_prompt') as prompted:
                executor._generate_xml()

            built.assert_called_once_with()
            prompted.assert_not_called()

    def test_enabled_ai_block_invokes_the_ai_phase_with_the_expected_argv(self):
        ai_spec = {
            'enabled': True,
            'prompt': 'two routers',
            'retries': 0,
            'timeout_s': 480.0,
            'bridge_mode': 'mcp-python-sdk',
            'provider': 'openai',
            'model': 'test-model',
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, ai_spec)
            recorded = {}

            def _fake_phase(phase, xml_path, scenario_name, **kwargs):
                recorded.update(
                    phase=phase, xml_path=xml_path, scenario_name=scenario_name, kwargs=kwargs
                )
                return {'phase': 'ai', 'plan_payload': _ai_payload(), 'log_path': None}

            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=_fake_phase
            ), mock.patch.object(
                executor, '_apply_core_connection_to_generated_xml'
            ), mock.patch.object(executor, '_generate_xml_from_spec') as built:
                xml_path = executor._generate_xml()

            built.assert_not_called()
            self.assertEqual(xml_path, os.path.join(temp_dir, 'scenario.xml'))
            self.assertEqual(recorded['phase'], 'ai')
            self.assertEqual(recorded['scenario_name'], 'ai-run')
            self.assertEqual(recorded['kwargs']['seed'], 4242)

            extra = recorded['kwargs']['extra_args']
            self.assertEqual(extra[extra.index('--prompt') + 1], 'two routers')
            self.assertIn('--force', extra)
            self.assertEqual(extra[extra.index('--ai-bridge-mode') + 1], 'mcp-python-sdk')
            self.assertEqual(extra[extra.index('--ai-provider') + 1], 'openai')
            self.assertEqual(extra[extra.index('--ai-model') + 1], 'test-model')
            self.assertEqual(extra[extra.index('--ai-timeout-seconds') + 1], '480.0')
            # A bridged run is the whole point; skipping it breaks reasoning models.
            self.assertNotIn('--ai-skip-bridge', extra)
            self.assertNotIn('--ai-preview-only', extra)
            # Credentials are never passed from the eval side.
            self.assertNotIn('--ai-api-key', extra)

    def test_ai_phase_timeout_always_clears_the_provider_budget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, {'enabled': True, 'prompt': 'p'})
            # A batch-wide phase timeout below the provider budget would kill a
            # generation the provider was still entitled to finish.
            executor.phase_timeout_s = 300

            budget = executor._ai_phase_timeout({'timeout_s': AI_BRIDGE_TIMEOUT_CEILING_S})

        self.assertGreater(budget, AI_BRIDGE_TIMEOUT_CEILING_S)

    def test_ai_phase_timeout_never_shortens_a_larger_batch_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, {'enabled': True, 'prompt': 'p'})
            executor.phase_timeout_s = 1200

            self.assertEqual(executor._ai_phase_timeout({'timeout_s': 60.0}), 1200)

    def test_omitted_overrides_are_left_off_the_command_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, {'enabled': True, 'prompt': 'p'})
            extra = executor._ai_phase_extra_args(executor._ai_spec())

        for flag in ('--ai-provider', '--ai-model', '--ai-base-url', '--ai-timeout-seconds'):
            self.assertNotIn(flag, extra)

    def test_successful_generation_records_prompt_provider_and_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(
                temp_dir, {'enabled': True, 'prompt': 'two routers', 'retries': 0}
            )
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor,
                '_run_cli_phase',
                return_value={'phase': 'ai', 'plan_payload': _ai_payload(), 'log_path': None},
            ), mock.patch.object(executor, '_apply_core_connection_to_generated_xml'):
                executor._generate_xml()

            generation = executor._ai_generation

        self.assertEqual(generation['prompt'], 'two routers')
        self.assertEqual(generation['provider'], 'openai')
        self.assertEqual(generation['model'], 'test-model')
        self.assertEqual(generation['base_url'], 'https://example.invalid/v1')
        self.assertEqual(generation['applied_actions'], [{'tool': 'set_node_info'}])
        self.assertEqual(generation['acting_user'], 'eval-operator')
        self.assertEqual(generation['attempts'], 1)
        # The key never travels with the run record, redacted or not.
        self.assertNotIn('api_key', generation['settings'])
        self.assertNotIn('api_key_source', generation['settings'])
        self.assertNotIn('api_key', json.dumps(generation))

    def test_clamped_timeout_is_reported_as_a_run_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(
                temp_dir,
                {
                    'enabled': True,
                    'prompt': 'p',
                    'timeout_s': AI_TIMEOUT_CEILING_S,
                    'timeout_requested_s': 900.0,
                },
            )
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor,
                '_run_cli_phase',
                return_value={'phase': 'ai', 'plan_payload': _ai_payload(), 'log_path': None},
            ), mock.patch.object(executor, '_apply_core_connection_to_generated_xml'):
                executor._generate_xml()

            result = {}
            executor._record_ai_generation(result)

        self.assertTrue(any('480' in warning and '900' in warning for warning in result['warnings']))


class AiFailureSurfaceTests(unittest.TestCase):
    def _executor(self, temp_dir, **ai_overrides):
        ai_spec = {'enabled': True, 'prompt': 'two routers', 'retries': 0}
        ai_spec.update(ai_overrides)
        return Executor(
            spec={'name': 'ai-run', 'seed': 1, 'ai': ai_spec}, out_dir=temp_dir, sf_path=temp_dir
        )

    def test_provider_http_error_surfaces_the_providers_own_text(self):
        payload = {
            'ok': False,
            'phase': 'ai',
            'status': 502,
            'error': 'OpenAI-compatible endpoint returned HTTP 401',
        }
        failure = PhaseExecutionError(
            # The phase prints its envelope indented, so the exception message
            # itself ends at a brace: the cause has to come from the payload.
            'scenarioforge.cli ai failed with exit code 1. Last output: }',
            {'phase': 'ai', 'plan_payload': payload, 'timed_out': False},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir)
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=failure
            ):
                with self.assertRaises(PhaseExecutionError) as caught:
                    executor._generate_xml()

            generation = executor._ai_generation

        self.assertIn('OpenAI-compatible endpoint returned HTTP 401', str(caught.exception))
        self.assertIn('502', str(caught.exception))
        self.assertIn('OpenAI-compatible endpoint returned HTTP 401', generation['error'])

    def test_a_provider_failure_fails_the_run_without_aborting_the_batch(self):
        payload = {'ok': False, 'phase': 'ai', 'status': 502, 'error': 'HTTP 401'}
        failure = PhaseExecutionError('boom', {'phase': 'ai', 'plan_payload': payload})
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir)
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=failure
            ), mock.patch.object(executor, '_snapshot_webui_xml', return_value=None), \
                    mock.patch.object(executor, '_snapshot_reproduction_bundle', return_value=None):
                result = executor.run()

        # run() converts the failure into a reported result rather than raising,
        # which is what keeps the surrounding batch going.
        self.assertFalse(result['success'])
        self.assertIn('HTTP 401', result['error'])
        self.assertEqual(result['metadata']['ai_generation']['error'], 'HTTP 401 (status 502)')

    def test_a_timeout_is_retried_up_to_the_configured_budget(self):
        timeout_failure = PhaseExecutionError(
            'scenarioforge.cli ai timed out after 1200 seconds.',
            {'phase': 'ai', 'plan_payload': None, 'timed_out': True},
        )
        success = {'phase': 'ai', 'plan_payload': _ai_payload(), 'log_path': None}
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, retries=1)
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=[timeout_failure, success]
            ) as phase, mock.patch.object(executor, '_apply_core_connection_to_generated_xml'):
                xml_path = executor._generate_xml()

        self.assertEqual(xml_path, os.path.join(temp_dir, 'scenario.xml'))
        self.assertEqual(phase.call_count, 2)
        self.assertEqual(executor._ai_generation['attempts'], 2)
        # Retried attempts get their own log/JSON so the first failure survives.
        self.assertEqual(phase.call_args_list[0].kwargs['log_name'], 'ai.log')
        self.assertEqual(phase.call_args_list[1].kwargs['log_name'], 'ai-attempt2.log')

    def test_a_non_timeout_failure_is_not_retried(self):
        failure = PhaseExecutionError(
            'boom',
            {
                'phase': 'ai',
                'plan_payload': {'ok': False, 'error': 'did not return valid JSON for scenario generation'},
                'timed_out': False,
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, retries=3)
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=failure
            ) as phase:
                with self.assertRaises(PhaseExecutionError):
                    executor._generate_xml()

        self.assertEqual(phase.call_count, 1)

    def test_retries_stop_after_the_budget_is_exhausted(self):
        timeout_failure = PhaseExecutionError(
            'read timed out',
            {'phase': 'ai', 'plan_payload': {'ok': False, 'error': 'read timed out'}, 'timed_out': True},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = self._executor(temp_dir, retries=2)
            with mock.patch.object(executor, '_load_runtime_env'), mock.patch.object(
                executor, '_run_cli_phase', side_effect=timeout_failure
            ) as phase:
                with self.assertRaises(PhaseExecutionError):
                    executor._generate_xml()

        self.assertEqual(phase.call_count, 3)


class AiGeneratedXmlConnectionTests(unittest.TestCase):
    """The ai phase writes no SSH password, which downstream phases need."""

    GENERATED_XML = textwrap.dedent(
        """\
        <?xml version='1.0' encoding='utf-8'?>
        <Scenarios>
          <CoreConnection host="127.0.0.1" port="50051" ssh_enabled="true" ssh_host="192.0.2.10" ssh_port="22" ssh_username="core-operator" venv_bin="/opt/core/venv/bin" validated="True"/>
          <Scenario name="aigenerated" density_count="0" scenario_total_nodes="5" base_nodes="0">
            <ScenarioEditor>
              <BaseScenario filepath=""/>
              <section name="Node Information" density_count="0" base_nodes="0" additive_nodes="3" combined_nodes="3" weight_rows="0" count_rows="1" weight_sum="0.000">
                <item selected="Docker" factor="1.000" v_metric="Count" v_count="3"/>
              </section>
              <section name="Routing" density="0.000" explicit_count="2" derived_count="0" total_planned="2" weight_rows="0" count_rows="1" weight_sum="0.000">
                <item selected="OSPFv2" factor="1.000" v_metric="Count" v_count="2"/>
              </section>
              <section name="Services" density="0.000" explicit_count="0" weight_rows="1" count_rows="0" weight_sum="1.000">
                <item selected="SSH" factor="1.000"/>
              </section>
            </ScenarioEditor>
          </Scenario>
        </Scenarios>
        """
    )

    def _sf_path(self) -> str:
        sf_path = os.environ.get('SCENARIOFORGE_PATH') or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'scenarioforge',
        )
        try:
            if sf_path not in sys.path:
                sys.path.insert(0, sf_path)
            import webapp.app_backend  # noqa: F401
        except Exception:
            self.skipTest('ScenarioForge checkout is not importable')
        return sf_path

    def test_generated_xml_gains_the_evaluators_core_connection(self):
        sf_path = self._sf_path()
        with mock.patch.dict(
            os.environ,
            {
                'CORE_HOST': '127.0.0.1',
                'CORE_PORT': '50051',
                'CORE_SSH_HOST': '192.0.2.10',
                'CORE_SSH_USERNAME': 'core-operator',
                'CORE_SSH_PASSWORD': 'dummy-password',
            },
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                executor = Executor(
                    spec={'name': 'ai-run', 'seed': 1, 'hitl': {'use_env': False}},
                    out_dir=temp_dir,
                    sf_path=sf_path,
                )
                xml_path = os.path.join(temp_dir, 'scenario.xml')
                with open(xml_path, 'w', encoding='utf-8') as handle:
                    handle.write(self.GENERATED_XML)

                # Without a password the evaluator reads the run as local-only.
                self.assertFalse(executor._xml_supports_remote_delegation(xml_path))

                executor._apply_core_connection_to_generated_xml(xml_path)

                self.assertTrue(executor._xml_supports_remote_delegation(xml_path))
                text = open(xml_path, encoding='utf-8').read()

        # The model's authored sections must survive the rewrite untouched.
        self.assertIn('selected="Docker"', text)
        self.assertIn('OSPFv2', text)
        self.assertIn('selected="SSH"', text)


class AiReproductionTests(unittest.TestCase):
    def test_spec_built_runs_are_marked_seed_reproducible(self):
        summary = _generation_summary(None)

        self.assertEqual(summary['source'], 'spec')
        self.assertIs(summary['seed_reproducible'], True)

    def test_prompt_built_runs_record_the_request_and_disclaim_seed_replay(self):
        summary = _generation_summary({
            'prompt': 'two routers',
            'provider': 'openai',
            'model': 'test-model',
            'base_url': 'https://example.invalid/v1',
            'attempts': 1,
            'applied_actions': [{'tool': 'set_node_info'}],
        })

        self.assertEqual(summary['source'], 'ai-prompt')
        self.assertIs(summary['seed_reproducible'], False)
        self.assertEqual(summary['prompt'], 'two routers')
        self.assertEqual(summary['model'], 'test-model')
        self.assertEqual(summary['applied_actions'], [{'tool': 'set_node_info'}])


class AiSpecFixtureTests(unittest.TestCase):
    def test_shipped_ai_spec_resolves_to_an_enabled_bridged_generation(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resolved = SpecParser(
            os.path.join(root, 'test_specs', '12-ai-prompt-generated.spec.yaml')
        ).get_ai_spec()

        self.assertTrue(resolved['enabled'])
        self.assertIn('two routers', resolved['prompt'])
        self.assertEqual(resolved['bridge_mode'], DEFAULT_AI_BRIDGE_MODE)
        self.assertLessEqual(resolved['timeout_s'], AI_BRIDGE_TIMEOUT_CEILING_S)


if __name__ == '__main__':
    unittest.main()
