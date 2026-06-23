import os
import random
import tempfile
import textwrap
import unittest
from unittest import mock

from scenarioforge_eval.executor import Executor
from scenarioforge_eval.parser import SpecParser


class SpecParserServiceSpecTests(unittest.TestCase):
    def test_services_count_and_filters_are_preserved(self):
        spec_text = textwrap.dedent(
            """
            name: parser-check
            services:
              randomize: true
              count: 4
              include: [ssh, http, dhcp]
              exclude: [dhcpclient]
            """
        )

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False) as handle:
            handle.write(spec_text)
            spec_path = handle.name

        try:
            parser = SpecParser(spec_path)
            self.assertEqual(
                parser.get_services_spec(),
                {
                    'enabled': True,
                    'count': 4,
                    'density': 1.0,
                    'include': ['SSH', 'HTTP', 'DHCPClient'],
                    'exclude': ['DHCPClient'],
                },
            )
        finally:
            os.unlink(spec_path)

    def test_services_fixed_count_stays_enabled_when_randomize_false(self):
        spec_text = textwrap.dedent(
            """
            name: parser-check
            services:
              randomize: false
              count: 2
            """
        )

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False) as handle:
            handle.write(spec_text)
            spec_path = handle.name

        try:
            parser = SpecParser(spec_path)
            self.assertEqual(
                parser.get_services_spec(),
                {
                    'enabled': True,
                    'count': 2,
                    'density': 1.0,
                    'include': [],
                    'exclude': [],
                },
            )
        finally:
            os.unlink(spec_path)

    def test_flows_legacy_count_alias_enables_fixed_flag_sequencing(self):
        spec_text = textwrap.dedent(
            """
            name: parser-check
            flows:
              randomize: false
              count: 1
            """
        )

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False) as handle:
            handle.write(spec_text)
            spec_path = handle.name

        try:
            parser = SpecParser(spec_path)
            self.assertEqual(
                parser.get_flows_spec(),
                {
                    'enabled': True,
                    'chain_length': 1,
                    'allow_duplicates': False,
                },
            )
        finally:
            os.unlink(spec_path)

    def test_flows_randomize_false_without_length_disables_flag_sequencing(self):
        spec_text = textwrap.dedent(
            """
            name: parser-check
            flows:
              randomize: false
            """
        )

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False) as handle:
            handle.write(spec_text)
            spec_path = handle.name

        try:
            parser = SpecParser(spec_path)
            self.assertEqual(
                parser.get_flows_spec(rng=random.Random(0)),
                {
                    'enabled': False,
                    'chain_length': 4,
                    'allow_duplicates': False,
                },
            )
        finally:
            os.unlink(spec_path)


class ExecutorServiceItemTests(unittest.TestCase):
    def test_topology_payload_uses_current_section_model(self):
        executor = Executor(spec={}, out_dir=tempfile.gettempdir(), sf_path='.')

        payload = executor._build_topology_payload({'hosts': 10, 'routers': 2})

        self.assertEqual(payload['density_count'], 10)
        self.assertEqual(
            payload['sections']['Node Information'],
            {'items': [{'selected': 'Workstation', 'factor': 1.0}]},
        )
        self.assertEqual(
            payload['sections']['Routing'],
            {
                'density': 0.0,
                'items': [],
                'node_count_min_enabled': True,
                'node_count_min': 2,
                'node_count_max_enabled': True,
                'node_count_max': 2,
            },
        )

    def test_default_vm_safe_pool_excludes_dhcpclient(self):
        executor = Executor(spec={'seed': 123}, out_dir=tempfile.gettempdir(), sf_path='.')

        with mock.patch.object(executor._rng, 'choice', side_effect=['HTTP', 'SSH', 'HTTP', 'SSH']):
            items = executor._build_service_items({'count': 4})

        self.assertEqual(
            items,
            [
                {'selected': 'SSH', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 2},
                {'selected': 'HTTP', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 2},
            ],
        )

    def test_explicit_include_can_opt_into_dhcpclient(self):
        executor = Executor(spec={'seed': 456}, out_dir=tempfile.gettempdir(), sf_path='.')

        with mock.patch.object(executor._rng, 'choice', side_effect=['DHCPClient']):
            items = executor._build_service_items({'count': 1, 'include': ['DHCPClient']})

        self.assertEqual(
            items,
            [
                {'selected': 'DHCPClient', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 1},
            ],
        )


if __name__ == '__main__':
    unittest.main()