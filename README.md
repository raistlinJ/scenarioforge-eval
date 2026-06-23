# ScenarioForge-Eval

ScenarioForge-Eval is a batch-testing harness and evaluation tool for `scenarioforge`. It allows you to define scenario specifications in `.spec.yaml` files and automatically executes the current ScenarioForge CLI pipeline: `preview-plan`, optional `flag-sequencing`, and `execute`, or `topo` when requested.

## Features

- **Batch Execution**: Run thousands of scenario permutations automatically.
- **Specification Files**: Define simple bounds for topology and parameters in YAML format.
- **Automated Logging**: Output success/failure reports, per-phase logs, and parsed validation artifacts.
- **Compatibility Tracking**: Persists one random seed per iteration, reuses the same authoritative XML across phases, and serializes runtime phases that share one CORE VM target.
- **AI-Friendly Error Reporting**: Automatically writes an AI-ready Markdown prompt with the stack trace plus captured phase artifacts when a scenario fails, while redacting embedded CORE SSH passwords from copied XML.

## Project Structure

- `scenarioforge_eval/parser.py`: Parses `.spec.yaml` bounds and handles random ranges.
- `scenarioforge_eval/executor.py`: Generates a ScenarioForge XML, writes it atomically, embeds mode-aware CORE connection data from the environment, and drives the real `scenarioforge` CLI phases for batch execution.
- `scenarioforge_eval/reporter.py`: Manages the output directory, logs pass/fail statuses, and creates `_ai_prompt.md` files from the captured phase artifacts upon failure.
- `scenarioforge_eval/main.py`: The CLI entry point.

## Usage

Create a `.spec.yaml` file (e.g., `test.spec.yaml`):

```yaml
name: "eval-test-1"
iterations: 10 # Number of times to generate and test this scenario
topology:
  type: "star"
  routers: [1, 3] # Can be a range for random generation
  hosts: [2, 5]
  randomize: true
services:
  randomize: true
  count: 3
vulns:
  randomize: true
  count: 2
flows:
  randomize: true
validation:
  policy: strict
```

For Flow specs, prefer `chain_length`. The evaluator also accepts legacy `flows.count` as an alias.

Run the evaluator by passing the directory containing your `.spec.yaml` files (or a single file), along with the path to the `scenarioforge` codebase.

Without a phase flag, the evaluator defaults to the full `execute` path to match ScenarioForge's CLI default phase.

The generated XML embeds the resolved CORE connection so the downstream CLI phases operate against the same target as the Web UI.

For the normal remote CORE VM path, the evaluator does not need a locally importable `core` Python package. Local system-site packages are only required if you are intentionally running CORE natively on the same machine as the evaluator.

Typical setup:
```bash
uv venv
uv sync
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --execute
```

## Remote Helper VM Workflow

One supported deployment model is:

- `scenarioforge-eval` runs on a helper VM
- the sibling `scenarioforge` checkout is on that same helper VM
- CORE itself runs on a separate CORE VM
- the generated XML carries the saved remote CORE SSH connection used by ScenarioForge remote delegation

In that setup, the evaluator does not need a local CORE daemon. It only needs the generated XML to contain a usable remote delegation path, which ScenarioForge then uses to stage artifacts and launch the remote CLI on the CORE VM.

The sibling `scenarioforge` checkout on the helper VM must still be writable by the evaluator user. Current CLI and backend startup paths expect writable repo-local artifact roots under `outputs/` and `uploads/`, and later execute/report phases may also write under `reports/`.

The evaluator's local loopback preflight is intentionally narrow:

- if the XML points at loopback CORE gRPC and does not contain a usable remote SSH path, the evaluator fails early
- if the XML points at loopback CORE gRPC but does contain non-loopback remote SSH metadata, the evaluator skips the local-only preflight and lets ScenarioForge handle remote delegation

If your helper VM is meant to delegate remotely, make sure the sibling `scenarioforge` environment resolves to the actual CORE VM SSH target rather than to placeholder local-only values.

If you do need native local CORE execution for debugging, recreate the environment with system package access:

```bash
uv venv --system-site-packages
uv sync
```

By default, the logs and plans will be written to `/tmp/scenarioforge-eval-out/`.

Phase selection mirrors ScenarioForge's CLI semantics:

- `--topology`: run the upstream `topo` phase and stop after the CORE topology is built.
- `--flag-sequencing`: run `preview-plan` and `flag-sequencing`, then stop before `execute`.
- `--execute` or no phase flag: run the full evaluator pipeline through `execute`.

## Compatibility Contract Notes

Each iteration now persists one seed and passes it through every CLI phase so `preview-plan`, `flag-sequencing`, `topo`, and `execute` all operate on the same randomized scenario.

