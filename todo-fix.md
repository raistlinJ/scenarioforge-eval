# TODO: Fix Failing Dataset Runs

> **Generated from:** `/private/tmp/dataset/combined-latest.errors`
> **Date:** 2026-08-06
> **Purpose:** Structured error reports for LLM-assisted fixing

---

## Summary

- **14 runs** failed with hard errors (execution/validation failures)
- **23 runs** had warnings (missing Docker images) but validation passed
- **7 error categories** identified

---

## Error Categories (Grouped by Root Cause)

### ScenarioForge Module Missing on CORE VM

**Severity:** CRITICAL
**Affected runs (4):** 'dataset-scale-segmented-combined_run04', 'dataset-segmented-enterprise-pivots_run04', 'dataset-catalog-coverage-042', 'dataset-scale-segmented-combined_run02'

**Description:** The remote CORE VM lacks the `scenarioforge` Python module. Flow artifact regeneration fails with `ModuleNotFoundError`, preventing VALIDATION_SUMMARY_JSON emission. Error: 'Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator'.

**Fix Action:** Install `scenarioforge` on the CORE VM. Run `python3 -c 'import scenarioforge'` to verify. Check PYTHONPATH and virtualenv config on the remote machine.

**Files/Components:** scenarioforge_eval/executor.py line 2070

### Missing Pre-generated Flow Values in XML

**Severity:** CRITICAL
**Affected runs (3):** 'dataset-artifact-name-identity_run05', 'dataset-mixed-enterprise-data_run05', 'dataset-vuln-collaboration_run02'

**Description:** The scenario XML lacks pre-generated Flow values. The executor requires `Generate (resolve)` before `Execute` to populate resolved flow data. Error: 'Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.'

**Fix Action:** 1. Run the Generate/Resolve step on the scenario XML before Execute. 2. Ensure `scenarioforge.cli generate` was run. 3. Verify the XML was saved with resolved values.

**Files/Components:** scenarioforge_eval/executor.py (preflight check)

### CORE Session Stuck in 'configuration' State

**Severity:** HIGH
**Affected runs (5):** 'dataset-vuln-cache_run04', 'dataset-mixed-application-mesh_run04', 'dataset-vuln-cache_run02', 'dataset-mixed-shared-data_run01', 'dataset-mixed-perimeter-identity_run05'

**Description:** The CORE session stays in 'configuration' state, never instantiating the topology. No interface/address attached to docker nodes. Causes: missing Docker images, containers failing to start, or restarting loops.

**Fix Action:** 1. Pull all missing Docker images (listed per-run). 2. Run `docker-compose up -d` per node and verify 'running' state. 3. Check docker-compose.yml for syntax errors.

**Files/Components:** core session startup, docker-compose validation

### Docker Build Timeout (DeadlineExceeded)

**Severity:** MEDIUM
**Affected runs (1):** 'dataset-artifact-data-stores_run03'

**Description:** Docker build timed out fetching base image from Docker Hub. Error: 'failed to solve: DeadlineExceeded: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim' and 'net/http: timeout awaiting response headers'.

**Fix Action:** 1. Check network connectivity to registry-1.docker.io. 2. Configure Docker daemon mirror/proxy. 3. Pre-pull base images with `docker pull python:3.11-slim`.

**Files/Components:** Docker build process, registry connectivity

### Missing Docker Images

**Severity:** HIGH
**Affected runs (1):** 'dataset-mixed-perimeter-identity_run03'

**Description:** Docker cannot find required images. Containers fail to start or are restarting, preventing CORE topology instantiation.

**Fix Action:** Pull all missing images listed per-run: `docker pull <image>`. Verify with `docker images | grep <image>`.

**Files/Components:** Docker image registry, compose file references

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
[remote] flow.artifacts.regenerate failed details: assignment 6 (dep_api_key_admin_endpoint) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 2. dataset-mixed-perimeter-identity_run03

