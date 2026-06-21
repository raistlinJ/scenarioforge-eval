# ScenarioForge-Eval

ScenarioForge-Eval is a batch-testing harness and evaluation tool for `scenarioforge`. It allows you to define scenario specifications in `.spec.yaml` files and automatically executes the current ScenarioForge CLI pipeline: `preview-plan`, optional `flag-sequencing`, and `execute`, or `topo` when requested.

## Features

- **Batch Execution**: Run thousands of scenario permutations automatically.
- **Specification Files**: Define simple bounds for topology and parameters in YAML format.
- **Automated Logging**: Output success/failure reports and capture execution plans.
- **AI-Friendly Error Reporting**: Automatically writes an AI-ready Markdown prompt with the stack trace plus any captured `scenario.xml`, phase JSON, and phase logs when a scenario fails.

## Project Structure

- `scenarioforge_eval/parser.py`: Parses `.spec.yaml` bounds and handles random ranges.
- `scenarioforge_eval/executor.py`: Generates a ScenarioForge XML, embeds VM-mode CORE connection data from the environment, and drives the real `scenarioforge` CLI phases for batch execution.
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
```

Run the evaluator by passing the directory containing your `.spec.yaml` files (or a single file), along with the path to the `scenarioforge` codebase.

Without a phase flag, the evaluator defaults to the full `execute` path to match ScenarioForge's CLI default phase.

**Important:** If you are using `uv` to manage dependencies, the virtual environment is strictly isolated by default. Because `scenarioforge` requires the `core` gRPC library (which is typically installed system-wide on the VM), `uv` will not be able to find it and the CLI phases will fail or fallback unexpectedly.

To fix this, ensure you create your `uv` environment with system package access before running:
```bash
uv venv --system-site-packages
uv sync
uv run scenarioforge-eval test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge --execute
```

By default, the logs and plans will be written to `/tmp/scenarioforge-eval-out/`.

Phase selection mirrors ScenarioForge's CLI semantics:

- `--topology`: run the upstream `topo` phase and stop after the CORE topology is built.
- `--flag-sequencing`: run `preview-plan` and `flag-sequencing`, then stop before `execute`.
- `--execute` or no phase flag: run the full evaluator pipeline through `execute`.

## Services in VM Mode

`scenarioforge-eval` only supports ScenarioForge's `vm` mode. It now writes the VM-mode CORE connection values from the environment directly into the generated ScenarioForge XML so the downstream CLI phases behave the same way as the Web UI given the same XML.

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
