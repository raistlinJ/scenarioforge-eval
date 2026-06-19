# ScenarioForge-Eval

ScenarioForge-Eval is a batch-testing harness and evaluation tool for `scenarioforge`. It allows you to define scenario specifications in `.spec.yaml` files and automatically executes the `scenarioforge` pipeline (Topology Generation, Flag Sequencing, Preview, and Execution) to validate the underlying scenario generators.

## Features

- **Batch Execution**: Run thousands of scenario permutations automatically.
- **Specification Files**: Define simple bounds for topology and parameters in YAML format.
- **Automated Logging**: Output success/failure reports and capture execution plans.
- **AI-Friendly Error Reporting**: Automatically extracts full stack traces, `injects_missing` summaries, and generated `docker-compose.yml` outputs into an AI-ready Markdown format when a scenario fails.

## Project Structure

- `scenarioforge_eval/parser.py`: Parses `.spec.yaml` bounds and handles random ranges.
- `scenarioforge_eval/executor.py`: Hooks into the `scenarioforge` internal python API to generate topologies and execute runs.
- `scenarioforge_eval/reporter.py`: Manages the output directory, logs pass/fail statuses, and creates `_ai_prompt.md` files upon failure.
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
vulns:
  randomize: true
  count: 2
flows:
  randomize: true
```

Run the evaluator by passing the directory containing your `.spec.yaml` files (or a single file), along with the path to the `scenarioforge` codebase. 

**Important:** If you are using `uv` to manage dependencies, the virtual environment is strictly isolated by default. Because `scenarioforge` requires the `core` gRPC library (which is typically installed system-wide on the VM), `uv` will not be able to find it and `scenarioforge` will instantly fallback to an offline report (taking only 3-4 seconds).

To fix this, ensure you create your `uv` environment with system package access before running:
```bash
uv venv --system-site-packages
uv sync
uv run python scenarioforge_eval/main.py test_specs/00-sanity-check.spec.yaml --sf-path ../scenarioforge/ --execute
```

By default, the logs and plans will be written to `/tmp/scenarioforge-eval-out/`.