- **Timestamp:** `2026-08-06T15:00:24.191059`
- **Seed:** `1643630141`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** container_restarting=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
time="2026-08-06T14:58:19-06:00" level=warning msg="No services to build"
2026-08-06 14:59:21,645 WARNING scenarioforge.builders.topology - [docker-node] preflight detected unhealthy container state; force-recreating node=docker-8 service=docker-8 status=restarting inspect=docker-8
{"Status":"restarting","Running":true,"Paused":false,"Restarting":true,"OOMKilled":false,"Dead":false,"Pid":0,"ExitCode":2,"Error":"","StartedAt":"2026-08-06T21:00:13.855362849Z","FinishedAt":"2026-08-06T21:00:13.947140108Z"}
2026-08-06 15:00:24,169 ERROR scenarioforge.builders.topology - [docker-node] compose preflight failed node=docker-8 compose=/tmp/vulns/.compose-projects/docker-8/docker-compose.yml reason=docker preflight startup failed: container PID remained 0 (node=docker-8 compose=/tmp/vulns/.compose-projects/docker-8/docker-compose.yml service=docker-8 inspect=docker-8 rc=0). This would cause CORE to fail with /proc/0/environ.
state_rc=0 state_tail={"Status":"restarting","Running":true,"Paused":false,"Restarting":true,"OOMKilled":false,"Dead":false,"Pid":0,"ExitCode":2,"Error":"","StartedAt":"2026-08-06T21:00:13.855362849Z","FinishedAt":"2026-08-06T21:00:13.947140108Z"}
state_rc=0 state_tail={"Status":"restarting","Running":true,"Paused":false,"Restarting":true,"OOMKilled":false,"Dead":false,"Pid":0,"ExitCode":2,"Error":"","StartedAt":"2026-08-06T21:00:13.855362849Z","FinishedAt":"2026-08-06T21:00:13.947140108Z"}
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): RuntimeError: docker preflight startup failed: container PID remained 0 (node=docker-8 compose=/tmp/vulns/.compose-projects/docker-8/docker-compose.yml service=docker-8 inspect=docker-8 rc=0). This would cause CORE to fail with /proc/0/environ.". See execute.log
--- END ERROR ---
```

### 3. dataset-vuln-cache_run04

- **Timestamp:** `2026-08-06T15:20:34.987432`
- **Seed:** `1387798055`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/redis:4.0.14` | `vulhub/redis:5.0.7`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/redis:4.0.14
Error response from daemon: No such image: vulhub/redis:5.0.7
2026-08-06 15:20:34,826 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-5, docker-6
2026-08-06 15:20:34,906 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-5 skipped: no container pid
2026-08-06 15:20:34,906 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no global IPv4 address
2026-08-06 15:20:34,986 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:20:34,986 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
- 2026-08-06 15:20:34,986 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:20:34,986 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 4. dataset-artifact-name-identity_run05

- **Timestamp:** `2026-08-06T15:21:46.210463`
- **Seed:** `1232699725`
- **Error Category:** `preflight_flow_values_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 15:21:46,227 ERROR root - Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.
2026-08-06 15:21:46,227 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:21:46,227 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
- 2026-08-06 15:21:46,227 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:21:46,227 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [". See execute.log
--- END ERROR ---
```

### 5. dataset-mixed-application-mesh_run04

- **Timestamp:** `2026-08-06T15:31:35.789633`
- **Seed:** `1593105510`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `nginx:1` | `php:7.2.10-fpm` | `vulhub/php:5.6.38-apache` | `vulhub/spring-webmvc:5.3.17`

