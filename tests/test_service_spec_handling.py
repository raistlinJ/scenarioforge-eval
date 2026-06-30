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

    def test_vulns_count_and_filters_are_preserved(self):
        spec_text = textwrap.dedent(
            """
            name: parser-check
            vulns:
              randomize: false
              count: 2
              include: [weblogic/*]
              exclude: [nginx, php]
            """
        )

        with tempfile.NamedTemporaryFile('w', suffix='.spec.yaml', delete=False) as handle:
            handle.write(spec_text)
            spec_path = handle.name

        try:
            parser = SpecParser(spec_path)
            self.assertEqual(
                parser.get_vulns_spec(),
                {
                    'enabled': True,
                    'count': 2,
                    'include': ['weblogic/*'],
                    'exclude': ['nginx', 'php'],
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

    def test_vulnerability_count_is_encoded_as_exact_count(self):
        executor = Executor(spec={'seed': 789}, out_dir=tempfile.gettempdir(), sf_path='.')

        section = executor._build_vulnerability_section({'count': 1})

        self.assertEqual(
            section,
            {
                'density': 0.0,
                'items': [{
                    'selected': 'Random',
                    'v_metric': 'Count',
                    'v_count': 1,
                    'factor': 1.0,
                }],
            },
        )

    def test_vulnerability_count_prefers_specific_existing_catalog_entries(self):
        executor = Executor(
            spec={'seed': 789, 'name': 'catalog-check'},
            out_dir=tempfile.gettempdir(),
            sf_path='.',
        )
        catalog = [
            {
                'name': 'weblogic/CVE-2017-10271',
                'path': '/tmp/catalog/weblogic/docker-compose.yml',
                'validated_ok': True,
                'validated_at': '2026-06-04 16:33:40',
            },
            {
                'name': 'jboss/CVE-2017-12149',
                'path': '/tmp/catalog/jboss/docker-compose.yml',
                'validated_ok': True,
                'validated_at': '2026-06-04 16:33:41',
            },
        ]

        with mock.patch.object(executor, '_load_eligible_vulnerability_catalog', return_value=catalog):
            section = executor._build_vulnerability_section({'count': 2})

        self.assertEqual(section['density'], 0.0)
        self.assertEqual(section['flag_type'], 'text')
        self.assertEqual(len(section['items']), 2)
        self.assertEqual({item['selected'] for item in section['items']}, {'Specific'})
        self.assertEqual({item['v_count'] for item in section['items']}, {1})
        self.assertEqual(
            {item['v_name'] for item in section['items']},
            {'weblogic/CVE-2017-10271', 'jboss/CVE-2017-12149'},
        )
        self.assertEqual(executor._vulnerability_selection['mode'], 'specific_from_eligible_catalog')
        self.assertEqual(executor._vulnerability_selection['eligible_count'], 2)

    def test_vulnerability_filters_exclude_matching_catalog_entries(self):
        executor = Executor(
            spec={'seed': 789, 'name': 'catalog-check'},
            out_dir=tempfile.gettempdir(),
            sf_path='.',
        )
        catalog = [
            {
                'name': 'nginx/nginx_parsing_vulnerability',
                'path': '/tmp/catalog/nginx/nginx_parsing_vulnerability/docker-compose.yml',
                'validated_ok': True,
            },
            {
                'name': 'php/CVE-2019-11043',
                'path': '/tmp/catalog/php/CVE-2019-11043/docker-compose.yml',
                'validated_ok': True,
            },
            {
                'name': 'weblogic/CVE-2017-10271',
                'path': '/tmp/catalog/weblogic/docker-compose.yml',
                'validated_ok': True,
            },
        ]

        with mock.patch.object(executor, '_load_eligible_vulnerability_catalog', return_value=catalog):
            section = executor._build_vulnerability_section({'count': 1, 'exclude': ['nginx/*', 'php']})

        self.assertEqual(len(section['items']), 1)
        self.assertEqual(section['items'][0]['v_name'], 'weblogic/CVE-2017-10271')
        self.assertEqual(executor._vulnerability_selection['eligible_count_unfiltered'], 3)
        self.assertEqual(executor._vulnerability_selection['eligible_count'], 1)
        self.assertEqual(executor._vulnerability_selection['exclude'], ['nginx/*', 'php'])

    def test_vulnerability_filters_include_matching_catalog_entries(self):
        executor = Executor(
            spec={'seed': 789, 'name': 'catalog-check'},
            out_dir=tempfile.gettempdir(),
            sf_path='.',
        )
        catalog = [
            {
                'name': 'nginx/nginx_parsing_vulnerability',
                'path': '/tmp/catalog/nginx/nginx_parsing_vulnerability/docker-compose.yml',
                'validated_ok': True,
            },
            {
                'name': 'weblogic/CVE-2017-10271',
                'path': '/tmp/catalog/weblogic/docker-compose.yml',
                'validated_ok': True,
            },
        ]

        with mock.patch.object(executor, '_load_eligible_vulnerability_catalog', return_value=catalog):
            section = executor._build_vulnerability_section({'count': 1, 'include': ['weblogic']})

        self.assertEqual(len(section['items']), 1)
        self.assertEqual(section['items'][0]['v_name'], 'weblogic/CVE-2017-10271')
        self.assertEqual(executor._vulnerability_selection['include'], ['weblogic'])

    def test_vulnerability_count_fails_when_inspected_catalog_has_too_few_entries(self):
        executor = Executor(
            spec={'seed': 789, 'name': 'catalog-check'},
            out_dir=tempfile.gettempdir(),
            sf_path='.',
        )

        with mock.patch.object(executor, '_load_eligible_vulnerability_catalog', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'only 0 validated vulnerability catalog entries'):
                executor._build_vulnerability_section({'count': 1})

    def test_zero_vulnerability_count_omits_section(self):
        executor = Executor(spec={'seed': 790}, out_dir=tempfile.gettempdir(), sf_path='.')

        self.assertIsNone(executor._build_vulnerability_section({'count': 0}))


if __name__ == '__main__':
    unittest.main()
