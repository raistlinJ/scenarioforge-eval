# ScenarioForge-Eval

ScenarioForge-Eval is a batch-testing harness and evaluation tool for `scenarioforge`. It allows you to define scenario specifications in `.spec.yaml` files and automatically executes the current ScenarioForge CLI pipeline: `preview-plan`, optional `flag-sequencing`, and `execute`, or `topo` when requested.

## Features

- **Batch Execution**: Run thousands of scenario permutations automatically.
- **Specification Files**: Define simple bounds for topology and parameters in YAML format.
- **Automated Logging**: Output success/failure reports, per-phase logs, and parsed validation artifacts.
- **Batch Metrics**: Captures per-run and per-phase timing, estimated output tokens, artifact sizes, CPU/resource counters, pass rates, and validation outcomes.
- **Live Artifact Checks**: Optionally validates the running CORE session after execute — containers, services, ports, injects, segmentation, traffic agents, pivot access, and reachability — and grades the run on the result.
- **Compatibility Tracking**: Persists one random seed per iteration, reuses the same authoritative XML across phases, and serializes runtime phases that share one CORE VM target.
- **AI-Friendly Error Reporting**: Automatically writes an AI-ready Markdown prompt with the stack trace plus captured phase artifacts when a scenario fails, while redacting embedded CORE SSH passwords from copied XML.

## Project Structure

- `scenarioforge_eval/parser.py`: Parses `.spec.yaml` bounds and handles random ranges.
- `scenarioforge_eval/executor.py`: Generates a ScenarioForge XML, writes it atomically, embeds mode-aware CORE connection data from the environment, and drives the real `scenarioforge` CLI phases for batch execution.
- `scenarioforge_eval/reporter.py`: Manages the output directory, logs pass/fail statuses, writes batch metrics exports, and creates `_ai_prompt.md` files from the captured phase artifacts upon failure.
- `scenarioforge_eval/dashboard.py`: Runs evaluator jobs and recursively indexes result folders for the metrics dashboard.
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
flag_node_generators:
  enabled: true
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

Each run always preserves its final `scenarioforge-webui.xml`. Use
`--reproduction-mode replay` to also create a deterministic replay package, or
`--reproduction-mode bundle` to include every referenced generated Flow artifact
source that is available on the evaluator host:

```bash
uv run scenarioforge-eval test_specs --sf-path ../scenarioforge --execute \
  --reproduction-mode bundle
```

Both package modes produce `scenarioforge-reproduction.zip`. Its manifest records
the seed, positional chain and generator IDs, source revisions, artifact paths, and
SHA-256 hashes. In VM mode, `bundle` also attempts to download referenced generator
payloads from the CORE VM. If any source cannot be collected, it automatically
records a lower `partial-artifacts` or `deterministic-replay` fidelity instead of
claiming a complete portable copy.

Artifact bundles can contain flags, credentials, and other generated secrets. They
also carry the scenario's own `CoreConnection` credentials — including its SSH
password — so that importing one can reach a CORE host without re-entering them;
the bundle manifest records this under `credentials`. The evaluator writes bundles
with owner-only permissions, but they should still be handled as sensitive data,
kept out of source control, and shared only with people you would give the CORE
host's password.

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

At run finalization, the evaluator snapshots that final XML as
`<out>/<spec_name>/scenarioforge-webui.xml`. This is the ScenarioForge editor/import
format, so it can be imported in the WebUI and run again. A second copy is collected
at `<out>/webui-xml/<spec_name>.xml` for convenient access across a batch. These files
can contain CORE connection credentials and are therefore written with owner-only
permissions.

Full execute runs always add `--post-execution-validation`, parse the last `VALIDATION_SUMMARY_JSON:` marker from combined stdout/stderr, and save the parsed payload as `execute-validation.json`.

Execute output is streamed while the phase is running, so image preparation counters
such as `[images] pulling=5 cached=0 pending=3` remain visible in the terminal. The
same output is retained in `execute.log`.