- **Flags:** container_restarting=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/php:5.6.38-apache
Error response from daemon: No such image: vulhub/spring-webmvc:5.3.17
Error response from daemon: No such image: nginx:1
Error response from daemon: No such image: php:7.2.10-fpm
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
2026-08-06 15:29:32,280 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-15 container=docker-15
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
Error response from daemon: Container cfac2408458116a5bb6b6244dd8da4d2f99d2246d03ad19aba794fbaca9e768c is restarting, wait until the container is running
2026-08-06 15:29:32,545 WARNING scenarioforge.builders.topology - [docker-node] busybox `ip` injection did not take node=docker-15 container=docker-15
2026-08-06 15:31:35,401 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-10, docker-11, docker-12, docker-13, docker-14, docker-15
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-10 skipped: no global IPv4 address
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-11 skipped: no global IPv4 address
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-12 skipped: no global IPv4 address
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-13 skipped: no global IPv4 address
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-14 skipped: no global IPv4 address
2026-08-06 15:31:35,551 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-15 skipped: no global IPv4 address
2026-08-06 15:31:35,803 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-12, docker-13, docker-14, docker-15. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:31:35,803 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-12, docker-13, docker-14, docker-15. The containers are running but the scenario is not deployed.
- 2026-08-06 15:31:35,803 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-12, docker-13, docker-14, docker-15. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 15:31:35,803 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-12, docker-13, docker-14, docker-15. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 6. dataset-segmented-enterprise-pivots_run04

- **Timestamp:** `2026-08-06T15:40:50.875096`
- **Seed:** `317229950`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 7 (encoded_base64_dispatch) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 7. dataset-artifact-data-stores_run03

