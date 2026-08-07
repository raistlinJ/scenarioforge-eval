# TODO: Fix Failing Dataset Runs

> **Generated from:** `/private/tmp/dataset/combined-latest.errors`
> **Date:** 2026-08-06
> **Purpose:** Structured error reports for LLM-assisted fixing

---

## Summary

- **155 runs** failed with hard errors (execution/validation failures)
- **59 runs** had warnings (missing Docker images) but validation passed
- **9 error categories** identified

---

## Error Categories (Grouped by Root Cause)

### ScenarioForge Module Missing on CORE VM

**Severity:** CRITICAL
**Affected runs (6):** 'dataset-scale-segmented-combined_run04', 'dataset-segmented-enterprise-pivots_run04', 'dataset-catalog-coverage-042', 'dataset-scale-segmented-combined_run02', 'dataset-mixed-collaboration-messaging_run04', 'dataset-segmented-enterprise-pivots_run05'

**Description:** The remote CORE VM lacks the `scenarioforge` Python module. Flow artifact regeneration fails with `ModuleNotFoundError`, preventing VALIDATION_SUMMARY_JSON emission. Error: 'Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator'.

**Fix Action:** Install `scenarioforge` on the CORE VM. Run `python3 -c 'import scenarioforge'` to verify. Check PYTHONPATH and virtualenv config on the remote machine.

**Files/Components:** scenarioforge_eval/executor.py line 2070

### Missing Pre-generated Flow Values in XML

**Severity:** CRITICAL
**Affected runs (5):** 'dataset-artifact-name-identity_run05', 'dataset-mixed-enterprise-data_run05', 'dataset-vuln-collaboration_run02', 'dataset-mixed-application-mesh_run02', 'dataset-scale-segmented-combined_run05'

**Description:** The scenario XML lacks pre-generated Flow values. The executor requires `Generate (resolve)` before `Execute` to populate resolved flow data. Error: 'Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.'

**Fix Action:** 1. Run the Generate/Resolve step on the scenario XML before Execute. 2. Ensure `scenarioforge.cli generate` was run. 3. Verify the XML was saved with resolved values.

**Files/Components:** scenarioforge_eval/executor.py (preflight check)

### CORE Session Stuck in 'configuration' State

**Severity:** HIGH
**Affected runs (13):** 'dataset-vuln-cache_run04', 'dataset-mixed-application-mesh_run04', 'dataset-vuln-cache_run02', 'dataset-mixed-shared-data_run01', 'dataset-mixed-perimeter-identity_run05', 'dataset-segmented-mixed-perimeter_run04', 'dataset-vuln-cache_run05', 'dataset-catalog-coverage-045', 'dataset-catalog-coverage-057', 'dataset-mixed-perimeter-identity_run04', 'dataset-catalog-coverage-076', 'dataset-catalog-coverage-034', 'dataset-catalog-coverage-015'

**Description:** The CORE session stays in 'configuration' state, never instantiating the topology. No interface/address attached to docker nodes. Causes: missing Docker images, containers failing to start, or restarting loops.

**Fix Action:** 1. Pull all missing Docker images (listed per-run). 2. Run `docker-compose up -d` per node and verify 'running' state. 3. Check docker-compose.yml for syntax errors.

**Files/Components:** core session startup, docker-compose validation

### Docker Build Timeout (DeadlineExceeded)

**Severity:** MEDIUM
**Affected runs (2):** 'dataset-artifact-data-stores_run03', 'dataset-scale-segmented-combined_run03'

**Description:** Docker build timed out fetching base image from Docker Hub. Error: 'failed to solve: DeadlineExceeded: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim' and 'net/http: timeout awaiting response headers'.

**Fix Action:** 1. Check network connectivity to registry-1.docker.io. 2. Configure Docker daemon mirror/proxy. 3. Pre-pull base images with `docker pull python:3.11-slim`.

**Files/Components:** Docker build process, registry connectivity

### Missing Docker Images

**Severity:** HIGH
**Affected runs (107):** 'dataset-mixed-perimeter-identity_run03', 'dataset-segmented-enterprise-pivots_run02', 'dataset-scale-multi-vulnerability_run01', 'dataset-mixed-perimeter-identity_run02', 'dataset-vuln-search-data_run04', 'dataset-vuln-cache_run03', 'dataset-vuln-perimeter_run01', 'dataset-artifact-data-stores_run02', 'dataset-catalog-coverage-043', 'dataset-segmented-mixed-perimeter_run02', 'dataset-catalog-coverage-001', 'dataset-artifact-name-identity_run02', 'dataset-catalog-coverage-046', 'dataset-vuln-perimeter_run04', 'dataset-mixed-enterprise-data_run01', 'dataset-mixed-ci-supply-chain_run04', 'dataset-catalog-coverage-052', 'dataset-vuln-search-data_run01', 'dataset-artifact-dependency_run04', 'dataset-catalog-coverage-028', 'dataset-mixed-data-caching_run04', 'dataset-segmented-firewall-pivot_run03', 'dataset-catalog-coverage-073', 'dataset-mixed-perimeter-identity_run01', 'dataset-mixed-shared-data_run05', 'dataset-scale-multi-artifact_run02', 'dataset-catalog-coverage-009', 'dataset-artifact-file-shares_run04', 'dataset-catalog-coverage-067', 'dataset-mixed-cms-remote-access_run01', 'dataset-mixed-web-exploit-delivery_run04', 'dataset-catalog-coverage-031', 'dataset-scale-multi-vulnerability_run05', 'dataset-catalog-coverage-025', 'dataset-segmented-nat-artifacts_run05', 'dataset-catalog-coverage-004', 'dataset-catalog-coverage-010', 'dataset-mixed-shared-data_run03', 'dataset-mixed-collaboration-messaging_run01', 'dataset-scale-multi-artifact_run04', 'dataset-segmented-mixed-perimeter_run01', 'dataset-catalog-coverage-075', 'dataset-segmented-firewall-pivot_run05', 'dataset-catalog-coverage-061', 'dataset-artifact-file-shares_run02', 'dataset-catalog-coverage-040', 'dataset-vuln-perimeter_run02', 'dataset-artifact-data-stores_run01', 'dataset-mixed-data-caching_run02', 'dataset-artifact-dependency_run02', 'dataset-catalog-coverage-054', 'dataset-mixed-ci-supply-chain_run02', 'dataset-catalog-coverage-002', 'dataset-segmented-nat-artifacts_run03', 'dataset-artifact-name-identity_run01', 'dataset-catalog-coverage-016', 'dataset-mixed-web-exploit-delivery_run02', 'dataset-catalog-coverage-037', 'dataset-catalog-coverage-023', 'dataset-catalog-coverage-059', 'dataset-scale-multi-vulnerability_run03', 'dataset-catalog-coverage-053', 'dataset-mixed-ci-supply-chain_run05', 'dataset-mixed-data-caching_run05', 'dataset-catalog-coverage-029', 'dataset-artifact-dependency_run05', 'dataset-catalog-coverage-047', 'dataset-vuln-perimeter_run05', 'dataset-artifact-file-shares_run05', 'dataset-catalog-coverage-066', 'dataset-segmented-firewall-pivot_run02', 'dataset-catalog-coverage-072', 'dataset-mixed-shared-data_run04', 'dataset-scale-multi-artifact_run03', 'dataset-catalog-coverage-008', 'dataset-scale-multi-vulnerability_run04', 'dataset-catalog-coverage-024', 'dataset-mixed-web-exploit-delivery_run05', 'dataset-catalog-coverage-030', 'dataset-catalog-coverage-011', 'dataset-catalog-coverage-005', 'dataset-segmented-nat-artifacts_run04', 'dataset-catalog-coverage-060', 'dataset-artifact-file-shares_run03', 'dataset-vuln-collaboration_run01', 'dataset-mixed-shared-data_run02', 'dataset-scale-multi-artifact_run05', 'dataset-scale-segmented-combined_run01', 'dataset-catalog-coverage-074', 'dataset-segmented-firewall-pivot_run04', 'dataset-artifact-dependency_run03', 'dataset-mixed-data-caching_run03', 'dataset-vuln-cache_run01', 'dataset-mixed-ci-supply-chain_run03', 'dataset-catalog-coverage-055', 'dataset-catalog-coverage-041', 'dataset-vuln-perimeter_run03', 'dataset-mixed-application-mesh_run01', 'dataset-catalog-coverage-017', 'dataset-segmented-nat-artifacts_run02', 'dataset-catalog-coverage-003', 'dataset-catalog-coverage-022', 'dataset-segmented-enterprise-pivots_run01', 'dataset-catalog-coverage-058', 'dataset-scale-multi-vulnerability_run02', 'dataset-mixed-web-exploit-delivery_run03', 'dataset-catalog-coverage-036'