When `validation.check_artifacts.enabled` is set, execute additionally receives
`--check-artifacts` (plus `--check-artifacts-delay` / `--strict`), and the evaluator parses
the last `CHECK_ARTIFACTS_SUMMARY_JSON:` marker the same way, saving it as
`execute-check-artifacts.json`. See [Artifact checks](#artifact-checks).

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

### Artifact checks

After execute and post-execution validation, the evaluator can run ScenarioForge's
`check-artifacts` phase against the live CORE session. It verifies that the expected
containers are on the right nodes, services are running, service ports are reachable
across the CORE network, inject files landed, segmentation rules are enforced, traffic
agents are running, each traffic source can reach its destination, and every pivot
provider is reachable from the participant network.

```yaml
validation:
  policy: strict
  check_artifacts:
    enabled: true
    delay_seconds: 45   # wait for routing convergence before probing
    strict: false       # true promotes check warnings to run failures
```

Notes:

- `delay_seconds` is applied by the CLI after execute, so slow services and routing
  have time to settle before the probes run.
- With `strict: false` (the default), checks that come back `warn` are recorded in the
  run's `warnings` list; `fail`/`error` checks always fail the run.
- The parsed payload is saved as the `execute-check-artifacts.json` artifact, and the
  metrics gain `check_artifacts_ok` / `check_artifacts_overall` columns.
- Artifact checks only run when execute itself succeeded, so they add findings rather
  than masking an earlier failure.

Legacy spec compatibility notes:

- `flows.count` is treated as an alias for `flows.chain_length`.
- `randomize: false` with no explicit count/length disables the feature.
- `randomize: false` with an explicit count/length keeps the feature enabled and uses the fixed value.

When multiple evaluator iterations target the same CORE VM, runtime phases that can interfere with each other are serialized using a per-VM lock derived from the embedded CORE connection in `scenario.xml`.

For large execute batches, you can opt in to destructive remote Docker cleanup before each runtime run:

```bash
uv run scenarioforge-eval test_specs --sf-path ../scenarioforge --execute \
  --dangerous-cleanup-between-runs \
  --out /tmp/scenarioforge-eval-clean-batch
```

This calls ScenarioForge's `cleanup-scenarioforge-docker --force` while holding the same shared VM lock. It removes all Docker containers, images, build cache, and unused Docker volumes/networks on the configured remote CORE host before each `topo`, `flag-sequencing`, or `execute` runtime run. Use it only on disposable CORE VMs dedicated to evaluation.

Failure prompts redact `CoreConnection/@ssh_password` before copying XML into `_ai_prompt.md`.

Common per-run artifacts include:

- `scenario.xml`
- `scenarioforge-webui.xml`, the final WebUI-importable rerun snapshot
- `scenarioforge-reproduction.zip` when `--reproduction-mode replay` or `bundle` is selected
- `seed.txt`
- `preview-plan.json` and `preview-plan.log`
- `flag-sequencing.json` and `flag-sequencing.log` when Flow is enabled
- `execute.log`
- `execute-validation.json` for full execute runs
- `execute-check-artifacts.json` when `validation.check_artifacts.enabled` is set

When a run has validation issues, warning/error log lines, or a captured
exception, the output root also gets `latest.errors` for the most recent
diagnostic run and `combined-latest.errors` for the batch. These files include
validation results, generator metadata when ScenarioForge emits it, and filtered
`WARNING`/`error` output without routine `INFO` chatter.

Each per-run `<spec>_result.json` includes a `metrics` object with:

- run start/end timestamps and duration
- resolved spec counts for routers, hosts, services, vulnerabilities, flag-node-generators, and flow length
- concrete generated-content counts for challenges, chains, chains longer than one step,
  average chain length, pivot-producing challenges, segmentation pivot providers,
  Flow flag-node-generator challenges, and topology flag-node-generator nodes
- per-phase duration, return code, timeout flag, stdout/stderr/log sizes, and estimated output tokens
- process resource counters from `resource.getrusage`, including CPU time, max RSS, block I/O, page faults, and context switches
- artifact file sizes and output-directory totals

Token counts are deterministic text estimates for logs and CLI output, using a regex word/punctuation estimator. They are intended for trend analysis and graphing, not for API billing reconciliation.

At the end of every batch, the evaluator also writes graph/table-friendly files in the output root:

- `batch_metrics_summary.json`: machine-readable aggregate pass rate, duration, token,
  artifact, resource, challenge, chain, pivot, and flag-node-generator summaries.
- `batch_metrics_summary.md`: quick human-readable summary tables.
- `batch_metrics_raw.jsonl`: one full result object per run.
- `batch_metrics_runs.csv`: one flat row per run.
- `batch_metrics_phases.csv`: one flat row per run phase.

The same batch files are also mirrored under `metrics/` in the output root, for example `metrics/batch_metrics_runs.csv`. Each individual run gets its own metrics bundle in two places:

- `<out>/<spec_name>/metrics/`: colocated with that run's logs and artifacts.
- `<out>/metrics/runs/<spec_name>/`: collected under the batch-level metrics folder.

Each run metrics bundle includes `run_metrics_summary.json`, `run_metrics_raw.json`, `run_metrics_summary.md`, `run_metrics.csv`, and `phase_metrics.csv`.

## Metrics dashboard

Point the dashboard at any parent folder containing evaluator outputs. It recursively
discovers canonical `*_result.json` files, including results nested across multiple
batches, and reads their run, phase, resource, artifact, validation, and generated-
content metrics.

```bash
uv run scenarioforge-eval-dashboard /tmp/scenarioforge-eval-out --open
```

The `root` folder argument is optional after the first run: the dashboard remembers
the data source folder and Execute tab settings (spec path, ScenarioForge path,
target phase, reproduction mode, and flags) in
`~/.scenarioforge_eval/dashboard_settings.json`, and restores them the next time it
starts. Passing a `root` folder on the command line overrides the saved folder (and
becomes the new saved folder for next time); omit it to reopen where you left off.

The dashboard listens on `127.0.0.1:8088` by default. Use `--host` and `--port` to
change the listener. The **Execute** tab configures a spec file or folder,
ScenarioForge path, output folder, target phase, reproduction output, and the
supported evaluator CLI flags. It runs one evaluator job at a time, streams bounded
console output, supports stopping the active job, and can send its output folder
directly to **Analysis**.
Path fields support typing or native file/folder selection on the dashboard host.
Executions are owned by the dashboard server, so refreshing or closing the browser
does not stop an active job; reopening the dashboard restores its configuration,
retained console output, and live status polling.

The **Analysis** tab contains the result dashboard. Refreshing it rescans the parent
folder, so completed runs appear without restarting the service. If only copied
`run_metrics_raw.json` bundles are available, the loader uses those as a deduplicated
fallback. Use **New datasource** to switch the dashboard to another folder on the
machine running the server. Use **Explore Folder** beside the source path to reveal
the dashboard root, or select a run and use **Explore Folder** in its detail drawer
to reveal that run's artifacts.

The timing trend separates each run into **Create** (`scenario-xml`), **Test**
(`preview-plan` plus `flag-sequencing`), **Run** (`execute` or `topo`), and end-to-end
**Total** wall time. Each series can be toggled from the chart legend. Challenge
composition is reported as unique generator catalog/ID pairs over total generated
challenge assignments; older metrics without assignment identities show the unique
count as unavailable or as a lower bound.

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

Validate the live session after execute by enabling artifact checks in the spec:

```yaml
validation:
  policy: strict
  check_artifacts:
    enabled: true
    delay_seconds: 45
```

Then run the spec normally; the evaluator adds the CLI flags, saves
`execute-check-artifacts.json`, and records any check warnings on the run.

Run preview-plan plus flag sequencing only:

```bash
uv run scenarioforge-eval test_specs/09-integrated-services-flow.spec.yaml --sf-path ../scenarioforge --flag-sequencing --out /tmp/scenarioforge-eval-flag
```

Run topology only:

```bash
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --topology --out /tmp/scenarioforge-eval-topo
```

Run every spec in the test directory:

```bash
uv run scenarioforge-eval test_specs --sf-path ../scenarioforge --execute --out /tmp/scenarioforge-eval-batch
```

Run every spec with destructive remote Docker cleanup before each runtime run:

```bash
uv run scenarioforge-eval test_specs --sf-path ../scenarioforge --execute \
  --dangerous-cleanup-between-runs \
  --out /tmp/scenarioforge-eval-clean-batch
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

## Vulnerability Catalog Selection

When `vulns.count` requests randomized vulnerabilities, the evaluator first asks the configured ScenarioForge checkout for selectable vulnerability catalog entries and filters that list to entries whose `docker-compose.yml` exists locally under `--sf-path`. It then writes those selected entries into the generated XML as `Specific` vulnerabilities, and records the names/paths under `metadata.vulnerability_selection` in the per-run result.

Use `vulns.include` and `vulns.exclude` to narrow the eligible catalog when a family is unsuitable for your current CORE/Docker runtime. Filters match either vulnerability name or compose path, using glob-style patterns and substring matches:

```yaml
vulns:
  randomize: true
  count: 2
  exclude:
    - nginx/*
    - php
```

If the catalog cannot be inspected, the evaluator falls back to ScenarioForge's upstream `Random` vulnerability behavior. If the catalog can be inspected but does not have enough eligible compose entries, the run fails during XML generation with a direct catalog eligibility error instead of failing later during CORE startup.

## Flag-Node-Generator Selection

`flag_node_generators` adds flag-node-generator nodes at topology generation time. They are additional to the base Docker host count, just like vulnerabilities. The evaluator resolves every requested node from ScenarioForge's enabled, installed flag-node-generator catalog and writes `Specific` rows (stable `g_id`, name, and count) into the XML. It never uses disabled, uninstalled, or stale pack entries.

The section is opt-in: omit it, or set `enabled: false` with `count: 0`, when a test does not need flag-node-generator topology. Its XML representation is the `Flag Node Generators` topology section, so the ScenarioForge UI, XML, flow sequencing, and execution consume the same ground-truth selection.

```yaml
flag_node_generators:
  enabled: true
  count: 3
  include: [git_*, hash_*]
  exclude: [git_deploy_key_repo]
```

`include` and `exclude` use glob/substr matching against a generator's stable ID and display name. Counts may be greater than the number of eligible generator definitions; the evaluator then assigns multiple topology nodes to an enabled definition and records the exact resolved rows under `metadata.flag_node_generator_selection`. An empty eligible catalog is a direct XML-generation error.

## AI Prompt Generation

A spec can describe what it wants in prose instead of in resolved bounds. When an
`ai` block carries a prompt, the evaluator generates the scenario XML through
ScenarioForge's `ai` CLI phase — the same backend path the Web UI uses, MCP
bridge included — and every later phase (`preview-plan`, `flag-sequencing`,
`execute`, artifact checks, metrics, reporting) runs against the result
unchanged, because the phase writes the same scenario XML the deterministic
builder writes.

```yaml
name: "ai-demo-01"
iterations: 1
seed: 12345
ai:
  prompt: "two routers, three docker hosts, ssh service, and two flag node generators"
  enabled: true      # defaults to true whenever a prompt is present
  timeout_s: 480     # provider budget; ScenarioForge caps this at 480s
  retries: 1         # extra attempts, applied only to timed-out generations
```

A bare top-level `prompt:` is shorthand for `ai.prompt`. Specs with no `ai` or
`prompt` key are unaffected and keep using the deterministic spec-to-XML builder,
so the `topology`/`services`/`vulns`/`flows` sections behave exactly as before.
Because the prompt replaces those sections, a prompt-driven spec normally omits
them.

`--prompt "..."` overrides whatever prompt a spec carries, and `--no-ai` forces
the deterministic path for a spec that has one.

### Provider configuration

Provider settings are **never** read from spec files or from this repository.
They come from `CORETG_AI_*` in the ScenarioForge checkout's
`.scenarioforge.env`, which the evaluator already loads:

| key | meaning |
| --- | --- |
| `CORETG_AI_PROVIDER` | `ollama`, `litellm`, or `openai` |
| `CORETG_AI_MODEL` | model name as the endpoint expects it |
| `CORETG_AI_BASE_URL` | provider base URL |
| `CORETG_AI_API_KEY` | key sent to the provider |
| `CORETG_AI_API_KEY_USER` | username whose encrypted stored credential supplies the key |

Optional per-spec `provider`, `model`, and `base_url` keys map onto the phase's
`--ai-*` flags and beat the environment. An omitted key inherits the
environment; an explicitly empty one is not treated as an override. API keys have
no spec-level equivalent by design.

The evaluator always requests the MCP bridge (`--ai-bridge-mode
mcp-python-sdk`), overridable via `ai.bridge_mode`. Without an explicit bridge
mode the request silently falls back to direct-JSON generation, which fails on
reasoning models that emit `<think>` blocks. The `ai` phase also needs a local
ScenarioForge user account to run as, so a headless environment needs that user
database present.

### Timeouts and reproducibility

ScenarioForge clamps the provider timeout to 480 seconds. A larger `timeout_s`
is lowered to that ceiling and the run records a warning rather than promising a
budget it cannot get. The evaluator's own phase timeout is held above the
provider budget so it never cuts off a generation that was still within it.
Provider latency varies widely for the same prompt, so `retries` re-runs a
generation that timed out; other failures (a 401, an unparseable response) fail
the run immediately with the provider's own error text, and the batch continues
to the next spec.

AI generation is **not reproducible from a seed** — the same prompt and seed can
yield different scenarios. Each run therefore records the prompt, the resolved
provider/model/base URL (never the key), the applied bridge actions, and the
generated XML under `metadata.ai_generation`, with the phase envelope in
`ai.json`. The XML remains the reproducible artifact: reproduction bundles mark
it `source: ai-prompt` with `seed_reproducible: false` so a reader can tell a
replayable build from a one-off generation.
