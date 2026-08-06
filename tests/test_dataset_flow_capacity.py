"""Keep source and resolved dataset Flow chains statically feasible."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parent.parent


def _minimum(value) -> int:
    if isinstance(value, list):
        return min(int(item) for item in value)
    return int(value or 0)


def _flow_capacity(spec: dict) -> int:
    topology = spec.get("topology") or {}
    vulnerabilities = spec.get("vulns") or {}
    generators = spec.get("flag_node_generators") or {}
    capacity = 0
    if vulnerabilities.get("enabled", vulnerabilities.get("randomize", False)):
        capacity += _minimum(vulnerabilities.get("count"))
    if generators.get("enabled", generators.get("randomize", False)):
        capacity += _minimum(generators.get("count"))
    capacity += sum(
        _minimum(topology.get(key))
        for key in ("docker", "vulnerability_slots", "flag_gen_slots")
    )
    return capacity


class DatasetFlowCapacityTests(unittest.TestCase):
    def _assert_feasible(self, folder: str) -> None:
        paths = sorted((ROOT / folder).glob("*.spec.yaml"))
        self.assertTrue(paths, folder)
        for path in paths:
            spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            flows = spec.get("flows") or {}
            if not flows.get("enabled", flows.get("randomize", False)):
                continue
            if flows.get("allow_duplicates", False):
                continue
            requested = _minimum(flows.get("chain_length", flows.get("count")))
            available = _flow_capacity(spec)
            self.assertLessEqual(
                requested,
                available,
                f"{path.name} requests {requested} unique Flow nodes but declares "
                f"only {available} challenge-capable nodes",
            )

    def test_source_dataset_flows_are_feasible_at_minimum_counts(self):
        self._assert_feasible("datasets")

    def test_resolved_dataset_flows_are_feasible(self):
        self._assert_feasible("dataset-resolved")


if __name__ == "__main__":
    unittest.main()