**Description:** Docker cannot find required images. Containers fail to start or are restarting, preventing CORE topology instantiation.

**Fix Action:** Pull all missing images listed per-run: `docker pull <image>`. Verify with `docker images | grep <image>`.

**Files/Components:** Docker image registry, compose file references

### Remote DISK FULL / No Space Left on Device

**Severity:** CRITICAL
**Affected runs (22):** 'dataset-artifact-web-delivery_run01', 'dataset-vuln-collaboration_run03', 'dataset-mixed-application-mesh_run03', 'dataset-artifact-messaging_run03', 'dataset-artifact-web-delivery_run04', 'dataset-artifact-remote-access_run02', 'dataset-vuln-cms_run05', 'dataset-vuln-web-frameworks_run02', 'dataset-artifact-web-delivery_run02', 'dataset-vuln-web-frameworks_run04', 'dataset-vuln-devops_run01', 'dataset-vuln-cms_run03', 'dataset-artifact-remote-access_run04', 'dataset-artifact-web-delivery_run05', 'dataset-artifact-remote-access_run03', 'dataset-vuln-cms_run04', 'dataset-vuln-web-frameworks_run03', 'dataset-artifact-web-delivery_run03', 'dataset-vuln-web-frameworks_run05', 'dataset-vuln-cms_run02', 'dataset-artifact-messaging_run01', 'dataset-artifact-remote-access_run05'

**Description:** The CORE VM has run out of disk space during remote execution. Failures include: 'No space left on device' errors when uploading custom services (CoreTGPrereqs.py), and upload attempts failing due to insufficient space.

**Fix Action:** 1. SSH into the CORE VM and free disk space: `df -h` to check, `du -sh /* | sort -rh` to find large dirs. 2. Clean up old Docker images/containers: `docker system prune -a`. 3. Clean up old logs: `journalctl --vacuum-size=100M`. 4. Remove unused data directories in /tmp/. 5. Verify space is freed before re-running.

**Files/Components:** CORE VM disk, /opt/core, /tmp/coretg_custom_services

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

### 15. dataset-segmented-enterprise-pivots_run02

- **Timestamp:** `2026-08-06T17:06:29.940260`
- **Seed:** `779418175`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `N/A`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    if chain_ids:
--- END ERROR ---
```

### 16. dataset-scale-multi-vulnerability_run01

- **Timestamp:** `2026-08-06T17:40:03.558033`
- **Seed:** `73467217`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `N/A`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2033, in run
    },
--- END ERROR ---
```

### 17. dataset-mixed-application-mesh_run02

- **Timestamp:** `2026-08-06T17:51:46.387805`
- **Seed:** `577196621`
- **Error Category:** `preflight_flow_values_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 17:51:46,329 ERROR root - Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.
2026-08-06 17:51:46,329 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 17:51:46,329 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
- 2026-08-06 17:51:46,329 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 17:51:46,329 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [". See execute.log
--- END ERROR ---
```

### 18. dataset-segmented-mixed-perimeter_run04

- **Timestamp:** `2026-08-06T18:02:16.003002`
- **Seed:** `1621377830`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `nginx:1`

- **Flags:** container_restarting=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: nginx:1
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
2026-08-06 18:00:13,909 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-11 container=docker-11
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
Error response from daemon: Container 2644ea0ece1a7d27fd9345c3ce33fbb13f675ee4aaedcc155d904c9a1be5b469 is restarting, wait until the container is running
2026-08-06 18:00:14,117 WARNING scenarioforge.builders.topology - [docker-node] busybox `ip` injection did not take node=docker-11 container=docker-11
2026-08-06 18:02:15,663 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-10, docker-11, docker-9
2026-08-06 18:02:15,770 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-10 skipped: no global IPv4 address
2026-08-06 18:02:15,770 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-11 skipped: no global IPv4 address
2026-08-06 18:02:15,770 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
2026-08-06 18:02:15,874 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-9. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:02:15,874 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-9. The containers are running but the scenario is not deployed.
- 2026-08-06 18:02:15,874 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-9. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:02:15,874 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-10, docker-11, docker-9. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 19. dataset-scale-segmented-combined_run05

