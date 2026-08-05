import json
import os
import tempfile
import unittest

from scenarioforge_eval.dashboard import create_app, load_dashboard_data


def _result(name, *, success, duration, started_at, phase="execute", failed_stage=""):
    stages = {"scenario_xml": "PASS", "preview_plan": "PASS"}
    if failed_stage:
        stages[failed_stage] = "FAIL"
        stages["failed_at"] = failed_stage
    return {
        "success": success,
        "stages": stages,
        "warnings": ["slow image pull"] if not success else [],
        "error": "RuntimeError: failed" if not success else None,
        "metadata": {
            "spec_name": name,
            "iteration_index": 1,
            "iteration_count": 1,
            "target_phase": phase,
        },
        "phase_results": {
            phase: {
                "returncode": 0 if success else 1,
                "timed_out": False,
                "metrics": {
                    "started_at": started_at,
                    "ended_at": started_at,
                    "duration_s": duration,
                    "outputs": {
                        "combined": {"bytes": 120, "lines": 2, "estimated_tokens": 30},
                    },
                    "log": {"size_bytes": 120},
                    "resources": {"cpu_total_s": duration / 2, "max_rss_bytes": 2048},
                },
            }
        },
        "metrics": {
            "run": {
                "started_at": started_at,
                "ended_at": started_at,
                "duration_s": duration,
                "resources": {"cpu_total_s": duration / 2, "max_rss_bytes": 2048},
            },
            "spec": {
                "name": name,
                "seed": 42,
                "target_phase": phase,
                "topology": {"routers": 1, "hosts": 2, "nodes": 3},
                "services": {"count": 2},
                "vulnerabilities": {"count": 1},
                "flows": {"enabled": True, "chain_length": 2},
            },
            "phases": {
                phase: {
                    "duration_s": duration,
                    "outputs": {"combined": {"estimated_tokens": 30}},
                    "log": {"size_bytes": 120},
                    "resources": {"cpu_total_s": duration / 2, "max_rss_bytes": 2048},
                }
            },
            "artifacts": {"output_dir": {"file_count": 4, "total_size_bytes": 4096}},
            "content": {
                "challenges": {"count": 3, "pivot_count": 1, "flag_node_generator_count": 1},
                "chains": {"count": 1, "average_length": 2.0, "length_gt_1_count": 1},
                "topology": {"pivot_provider_count": 1, "flag_node_generator_count": 1},
            },
        },
    }


class DashboardDataTests(unittest.TestCase):
    def test_recursively_loads_results_and_aggregates_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            nested = os.path.join(temp_dir, "batch-a", "nested")
            os.makedirs(nested)
            with open(os.path.join(temp_dir, "batch-a", "alpha_result.json"), "w", encoding="utf-8") as handle:
                json.dump(_result("alpha", success=True, duration=10, started_at="2026-08-01T12:00:00Z"), handle)
            with open(os.path.join(nested, "beta_result.json"), "w", encoding="utf-8") as handle:
                json.dump(_result("beta", success=False, duration=30, started_at="2026-08-02T12:00:00Z", failed_stage="execute"), handle)
            with open(os.path.join(temp_dir, "broken_result.json"), "w", encoding="utf-8") as handle:
                handle.write("{not json")
            with open(os.path.join(temp_dir, "execute-validation.json"), "w", encoding="utf-8") as handle:
                json.dump({"ok": True}, handle)

            data = load_dashboard_data(temp_dir)

            self.assertEqual(data["meta"]["candidate_files"], 3)
            self.assertEqual(data["meta"]["loaded_runs"], 2)
            self.assertEqual(len(data["meta"]["load_errors"]), 1)
            self.assertEqual(data["summary"]["total_runs"], 2)
            self.assertEqual(data["summary"]["successes"], 1)
            self.assertEqual(data["summary"]["failures"], 1)
            self.assertEqual(data["summary"]["pass_rate"], 0.5)
            self.assertEqual(data["summary"]["median_duration_s"], 20.0)
            self.assertEqual(data["summary"]["estimated_output_tokens"], 60)
            self.assertEqual(data["summary"]["artifact_total_size_bytes"], 8192)
            self.assertEqual(data["summary"]["challenges"], 6)
            self.assertEqual(data["failure_stages"], [{"stage": "execute", "count": 1}])
            self.assertEqual(data["phase_summary"][0]["count"], 2)
            self.assertEqual(data["phase_summary"][0]["avg_duration_s"], 20.0)
            self.assertEqual(data["runs"][1]["warning_count"], 1)

    def test_uses_deduplicated_raw_metrics_as_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = {
                "success": True,
                "run": {
                    "spec_name": "fallback",
                    "duration_s": 2.5,
                    "estimated_output_tokens": 9,
                },
                "phases": [{"phase": "preview-plan", "duration_s": 2.5}],
                "metrics": {},
            }
            for folder in ("metrics/runs/fallback", "fallback/metrics"):
                path = os.path.join(temp_dir, folder)
                os.makedirs(path)
                with open(os.path.join(path, "run_metrics_raw.json"), "w", encoding="utf-8") as handle:
                    json.dump(payload, handle)

            data = load_dashboard_data(temp_dir)

            self.assertEqual(data["meta"]["source_mode"], "metrics-fallback")
            self.assertEqual(data["meta"]["candidate_files"], 2)
            self.assertEqual(data["summary"]["total_runs"], 1)
            self.assertEqual(data["runs"][0]["spec_name"], "fallback")
            self.assertEqual(data["phase_summary"][0]["phase"], "preview-plan")

    def test_flask_routes_serve_dashboard_and_fresh_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "alpha_result.json"), "w", encoding="utf-8") as handle:
                json.dump(_result("alpha", success=True, duration=1, started_at="2026-08-01T12:00:00Z"), handle)
            app = create_app(temp_dir)
            client = app.test_client()

            page = client.get("/")
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Run intelligence", page.data)
            self.assertEqual(page.headers["Cache-Control"], "no-store")

            response = client.get("/api/dashboard")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["summary"]["total_runs"], 1)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

            health = client.get("/healthz")
            self.assertEqual(health.status_code, 200)
            self.assertTrue(health.json["ok"])


if __name__ == "__main__":
    unittest.main()
