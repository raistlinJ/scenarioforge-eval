"""Keep the shipped smoke suite representative of supported spec values."""

import glob
import os
import unittest

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _specs():
    loaded = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'test_specs', '*.spec.yaml'))):
        with open(path) as handle:
            loaded.append(yaml.safe_load(handle))
    return loaded


class ShippedSpecCoverageTests(unittest.TestCase):
    def test_segmentation_rows_cover_firewall_and_nat(self):
        segmented = [spec['segmentation'] for spec in _specs() if spec.get('segmentation', {}).get('enabled')]
        rows = [row for section in segmented for row in section.get('items') or []]

        self.assertGreaterEqual(len(segmented), 6)
        self.assertEqual({str(row['type']).lower() for row in rows}, {'firewall', 'nat'})

    def test_flow_and_pivot_integration_specs_are_explicit(self):
        pivot_flow_specs = []
        for spec in _specs():
            if not (spec.get('flows') or {}).get('enabled'):
                continue
            segmentation = spec.get('segmentation') or {}
            pivot_rows = [
                row for row in segmentation.get('items') or []
                if row.get('pivot_enabled')
            ]
            if segmentation.get('accessible_by_pivot') or pivot_rows:
                pivot_flow_specs.append(spec.get('name'))

        self.assertEqual(
            pivot_flow_specs,
            ['artifact-validation', 'system-mixed-feature-stress'],
        )

    def test_flow_edge_case_specs_have_solvable_candidate_counts(self):
        specs = {spec.get('name'): spec for spec in _specs()}

        duplicate = specs['duplicate-flow-chain']
        self.assertIs(duplicate['flows']['allow_duplicates'], True)
        self.assertGreaterEqual(duplicate['flag_node_generators']['count'], 1)

        stress = specs['bounded-randomized-stress']
        self.assertIs(stress['flows']['allow_duplicates'], True)

        slots = specs['challenge-slots']
        self.assertEqual(slots['flows']['chain_length'], 6)
        self.assertEqual(slots['flows']['chain_ids'], ['14', '15', '16', '17'])

    def test_plan_shaping_segmentation_settings_are_represented(self):
        sections = [spec.get('segmentation') or {} for spec in _specs()]
        present = {key for section in sections for key in section}
        self.assertTrue({
            'nat_mode',
            'include_hosts',
            'dnat_probability',
            'allow_src_subnet_prob',
            'allow_dst_subnet_prob',
            'accessible_by_pivot',
        } <= present)

    def test_every_flow_dependency_level_is_represented(self):
        levels = {
            spec.get('flows', {}).get('dependency_level')
            for spec in _specs()
            if spec.get('flows', {}).get('dependency_level') is not None
        }
        self.assertEqual(levels, {1, 2, 3, 4, 5})

    def test_every_spec_runs_delayed_non_strict_artifact_checks(self):
        for spec in _specs():
            checks = (spec.get('validation') or {}).get('check_artifacts') or {}
            self.assertIs(checks.get('enabled'), True, spec.get('name'))
            self.assertEqual(checks.get('delay_seconds'), 60, spec.get('name'))
            self.assertIs(checks.get('strict'), False, spec.get('name'))

    def test_system_mixed_feature_stress_exercises_full_pipeline(self):
        specs = {spec.get('name'): spec for spec in _specs()}
        stress = specs['system-mixed-feature-stress']

        self.assertEqual(stress['iterations'], 10)
        self.assertEqual(stress['seed'], 202608040)
        for section in (
            'services',
            'traffic',
            'vulns',
            'flag_node_generators',
            'flows',
            'segmentation',
        ):
            self.assertIs(stress[section]['enabled'], True, section)

        self.assertTrue({
            'docker',
            'vulnerability_slots',
            'flag_gen_slots',
        } <= set(stress['topology']))
        self.assertEqual(
            {item['pattern'] for item in stress['traffic']['items']},
            {'continuous', 'periodic', 'burst', 'poisson', 'ramp'},
        )
        self.assertEqual(
            {item['content_type'] for item in stress['traffic']['items']},
            {'text', 'photo', 'audio', 'video', 'gibberish'},
        )
        self.assertIs(stress['flows']['allow_duplicates'], True)
        self.assertIs(stress['flows']['include_all_topology_pivots'], True)
        self.assertEqual(stress['flows']['execution'], 'remote')
        self.assertIs(stress['flows']['cleanup_generated_artifacts'], True)
        self.assertIs(stress['segmentation']['accessible_by_pivot'], True)
        self.assertEqual(
            {item['type'] for item in stress['segmentation']['items']},
            {'Firewall', 'NAT'},
        )


if __name__ == '__main__':
    unittest.main()
