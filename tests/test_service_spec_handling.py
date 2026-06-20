import os
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
        executor = Executor(spec={}, out_dir=tempfile.gettempdir(), sf_path='.')

        with mock.patch('scenarioforge_eval.executor.random.choice', side_effect=['HTTP', 'SSH', 'HTTP', 'SSH']):
            items = executor._build_service_items({'count': 4})

        self.assertEqual(
            items,
            [
                {'selected': 'SSH', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 2},
                {'selected': 'HTTP', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 2},
            ],
        )

    def test_explicit_include_can_opt_into_dhcpclient(self):
        executor = Executor(spec={}, out_dir=tempfile.gettempdir(), sf_path='.')

        with mock.patch('scenarioforge_eval.executor.random.choice', side_effect=['DHCPClient']):
            items = executor._build_service_items({'count': 1, 'include': ['DHCPClient']})

        self.assertEqual(
            items,
            [
                {'selected': 'DHCPClient', 'factor': 1.0, 'v_metric': 'Count', 'v_count': 1},
            ],
        )


if __name__ == '__main__':
    unittest.main()