The evaluator retains the authoritative `scenario.xml` generated at the start of the run and does not regenerate it between phases. `preview-plan` and `flag-sequencing` are allowed to mutate that XML in place, and `execute` consumes the mutated file.

Full execute runs always add `--post-execution-validation`, parse the last `VALIDATION_SUMMARY_JSON:` marker from combined stdout/stderr, and save the parsed payload as `execute-validation.json`.

Current ScenarioForge also emits that marker when CORE startup fails before the
detailed validator can run. The evaluator streams and reports its
`validation_unavailable`, startup error, session id, and daemon hint rather than
collapsing the failure into a missing-marker message.

Before invoking ScenarioForge CLI phases, the evaluator ensures the minimal sibling-repo runtime roots exist under `outputs/` and `uploads/`.

Before `topo` or `execute`, when the generated XML targets a loopback CORE gRPC endpoint such as `127.0.0.1:50051` and does not already carry a usable remote-delegation SSH path, the evaluator performs a local socket preflight and fails early with a direct message if the local CORE daemon is unreachable.

Validation policy is explicit in the spec:

```yaml
validation:
  policy: strict
```

Supported policies:

- `strict`: require process exit `0` and `validation_summary.ok == true`.
- `warning_tolerant`: allow warning-only validation summaries while still failing on validation error fields.

Legacy spec compatibility notes:

- `flows.count` is treated as an alias for `flows.chain_length`.
- `randomize: false` with no explicit count/length disables the feature.
- `randomize: false` with an explicit count/length keeps the feature enabled and uses the fixed value.

When multiple evaluator iterations target the same CORE VM, runtime phases that can interfere with each other are serialized using a per-VM lock derived from the embedded CORE connection in `scenario.xml`.

Failure prompts redact `CoreConnection/@ssh_password` before copying XML into `_ai_prompt.md`.

Common per-run artifacts include:

- `scenario.xml`
- `seed.txt`
- `preview-plan.json` and `preview-plan.log`
- `flag-sequencing.json` and `flag-sequencing.log` when Flow is enabled
- `execute.log`
- `execute-validation.json` for full execute runs

## Sample Commands

Set up the environment on the helper VM:

```bash
uv venv
uv sync
```

Run one spec through the full pipeline:

```bash
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --execute
```

Run one spec with a dedicated output directory and verbose CLI logs:

```bash
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --execute --verbose --out /tmp/scenarioforge-eval-smoke
```

Run preview-plan plus flag sequencing only:

```bash
uv run scenarioforge-eval test_specs/11-30-permutations.spec.yaml --sf-path ../scenarioforge --flag-sequencing --out /tmp/scenarioforge-eval-flag
```

Run topology only:

```bash
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --topology --out /tmp/scenarioforge-eval-topo
```

Run every spec in the test directory:

```bash
uv run scenarioforge-eval test_specs --sf-path ../scenarioforge --execute --out /tmp/scenarioforge-eval-batch
```

Increase the per-phase timeout for slower remote runs:

```bash
SCENARIOFORGE_EVAL_PHASE_TIMEOUT_S=1800 \
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --execute --out /tmp/scenarioforge-eval-long
```

Run the unit test suite:

```bash
uv run python -m unittest discover -s tests
```

Inspect the non-secret CORE mode and connection settings in the sibling `scenarioforge` repo:

```bash
cd ../scenarioforge
rg -n '^(CORETG_WEBUI_MODE|CORE_HOST|CORE_PORT|CORE_SSH_HOST|CORE_SSH_PORT|CORE_SSH_USERNAME|CORETG_VM_MODE_HITL_ENABLED)=' .scenarioforge.env
```

Inspect the evaluator outputs for one run:

```bash
find /tmp/scenarioforge-eval-smoke -maxdepth 2 -type f | sort
cat /tmp/scenarioforge-eval-smoke/sanity-check_result.json
```

Inspect the execute log for a failed run:

```bash
sed -n '1,220p' /tmp/scenarioforge-eval-smoke/sanity-check/execute.log
```

## CORE Connection And Services

`scenarioforge-eval` writes the resolved CORE connection values from the environment directly into the generated ScenarioForge XML so the downstream CLI phases behave the same way as the Web UI given the same XML.

Because the stock CORE docker image used in VM mode does not include `dhclient`, the evaluator defaults its randomized service pool to `SSH` and `HTTP`.

If your environment has a compatible image and you intentionally want DHCP client startup, opt in explicitly:

```yaml
services:
  randomize: true
  count: 2
  include: [SSH, HTTP, DHCPClient]
```

You can also blacklist individual service types when narrowing a failing spec:

```yaml
services:
  randomize: true
  count: 4
  exclude: [DHCPClient]
```
