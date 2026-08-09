import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from scenarioforge_eval.reproduction import (
    MANIFEST_NAME,
    create_reproduction_bundle,
)


class ReproductionBundleTests(unittest.TestCase):
    def _scenario_xml(self, root: Path, artifact_dir: Path) -> Path:
        document = ET.Element("Scenarios")
        ET.SubElement(
            document,
            "CoreConnection",
            {
                "ssh_host": "source-core.invalid",
                "ssh_username": "source-user",
                "ssh_password": "source-secret",
            },
        )
        scenario = ET.SubElement(document, "Scenario", {"name": "portable-demo"})
        sequencing = ET.SubElement(scenario, "FlagSequencing")
        state = ET.SubElement(sequencing, "FlowState")
        state.text = json.dumps(
            {
                "scenario": "portable-demo",
                "seed": 123,
                "chain": [{"id": "7"}],
                "flag_assignments": [
                    {
                        "id": "demo-generator",
                        "node_id": "7",
                        "artifacts_dir": str(artifact_dir),
                        "resolved_inputs": {"seed": "123"},
                        "resolved_outputs": {"Flag(flag_id)": "FLAG-123"},
                    }
                ],
            }
        )
        xml_path = root / "scenarioforge-webui.xml"
        ET.ElementTree(document).write(xml_path, encoding="utf-8", xml_declaration=True)
        return xml_path

    def test_bundle_includes_available_artifacts_and_integrity_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_dir = root / "generated" / "artifacts"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "flag.txt").write_text("FLAG-123\n", encoding="utf-8")
            xml_path = self._scenario_xml(root, artifact_dir)

            bundle_path, manifest = create_reproduction_bundle(
                xml_path=str(xml_path),
                output_dir=str(root / "out"),
                mode="bundle",
                seed=123,
                sf_path=str(root),
                eval_repo=str(root),
            )

            self.assertEqual(manifest["fidelity"], "portable-artifacts")
            self.assertEqual(manifest["flow"]["chain_ids"], ["7"])
            self.assertTrue(manifest["artifact_sources"][0]["bundled"])
            # The bundle carries its scenario's CORE credentials so an import
            # can reach a host without re-entering them, and the manifest says
            # so plainly -- a reader has to be able to tell that this archive
            # is secret-bearing before passing it on.
            self.assertTrue(manifest["credentials"]["included"])
            self.assertEqual(manifest["credentials"]["source"], "source-scenario")
            self.assertEqual(manifest["credentials"]["carried_attributes"], 1)
            with zipfile.ZipFile(bundle_path) as archive:
                self.assertIn(MANIFEST_NAME, archive.namelist())
                self.assertIn("scenario.xml", archive.namelist())
                self.assertIn("artifacts/001/flag.txt", archive.namelist())
                archived_xml = archive.read("scenario.xml")
                self.assertIn(b"source-secret", archived_xml)
                self.assertIn(b"ssh_password", archived_xml)
                self.assertEqual(
                    manifest["scenario"]["sha256"],
                    hashlib.sha256(archived_xml).hexdigest(),
                )
            self.assertIn("source-secret", xml_path.read_text(encoding="utf-8"))

    def test_replay_package_records_sources_without_copying_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_dir = root / "generated"
            artifact_dir.mkdir()
            (artifact_dir / "secret.txt").write_text("secret", encoding="utf-8")
            xml_path = self._scenario_xml(root, artifact_dir)

            bundle_path, manifest = create_reproduction_bundle(
                xml_path=str(xml_path),
                output_dir=str(root / "out"),
                mode="replay",
                seed=123,
                sf_path=str(root),
                eval_repo=str(root),
            )

            self.assertEqual(manifest["fidelity"], "deterministic-replay")
            self.assertFalse(manifest["artifact_sources"][0]["bundled"])
            with zipfile.ZipFile(bundle_path) as archive:
                self.assertFalse(any(name.startswith("artifacts/") for name in archive.namelist()))

    def test_bundle_uses_downloaded_override_for_remote_artifact_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            remote_source = Path("/tmp/vulns/flag_generators_runs/portable-demo")
            xml_path = self._scenario_xml(root, remote_source)
            downloaded = root / "downloaded"
            downloaded.mkdir()
            (downloaded / "outputs.json").write_text('{"ok":true}\n', encoding="utf-8")

            bundle_path, manifest = create_reproduction_bundle(
                xml_path=str(xml_path),
                output_dir=str(root / "out"),
                mode="bundle",
                seed=123,
                sf_path=str(root),
                eval_repo=str(root),
                artifact_overrides={str(remote_source): str(downloaded)},
            )

            self.assertEqual(manifest["fidelity"], "portable-artifacts")
            with zipfile.ZipFile(bundle_path) as archive:
                self.assertIn("artifacts/001/outputs.json", archive.namelist())


if __name__ == "__main__":
    unittest.main()