- **Timestamp:** `2026-08-06T15:48:30.093101`
- **Seed:** `1839815312`
- **Error Category:** `docker_build_timeout`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `docker-10conf-docker-10:latest`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
#2 ERROR: failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim": net/http: timeout awaiting response headers
ERROR: failed to build: failed to solve: DeadlineExceeded: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim: failed to do request: Head "https://registry-1.docker.io/v2/library/python/manifests/3.11-slim": net/http: timeout awaiting response headers
service:docker-10:1 Error response from daemon: No such image: docker-10conf-docker-10:latest
Error response from daemon: No such image: docker-10conf-docker-10:latest
2026-08-06 15:48:29,579 ERROR scenarioforge.builders.topology - [docker-node] compose preflight failed node=docker-10 compose=/tmp/vulns/.compose-projects/docker-10/docker-compose.yml reason=docker compose up -d failed (node=docker-10 compose=/tmp/vulns/.compose-projects/docker-10/docker-compose.yml svc=docker-10 helpers=['inject_copy'] rc=1)
service:docker-10:1 Error response from daemon: No such image: docker-10conf-docker-10:latest
Error response from daemon: No such image: docker-10conf-docker-10:latest
service:docker-10:1 Error response from daemon: No such image: docker-10conf-docker-10:latest
Error response from daemon: No such image: docker-10conf-docker-10:latest
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): Error response from daemon: No such image: docker-10conf-docker-10:latest
- Error response from daemon: No such image: docker-10conf-docker-10:latest
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): Error response from daemon: No such image: docker-10conf-docker-10:latest". See execute.log
--- END ERROR ---
```

### 8. dataset-catalog-coverage-042

- **Timestamp:** `2026-08-06T16:00:50.291201`
- **Seed:** `1206731851`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 1 (encoded_base64_dispatch) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}; assignment 2 (140) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 9. dataset-mixed-enterprise-data_run05

- **Timestamp:** `2026-08-06T16:13:31.100528`
- **Seed:** `221472014`
- **Error Category:** `preflight_flow_values_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 16:13:31,123 ERROR root - Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.
2026-08-06 16:13:31,123 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:13:31,123 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
- 2026-08-06 16:13:31,123 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:13:31,123 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [". See execute.log
--- END ERROR ---
```

### 10. dataset-vuln-cache_run02

- **Timestamp:** `2026-08-06T16:17:45.863575`
- **Seed:** `1448403034`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/redis:4.0.14` | `vulhub/redis:5.0.7`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/redis:4.0.14
Error response from daemon: No such image: vulhub/redis:5.0.7
2026-08-06 16:17:45,580 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-5, docker-6
2026-08-06 16:17:45,670 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-5 skipped: no container pid
2026-08-06 16:17:45,670 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no global IPv4 address
2026-08-06 16:17:45,760 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:17:45,760 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
- 2026-08-06 16:17:45,760 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:17:45,760 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-6. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 11. dataset-scale-segmented-combined_run02

- **Timestamp:** `2026-08-06T16:18:40.160211`
- **Seed:** `1633263912`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 3 (115) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 12. dataset-mixed-shared-data_run01

- **Timestamp:** `2026-08-06T16:25:53.509264`
- **Seed:** `132732739`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `redis:latest` | `vulhub/celery:3.1.23` | `vulhub/redis:5.0.7`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: redis:latest
Error response from daemon: No such image: vulhub/celery:3.1.23
Error response from daemon: No such image: vulhub/redis:5.0.7
2026-08-06 16:25:52,775 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-10, docker-11, docker-12, docker-13, docker-8, docker-9
2026-08-06 16:25:53,009 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 16:25:53,233 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-8. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:25:53,233 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-8. The containers are running but the scenario is not deployed.
- 2026-08-06 16:25:53,233 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-8. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:25:53,233 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-8. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 13. dataset-mixed-perimeter-identity_run05

- **Timestamp:** `2026-08-06T16:30:39.073026`
- **Seed:** `1512455784`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `nginx:1` | `php:7.1-fpm` | `vulhub/nginx:1.4.2`

- **Flags:** container_restarting=yes, oci_runtime_error=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: nginx:1
Error response from daemon: No such image: php:7.1-fpm
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
2026-08-06 16:28:04,745 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-9 container=docker-9
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
OCI runtime exec failed: exec failed: unable to start container process: error adding pid 581396 to cgroups: failed to write 581396: openat2 /sys/fs/cgroup/system.slice/docker-c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942.scope (deleted)/cgroup.procs: no such file or directory
Error response from daemon: Container c65197fb40fd59428a57ccf95430b688c3691076dcacb11efdc05c1d400f3942 is restarting, wait until the container is running
2026-08-06 16:28:04,892 WARNING scenarioforge.builders.topology - [docker-node] busybox `ip` injection did not take node=docker-9 container=docker-9
Error response from daemon: No such image: vulhub/nginx:1.4.2
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
2026-08-06 16:28:35,044 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-10 container=docker-10
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
Error response from daemon: Container 684ed600b18e90faec38aeeea8aeb89ae525800220425c41f2d151de18f17510 is restarting, wait until the container is running
2026-08-06 16:28:35,235 WARNING scenarioforge.builders.topology - [docker-node] busybox `ip` injection did not take node=docker-10 container=docker-10
2026-08-06 16:30:38,649 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-10, docker-7, docker-8, docker-9
2026-08-06 16:30:38,776 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-10 skipped: no global IPv4 address
2026-08-06 16:30:38,776 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-7 skipped: no global IPv4 address
2026-08-06 16:30:38,776 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 16:30:38,776 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
2026-08-06 16:30:38,936 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:30:38,936 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
- 2026-08-06 16:30:38,936 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:30:38,936 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-10, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 14. dataset-vuln-collaboration_run02

- **Timestamp:** `2026-08-06T16:31:44.063600`
- **Seed:** `2065263167`
- **Error Category:** `preflight_flow_values_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 16:31:43,966 ERROR root - Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.
2026-08-06 16:31:43,966 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:31:43,966 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
- 2026-08-06 16:31:43,966 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 16:31:43,966 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [". See execute.log
--- END ERROR ---
```

---

## Runs with Docker Image Warnings (Validation Passed)

These runs completed but reported missing Docker images. Scenarios may be incomplete.

- **dataset-catalog-coverage-071**: vulhub/vite:6.2.2, vulhub/weblogic:10.3.6.0-2017
- **dataset-segmented-firewall-pivot_run01**: vulhub/drupal:7.57, vulhub/drupal:8.5.0
- **dataset-segmented-mixed-perimeter_run05**: vulhub/nginx:1.13.2, vulhub/nginx:1.4.2, vulhub/php:5.6-fpm
- **dataset-mixed-collaboration-messaging_run05**: postgres:12.8-alpine, postgres:15.4-alpine, vulhub/confluence:7.13.6, vulhub/confluence:8.5.1
- **dataset-vuln-collaboration_run04**: vulhub/confluence:7.4.10, vulhub/confluence:8.5.1, vulhub/confluence:8.5.3
- **dataset-mixed-cms-remote-access_run03**: vulhub/drupal:7.57, vulhub/drupal:8.3.0
- **dataset-catalog-coverage-065**: vulhub/spring-cloud-function:3.2.2, vulhub/superset:2.0.1
- **dataset-catalog-coverage-044**: vulhub/nacos:1.4.0, vulhub/neo4j:3.4.18, vulhub/nextjs:15.2.2
- **dataset-mixed-enterprise-data_run03**: vulhub/struts2:2.3.28, vulhub/struts2:2.3.30
- **dataset-vuln-search-data_run03**: vulhub/elasticsearch:1.1.1, vulhub/elasticsearch:1.4.2
- **dataset-catalog-coverage-050**: vulhub/openssl:1.1.1m-with-curl, vulhub/opentsdb:2.4.0, vulhub/opentsdb:2.4.1
- **dataset-catalog-coverage-006**: vulhub/appweb:7.0.1, vulhub/aria2:1.18.8, vulhub/bash:4.3.0-with-httpd
- **dataset-catalog-coverage-012**: mysql:8.4, vulhub/craftcms:5.5.1.1, vulhub/cups-browsed:2.0.1, vulhub/discuz:7.2
- **dataset-vuln-devops_run05**: vulhub/jenkins:2.441
- **dataset-catalog-coverage-068**: vulhub/tomcat:9.0.30
- **dataset-catalog-coverage-033**: vulhub/jetty:9.4.40, vulhub/jimureport:1.6.0
- **dataset-catalog-coverage-049**: vulhub/opensmtpd:6.6.1p1, vulhub/openssl:1.0.1c-with-nginx
- **dataset-catalog-coverage-027**: vulhub/tomcat:8.5.19
- **dataset-catalog-coverage-038**: vulhub/langflow:1.2.0, vulhub/laravel:8.4.2, vulhub/librsvg:2.50.7-php
- **dataset-catalog-coverage-056**: vulhub/nextjs:15.5.6, vulhub/rails:5.0.7
- **dataset-vuln-search-data_run05**: vulhub/elasticsearch:1.4.2
- **dataset-mixed-collaboration-messaging_run03**: vulhub/confluence:8.5.3
- **dataset-segmented-mixed-perimeter_run03**: vulhub/nginx:1, vulhub/nginx:1.13.2

---

## Prioritized Fix List

| Priority | Issue | Runs Fixed |
|----------|-------|------------|
| CRITICAL | Install `scenarioforge` on CORE VM | scale-segmented-combined_run02, run04, catalog-coverage-042 |
| CRITICAL | Fix pre-generated Flow values in XML | artifact-name-identity_run05, mixed-enterprise-data_run05, vuln-collaboration_run02 |
| HIGH | Fix docker-8 container restart loop (PID 0) | mixed-perimeter-identity_run03 |
| HIGH | Pull missing Docker images + fix CORE session config | vuln-cache_run02, run04, mixed-application-mesh_run04, mixed-perimeter-identity_run05 |
| HIGH | Fix OCI runtime / cgroup corruption | mixed-perimeter-identity_run05 |
| MEDIUM | Fix Docker build timeout (python:3.11-slim) | artifact-data-stores_run03 |
| LOW | Pull all missing Docker images for warning-only runs | 22 runs listed above |