- **Timestamp:** `2026-08-06T18:05:21.861495`
- **Seed:** `1480456867`
- **Error Category:** `preflight_flow_values_missing`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 18:05:21,764 ERROR root - Execute requires pre-generated Flow values saved in the XML. Run Generate (resolve) and save the XML before executing via CLI.
2026-08-06 18:05:21,764 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:05:21,764 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
- 2026-08-06 18:05:21,764 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:05:21,764 ERROR root - FLOW_EXECUTE_PREFLIGHT_DETAILS: [". See execute.log
--- END ERROR ---
```

### 20. dataset-mixed-perimeter-identity_run02

- **Timestamp:** `2026-08-06T18:05:25.274967`
- **Seed:** `1776123926`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Flow validation failed before generator execution: missing flag assignments; eligible_flag_generators=59; eligible_flag_node_generators=87; chain_nodes=5; chain_vuln_nodes=2; chain_docker_nodes=5. See /private/tmp/dataset/dataset-mixed-perimeter-identity_run02/flag-sequencing.json
--- END ERROR ---
```

### 21. dataset-mixed-collaboration-messaging_run04

- **Timestamp:** `2026-08-06T18:09:26.832272`
- **Seed:** `403392529`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 5 (142) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 22. dataset-vuln-cache_run05

- **Timestamp:** `2026-08-06T18:19:34.188072`
- **Seed:** `978861260`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `redis:latest` | `vulhub/redis:4.0.14`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: redis:latest
Error response from daemon: No such image: vulhub/redis:4.0.14
2026-08-06 18:19:34,060 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-5, docker-6
2026-08-06 18:19:34,135 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-5 skipped: no global IPv4 address
2026-08-06 18:19:34,135 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no container pid
2026-08-06 18:19:34,195 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-5. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:19:34,195 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-5. The containers are running but the scenario is not deployed.
- 2026-08-06 18:19:34,195 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-5. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:19:34,195 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-5. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 23. dataset-catalog-coverage-045

- **Timestamp:** `2026-08-06T18:25:33.987477`
- **Seed:** `1977551506`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/nexus:3.14.0` | `vulhub/nexus:3.21.1`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/nexus:3.21.1
time="2026-08-06T18:23:05-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:05-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:06-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
2026-08-06 18:23:06,080 INFO scenarioforge.builders.topology - [docker-node] preflight cmd=sudo -S -p  docker inspect --format {{.State.ExitCode}} {{.State.Status}} time="2026-08-06T18:23:06-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string." rc=1
error: no such object: time="2026-08-06T18:23:06-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:06-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
Error response from daemon: No such image: vulhub/nexus:3.21.1
time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
2026-08-06 18:23:07,554 INFO scenarioforge.builders.topology - [docker-node] preflight cmd=sudo -S -p  docker inspect --format {{.State.ExitCode}} {{.State.Status}} time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string." rc=1
error: no such object: time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:07-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
Error response from daemon: No such image: vulhub/nexus:3.14.0
time="2026-08-06T18:23:31-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:31-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:32-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
2026-08-06 18:23:32,058 INFO scenarioforge.builders.topology - [docker-node] preflight cmd=sudo -S -p  docker inspect --format {{.State.ExitCode}} {{.State.Status}} time="2026-08-06T18:23:32-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string." rc=1
error: no such object: time="2026-08-06T18:23:32-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
time="2026-08-06T18:23:32-06:00" level=warning msg="The \"SONATYPE_DIR\" variable is not set. Defaulting to a blank string."
2026-08-06 18:25:33,749 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-10, docker-11, docker-8, docker-9
2026-08-06 18:25:33,856 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-10 skipped: no global IPv4 address
2026-08-06 18:25:33,856 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-11 skipped: no container pid
2026-08-06 18:25:33,856 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no container pid
2026-08-06 18:25:33,856 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no container pid
2026-08-06 18:25:33,938 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:25:33,938 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10. The containers are running but the scenario is not deployed.
- 2026-08-06 18:25:33,938 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-10. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 18:25:33,938 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-10. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 24. dataset-segmented-enterprise-pivots_run05

- **Timestamp:** `2026-08-06T18:41:36.917581`
- **Seed:** `762270678`
- **Error Category:** `scenarioforge_module_missing`
- **Exit Code:** `1`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
[remote] flow.artifacts.regenerate failed details: assignment 7 (nfs_backup_archive_passphrase) regenerate failed: {"ok": false, "error": "No module named 'scenarioforge'", "traceback": "Traceback (most recent call last):\n File \"<stdin>\", line 36, in <module>\nModuleNotFoundError: No module named 'scenarioforge'\n"}
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1 and did not emit VALIDATION_SUMMARY_JSON. Last output: RuntimeError: Challenges and Flow Data not found on CORE VM. Please re-run Flow Generator... See execute.log
--- END ERROR ---
```

### 25. dataset-catalog-coverage-057

- **Timestamp:** `2026-08-06T19:02:47.780068`
- **Seed:** `804812691`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `mongo:4.0` | `vulhub/rocketchat:3.12.1`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/rocketchat:3.12.1
Error response from daemon: No such image: mongo:4.0
2026-08-06 19:00:20,619 WARNING scenarioforge.builders.topology - [vuln-node] compose services unavailable node=docker-6 requested=docker-6; keeping requested compose_name
2026-08-06 19:02:44,286 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-6, docker-7, docker-8, docker-9
2026-08-06 19:02:46,360 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no global IPv4 address
2026-08-06 19:02:46,360 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-7 skipped: no global IPv4 address
2026-08-06 19:02:46,360 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 19:02:46,360 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
2026-08-06 19:02:47,330 ERROR root - Failed to write scenario summary JSON
2026-08-06 19:02:47,433 ERROR root - Failed to rewrite scenario report with runtime status
2026-08-06 19:02:47,456 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:02:47,456 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
- 2026-08-06 19:02:47,456 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:02:47,456 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 26. dataset-vuln-search-data_run04

- **Timestamp:** `2026-08-06T19:03:05.381501`
- **Seed:** `2122640470`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2700691. See /private/tmp/dataset/dataset-vuln-search-data_run04/flag-sequencing.json
--- END ERROR ---
```

### 27. dataset-vuln-cache_run03

- **Timestamp:** `2026-08-06T19:03:18.960127`
- **Seed:** `1583156706`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2707600. See /private/tmp/dataset/dataset-vuln-cache_run03/flag-sequencing.json
--- END ERROR ---
```

### 28. dataset-vuln-perimeter_run01

- **Timestamp:** `2026-08-06T19:03:32.357097`
- **Seed:** `76073265`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2701636. See /private/tmp/dataset/dataset-vuln-perimeter_run01/flag-sequencing.json
--- END ERROR ---
```

### 29. dataset-artifact-data-stores_run02

- **Timestamp:** `2026-08-06T19:03:45.686075`
- **Seed:** `1886165012`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2785614. See /private/tmp/dataset/dataset-artifact-data-stores_run02/flag-sequencing.json
--- END ERROR ---
```

### 30. dataset-catalog-coverage-043

- **Timestamp:** `2026-08-06T19:03:58.898002`
- **Seed:** `522020398`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2725405. See /private/tmp/dataset/dataset-catalog-coverage-043/flag-sequencing.json
--- END ERROR ---
```

### 31. dataset-artifact-web-delivery_run01

- **Timestamp:** `2026-08-06T19:04:02.723106`
- **Seed:** `162275504`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 32. dataset-scale-segmented-combined_run03

- **Timestamp:** `2026-08-06T19:16:59.664256`
- **Seed:** `1775968854`
- **Error Category:** `docker_build_timeout`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/struts2:2.3.28`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
1 warning found (use docker --debug to expand):
ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head "https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable
Error response from daemon: No such image: vulhub/struts2:2.3.28
2026-08-06 19:16:59,435 ERROR scenarioforge.builders.topology - [docker-node] compose preflight failed node=docker-14 compose=/tmp/vulns/.compose-projects/docker-14/docker-compose.yml reason=docker wrapper image build failed; refusing to use an existing/stale local image
ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head "https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable
ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head "https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head "https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable
- ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head "https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): ERROR: failed to build: failed to solve: vulhub/struts2:2.3.28: failed to resolve source metadata for docker.io/vulhub/struts2:2.3.28: failed to do request: Head \"https://registry-1.docker.io/v2/vulhub/struts2/manifests/2.3.28\": dial tcp [2600:1f18:2148:bc00:6642:59a6:2d64:33d1]:443: connect: network is unreachable". See execute.log
--- END ERROR ---
```

### 33. dataset-vuln-collaboration_run03

- **Timestamp:** `2026-08-06T19:22:47.443250`
- **Seed:** `1899008699`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/confluence:6.10.2` | `vulhub/confluence:7.13.6` | `vulhub/confluence:8.5.3`

- **Flags:** disk_full=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/confluence:7.13.6
Error response from daemon: No such image: vulhub/confluence:8.5.3
Error response from daemon: No such image: vulhub/confluence:6.10.2
2026-08-06 19:22:31,520 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 19:22:31,520 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
ERROR: Validation unavailable (1)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="CORE session XML export failed because the current Python environment cannot import core.api.grpc, remote save_xml fallback failed ([Errno 28] No space left on device: '/tmp/scenarioforge/core-post'), and local CORE Python fallback failed (local CORE Python save_xml fallback failed: /opt/core/venv/python3.8/bin/python: [Errno 2] No such file or directory: '/opt/core/venv/python3.8/bin/python'; core-python: [Errno 2] No such file or directory: 'core-python'; python3: exit=1 stdout= stderr=Traceback (most recent call last): File \"<string>\", line 6, in <module> ModuleNotFoundError: No module named 'core'; python: exit=1 stdout= stderr=Traceback (most recent call last): File \"<string>\", line 6, in <module> ModuleNotFoundError: No module named 'core')". See execute.log
--- END ERROR ---
```

### 34. dataset-mixed-perimeter-identity_run04

- **Timestamp:** `2026-08-06T19:26:24.168319`
- **Seed:** `1675244378`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `nginx:1`

- **Flags:** container_restarting=yes, oci_runtime_error=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: nginx:1
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
2026-08-06 19:23:47,338 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-6 container=docker-6
OCI runtime exec failed: exec failed: unable to start container process: error writing config to pipe: write init-p: broken pipe
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
Error response from daemon: Container 60d8487d4f5515fb07b0ac0d1ea8acd0d22c491ae90dc1203ac6b3f72629e991 is restarting, wait until the container is running
2026-08-06 19:23:47,508 WARNING scenarioforge.builders.topology - [docker-node] busybox `ip` injection did not take node=docker-6 container=docker-6
2026-08-06 19:26:23,760 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-6, docker-7, docker-8, docker-9
2026-08-06 19:26:23,895 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no global IPv4 address
2026-08-06 19:26:23,895 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-7 skipped: no global IPv4 address
2026-08-06 19:26:23,895 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 19:26:23,895 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
2026-08-06 19:26:24,036 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:26:24,036 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
- 2026-08-06 19:26:24,036 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:26:24,036 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 35. dataset-catalog-coverage-076

- **Timestamp:** `2026-08-06T19:29:29.543597`
- **Seed:** `290062843`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
2026-08-06 19:29:29,167 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-11, docker-12, docker-13, docker-14
2026-08-06 19:29:29,289 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-11 skipped: no container pid
2026-08-06 19:29:29,289 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-12 skipped: no global IPv4 address
2026-08-06 19:29:29,289 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-13 skipped: no container pid
2026-08-06 19:29:29,290 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-14 skipped: no global IPv4 address
2026-08-06 19:29:29,423 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-14. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:29:29,423 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-14. The containers are running but the scenario is not deployed.
- 2026-08-06 19:29:29,423 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-14. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:29:29,423 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-12, docker-14. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 36. dataset-segmented-mixed-perimeter_run02

- **Timestamp:** `2026-08-06T19:29:39.245819`
- **Seed:** `383870187`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Flow validation failed before generator execution: 10: first chain step needs ['TOKEN'] to follow its access instructions, but its low hints never reveal them; nothing earlier in the chain can supply them either. Promote the disclosing hint to 'low' or place this generator later in the chain.. See /private/tmp/dataset/dataset-segmented-mixed-perimeter_run02/flag-sequencing.json
--- END ERROR ---
```

### 37. dataset-catalog-coverage-034

- **Timestamp:** `2026-08-06T19:40:04.367900`
- **Seed:** `175926066`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/jira:8.1.0` | `vulhub/jmeter:3.3` | `vulhub/joomla:3.4.5`

- **Flags:** container_restarting=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/jmeter:3.3
time="2026-08-06T19:36:46-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string."
time="2026-08-06T19:36:46-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string."
time="2026-08-06T19:36:47-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string."
2026-08-06 19:36:47,140 INFO scenarioforge.builders.topology - [docker-node] preflight cmd=sudo -S -p  docker inspect --format {{.State.ExitCode}} {{.State.Status}} time="2026-08-06T19:36:47-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string." rc=1
error: no such object: time="2026-08-06T19:36:47-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string."
time="2026-08-06T19:36:47-06:00" level=warning msg="The \"JMETER_VERSION\" variable is not set. Defaulting to a blank string."
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
2026-08-06 19:36:47,356 WARNING scenarioforge.builders.topology - [docker-node] container has no `ip`; injecting busybox node=docker-11 container=docker-11
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
Error response from daemon: Container 8d6500145abd1984b022b87f0f8629761feff7a55ae35ddfa0bcdc9f8fa2e7f4 is restarting, wait until the container is running
Error response from daemon: No such image: vulhub/joomla:3.4.5
Error response from daemon: No such image: vulhub/jira:8.1.0
2026-08-06 19:40:03,850 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-11, docker-12, docker-13, docker-14
2026-08-06 19:40:04,039 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-11 skipped: no container pid
2026-08-06 19:40:04,039 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-12 skipped: no global IPv4 address
2026-08-06 19:40:04,039 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-13 skipped: no global IPv4 address
2026-08-06 19:40:04,039 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-14 skipped: no global IPv4 address
2026-08-06 19:40:04,255 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-13, docker-14. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:40:04,255 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-13, docker-14. The containers are running but the scenario is not deployed.
- 2026-08-06 19:40:04,255 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-12, docker-13, docker-14. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:40:04,255 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-12, docker-13, docker-14. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 38. dataset-catalog-coverage-015

- **Timestamp:** `2026-08-06T19:46:27.410225`
- **Seed:** `1679816996`
- **Error Category:** `core_session_config_stuck`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `nginx:1` | `vulhub/electron:wine` | `vulhub/elfinder:2.1.58`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/elfinder:2.1.58
Error response from daemon: No such image: nginx:1
Error response from daemon: No such image: vulhub/electron:wine
Error response from daemon: No such image: nginx:1
2026-08-06 19:46:26,724 WARNING root - CORE session stayed in configuration; deferring failure pending docker-compose runtime validation for nodes: docker-6, docker-7, docker-8, docker-9
2026-08-06 19:46:26,998 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-6 skipped: no global IPv4 address
2026-08-06 19:46:26,998 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-7 skipped: no global IPv4 address
2026-08-06 19:46:26,998 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-8 skipped: no global IPv4 address
2026-08-06 19:46:26,998 WARNING scenarioforge.builders.topology - [docker-node] host-side default route node=docker-9 skipped: no global IPv4 address
2026-08-06 19:46:27,204 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
ERROR: Validation unavailable (2)
- remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:46:27,204 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
- 2026-08-06 19:46:27,204 ERROR root - Start validation failed: CORE session stayed in "configuration": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="remote execute failed before post-execution validation (exit code 1): 2026-08-06 19:46:27,204 ERROR root - Start validation failed: CORE session stayed in \"configuration\": it never instantiated the topology, so no interface or address was attached to docker-6, docker-7, docker-8, docker-9. The containers are running but the scenario is not deployed.". See execute.log
--- END ERROR ---
```

### 39. dataset-mixed-application-mesh_run03

- **Timestamp:** `2026-08-06T19:52:25.106403`
- **Seed:** `1132657207`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Missing Docker Images:** `vulhub/oracle:12c-ee` | `vulhub/php:8.1-backdoor` | `vulhub/spring-data-commons:2.0.5`

- **Flags:** disk_full=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
Error response from daemon: No such image: vulhub/spring-data-commons:2.0.5
Error response from daemon: No such image: vulhub/php:8.1-backdoor
1 warning found (use docker --debug to expand):
Error response from daemon: No such image: vulhub/oracle:12c-ee
ERROR: Validation unavailable (1)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="CORE session XML export failed because the current Python environment cannot import core.api.grpc, remote save_xml fallback failed ([Errno 28] No space left on device: '/tmp/scenarioforge/core-post'), and local CORE Python fallback failed (local CORE Python save_xml fallback failed: /opt/core/venv/python3.8/bin/python: [Errno 2] No such file or directory: '/opt/core/venv/python3.8/bin/python'; core-python: [Errno 2] No such file or directory: 'core-python'; python3: exit=1 stdout= stderr=Traceback (most recent call last): File \"<string>\", line 6, in <module> ModuleNotFoundError: No module named 'core'; python: exit=1 stdout= stderr=Traceback (most recent call last): File \"<string>\", line 6, in <module> ModuleNotFoundError: No module named 'core')". See execute.log
--- END ERROR ---
```

### 40. dataset-artifact-messaging_run03

- **Timestamp:** `2026-08-06T19:52:29.338247`
- **Seed:** `1469365089`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 41. dataset-catalog-coverage-001

- **Timestamp:** `2026-08-06T19:52:45.216106`
- **Seed:** `470197998`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2740139. See /private/tmp/dataset/dataset-catalog-coverage-001/flag-sequencing.json
--- END ERROR ---
```

### 42. dataset-artifact-name-identity_run02

- **Timestamp:** `2026-08-06T19:52:58.180013`
- **Seed:** `690285459`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2747090. See /private/tmp/dataset/dataset-artifact-name-identity_run02/flag-sequencing.json
--- END ERROR ---
```

### 43. dataset-catalog-coverage-046

- **Timestamp:** `2026-08-06T19:53:10.847151`
- **Seed:** `1541209449`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2732660. See /private/tmp/dataset/dataset-catalog-coverage-046/flag-sequencing.json
--- END ERROR ---
```

### 44. dataset-artifact-web-delivery_run04

- **Timestamp:** `2026-08-06T19:53:14.907048`
- **Seed:** `1186340165`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 45. dataset-vuln-perimeter_run04

- **Timestamp:** `2026-08-06T19:53:27.616633`
- **Seed:** `1339080804`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2684374. See /private/tmp/dataset/dataset-vuln-perimeter_run04/flag-sequencing.json
--- END ERROR ---
```

### 46. dataset-mixed-enterprise-data_run01

- **Timestamp:** `2026-08-06T19:53:40.470081`
- **Seed:** `1373666488`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2811162. See /private/tmp/dataset/dataset-mixed-enterprise-data_run01/flag-sequencing.json
--- END ERROR ---
```

### 47. dataset-mixed-ci-supply-chain_run04

- **Timestamp:** `2026-08-06T19:53:53.485814`
- **Seed:** `1050993566`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2726110. See /private/tmp/dataset/dataset-mixed-ci-supply-chain_run04/flag-sequencing.json
--- END ERROR ---
```

### 48. dataset-catalog-coverage-052

- **Timestamp:** `2026-08-06T19:54:06.819130`
- **Seed:** `714027261`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2731468. See /private/tmp/dataset/dataset-catalog-coverage-052/flag-sequencing.json
--- END ERROR ---
```

### 49. dataset-vuln-search-data_run01

- **Timestamp:** `2026-08-06T19:54:19.836469`
- **Seed:** `1618199664`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2716354. See /private/tmp/dataset/dataset-vuln-search-data_run01/flag-sequencing.json
--- END ERROR ---
```

### 50. dataset-artifact-dependency_run04

- **Timestamp:** `2026-08-06T19:54:32.905144`
- **Seed:** `1019603164`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2709167. See /private/tmp/dataset/dataset-artifact-dependency_run04/flag-sequencing.json
--- END ERROR ---
```

### 51. dataset-catalog-coverage-028

- **Timestamp:** `2026-08-06T19:54:46.069622`
- **Seed:** `2109219025`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2735233. See /private/tmp/dataset/dataset-catalog-coverage-028/flag-sequencing.json
--- END ERROR ---
```

### 52. dataset-mixed-data-caching_run04

- **Timestamp:** `2026-08-06T19:54:59.099501`
- **Seed:** `1110581676`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2816225. See /private/tmp/dataset/dataset-mixed-data-caching_run04/flag-sequencing.json
--- END ERROR ---
```

### 53. dataset-segmented-firewall-pivot_run03

- **Timestamp:** `2026-08-06T19:55:12.277364`
- **Seed:** `351395194`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2709234. See /private/tmp/dataset/dataset-segmented-firewall-pivot_run03/flag-sequencing.json
--- END ERROR ---
```

### 54. dataset-catalog-coverage-073

- **Timestamp:** `2026-08-06T19:55:25.252358`
- **Seed:** `1710224640`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2736205. See /private/tmp/dataset/dataset-catalog-coverage-073/flag-sequencing.json
--- END ERROR ---
```

### 55. dataset-mixed-perimeter-identity_run01

- **Timestamp:** `2026-08-06T19:55:37.913531`
- **Seed:** `780556680`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2736383. See /private/tmp/dataset/dataset-mixed-perimeter-identity_run01/flag-sequencing.json
--- END ERROR ---
```

### 56. dataset-mixed-shared-data_run05

- **Timestamp:** `2026-08-06T19:55:50.557054`
- **Seed:** `435225693`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2725220. See /private/tmp/dataset/dataset-mixed-shared-data_run05/flag-sequencing.json
--- END ERROR ---
```

### 57. dataset-scale-multi-artifact_run02

- **Timestamp:** `2026-08-06T19:56:02.975447`
- **Seed:** `291352685`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2675728. See /private/tmp/dataset/dataset-scale-multi-artifact_run02/flag-sequencing.json
--- END ERROR ---
```

### 58. dataset-catalog-coverage-009

- **Timestamp:** `2026-08-06T19:56:15.523422`
- **Seed:** `1042150194`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2735184. See /private/tmp/dataset/dataset-catalog-coverage-009/flag-sequencing.json
--- END ERROR ---
```

### 59. dataset-artifact-file-shares_run04

- **Timestamp:** `2026-08-06T19:56:27.990142`
- **Seed:** `1566716896`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2766887. See /private/tmp/dataset/dataset-artifact-file-shares_run04/flag-sequencing.json
--- END ERROR ---
```

### 60. dataset-catalog-coverage-067

- **Timestamp:** `2026-08-06T19:56:40.315286`
- **Seed:** `1311808772`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2749475. See /private/tmp/dataset/dataset-catalog-coverage-067/flag-sequencing.json
--- END ERROR ---
```

### 61. dataset-mixed-cms-remote-access_run01

- **Timestamp:** `2026-08-06T19:56:52.772495`
- **Seed:** `1065658737`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2708900. See /private/tmp/dataset/dataset-mixed-cms-remote-access_run01/flag-sequencing.json
--- END ERROR ---
```

### 62. dataset-mixed-web-exploit-delivery_run04

- **Timestamp:** `2026-08-06T19:57:04.947278`
- **Seed:** `1516475353`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2715084. See /private/tmp/dataset/dataset-mixed-web-exploit-delivery_run04/flag-sequencing.json
--- END ERROR ---
```

### 63. dataset-catalog-coverage-031

- **Timestamp:** `2026-08-06T19:57:17.289631`
- **Seed:** `1943606770`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2733432. See /private/tmp/dataset/dataset-catalog-coverage-031/flag-sequencing.json
--- END ERROR ---
```

### 64. dataset-artifact-remote-access_run02

- **Timestamp:** `2026-08-06T19:57:21.265356`
- **Seed:** `138878521`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 65. dataset-scale-multi-vulnerability_run05

- **Timestamp:** `2026-08-06T19:57:34.121225`
- **Seed:** `1399182774`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2717578. See /private/tmp/dataset/dataset-scale-multi-vulnerability_run05/flag-sequencing.json
--- END ERROR ---
```

### 66. dataset-catalog-coverage-025

- **Timestamp:** `2026-08-06T19:57:46.987390`
- **Seed:** `1082664047`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2730220. See /private/tmp/dataset/dataset-catalog-coverage-025/flag-sequencing.json
--- END ERROR ---
```

### 67. dataset-segmented-nat-artifacts_run05

- **Timestamp:** `2026-08-06T19:57:59.348854`
- **Seed:** `1047448166`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2699917. See /private/tmp/dataset/dataset-segmented-nat-artifacts_run05/flag-sequencing.json
--- END ERROR ---
```

### 68. dataset-catalog-coverage-004

- **Timestamp:** `2026-08-06T19:58:12.234566`
- **Seed:** `79176491`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2740126. See /private/tmp/dataset/dataset-catalog-coverage-004/flag-sequencing.json
--- END ERROR ---
```

### 69. dataset-catalog-coverage-010

- **Timestamp:** `2026-08-06T19:58:24.598697`
- **Seed:** `1015384667`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2747621. See /private/tmp/dataset/dataset-catalog-coverage-010/flag-sequencing.json
--- END ERROR ---
```

### 70. dataset-vuln-cms_run05

- **Timestamp:** `2026-08-06T19:58:28.112828`
- **Seed:** `1456872161`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 71. dataset-vuln-web-frameworks_run02

- **Timestamp:** `2026-08-06T19:58:31.972787`
- **Seed:** `1264608295`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 72. dataset-mixed-shared-data_run03

- **Timestamp:** `2026-08-06T19:58:44.562284`
- **Seed:** `1050928609`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2744703. See /private/tmp/dataset/dataset-mixed-shared-data_run03/flag-sequencing.json
--- END ERROR ---
```

### 73. dataset-mixed-collaboration-messaging_run01

- **Timestamp:** `2026-08-06T19:58:57.221653`
- **Seed:** `1391104831`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2796874. See /private/tmp/dataset/dataset-mixed-collaboration-messaging_run01/flag-sequencing.json
--- END ERROR ---
```

### 74. dataset-scale-multi-artifact_run04

- **Timestamp:** `2026-08-06T19:59:09.824139`
- **Seed:** `1858590118`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2713839. See /private/tmp/dataset/dataset-scale-multi-artifact_run04/flag-sequencing.json
--- END ERROR ---
```

### 75. dataset-segmented-mixed-perimeter_run01

- **Timestamp:** `2026-08-06T19:59:22.425273`
- **Seed:** `588039118`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2722849. See /private/tmp/dataset/dataset-segmented-mixed-perimeter_run01/flag-sequencing.json
--- END ERROR ---
```

### 76. dataset-catalog-coverage-075

- **Timestamp:** `2026-08-06T19:59:34.971033`
- **Seed:** `534376755`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2749109. See /private/tmp/dataset/dataset-catalog-coverage-075/flag-sequencing.json
--- END ERROR ---
```

### 77. dataset-segmented-firewall-pivot_run05

- **Timestamp:** `2026-08-06T19:59:47.726648`
- **Seed:** `1035585714`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2712587. See /private/tmp/dataset/dataset-segmented-firewall-pivot_run05/flag-sequencing.json
--- END ERROR ---
```

### 78. dataset-catalog-coverage-061

- **Timestamp:** `2026-08-06T20:00:00.340590`
- **Seed:** `992812102`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-061/flag-sequencing.json
--- END ERROR ---
```

### 79. dataset-artifact-file-shares_run02

- **Timestamp:** `2026-08-06T20:00:12.741653`
- **Seed:** `770273820`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-file-shares_run02/flag-sequencing.json
--- END ERROR ---
```

### 80. dataset-artifact-web-delivery_run02

- **Timestamp:** `2026-08-06T20:00:16.620921`
- **Seed:** `538243507`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 81. dataset-catalog-coverage-040

- **Timestamp:** `2026-08-06T20:00:29.538925`
- **Seed:** `556378873`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-040/flag-sequencing.json
--- END ERROR ---
```

### 82. dataset-vuln-perimeter_run02

- **Timestamp:** `2026-08-06T20:00:42.211489`
- **Seed:** `2028110693`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2704258. See /private/tmp/dataset/dataset-vuln-perimeter_run02/flag-sequencing.json
--- END ERROR ---
```

### 83. dataset-artifact-data-stores_run01

- **Timestamp:** `2026-08-06T20:00:54.724957`
- **Seed:** `1689068700`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-data-stores_run01/flag-sequencing.json
--- END ERROR ---
```

### 84. dataset-mixed-data-caching_run02

- **Timestamp:** `2026-08-06T20:01:07.514484`
- **Seed:** `477903201`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2811660. See /private/tmp/dataset/dataset-mixed-data-caching_run02/flag-sequencing.json
--- END ERROR ---
```

### 85. dataset-artifact-dependency_run02

- **Timestamp:** `2026-08-06T20:01:20.723031`
- **Seed:** `240579627`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2709166. See /private/tmp/dataset/dataset-artifact-dependency_run02/flag-sequencing.json
--- END ERROR ---
```

### 86. dataset-catalog-coverage-054

- **Timestamp:** `2026-08-06T20:01:33.716126`
- **Seed:** `1485533443`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-054/flag-sequencing.json
--- END ERROR ---
```

### 87. dataset-mixed-ci-supply-chain_run02

- **Timestamp:** `2026-08-06T20:01:46.938748`
- **Seed:** `1404091470`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-ci-supply-chain_run02/flag-sequencing.json
--- END ERROR ---
```

### 88. dataset-catalog-coverage-002

- **Timestamp:** `2026-08-06T20:01:59.625101`
- **Seed:** `621274374`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2735302. See /private/tmp/dataset/dataset-catalog-coverage-002/flag-sequencing.json
--- END ERROR ---
```

### 89. dataset-segmented-nat-artifacts_run03

- **Timestamp:** `2026-08-06T20:02:12.089892`
- **Seed:** `2013814722`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2735670. See /private/tmp/dataset/dataset-segmented-nat-artifacts_run03/flag-sequencing.json
--- END ERROR ---
```

### 90. dataset-artifact-name-identity_run01

- **Timestamp:** `2026-08-06T20:02:24.556669`
- **Seed:** `1008910915`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-name-identity_run01/flag-sequencing.json
--- END ERROR ---
```

### 91. dataset-vuln-web-frameworks_run04

- **Timestamp:** `2026-08-06T20:02:28.438823`
- **Seed:** `844353016`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 92. dataset-vuln-devops_run01

- **Timestamp:** `2026-08-06T20:02:32.302476`
- **Seed:** `1700240743`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 93. dataset-vuln-cms_run03

- **Timestamp:** `2026-08-06T20:02:36.171974`
- **Seed:** `227311665`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 94. dataset-catalog-coverage-016

- **Timestamp:** `2026-08-06T20:02:49.129842`
- **Seed:** `749778673`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2747501. See /private/tmp/dataset/dataset-catalog-coverage-016/flag-sequencing.json
--- END ERROR ---
```

### 95. dataset-mixed-web-exploit-delivery_run02

- **Timestamp:** `2026-08-06T20:03:01.641068`
- **Seed:** `1221762782`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2714987. See /private/tmp/dataset/dataset-mixed-web-exploit-delivery_run02/flag-sequencing.json
--- END ERROR ---
```

### 96. dataset-catalog-coverage-037

- **Timestamp:** `2026-08-06T20:03:14.300080`
- **Seed:** `661817696`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2721748. See /private/tmp/dataset/dataset-catalog-coverage-037/flag-sequencing.json
--- END ERROR ---
```

### 97. dataset-catalog-coverage-023

- **Timestamp:** `2026-08-06T20:03:26.619469`
- **Seed:** `1605424124`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2754063. See /private/tmp/dataset/dataset-catalog-coverage-023/flag-sequencing.json
--- END ERROR ---
```

### 98. dataset-artifact-remote-access_run04

- **Timestamp:** `2026-08-06T20:03:30.546608`
- **Seed:** `1032438899`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 99. dataset-catalog-coverage-059

- **Timestamp:** `2026-08-06T20:03:42.966724`
- **Seed:** `810559406`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2726229. See /private/tmp/dataset/dataset-catalog-coverage-059/flag-sequencing.json
--- END ERROR ---
```

### 100. dataset-scale-multi-vulnerability_run03

- **Timestamp:** `2026-08-06T20:03:55.727639`
- **Seed:** `391276166`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2730221. See /private/tmp/dataset/dataset-scale-multi-vulnerability_run03/flag-sequencing.json
--- END ERROR ---
```

### 101. dataset-catalog-coverage-053

- **Timestamp:** `2026-08-06T20:04:08.584281`
- **Seed:** `178800699`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2749319. See /private/tmp/dataset/dataset-catalog-coverage-053/flag-sequencing.json
--- END ERROR ---
```

### 102. dataset-mixed-ci-supply-chain_run05

- **Timestamp:** `2026-08-06T20:04:20.939219`
- **Seed:** `601539727`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-ci-supply-chain_run05/flag-sequencing.json
--- END ERROR ---
```

### 103. dataset-mixed-data-caching_run05

- **Timestamp:** `2026-08-06T20:04:33.363660`
- **Seed:** `440728127`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-data-caching_run05/flag-sequencing.json
--- END ERROR ---
```

### 104. dataset-catalog-coverage-029

- **Timestamp:** `2026-08-06T20:04:46.170775`
- **Seed:** `2054058190`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-029/flag-sequencing.json
--- END ERROR ---
```

### 105. dataset-artifact-dependency_run05

- **Timestamp:** `2026-08-06T20:04:58.554479`
- **Seed:** `91873073`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-dependency_run05/flag-sequencing.json
--- END ERROR ---
```

### 106. dataset-artifact-web-delivery_run05

- **Timestamp:** `2026-08-06T20:05:02.470751`
- **Seed:** `329150020`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 107. dataset-catalog-coverage-047

- **Timestamp:** `2026-08-06T20:05:15.059831`
- **Seed:** `1297765867`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2730218. See /private/tmp/dataset/dataset-catalog-coverage-047/flag-sequencing.json
--- END ERROR ---
```

### 108. dataset-vuln-perimeter_run05

- **Timestamp:** `2026-08-06T20:05:27.746588`
- **Seed:** `1346152827`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2697294. See /private/tmp/dataset/dataset-vuln-perimeter_run05/flag-sequencing.json
--- END ERROR ---
```

### 109. dataset-artifact-file-shares_run05

- **Timestamp:** `2026-08-06T20:05:40.424775`
- **Seed:** `1837198052`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2710401. See /private/tmp/dataset/dataset-artifact-file-shares_run05/flag-sequencing.json
--- END ERROR ---
```

### 110. dataset-catalog-coverage-066

- **Timestamp:** `2026-08-06T20:05:53.213676`
- **Seed:** `447003867`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2719065. See /private/tmp/dataset/dataset-catalog-coverage-066/flag-sequencing.json
--- END ERROR ---
```

### 111. dataset-segmented-firewall-pivot_run02

- **Timestamp:** `2026-08-06T20:06:05.829008`
- **Seed:** `793857018`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2728720. See /private/tmp/dataset/dataset-segmented-firewall-pivot_run02/flag-sequencing.json
--- END ERROR ---
```

### 112. dataset-catalog-coverage-072

- **Timestamp:** `2026-08-06T20:06:18.571226`
- **Seed:** `587455037`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2730189. See /private/tmp/dataset/dataset-catalog-coverage-072/flag-sequencing.json
--- END ERROR ---
```

### 113. dataset-mixed-shared-data_run04

- **Timestamp:** `2026-08-06T20:06:30.990326`
- **Seed:** `1914046550`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2740555. See /private/tmp/dataset/dataset-mixed-shared-data_run04/flag-sequencing.json
--- END ERROR ---
```

### 114. dataset-scale-multi-artifact_run03

- **Timestamp:** `2026-08-06T20:06:43.567372`
- **Seed:** `179931555`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2713572. See /private/tmp/dataset/dataset-scale-multi-artifact_run03/flag-sequencing.json
--- END ERROR ---
```

### 115. dataset-catalog-coverage-008

- **Timestamp:** `2026-08-06T20:06:56.149708`
- **Seed:** `934593519`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-008/flag-sequencing.json
--- END ERROR ---
```

### 116. dataset-artifact-remote-access_run03

- **Timestamp:** `2026-08-06T20:07:00.112046`
- **Seed:** `2055485941`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 117. dataset-scale-multi-vulnerability_run04

- **Timestamp:** `2026-08-06T20:07:12.465917`
- **Seed:** `1936008423`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2725099. See /private/tmp/dataset/dataset-scale-multi-vulnerability_run04/flag-sequencing.json
--- END ERROR ---
```

### 118. dataset-catalog-coverage-024

- **Timestamp:** `2026-08-06T20:07:25.165454`
- **Seed:** `1941126199`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2731943. See /private/tmp/dataset/dataset-catalog-coverage-024/flag-sequencing.json
--- END ERROR ---
```

### 119. dataset-mixed-web-exploit-delivery_run05

- **Timestamp:** `2026-08-06T20:07:37.406900`
- **Seed:** `68344482`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-web-exploit-delivery_run05/flag-sequencing.json
--- END ERROR ---
```

### 120. dataset-catalog-coverage-030

- **Timestamp:** `2026-08-06T20:07:49.950823`
- **Seed:** `1038737727`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-030/flag-sequencing.json
--- END ERROR ---
```

### 121. dataset-vuln-cms_run04

- **Timestamp:** `2026-08-06T20:07:53.790881`
- **Seed:** `1667362400`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 122. dataset-catalog-coverage-011

- **Timestamp:** `2026-08-06T20:08:06.411495`
- **Seed:** `1006041196`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-011/flag-sequencing.json
--- END ERROR ---
```

### 123. dataset-vuln-web-frameworks_run03

- **Timestamp:** `2026-08-06T20:08:10.144038`
- **Seed:** `1103183010`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 124. dataset-catalog-coverage-005

- **Timestamp:** `2026-08-06T20:08:22.743473`
- **Seed:** `1159360653`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2719720. See /private/tmp/dataset/dataset-catalog-coverage-005/flag-sequencing.json
--- END ERROR ---
```

### 125. dataset-segmented-nat-artifacts_run04

- **Timestamp:** `2026-08-06T20:08:34.984123`
- **Seed:** `1578831621`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-segmented-nat-artifacts_run04/flag-sequencing.json
--- END ERROR ---
```

### 126. dataset-catalog-coverage-060

- **Timestamp:** `2026-08-06T20:08:47.842649`
- **Seed:** `1995305941`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2729144. See /private/tmp/dataset/dataset-catalog-coverage-060/flag-sequencing.json
--- END ERROR ---
```

### 127. dataset-artifact-file-shares_run03

- **Timestamp:** `2026-08-06T20:09:00.049941`
- **Seed:** `777788029`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-file-shares_run03/flag-sequencing.json
--- END ERROR ---
```

### 128. dataset-vuln-collaboration_run01

- **Timestamp:** `2026-08-06T20:09:12.419448`
- **Seed:** `1129543439`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2720925. See /private/tmp/dataset/dataset-vuln-collaboration_run01/flag-sequencing.json
--- END ERROR ---
```

### 129. dataset-mixed-shared-data_run02

- **Timestamp:** `2026-08-06T20:09:25.103734`
- **Seed:** `541354700`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2773400. See /private/tmp/dataset/dataset-mixed-shared-data_run02/flag-sequencing.json
--- END ERROR ---
```

### 130. dataset-scale-multi-artifact_run05

- **Timestamp:** `2026-08-06T20:09:37.744246`
- **Seed:** `1798374799`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-scale-multi-artifact_run05/flag-sequencing.json
--- END ERROR ---
```

### 131. dataset-scale-segmented-combined_run01

- **Timestamp:** `2026-08-06T20:09:50.280114`
- **Seed:** `519242783`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-scale-segmented-combined_run01/flag-sequencing.json
--- END ERROR ---
```

### 132. dataset-catalog-coverage-074

- **Timestamp:** `2026-08-06T20:10:02.711866`
- **Seed:** `1236697950`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-074/flag-sequencing.json
--- END ERROR ---
```

### 133. dataset-segmented-firewall-pivot_run04

- **Timestamp:** `2026-08-06T20:10:15.084046`
- **Seed:** `1306279396`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-segmented-firewall-pivot_run04/flag-sequencing.json
--- END ERROR ---
```

### 134. dataset-artifact-dependency_run03

- **Timestamp:** `2026-08-06T20:10:27.530660`
- **Seed:** `1788676839`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-artifact-dependency_run03/flag-sequencing.json
--- END ERROR ---
```

### 135. dataset-mixed-data-caching_run03

- **Timestamp:** `2026-08-06T20:10:39.953962`
- **Seed:** `1237415346`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-data-caching_run03/flag-sequencing.json
--- END ERROR ---
```

### 136. dataset-vuln-cache_run01

- **Timestamp:** `2026-08-06T20:10:52.347301`
- **Seed:** `1613141327`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-vuln-cache_run01/flag-sequencing.json
--- END ERROR ---
```

### 137. dataset-mixed-ci-supply-chain_run03

- **Timestamp:** `2026-08-06T20:11:04.573449`
- **Seed:** `495109622`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2710016. See /private/tmp/dataset/dataset-mixed-ci-supply-chain_run03/flag-sequencing.json
--- END ERROR ---
```

### 138. dataset-catalog-coverage-055

- **Timestamp:** `2026-08-06T20:11:16.957029`
- **Seed:** `424206683`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-055/flag-sequencing.json
--- END ERROR ---
```

### 139. dataset-catalog-coverage-041

- **Timestamp:** `2026-08-06T20:11:29.583453`
- **Seed:** `1453346733`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-041/flag-sequencing.json
--- END ERROR ---
```

### 140. dataset-artifact-web-delivery_run03

- **Timestamp:** `2026-08-06T20:11:33.467712`
- **Seed:** `1145989167`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 141. dataset-vuln-perimeter_run03

- **Timestamp:** `2026-08-06T20:11:45.967473`
- **Seed:** `166361016`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-vuln-perimeter_run03/flag-sequencing.json
--- END ERROR ---
```

### 142. dataset-vuln-web-frameworks_run05

- **Timestamp:** `2026-08-06T20:11:49.752610`
- **Seed:** `788335908`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 143. dataset-mixed-application-mesh_run01

- **Timestamp:** `2026-08-06T20:12:02.132600`
- **Seed:** `1109770563`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-application-mesh_run01/flag-sequencing.json
--- END ERROR ---
```

### 144. dataset-catalog-coverage-017

- **Timestamp:** `2026-08-06T20:12:14.697802`
- **Seed:** `1505569939`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-017/flag-sequencing.json
--- END ERROR ---
```

### 145. dataset-vuln-cms_run02

- **Timestamp:** `2026-08-06T20:12:18.508289`
- **Seed:** `53967130`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 146. dataset-segmented-nat-artifacts_run02

- **Timestamp:** `2026-08-06T20:12:30.785122`
- **Seed:** `245494484`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2709758. See /private/tmp/dataset/dataset-segmented-nat-artifacts_run02/flag-sequencing.json
--- END ERROR ---
```

### 147. dataset-catalog-coverage-003

- **Timestamp:** `2026-08-06T20:12:43.079016`
- **Seed:** `5654999`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-003/flag-sequencing.json
--- END ERROR ---
```

### 148. dataset-artifact-messaging_run01

- **Timestamp:** `2026-08-06T20:12:47.063261`
- **Seed:** `443505991`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 149. dataset-catalog-coverage-022

- **Timestamp:** `2026-08-06T20:12:59.486936`
- **Seed:** `1428437966`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2713982. See /private/tmp/dataset/dataset-catalog-coverage-022/flag-sequencing.json
--- END ERROR ---
```

### 150. dataset-segmented-enterprise-pivots_run01

- **Timestamp:** `2026-08-06T20:13:14.323941`
- **Seed:** `203125044`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-segmented-enterprise-pivots_run01/flag-sequencing.json
--- END ERROR ---
```

### 151. dataset-catalog-coverage-058

- **Timestamp:** `2026-08-06T20:13:26.838965`
- **Seed:** `453099428`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: size mismatch in put!  0 != 2731478. See /private/tmp/dataset/dataset-catalog-coverage-058/flag-sequencing.json
--- END ERROR ---
```

### 152. dataset-artifact-remote-access_run05

- **Timestamp:** `2026-08-06T20:13:30.906340`
- **Seed:** `337648091`
- **Error Category:** `disk_space_issue`
- **Exit Code:** `1`
- **Validation Failed:** `True`
- **Has RuntimeError:** `True`

- **Flags:** disk_full=yes, remote_size_mismatch=yes, core_python_path_missing=yes, core_python_cmd_not_found=yes

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---
ERROR: Validation unavailable (2)
--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2070, in run
    self._record_phase_result(result, topo_phase)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: scenarioforge.cli execute failed with exit code 1. Validation: validation_unavailable=true, error="Failed to refresh custom CORE services before remote execute: Failed uploading custom service CoreTGPrereqs.py to /tmp/coretg_custom_services/CoreTGPrereqs.py: attempt 1: remote size 0 != local size 5274; attempt 2: Failure; attempt 3: Failure; command-channel fallback failed: /opt/core/venv/python3.8/bin/python: exit=127 detail=bash: line 1: /opt/core/venv/python3.8/bin/python: No such file or directory; core-python: exit=127 detail=bash: line 1: core-python: command not found; python3: exit=1 detail=[Errno 28] No space left on device; python: exit=1 detail=[Errno 28] No space left on device". See execute.log
--- END ERROR ---
```

### 153. dataset-scale-multi-vulnerability_run02

- **Timestamp:** `2026-08-06T20:13:43.601199`
- **Seed:** `810950577`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-scale-multi-vulnerability_run02/flag-sequencing.json
--- END ERROR ---
```

### 154. dataset-mixed-web-exploit-delivery_run03

- **Timestamp:** `2026-08-06T20:13:56.186502`
- **Seed:** `1393939289`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-mixed-web-exploit-delivery_run03/flag-sequencing.json
--- END ERROR ---
```

### 155. dataset-catalog-coverage-036

- **Timestamp:** `2026-08-06T20:14:08.887936`
- **Seed:** `27947870`
- **Error Category:** `docker_images_missing`
- **Exit Code:** `0`
- **Validation Failed:** `False`
- **Has RuntimeError:** `True`

**Raw Output:**

```
--- WARNING/ERROR OUTPUT ---

--- END WARNING ---
--- RUN ERROR ---
Traceback (most recent call last):
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 2006, in run
    num_hosts = topo_spec.get('hosts', 5)
                                 ^^^^^^^^
  File "/Users/jcacosta/Documents/GitHub/scenarioforge-eval/scenarioforge_eval/executor.py", line 1101, in _run_cli_phase
    except OSError as exc:
        ^^^^^^^^^^^^^^^^^^
scenarioforge_eval.executor.PhaseExecutionError: scenarioforge.cli flag-sequencing reported failure despite exit code 0: Failed to sync repo to CORE VM: Failure. See /private/tmp/dataset/dataset-catalog-coverage-036/flag-sequencing.json
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
- **dataset-mixed-cms-remote-access_run05**: vulhub/drupal:7.57
- **dataset-catalog-coverage-063**: vulhub/solr:8.2.0, vulhub/solr:8.8.1, vulhub/spark:2.3.1
- **dataset-catalog-coverage-019**: postgis/postgis:14-3.3-alpine, vulhub/geoserver:2.17.2, vulhub/geoserver:2.22.1, vulhub/geoserver:2.23.2
- **dataset-catalog-coverage-035**: mariadb:10.11.5, redis:6.2.13, vulhub/joomla:3.7.0, vulhub/joomla:4.2.7, vulhub/jumpserver:3.6.3
- **dataset-catalog-coverage-021**: postgres:11.9-alpine, redis:4.0.14-alpine, vulhub/git:2.12.2-with-openssh, vulhub/gitea:1.4.0, vulhub/gitlab:8.13.1
- **dataset-vuln-cms_run01**: vulhub/drupal:8.3.0
- **dataset-catalog-coverage-014**: vulhub/dubbo:2.7.3, vulhub/ecshop:2.7.3, vulhub/ecshop:3.6.0, vulhub/ecshop:4.0.6, zookeeper:3.7.0
- **dataset-vuln-devops_run03**: vulhub/jenkins:2.441, vulhub/jenkins:2.46.1
- **dataset-mixed-cms-remote-access_run02**: vulhub/drupal:7.31, vulhub/drupal:8.3.0
- **dataset-catalog-coverage-064**: vulhub/spring-messaging:5.0.4, vulhub/spring-rest-data:2.6.6, vulhub/spring-security-oauth2:2.0.8
- **dataset-catalog-coverage-070**: nginx:1-alpine, redis:7-alpine, vulhub/uwsgi-python:2.0.17, vulhub/v2board:1.6.1, vulhub/vite:2.1.5
- **dataset-vuln-collaboration_run05**: postgres:10.7-alpine, vulhub/confluence:6.10.2, vulhub/confluence:7.13.6, vulhub/confluence:8.5.1
- **dataset-vuln-search-data_run02**: vulhub/elasticsearch:1.1.1, vulhub/elasticsearch:1.5.1-with-tomcat
- **dataset-catalog-coverage-051**: vulhub/pdfjs:4.1.392, vulhub/pgadmin:6.16, vulhub/pgadmin:7.6
- **dataset-mixed-enterprise-data_run02**: vulhub/struts2:s2-067
- **dataset-catalog-coverage-013**: vulhub/bind:latest, vulhub/discuz:x3.4
- **dataset-mixed-application-mesh_run05**: vulhub/php:7.0.30, vulhub/php:7.1-xdebug, vulhub/php:7.4-xdebug, vulhub/spring-security:5.6.3
- **dataset-vuln-devops_run04**: vulhub/jenkins:2.138, vulhub/jenkins:2.441
- **dataset-catalog-coverage-069**: vulhub/tomcat:8.0, vulhub/unomi:1.5.1, vulhub/uwsgi-php:2.0.16
- **dataset-vuln-web-frameworks_run01**: vulhub/struts2:2.5.25
- **dataset-catalog-coverage-007**: vulhub/cacti:1.2.22, vulhub/cacti:1.2.24, vulhub/cacti:1.2.28
- **dataset-catalog-coverage-026**: vulhub/hadoop:2.8.1, vulhub/hertzbeat:1.4.4, vulhub/spring-with-h2database:2.0.206
- **dataset-catalog-coverage-032**: vulhub/jboss:as-4.0.5, vulhub/jboss:as-6.1.0, vulhub/jetty:9.4.37
- **dataset-catalog-coverage-048**: vulhub/ofbiz:18.12.15, vulhub/openfire:4.7.4
- **dataset-mixed-data-caching_run01**: vulhub/elasticsearch:1.4.2
- **dataset-mixed-enterprise-data_run04**: vulhub/struts2:2.3.32-showcase
- **dataset-mixed-ci-supply-chain_run01**: vulhub/jenkins:2.46.1
- **dataset-catalog-coverage-039**: vulhub/libssh:0.8.1, vulhub/liferay-portal:7.2.0-ga1, vulhub/livewire:3.6.3
- **dataset-mixed-cms-remote-access_run04**: vulhub/drupal:8.5.0
- **dataset-catalog-coverage-062**: vulhub/solr:7.0.1, vulhub/solr:8.1.1
- **dataset-catalog-coverage-018**: vulhub/flink:1.11.2, vulhub/geoserver:2.19.1
- **dataset-mixed-collaboration-messaging_run02**: vulhub/confluence:8.5.1
- **dataset-segmented-enterprise-pivots_run03**: vulhub/struts2:2.3.30, vulhub/struts2:s2-053
- **dataset-catalog-coverage-020**: vulhub/imagemagick:7.0.8-10-php, vulhub/imagemagick:7.0.8-20-php, vulhub/imagemagick:7.0.8-27-php
- **dataset-mixed-web-exploit-delivery_run01**: vulhub/struts2:2.3.34-showcase
- **dataset-vuln-devops_run02**: vulhub/jenkins:2.138

---

## Prioritized Fix List

| Priority | Issue | Runs Fixed |
|----------|-------|------------|
| CRITICAL | Free disk space on CORE VM | dataset-artifact-web-delivery_run01, dataset-vuln-collaboration_run03, dataset-mixed-application-mesh_run03, dataset-artifact-messaging_run03, dataset-artifact-web-delivery_run04, dataset-artifact-remote-access_run02, dataset-vuln-cms_run05, dataset-vuln-web-frameworks_run02, dataset-artifact-web-delivery_run02, dataset-vuln-web-frameworks_run04, dataset-vuln-devops_run01, dataset-vuln-cms_run03, dataset-artifact-remote-access_run04, dataset-artifact-web-delivery_run05, dataset-artifact-remote-access_run03, dataset-vuln-cms_run04, dataset-vuln-web-frameworks_run03, dataset-artifact-web-delivery_run03, dataset-vuln-web-frameworks_run05, dataset-vuln-cms_run02, dataset-artifact-messaging_run01, dataset-artifact-remote-access_run05 |
| CRITICAL | Install `scenarioforge` on CORE VM | dataset-scale-segmented-combined_run04, dataset-segmented-enterprise-pivots_run04, dataset-catalog-coverage-042, dataset-scale-segmented-combined_run02, dataset-mixed-collaboration-messaging_run04, dataset-segmented-enterprise-pivots_run05 |
| CRITICAL | Fix pre-generated Flow values in XML | dataset-artifact-name-identity_run05, dataset-mixed-enterprise-data_run05, dataset-vuln-collaboration_run02, dataset-mixed-application-mesh_run02, dataset-scale-segmented-combined_run05 |
| HIGH | Pull missing Docker images + fix CORE session config | dataset-vuln-cache_run04, dataset-mixed-application-mesh_run04, dataset-vuln-cache_run02, dataset-mixed-shared-data_run01, dataset-mixed-perimeter-identity_run05, dataset-segmented-mixed-perimeter_run04, dataset-vuln-cache_run05, dataset-catalog-coverage-045, dataset-catalog-coverage-057, dataset-mixed-perimeter-identity_run04, dataset-catalog-coverage-076, dataset-catalog-coverage-034, dataset-catalog-coverage-015 |
| MEDIUM | Fix Docker build timeout (python:3.11-slim) | dataset-artifact-data-stores_run03, dataset-scale-segmented-combined_run03 |
| HIGH | Pull missing Docker images (core reason) | dataset-mixed-perimeter-identity_run03, dataset-segmented-enterprise-pivots_run02, dataset-scale-multi-vulnerability_run01, dataset-mixed-perimeter-identity_run02, dataset-vuln-search-data_run04, dataset-vuln-cache_run03, dataset-vuln-perimeter_run01, dataset-artifact-data-stores_run02, dataset-catalog-coverage-043, dataset-segmented-mixed-perimeter_run02... |
| LOW | Pull all missing Docker images for warning-only runs | 59 runs listed above |
