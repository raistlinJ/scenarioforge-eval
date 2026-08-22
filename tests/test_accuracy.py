"""Tests for the accuracy grader.

This module is the measurement instrument for the authoring-method comparison,
so its failure modes are quiet by nature: a grader that silently under-counts
does not crash, it just reports a number someone will publish. These cover the
cases where that could happen.
"""

import os
import tempfile
import textwrap
import unittest

from scenarioforge_eval.accuracy import aggregate, observe_scenario, score_scenario


def _xml(body: str) -> str:
    handle = tempfile.NamedTemporaryFile('w', suffix='.xml', delete=False, encoding='utf-8')
    handle.write(body)
    handle.close()
    return handle.name


SCENARIO = textwrap.dedent("""\
    <?xml version='1.0' encoding='utf-8'?>
    <Scenarios>
      <Scenario name="graded">
        <ScenarioEditor>
          <HardwareInLoop enabled="true"/>
          <section name="Node Information">
            <item selected="Docker" v_metric="Count" v_count="3"/>
            <item selected="PC" v_metric="Count" v_count="2"/>
          </section>
          <section name="Routing">
            <item selected="OSPFv2" v_metric="Count" v_count="2"/>
          </section>
          <section name="Services">
            <item selected="SSH"/>
            <item selected="HTTP" v_count="4"/>
          </section>
          <section name="Vulnerabilities">
            <item selected="Specific" v_name="struts2/s2-061" v_count="1"/>
          </section>
          <section name="Flag Node Generators">
            <item selected="Specific" g_id="ssh_key_ops_bastion" g_name="SSH: Key Ops Bastion" v_count="1"/>
            <item selected="Specific" g_id="131" g_name="Cache: CDN Manifest Cache" v_count="1"/>
          </section>
          <section name="Segmentation">
            <item selected="Firewall" v_count="1"/>
          </section>
          <section name="Traffic">
            <item selected="TCP" v_count="1"/>
          </section>
        </ScenarioEditor>
      </Scenario>
    </Scenarios>
""")


class ObserveTests(unittest.TestCase):
    def setUp(self):
        self.observed = observe_scenario(_xml(SCENARIO))

    def test_hosts_sum_across_every_host_bearing_section(self):
        # Docker and PC rows contribute five ordinary hosts. The vulnerability
        # and two flag-node generators each materialize another CORE host, so
        # the same topology-level definition used for direct CORE XML totals 8.
        self.assertEqual(self.observed['hosts'], 8)

    def test_routers_come_from_the_routing_section(self):
        self.assertEqual(self.observed['routers'], 2)

    def test_service_row_without_a_count_still_counts_as_present(self):
        self.assertEqual(self.observed['services'], ['HTTP', 'SSH'])

    def test_named_entries_are_read_back(self):
        self.assertEqual(self.observed['vulnerability_names'], ['struts2/s2-061'])
        self.assertIn('SSH: Key Ops Bastion', self.observed['generator_names'])

    def test_counts_use_row_totals_not_row_counts(self):
        self.assertEqual(self.observed['flag_node_generators'], 2)
        self.assertEqual(self.observed['vulnerabilities'], 1)

    def test_hitl_and_traffic_are_booleans(self):
        self.assertIs(self.observed['hitl'], True)
        self.assertIs(self.observed['traffic'], True)


class ScoreTests(unittest.TestCase):
    def test_only_declared_fields_are_scored(self):
        # A prompt silent about traffic must not be penalised for it.
        score = score_scenario({'routers': 2}, _xml(SCENARIO))
        self.assertEqual(list(score['checks']), ['routers'])
        self.assertTrue(score['exact'])

    def test_count_mismatch_fails_with_detail(self):
        score = score_scenario({'hosts': 9}, _xml(SCENARIO))
        self.assertFalse(score['checks']['hosts']['ok'])
        self.assertIn('expected 9, got 8', score['checks']['hosts']['detail'])

    def test_named_entries_match_case_insensitively(self):
        score = score_scenario({'generator_names': ['ssh: key ops bastion']}, _xml(SCENARIO))
        self.assertTrue(score['exact'])

    def test_missing_named_entry_is_reported(self):
        score = score_scenario({'vulnerability_names': ['jboss/CVE-2017-12149']}, _xml(SCENARIO))
        self.assertFalse(score['checks']['vulnerability_names']['ok'])

    def test_extra_generated_content_does_not_fail_a_list_field(self):
        # Lists are scored as "everything asked for is present". Extra services
        # are not a miss; the count fields are where over-generation shows up.
        score = score_scenario({'services': ['SSH']}, _xml(SCENARIO))
        self.assertTrue(score['exact'])

    def test_unparseable_scenario_scores_zero_but_keeps_the_denominator(self):
        # An arm that returns prose must count as attempted-and-wrong, not as
        # absent, or its accuracy would be computed over a smaller denominator
        # than the arm it is being compared against.
        path = _xml('this is not a scenario, it is an explanation')
        score = score_scenario({'routers': 2, 'hosts': 3}, path)
        self.assertFalse(score['loadable'])
        self.assertEqual(score['accuracy'], 0.0)
        self.assertEqual(score['total'], 2)

    def test_missing_file_is_handled_like_unparseable_output(self):
        score = score_scenario({'routers': 1}, os.path.join(tempfile.gettempdir(), 'no-such.xml'))
        self.assertFalse(score['loadable'])


class AggregateTests(unittest.TestCase):
    def test_aggregate_counts_scenarios_checks_and_per_field(self):
        good = score_scenario({'routers': 2, 'hosts': 8}, _xml(SCENARIO))
        bad = score_scenario({'routers': 9, 'hosts': 8}, _xml(SCENARIO))
        agg = aggregate([good, bad])

        self.assertEqual(agg['scenarios'], 2)
        self.assertEqual(agg['exact_match'], 1)
        self.assertEqual(agg['checks_total'], 4)
        self.assertEqual(agg['checks_matched'], 3)
        self.assertAlmostEqual(agg['field_accuracy'], 0.75)
        self.assertEqual(agg['per_field']['routers'], {'matched': 1, 'total': 2, 'accuracy': 0.5})
        self.assertEqual(agg['per_field']['hosts']['accuracy'], 1.0)

    def test_unloadable_scenarios_still_reach_the_aggregate(self):
        agg = aggregate([score_scenario({'routers': 1}, _xml('nonsense'))])
        self.assertEqual(agg['scenarios'], 1)
        self.assertEqual(agg['loadable'], 0)
        self.assertEqual(agg['field_accuracy'], 0.0)


if __name__ == '__main__':
    unittest.main()
