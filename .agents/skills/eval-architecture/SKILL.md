---
name: eval-architecture
description: Trigger this skill when asked to modify or debug the scenarioforge-eval batch testing harness.
---

# ScenarioForge-Eval Architecture

You are working in the `scenarioforge-eval` repository. This is a batch testing harness designed to automatically generate and execute scenarios using the `scenarioforge` core engine.

## Overview
1. **`parser.py`**: Parses `.spec.yaml` files. Uses `scenarioforge_eval/schema.json` as the strict schema reference. Ranges like `[2, 5]` are automatically resolved to random integers.
2. **`executor.py`**: Currently imports `scenarioforge` as a direct Python library (`from webapp import app_backend`). It builds an internal JSON representation and forces `scenarioforge` to generate the XML topology. It then invokes the internal `cli.main()` method using a mock `sys.argv`.
   - **Future API Migration**: If instructed to migrate to the REST API, you should modify `executor.py` to use `requests` and `POST` payloads to the `scenarioforge` backend. When doing this, refer to the OpenAPI specification located in the main `scenarioforge` repository at `docs/openapi.yaml`.
3. **`reporter.py`**: Outputs `_result.json` and if an error occurs, packages the stack trace plus any generated `scenario.xml`, phase JSON, and phase logs into an `_ai_prompt.md` file designed to be read by LLMs to auto-fix the `scenarioforge` generators.

## Constraints
- Never rewrite the underlying `scenarioforge` generator code from this repository. This repository only contains the *evaluator* code.
- If you add or modify properties in `.spec.yaml`, you **must** update `scenarioforge_eval/schema.json` to match.
