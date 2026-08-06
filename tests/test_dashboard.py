import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scenarioforge_eval.dashboard import (
    _build_execution_command,
    _build_rerun_plan,
    _delete_rerun_paths,
    EvaluationJobManager,
    create_app,
    load_dashboard_data,
)


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
    def test_execution_manager_streams_logs_and_completes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec_path = root / "sample.spec.yaml"
            spec_path.write_text("name: sample\n", encoding="utf-8")
            sf_path = root / "scenarioforge"
            sf_path.mkdir()
            fake_process = mock.Mock(
                pid=4321,
                stdout=io.StringIO("first line\nsecond line\n"),
            )
            fake_process.wait.return_value = 0
            manager = EvaluationJobManager(root)

            with mock.patch(
                "scenarioforge_eval.dashboard.subprocess.Popen",
                return_value=fake_process,
            ):
                manager.start({
                    "spec_path": str(spec_path),
                    "sf_path": str(sf_path),
                    "out_path": str(root / "results"),
                    "phase": "scenario-xml",
                })
                for _ in range(100):
                    snapshot = manager.snapshot()
                    if snapshot["status"] == "succeeded":
                        break
                    time.sleep(0.01)

            self.assertEqual(snapshot["status"], "succeeded")
            self.assertEqual(snapshot["returncode"], 0)
            self.assertEqual(
                [line["text"] for line in snapshot["logs"]],
                ["first line", "second line"],
            )

    def test_active_execution_survives_page_reload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec_path = root / "sample.spec.yaml"
            spec_path.write_text("name: sample\n", encoding="utf-8")
            sf_path = root / "scenarioforge"
            sf_path.mkdir()
            app = create_app(root)
            client = app.test_client()
            manager = app.extensions["evaluation_job_manager"]

            with mock.patch("scenarioforge_eval.dashboard.Thread.start"):
                started = manager.start({
                    "spec_path": str(spec_path),
                    "sf_path": str(sf_path),
                    "out_path": str(root / "results"),
                    "phase": "execute",
                    "verbose": True,
                    "stop_on_error": True,
                })

            self.assertEqual(started["status"], "starting")
            self.assertEqual(client.get("/").status_code, 200)
            reconnected = client.get("/api/execution").json
            self.assertEqual(reconnected["id"], started["id"])
            self.assertEqual(reconnected["status"], "starting")
            self.assertEqual(reconnected["config"]["spec_path"], str(spec_path.resolve()))
            self.assertTrue(reconnected["config"]["verbose"])
            self.assertTrue(reconnected["config"]["stop_on_error"])

    def test_builds_execution_command_from_supported_cli_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec_path = root / "sample.spec.yaml"
            spec_path.write_text("name: sample\n", encoding="utf-8")
            sf_path = root / "scenarioforge"
            sf_path.mkdir()
            out_path = root / "results"

            command, config = _build_execution_command(
                {
                    "spec_path": str(spec_path),
                    "sf_path": str(sf_path),
                    "out_path": str(out_path),
                    "phase": "execute",
                    "verbose": True,
                    "stop_on_error": True,
                    "dangerous_cleanup_between_runs": True,
                },
                cwd=root,
            )

            self.assertEqual(command[1:3], ["-m", "scenarioforge_eval.main"])
            self.assertIn("--execute", command)
            self.assertIn("--verbose", command)
            self.assertIn("--stop-on-error", command)
            self.assertIn("--dangerous-cleanup-between-runs", command)
            self.assertEqual(config["out_path"], str(out_path.resolve()))

            with self.assertRaisesRegex(ValueError, "unsupported phase"):
                _build_execution_command(
                    {
                        "spec_path": str(spec_path),
                        "sf_path": str(sf_path),
                        "out_path": str(out_path),
                        "phase": "unknown",
                    },
                    cwd=root,
                )

    def test_builds_selected_iteration_reruns_with_optional_replacement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            spec_path = root / "sample.spec.yaml"
            spec_path.write_text("name: sample\niterations: 3\nseed: 41\n", encoding="utf-8")
            sf_path = root / "scenarioforge"
            sf_path.mkdir()
            run_output = root / "sample_run2"
            run_output.mkdir()
            (run_output / "artifact.txt").write_text("data", encoding="utf-8")
            result_path = root / "sample_run2_result.json"
            result = _result(
                "sample_run2",
                success=True,
                duration=1,
                started_at="2026-08-01T12:00:00Z",
            )
            result["metadata"].update({
                "spec_file": str(spec_path),
                "iteration_index": 2,
                "iteration_count": 3,
            })
            result["artifacts"] = {"output_dir": str(run_output)}
            result_path.write_text(json.dumps(result), encoding="utf-8")

            commands, config, cleanup_paths = _build_rerun_plan(
                {
                    "run_ids": [result_path.name],
                    "replace_original": False,
                    "sf_path": str(sf_path),
                    "verbose": True,
                },
                root=root,
                cwd=root,
            )

            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0][-2:], ["--iteration-index", "2"])
            self.assertIn("--verbose", commands[0])
            self.assertIn(str(root / "reruns"), config["out_path"])
            self.assertFalse(config["replace_original"])
            self.assertEqual(cleanup_paths, ())

            commands, config, cleanup_paths = _build_rerun_plan(
                {
                    "run_ids": [result_path.name],
                    "replace_original": True,
                    "sf_path": str(sf_path),
                },
                root=root,
                cwd=root,
            )

            self.assertEqual(config["out_path"], "Original result folders")
            self.assertIn(str(root), commands[0])
            self.assertIn(result_path, cleanup_paths)
            self.assertIn(run_output, cleanup_paths)
            _delete_rerun_paths(cleanup_paths)
            self.assertFalse(result_path.exists())
            self.assertFalse(run_output.exists())

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

            self.assertEqual(data["schema_version"], 3)
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
            self.assertEqual(data["summary"]["pivot_challenges"], 2)
            self.assertEqual(data["summary"]["pivot_providers"], 2)
            self.assertEqual(data["summary"]["pivots"], 2)
            self.assertEqual(data["summary"]["pivot_total"], 4)
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

    def test_recovers_stale_content_counts_from_phase_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = _result(
                "stale-counts",
                success=True,
                duration=1,
                started_at="2026-08-01T12:00:00Z",
            )
            result["metrics"]["content"] = {
                "challenges": {"count": 0, "pivot_count": 0},
                "chains": {"count": 0, "average_length": 0},
                "topology": {"pivot_provider_count": 0},
            }
            result["phase_results"]["flag-sequencing"] = {
                "plan_payload": {
                    "length": 2,
                    "chain": [{"id": "one"}, {"id": "two"}],
                    "flag_assignments": [
                        {"declared_outputs": ["Flag(one)"]},
                        {"actual_outputs": ["Flag(two)", "Pivot(router-1)"]},
                    ],
                }
            }
            result["phase_results"]["preview-plan"] = {
                "plan_payload": {
                    "full_preview": {
                        "display_artifacts": {
                            "segmentation": {
                                "json": {
                                    "metadata": {
                                        "pivot_access": {"provider_count": 2},
                                    }
                                }
                            }
                        }
                    }
                }
            }
            with open(os.path.join(temp_dir, "stale_result.json"), "w", encoding="utf-8") as handle:
                json.dump(result, handle)

            data = load_dashboard_data(temp_dir)

            self.assertEqual(data["runs"][0]["challenge_count"], 2)
            self.assertEqual(data["runs"][0]["chain_count"], 1)
            self.assertEqual(data["runs"][0]["average_chain_length"], 2.0)
            self.assertEqual(data["runs"][0]["pivot_count"], 1)
            self.assertEqual(data["runs"][0]["pivot_provider_count"], 2)
            self.assertEqual(data["summary"]["pivots"], 1)
            self.assertEqual(data["summary"]["pivot_total"], 3)

    def test_reports_unique_challenges_and_create_test_run_timings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for name, generator_ids, vulnerability_ids in (
                ("alpha", ["gen-a", "gen-b"], ["app/CVE-1", "app/CVE-2"]),
                ("beta", ["gen-a", "gen-c"], ["app/CVE-1", "app/CVE-3"]),
            ):
                result = _result(
                    name,
                    success=True,
                    duration=20,
                    started_at="2026-08-01T12:00:00Z",
                )
                phase_durations = {
                    "scenario-xml": 2,
                    "preview-plan": 3,
                    "flag-sequencing": 4,
                    "execute": 5,
                }
                result["phase_results"] = {}
                result["metrics"]["phases"] = {}
                for phase_name, phase_duration in phase_durations.items():
                    phase_metrics = {
                        "duration_s": phase_duration,
                        "outputs": {"combined": {"estimated_tokens": 1}},
                    }
                    result["phase_results"][phase_name] = {
                        "returncode": 0,
                        "timed_out": False,
                        "metrics": phase_metrics,
                    }
                    result["metrics"]["phases"][phase_name] = phase_metrics
                result["phase_results"]["flag-sequencing"]["plan_payload"] = {
                    "length": 2,
                    "chain": [{"id": "one"}, {"id": "two"}],
                    "flag_assignments": [
                        {
                            "id": generator_id,
                            "name": f"Generator {generator_id}",
                            "generator_catalog": (
                                "flag_node_generators"
                                if generator_id == "gen-b"
                                else "flag_generators"
                            ),
                        }
                        for generator_id in generator_ids
                    ],
                }
                result["metadata"]["vulnerability_selection"] = {
                    "selected": [{"name": vulnerability_id} for vulnerability_id in vulnerability_ids]
                }
                result["metrics"]["content"]["challenges"]["count"] = 2
                result["metrics"]["content"]["chains"]["average_length"] = 2
                result["metrics"]["spec"]["vulnerabilities"]["count"] = 2
                with open(os.path.join(temp_dir, f"{name}_result.json"), "w", encoding="utf-8") as handle:
                    json.dump(result, handle)

            data = load_dashboard_data(temp_dir)

            self.assertEqual(data["summary"]["challenges"], 4)
            self.assertEqual(data["summary"]["unique_challenges"], 3)
            self.assertTrue(data["summary"]["unique_challenges_complete"])
            self.assertEqual(data["summary"]["flag_node_generators_unique"], 1)
            self.assertEqual(data["summary"]["flag_node_generators_total"], 1)
            self.assertEqual(data["summary"]["flag_generators_unique"], 2)
            self.assertEqual(data["summary"]["flag_generators_total"], 3)
            self.assertEqual(data["summary"]["vulnerabilities_unique"], 3)
            self.assertEqual(data["summary"]["vulnerabilities_total"], 4)
            self.assertTrue(data["summary"]["vulnerabilities_complete"])
            self.assertEqual(
                [row["id"] for row in data["inventories"]["flag_generators"]],
                ["gen-a", "gen-c"],
            )
            self.assertEqual(data["inventories"]["flag_generators"][0]["count"], 2)
            self.assertEqual(data["inventories"]["flag_generators"][0]["run_count"], 2)
            self.assertEqual(len(data["inventories"]["vulnerabilities"]), 3)
            self.assertEqual(data["runs"][0]["unique_challenge_count"], 2)
            self.assertTrue(data["runs"][0]["unique_challenges_complete"])
            self.assertEqual(data["runs"][0]["create_duration_s"], 2)
            self.assertEqual(data["runs"][0]["test_duration_s"], 7)
            self.assertEqual(data["runs"][0]["run_duration_s"], 5)
            self.assertEqual(data["runs"][0]["total_duration_s"], 20)
            self.assertTrue(all(
                run["total_duration_s"]
                >= run["create_duration_s"] + run["test_duration_s"] + run["run_duration_s"]
                for run in data["runs"]
            ))

    def test_rerun_api_starts_selected_run_in_existing_job_manager(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            spec_path = root / "sample.spec.yaml"
            spec_path.write_text("name: sample\niterations: 2\n", encoding="utf-8")
            sf_path = root / "scenarioforge"
            sf_path.mkdir()
            result = _result(
                "sample_run2",
                success=True,
                duration=1,
                started_at="2026-08-01T12:00:00Z",
            )
            result["metadata"].update({
                "spec_file": str(spec_path),
                "iteration_index": 2,
                "iteration_count": 2,
            })
            result_path = root / "sample_run2_result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            app = create_app(root)
            client = app.test_client()
            manager = app.extensions["evaluation_job_manager"]

            with mock.patch.object(
                manager,
                "start_commands",
                return_value={"status": "starting", "logs": [], "log_sequence": 0},
            ) as start_commands:
                response = client.post(
                    "/api/rerun",
                    json={
                        "run_ids": [result_path.name],
                        "replace_original": False,
                        "sf_path": str(sf_path),
                    },
                )

            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json["status"], "starting")
            command = start_commands.call_args.args[0][0]
            self.assertEqual(command[-2:], ["--iteration-index", "2"])
            self.assertEqual(start_commands.call_args.kwargs["rebuild_root"], root)
            self.assertEqual(start_commands.call_args.kwargs["cleanup_paths"], ())

            invalid = client.post(
                "/api/rerun",
                json={"run_ids": [], "sf_path": str(sf_path)},
            )
            self.assertEqual(invalid.status_code, 400)

    def test_flask_routes_serve_dashboard_and_fresh_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "alpha_result.json"), "w", encoding="utf-8") as handle:
                json.dump(_result("alpha", success=True, duration=1, started_at="2026-08-01T12:00:00Z"), handle)
            app = create_app(temp_dir)
            client = app.test_client()

            page = client.get("/")
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Run intelligence", page.data)
            self.assertIn(b'id="execute-panel"', page.data)
            self.assertIn(b'id="analysis-panel"', page.data)
            self.assertIn(b"--dangerous-cleanup-between-runs", page.data)
            self.assertIn(b"Select file", page.data)
            self.assertIn(b"Select folder", page.data)
            self.assertIn(b'id="execution-follow"', page.data)
            self.assertIn(b">Follow</span>", page.data)
            self.assertIn(b'id="execution-continuity"', page.data)
            self.assertIn(b"Refreshing or closing this page will not stop it", page.data)
            self.assertIn(b"applyInitialExecutionConfig", page.data)
            self.assertIn(b"formatExecutionLogLine", page.data)
            self.assertIn(b"executionLogLevel", page.data)
            self.assertIn(b"lineLevel === 'debug'", page.data)
            self.assertIn(b"normalizeExecutionLogLine", page.data)
            self.assertIn(b"pivot source already has a compose assignment", page.data)
            self.assertIn(b"log-token-warning", page.data)
            self.assertIn(b"log-token-error", page.data)
            self.assertIn(b"log-token-phase", page.data)
            self.assertIn(b"log-token-step", page.data)
            self.assertIn(b"log-token-success", page.data)
            self.assertIn(b"Explore Folder", page.data)
            self.assertIn(b"New datasource", page.data)
            self.assertIn(b"Time to create, test, run", page.data)
            self.assertIn(b'id="inventory-view"', page.data)
            self.assertIn(b"Flag-node-generators", page.data)
            self.assertIn(b'id="select-visible-runs"', page.data)
            self.assertIn(b'id="rerun-selected"', page.data)
            self.assertIn(b'id="rerun-modal"', page.data)
            self.assertIn(b"Replace selected run data", page.data)
            self.assertIn(b"/api/rerun", page.data)
            self.assertEqual(page.headers["Cache-Control"], "no-store")

            response = client.get("/api/dashboard")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["summary"]["total_runs"], 1)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

            health = client.get("/healthz")
            self.assertEqual(health.status_code, 200)
            self.assertTrue(health.json["ok"])
            self.assertEqual(health.json["schema_version"], 3)

            execution_status = client.get("/api/execution")
            self.assertEqual(execution_status.status_code, 200)
            self.assertEqual(execution_status.json["status"], "idle")
            self.assertEqual(execution_status.json["defaults"]["out_path"], str(Path(temp_dir).resolve()))

            manager = app.extensions["evaluation_job_manager"]
            with mock.patch.object(
                manager,
                "start",
                return_value={"status": "starting", "logs": [], "log_sequence": 0},
            ):
                start_response = client.post("/api/execution", json={"phase": "execute"})
                self.assertEqual(start_response.status_code, 202)
                self.assertEqual(start_response.json["status"], "starting")

            with mock.patch.object(
                manager,
                "stop",
                return_value={"status": "stopping", "logs": [], "log_sequence": 0},
            ):
                stop_response = client.post("/api/execution/stop")
                self.assertEqual(stop_response.status_code, 200)
                self.assertEqual(stop_response.json["status"], "stopping")

            with mock.patch(
                "scenarioforge_eval.dashboard._select_path",
                return_value=str(Path(temp_dir).resolve()),
            ) as select_path:
                picker_response = client.post(
                    "/api/select-path",
                    json={"kind": "folder", "initial_path": temp_dir},
                )
                self.assertEqual(picker_response.status_code, 200)
                self.assertFalse(picker_response.json["cancelled"])
                self.assertEqual(picker_response.json["path"], str(Path(temp_dir).resolve()))
                select_path.assert_called_once_with("folder", temp_dir)

            with mock.patch("scenarioforge_eval.dashboard._select_path", return_value=None):
                cancelled_picker = client.post(
                    "/api/select-path",
                    json={"kind": "file", "initial_path": temp_dir},
                )
                self.assertEqual(cancelled_picker.status_code, 200)
                self.assertTrue(cancelled_picker.json["cancelled"])

            invalid_picker = client.post("/api/select-path", json={"kind": "anything"})
            self.assertEqual(invalid_picker.status_code, 400)

            with mock.patch("scenarioforge_eval.dashboard._open_folder") as open_folder:
                source_response = client.post("/api/open-folder", json={})
                self.assertEqual(source_response.status_code, 200)
                open_folder.assert_called_once_with(Path(temp_dir).resolve())

                open_folder.reset_mock()
                run_response = client.post(
                    "/api/open-folder",
                    json={"run_id": "alpha_result.json"},
                )
                self.assertEqual(run_response.status_code, 200)
                open_folder.assert_called_once_with(Path(temp_dir).resolve())

                invalid_response = client.post(
                    "/api/open-folder",
                    json={"run_id": "../outside_result.json"},
                )
                self.assertEqual(invalid_response.status_code, 400)
                self.assertFalse(invalid_response.json["ok"])

                non_json_response = client.post("/api/open-folder")
                self.assertEqual(non_json_response.status_code, 400)

            with tempfile.TemporaryDirectory() as second_dir:
                with open(os.path.join(second_dir, "beta_result.json"), "w", encoding="utf-8") as handle:
                    json.dump(_result("beta", success=True, duration=2, started_at="2026-08-02T12:00:00Z"), handle)

                datasource_response = client.post(
                    "/api/data-source",
                    json={"path": second_dir},
                )
                self.assertEqual(datasource_response.status_code, 200)
                self.assertEqual(datasource_response.json["root"], str(Path(second_dir).resolve()))

                switched_data = client.get("/api/dashboard")
                self.assertEqual(switched_data.json["runs"][0]["spec_name"], "beta")
                self.assertEqual(client.get("/healthz").json["root"], str(Path(second_dir).resolve()))
                with mock.patch("scenarioforge_eval.dashboard._open_folder") as open_folder:
                    explore_response = client.post("/api/open-folder", json={})
                    self.assertEqual(explore_response.status_code, 200)
                    open_folder.assert_called_once_with(Path(second_dir).resolve())

            invalid_datasource = client.post(
                "/api/data-source",
                json={"path": os.path.join(temp_dir, "missing")},
            )
            self.assertEqual(invalid_datasource.status_code, 400)


if __name__ == "__main__":
    unittest.main()
