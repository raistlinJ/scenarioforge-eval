"""Portable ScenarioForge reproduction bundles.

The XML remains the authoritative scenario definition.  A bundle adds enough
metadata to replay it deterministically and, when available locally, includes
the generated flow artifact directories referenced by FlowState/PlanPreview.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


BUNDLE_FORMAT = "scenarioforge-reproduction"
BUNDLE_VERSION = 1
MANIFEST_NAME = "scenarioforge-reproduction.json"
SCENARIO_NAME = "scenario.xml"
REPRODUCTION_MODES = ("xml", "replay", "bundle")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_scenario_xml(xml_file: Path) -> tuple[bytes, int]:
    """Build the archive XML, retaining its CORE connection as authored.

    Credentials are deliberately carried: a bundle is meant to reproduce a run
    without the importer re-entering connection details, and stripping them
    left imported scenarios unable to reach any CORE host (Materialize stalled
    on an SSH connection it had no password for). The bundle is therefore a
    secret-bearing artifact -- treat it like the credentials it contains and
    do not publish one you would not hand the CORE VM's password to.
    """
    tree = ET.parse(xml_file)
    carried = 0
    for element in tree.getroot().iter():
        if str(element.tag).rsplit("}", 1)[-1] != "CoreConnection":
            continue
        for attribute in ("ssh_password", "password"):
            if element.attrib.get(attribute):
                carried += 1
    output = io.BytesIO()
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output.getvalue(), carried


def _git_revision(repo: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _embedded_json_payloads(xml_path: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return payloads
    for element in root.iter():
        tag = str(element.tag).rsplit("}", 1)[-1]
        if tag not in {"FlowState", "PlanPreview"}:
            continue
        try:
            payload = json.loads(element.text or "")
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _flow_summary(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    flow = next(
        (
            payload
            for payload in payloads
            if isinstance(payload.get("flag_assignments"), list)
            or isinstance(payload.get("chain"), list)
        ),
        {},
    )
    assignments = flow.get("flag_assignments") if isinstance(flow, dict) else []
    chain = flow.get("chain") if isinstance(flow, dict) else []
    return {
        "scenario": str(flow.get("scenario") or ""),
        "seed": flow.get("seed"),
        "chain_ids": [
            str(item.get("id") if isinstance(item, dict) else item)
            for item in (chain or [])
        ],
        "assignment_ids": [
            str(item.get("id") or item.get("generator_id") or "")
            for item in (assignments or [])
            if isinstance(item, dict)
        ],
        "assignment_count": len(assignments or []),
    }


def _generation_summary(ai_generation: dict[str, Any] | None) -> dict[str, Any]:
    """Describe how the scenario was authored.

    A seed reproduces the deterministic builder, but not a model: the same
    prompt and seed can yield a different scenario. The archived XML is
    therefore the reproducible artifact, and this records what produced it so a
    reader can tell a replayable build from a one-off generation.
    """
    if not isinstance(ai_generation, dict) or not ai_generation:
        return {"source": "spec", "seed_reproducible": True}
    summary: dict[str, Any] = {
        "source": "ai-prompt",
        # The XML in this archive is authoritative; re-running the prompt is not
        # expected to reproduce it.
        "seed_reproducible": False,
        "prompt": str(ai_generation.get("prompt") or ""),
    }
    for key in ("provider", "model", "base_url", "bridge_mode", "scenario", "attempts"):
        value = ai_generation.get(key)
        if value not in (None, ""):
            summary[key] = value
    applied_actions = ai_generation.get("applied_actions")
    if applied_actions not in (None, ""):
        summary["applied_actions"] = applied_actions
    return summary


def _referenced_artifact_paths(payloads: list[dict[str, Any]]) -> list[str]:
    directory_keys = {"artifacts_dir", "run_dir", "inject_source_dir"}
    file_keys = {"outputs_manifest"}
    found: list[str] = []

    def add(value: Any, *, parent: bool = False) -> None:
        if isinstance(value, dict):
            value = value.get("path")
        if isinstance(value, list):
            for item in value:
                add(item, parent=parent)
            return
        if not isinstance(value, str) or not value.strip():
            return
        path = value.strip()
        if parent:
            path = os.path.dirname(path.rstrip("/")) or path
        if path not in found:
            found.append(path)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in directory_keys:
                    add(item)
                elif key in file_keys:
                    add(item, parent=True)
                elif key == "inject_sources":
                    add(item, parent=True)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for payload in payloads:
        walk(payload)
    return found


def _local_artifact_candidate(source: str, sf_path: Path) -> Path | None:
    path = Path(source).expanduser()
    if path.is_dir():
        return path.resolve()
    normalized = source.replace("\\", "/")
    remote_roots = (
        ("/tmp/vulns/flag_generators_runs/", "flag_generators_runs"),
        ("/tmp/vulns/flag_node_generators_runs/", "flag_node_generators_runs"),
    )
    for prefix, local_name in remote_roots:
        if not normalized.startswith(prefix):
            continue
        suffix = normalized[len(prefix) :].strip("/")
        for candidate in (
            sf_path / "outputs" / local_name / suffix,
            sf_path / "outputs" / "vulns" / local_name / suffix,
        ):
            if candidate.is_dir():
                return candidate.resolve()
    return None


def artifact_source_paths(xml_path: str) -> list[str]:
    """Return unique artifact directories referenced by saved flow metadata."""
    return _referenced_artifact_paths(_embedded_json_payloads(Path(xml_path).resolve()))


def local_artifact_source(source: str, sf_path: str) -> str:
    candidate = _local_artifact_candidate(source, Path(sf_path).resolve())
    return str(candidate) if candidate else ""


def _iter_regular_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        yield path


def create_reproduction_bundle(
    *,
    xml_path: str,
    output_dir: str,
    mode: str,
    seed: int,
    sf_path: str,
    eval_repo: str,
    artifact_overrides: dict[str, str] | None = None,
    ai_generation: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Create a replay or artifact-bearing reproduction archive."""
    if mode not in REPRODUCTION_MODES or mode == "xml":
        raise ValueError("reproduction bundles require mode 'replay' or 'bundle'")
    xml_file = Path(xml_path).resolve()
    out_dir = Path(output_dir).resolve()
    sf_repo = Path(sf_path).resolve()
    portable_xml, carried_credential_attributes = _portable_scenario_xml(xml_file)
    payloads = _embedded_json_payloads(xml_file)
    sources = _referenced_artifact_paths(payloads)
    artifact_sources: list[dict[str, Any]] = []
    archive_files: list[tuple[Path, str]] = []

    for index, source in enumerate(sources, start=1):
        override_value = (artifact_overrides or {}).get(source)
        override = Path(override_value).resolve() if override_value else None
        local = override if override and override.is_dir() else None
        if local is None and mode == "bundle":
            local = _local_artifact_candidate(source, sf_repo)
        archive_root = f"artifacts/{index:03d}"
        record: dict[str, Any] = {
            "source_path": source,
            "archive_path": archive_root if local else "",
            "bundled": bool(local),
        }
        if local:
            files = []
            for file_path in _iter_regular_files(local):
                relative = file_path.relative_to(local).as_posix()
                archive_name = f"{archive_root}/{relative}"
                archive_files.append((file_path, archive_name))
                file_stat = file_path.stat()
                files.append(
                    {
                        "path": relative,
                        "sha256": _sha256_file(file_path),
                        "size": file_stat.st_size,
                        "mode": stat.S_IMODE(file_stat.st_mode),
                    }
                )
            record["files"] = files
        artifact_sources.append(record)

    bundled_count = sum(1 for item in artifact_sources if item["bundled"])
    if mode == "replay":
        fidelity = "deterministic-replay"
    elif bundled_count == len(artifact_sources) and bundled_count:
        fidelity = "portable-artifacts"
    elif bundled_count:
        fidelity = "partial-artifacts"
    else:
        fidelity = "deterministic-replay"

    manifest: dict[str, Any] = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "requested_mode": mode,
        "fidelity": fidelity,
        "scenario": {
            "path": SCENARIO_NAME,
            "sha256": hashlib.sha256(portable_xml).hexdigest(),
        },
        # Reported honestly so a reader can tell whether this archive is a
        # secret-bearing artifact before sharing it.
        "credentials": {
            "included": bool(carried_credential_attributes),
            "source": "source-scenario" if carried_credential_attributes else "destination-runtime",
            "carried_attributes": carried_credential_attributes,
        },
        "seed": seed,
        "flow": _flow_summary(payloads),
        "generation": _generation_summary(ai_generation),
        "artifact_sources": artifact_sources,
        "versions": {
            "scenarioforge": _git_revision(sf_repo),
            "scenarioforge_eval": _git_revision(Path(eval_repo).resolve()),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / "scenarioforge-reproduction.zip"
    fd, temporary_name = tempfile.mkstemp(prefix=".scenarioforge-reproduction-", suffix=".zip", dir=out_dir)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.writestr(SCENARIO_NAME, portable_xml)
            for local_path, archive_name in archive_files:
                archive.write(local_path, archive_name)
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    finally:
        if temporary.exists():
            temporary.unlink()
    return str(destination), manifest
