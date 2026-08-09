# TODO: Fix Failing Dataset Runs

> **Generated from:** `dataset-scale-segmented-combined_run04`
> **Date:** 2026-08-07
> **Purpose:** Structured error report for LLM-assisted fixing

---

## Summary

- **1 run** failed with hard error (execution/validation failure)
- **1 error category** identified

---

## Error Categories (Grouped by Root Cause)

### ScenarioForge Module Missing on CORE VM

**Severity:** CRITICAL
**Affected runs (1):** 'dataset-scale-segmented-combined_run04'

**Description:** The remote CORE VM lacks the `scenarioforge` Python module. Flow artifact regeneration fails with `ModuleNotFoundError`, preventing VALIDATION_SUMMARY_JSON emission. Error: 'Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator'.

**Fix Action:** Install `scenarioforge` on the CORE VM. Run `python3 -c 'import scenarioforge'` to verify. Check PYTHONPATH and virtualenv config on the remote machine.

**Files/Components:** scenarioforge_eval/executor.py line 2070

---

## Detailed Per-Run Error Reports

Each section below contains structured error data an LLM can use to generate fixes.

### 1. dataset-scale-segmented-combined_run04

- **Timestamp:** `2026-08-06T14:49:58.443506`
- **Seed:** `191815643`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 6 (dep_api_key_admin_endpoint) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n  File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```