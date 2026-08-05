"""Authored spec values must survive main's parser-to-executor boundary."""

import json
import os
import random
import tempfile
import textwrap
import unittest

from scenarioforge_eval.executor import Executor
from scenarioforge_eval.parser import SpecParser


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _ParsedSpec:
    def __init__(self, body: str):
        self._handle = tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False)
        self._handle.write(textwrap.dedent(body))
        self._handle.close()
        self.parser = SpecParser(self._handle.name)

    def close(self):
        os.unlink(self._handle.name)


class SupportedValuePassThroughTests(unittest.TestCase):
    def test_additive_topology_counts_are_not_dropped(self):
        parsed = _ParsedSpec(
            """
            topology:
              routers: 2
              hosts: 6
              docker: 1
              vulnerability_slots: 2
              flag_gen_slots: [3, 3]
            """
        )
        try:
            self.assertEqual(
                parsed.parser.get_topology_spec(rng=random.Random(12)),
                {
                    'routers': 2,
                    'hosts': 6,
                    'docker': 1,
                    'vulnerability_slots': 2,
                    'flag_gen_slots': 3,
                },
            )
        finally:
            parsed.close()

    def test_flow_solver_and_operational_values_are_not_dropped(self):
        parsed = _ParsedSpec(
            """
            flows:
              enabled: true
              chain_length: 4
              dependency_level: 5
              chain_ids: [node-a, node-b]
              timeout_s: 90
              cleanup_generated_artifacts: true
              execution: remote
            """
        )
        try:
            flows = parsed.parser.get_flows_spec()
        finally:
            parsed.close()

        self.assertEqual(flows['dependency_level'], 5)
        self.assertEqual(flows['chain_ids'], ['node-a', 'node-b'])
        self.assertEqual(flows['timeout_s'], 90)
        self.assertIs(flows['cleanup_generated_artifacts'], True)
        self.assertEqual(flows['execution'], 'remote')

    def test_artifact_check_config_is_not_dropped(self):
        parsed = _ParsedSpec(
            """
            validation:
              policy: warning_tolerant
              check_artifacts:
                enabled: true
                delay_seconds: 12.5
                strict: false
            """
        )
        try:
            self.assertEqual(
                parsed.parser.get_validation_spec(),
                {
                    'policy': 'warning_tolerant',
                    'check_artifacts': {
                        'enabled': True,
                        'delay_seconds': 12.5,
                        'strict': False,
                    },
                },
            )
        finally:
            parsed.close()

    def test_segmentation_settings_reach_the_xml_writer_model(self):
        parsed = _ParsedSpec(
            """
            segmentation:
              enabled: true
              density: 0.6
              nat_mode: MASQUERADE
              include_hosts: true
              dnat_probability: 0.4
              allow_src_subnet_prob: 0.2
              allow_dst_subnet_prob: 0.8
              accessible_by_pivot: true
              items:
                - type: Firewall
                  count: 2
                  pivot_enabled: true
                  pivot_provider: vulnerability
                - type: NAT
                  count: 1
            """
        )
        try:
            resolved = parsed.parser.get_segmentation_spec()
        finally:
            parsed.close()

        section = Executor._build_segmentation_section(resolved)
        for key, expected in {
            'density': 0.6,
            'nat_mode': 'MASQUERADE',
            'include_hosts': True,
            'dnat_probability': 0.4,
            'allow_src_subnet_prob': 0.2,
            'allow_dst_subnet_prob': 0.8,
            'accessible_by_pivot': True,
        }.items():
            self.assertEqual(section[key], expected, key)
        self.assertEqual(section['items'][0]['v_count'], 2)
        self.assertEqual(section['items'][0]['pivot_provider'], 'vulnerability')
        self.assertEqual(section['items'][1]['selected'], 'NAT')


class SupportedValueSchemaTests(unittest.TestCase):
    def test_segmentation_settings_are_declared_in_the_schema(self):
        with open(os.path.join(HERE, 'scenarioforge_eval', 'schema.json')) as handle:
            schema = json.load(handle)
        segmentation = schema['properties']['segmentation']['properties']
        expected = {
            'nat_mode',
            'include_hosts',
            'dnat_probability',
            'allow_src_subnet_prob',
            'allow_dst_subnet_prob',
            'accessible_by_pivot',
        }
        self.assertTrue(expected <= set(segmentation))
        self.assertEqual(segmentation['nat_mode']['enum'], ['SNAT', 'MASQUERADE'])


if __name__ == '__main__':
    unittest.main()
