"""Challenge slots must be expressible from a spec.

`Node Information` was hardcoded to a single Workstation row, so no spec could
declare `Docker`, `VulnerabilitySlot` or `FlagGenSlot` hosts. Slots are the
newest topology feature and the evaluator could not exercise them at all.

A slot is capacity, not a placement: it materialises empty and flag-sequencing
fills it only when the requested chain length needs it. Both kinds add to the
counts declared in the Vulnerabilities and Flag Node Generators sections.
"""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scenarioforge_eval.executor import Executor


def _rows(topo_spec, seed=123):
    executor = Executor(spec={'seed': seed}, out_dir=tempfile.gettempdir(), sf_path='.')
    payload = executor._build_topology_payload(topo_spec)
    return payload['sections']['Node Information']['items']


def _by_role(rows):
    out = {}
    for row in rows:
        out.setdefault(str(row.get('selected')), []).append(row)
    return out


class ChallengeSlotTopologyTests(unittest.TestCase):
    def test_plain_topology_is_unchanged(self):
        """Specs that declare no Docker roles must emit exactly what they did."""
        self.assertEqual(
            _rows({'hosts': 6, 'routers': 2}),
            [{'selected': 'Workstation', 'factor': 1.0}],
        )

    def test_each_docker_role_becomes_a_count_row(self):
        rows = _by_role(_rows({
            'hosts': 6, 'docker': 1, 'vulnerability_slots': 2, 'flag_gen_slots': 3,
        }))
        for role, expected in (('Docker', 1), ('VulnerabilitySlot', 2), ('FlagGenSlot', 3)):
            self.assertIn(role, rows, f'{role} row missing')
            self.assertEqual(rows[role][0]['v_metric'], 'Count')
            self.assertEqual(rows[role][0]['v_count'], expected)

    def test_zero_and_missing_counts_emit_no_row(self):
        rows = _by_role(_rows({'hosts': 4, 'docker': 0, 'vulnerability_slots': None}))
        for role in ('Docker', 'VulnerabilitySlot', 'FlagGenSlot'):
            self.assertNotIn(role, rows, f'{role} should not appear')

    def test_a_range_is_resolved_within_bounds_and_is_reproducible(self):
        first = _rows({'hosts': 4, 'flag_gen_slots': [2, 5]}, seed=99)
        again = _rows({'hosts': 4, 'flag_gen_slots': [2, 5]}, seed=99)
        count = _by_role(first)['FlagGenSlot'][0]['v_count']
        self.assertGreaterEqual(count, 2)
        self.assertLessEqual(count, 5)
        self.assertEqual(count, _by_role(again)['FlagGenSlot'][0]['v_count'])

    def test_a_reversed_range_is_tolerated(self):
        count = _by_role(_rows({'hosts': 4, 'docker': [5, 2]}))['Docker'][0]['v_count']
        self.assertGreaterEqual(count, 2)
        self.assertLessEqual(count, 5)

    def test_a_malformed_count_does_not_raise(self):
        rows = _by_role(_rows({'hosts': 4, 'docker': 'two', 'flag_gen_slots': []}))
        self.assertNotIn('Docker', rows)
        self.assertNotIn('FlagGenSlot', rows)

    def test_rows_survive_into_the_generated_xml(self):
        """The evaluator shares ScenarioForge's XML builder, so this is the
        contract that actually matters."""
        try:
            from webapp import app_backend as backend
        except Exception as exc:  # pragma: no cover - depends on sibling checkout
            self.skipTest(f'ScenarioForge backend not importable: {exc}')

        rows = _rows({'hosts': 6, 'docker': 1, 'vulnerability_slots': 2, 'flag_gen_slots': 2})
        scenario = {
            'name': 'slot-xml', 'nodes': [], 'links': [], 'density_count': 6,
            'sections': {'Node Information': {'items': rows}},
        }
        tree = backend._build_scenarios_xml({'scenarios': [scenario], 'core': {}})
        with tempfile.NamedTemporaryFile('w', suffix='.xml', delete=False) as handle:
            xml_path = handle.name
        try:
            backend._write_xml_tree_atomic(tree, xml_path)
            section = ET.parse(xml_path).getroot().find(".//section[@name='Node Information']")
            self.assertIsNotNone(section)
            written = {item.get('selected'): item.get('v_count') for item in section}
        finally:
            os.unlink(xml_path)

        self.assertEqual(written.get('Docker'), '1')
        self.assertEqual(written.get('VulnerabilitySlot'), '2')
        self.assertEqual(written.get('FlagGenSlot'), '2')


class ChallengeSlotSpecTests(unittest.TestCase):
    def test_the_shipped_spec_requests_the_full_ceiling(self):
        """Asking for less than the ceiling never reaches a slot, so a spec that
        does not ask for it proves nothing."""
        import yaml

        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, 'test_specs', '11-challenge-slots.spec.yaml')) as handle:
            spec = yaml.safe_load(handle)

        topo = spec['topology']
        ceiling = (
            int(spec['vulns']['count'])
            + int(spec['flag_node_generators']['count'])
            + int(topo['vulnerability_slots'])
            + int(topo['flag_gen_slots'])
        )
        self.assertEqual(int(spec['flows']['chain_length']), ceiling)


if __name__ == '__main__':
    unittest.main()
