# CORE emulator vendor fixes

Patches applied directly to the `core` Python package (CORE emulator,
currently v9.2.1) as installed on the CORE VM, at
`/opt/core/venv/lib/python3.11/site-packages/core/`. These are **not**
ScenarioForge or scenarioforge-eval code — they live in a third-party
dependency, on the VM's filesystem, outside both git repos. **They do not
survive a CORE reinstall/upgrade** and must be reapplied by hand (or
reconfirmed as already fixed upstream) whenever CORE is reinstalled.

Two CORE builds are in play, and they need different patch text:

- **stock CORE v9.2.1** (the arm64 VM)
- **the raistlinJ/core fork** (the x86-64 VM at 129.108.4.45), which rewrites
  `DockerNode.startup()` to add compose support

`scripts/patch_core_docker_pid_race.py` handles both — it detects the variant,
applies whichever fixes are missing, and is safe to re-run.

| # | Fix | Applies to | Status |
| --- | --- | --- | --- |
| 1 / 1b | Docker node startup pid race | both (different patch text) | fixed at source in raistlinJ/core |
| 2 | Compose file mangled by the host shell | fork only | already fixed at source; VM is behind |
| 3 | `adopt_iface` lookalike — **not** a CORE bug, don't patch | both | n/a |

> **Fixed upstream (2026-08-10).** We own the fork
> (github.com/raistlinJ/core, checked out at `../core`), so fixes 1/1b and 2
> now live in its source rather than only as VM-local patches — see
> "Upstream status" below. The VM patch script is still needed until the VM is
> rebuilt from that source, because the installed copy at `/opt/core/venv/...`
> predates it.

Each section below has: the symptom that led to it, the exact upstream bug,
the patch applied, and how to reapply it.

---

## Upstream status (raistlinJ/core, `../core`)

What was actually changed in the fork's source, and how it differs from the
VM-local patch:

- **Fix 1 (pid race) — fixed in source.** Was still present on `master`. Added
  `DockerNode._wait_for_pid()` (`daemon/core/nodes/docker.py`), which polls
  until the container reports a non-zero pid *and* its `/proc/<pid>/environ`
  is readable, then returns both. Both conditions are checked in one loop on
  purpose: they come from the same underlying condition (init actually
  running), so testing them separately just reopens the race in the gap
  between the two calls. Raises `CoreError` after `PID_WAIT_TIMEOUT` (90s).
- **Fix 1, podman — same latent bug, also fixed.** `PodmanNode.startup()` had
  the identical unguarded `int(... .State.Pid)`. It never reads `environ`, so
  it can't fail the same way, but a pid of `0` propagates and fails later at
  `device_ns` — which is exactly the confusing "RTNETLINK answers: No such
  process" signature described in §3. Added a matching `_wait_for_pid()`
  returning just the pid.
- **Fix 2 (compose shell mangling) — already fixed on `master`.** The source
  now writes compose files via `_write_host_file()`, which uses
  `printf %s {shlex.quote(contents)}`; content goes through as a quoted
  argument, never as shell syntax. The VM's installed copy still has the old
  `printf "{rendered}"` form, which is why it still reproduced there. No
  source change was needed — **the VM is simply out of date.**

The cleanest way to retire the VM patch script entirely is to reinstall CORE
on the VM from the current fork source.

---

## 1. Docker node startup race: `cat /proc/0/environ: No such file or directory`

**File:** `core/nodes/docker.py`, `DockerNode.startup()`
**Backup of the pre-patch file:** `core/nodes/docker.py.orig` (same directory)

### Symptom

An execute run's CORE session sits in `CONFIGURATION_STATE` for the entire
startup timeout and never reaches `RUNTIME_STATE`. scenarioforge-eval reports
this as:

```
Start validation failed: CORE session stayed in "configuration": it never
instantiated the topology, so no interface or address was attached to <nodes>
```

This is **not** a resource-exhaustion or VM-overload symptom — confirmed by
reproducing it on a freshly rebooted VM with no other process touching it and
nearly 900MB free. It is a genuine race condition in CORE itself, though a
busier system (more concurrent docker activity) likely loses the race more
often, since Docker has more contention when assigning the container's PID.

### Root cause

`core-daemon`'s own journal (`journalctl -u core-daemon`) shows the real
exception, raised inside CORE's internal threadpool during node startup:

```
core.errors.CoreCommandError: command(cat /proc/0/environ), status(1):
stderr: cat: /proc/0/environ: No such file or directory
```

The original code (`core/nodes/docker.py`, in `startup()`):

```python
# retrieve pid and process environment for use in nsenter commands
self.pid = self.host_cmd(
    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.name}"
)
output = self.host_cmd(f"cat /proc/{self.pid}/environ")
```

Immediately after `docker run -td ...` returns, CORE queries
`docker inspect -f '{{.State.Pid}}'` and reads `/proc/<pid>/environ` with
**no retry and no wait**. If Docker hasn't finished assigning the container's
PID yet, `.State.Pid` is still `0` (Docker's "not running" placeholder), and
`cat /proc/0/environ` fails outright — PID 0 has no `/proc` entry. This
exception propagates out of the threadpool worker and that node's startup
never completes, which is why the whole session never leaves
`CONFIGURATION_STATE`: the state machine appears to wait on every node
finishing startup before it can advance.

### Fix applied

Wrapped the PID-fetch-and-environ-read in a bounded retry (10 attempts, 0.3s
apart): if `.State.Pid` comes back empty or `"0"`, or reading `/proc/<pid>/environ`
raises `CoreCommandError`, sleep briefly and retry rather than failing the
node (and therefore the session) on a single unlucky poll. On final exhaustion
it still raises — the original failure mode isn't hidden, just no longer
triggered by an ordinary momentary race. Also added `import time` to the
module (previously unused).

### How to reapply after a CORE reinstall

1. Confirm the bug still exists in whatever version got installed: reproduce
   (see below), or check the CORE changelog/`core/nodes/docker.py` source for
   whether this race has since been fixed upstream — if so, skip this patch.
2. If still present, re-run the patch script kept for this purpose:
   `scripts/patch_core_docker_pid_race.py` (see below) against the new
   install path, or hand-apply the diff shown in this document.
3. `sudo systemctl restart core-daemon` — required. The daemon is a
   long-running process that already has the old module loaded into memory;
   editing the file on disk alone does nothing until it restarts.

### Reproducing it (to confirm a fix, old or new, actually works)

Run any scenario with several docker nodes created close together (mixed-*
or catalog-coverage datasets in this repo reproduce it reliably) and watch
`journalctl -u core-daemon -f` during session start for
`cat: /proc/0/environ`. It's a race, not deterministic — a clean single run
may not hit it every time, so a few attempts are a fairer test than one.

### Patch script

Kept at `scripts/patch_core_docker_pid_race.py` in this repo (verifies the
exact pre-patch text is present before writing, so it fails loudly rather
than silently no-op'ing or double-patching). Run on the CORE VM as root:

```bash
sudo /opt/core/venv/bin/python3 scripts/patch_core_docker_pid_race.py
sudo systemctl restart core-daemon
```

### Verification status (2026-08-10, arm64 VM)

Applied and confirmed byte-identical to the repo script's output. Re-ran two
different previously-failing scenarios afterward (`mixed-perimeter-identity_run03`,
`catalog-coverage-010`): the specific `cat /proc/0/environ` exception did not
recur in either. Not fully conclusive on its own — it's a probabilistic race,
and both re-runs happened to fail anyway for the unrelated reason in §3 below,
which got in the way of a clean pass/fail read. Worth another look once
running on a machine that isn't also fighting image-compatibility failures.

---

## 1b. Fork variant of fix 1 (raistlinJ/core)

> Now also fixed in the fork's source as `DockerNode._wait_for_pid()` (and the
> podman equivalent) — see "Upstream status" above. The VM patch below is still
> what's running until the VM is rebuilt from that source.

The x86 CORE VM runs a modified CORE (github.com/raistlinJ/core), whose
`DockerNode.startup()` is a heavier rewrite — it adds compose and
`run_image_default` support. It has **the same pid race**, just spelled
differently (`self.runtime_container` instead of `self.name`, an inline
`int(...)` conversion), so the stock patch text doesn't match and the script
fails loudly rather than silently doing nothing. `scripts/patch_core_docker_pid_race.py`
now recognizes both variants and reports which one it matched.

Two differences from the stock patch, both evidence-driven:

- **Budget is 90 × 1.0s, not 10 × 0.3s.** The fork also brings containers up
  via `docker compose up -d`, which is much slower to settle than a plain
  `docker run -td` (cold image pull/build, plus a couple of early restarts).
  A 3s budget expired long before the container was ready.
- Only the two racing `host_cmd` calls are rewritten. The surrounding code
  (compose cleanup, `self.up = True`, the `image_compatibility` /
  `run_image_default` dispatch) differs enough from stock that reusing the
  wider stock block would be guessing.

---

## 2. Fork only: compose file contents mangled by the host shell

**File:** `core/nodes/docker.py`, `DockerNode.startup()`, the `if self.compose:` branch
**Applies to:** the raistlinJ/core fork only — stock CORE has no compose branch here
**Applied by:** the same `scripts/patch_core_docker_pid_race.py` (as "fix 2")

> **Already fixed in the fork's source**, which now writes compose files via
> `_write_host_file()` / `printf %s {shlex.quote(...)}`. The VM's installed
> copy predates that fix, which is why this still reproduced there. Keep this
> section for the diagnosis — the symptom is unusual enough to be worth
> recognizing — but no source change is needed.

### Symptom

A vulnerability container whose compose file contains a `$` crashes on boot
with a shell error that names a number nobody wrote, e.g.:

```
sh: 139182i: bad number
```

The corrupted text is baked into the container itself, visible with
`docker inspect <node> --format '{{json .Config.Cmd}}'`, so it is *not* a
Docker Compose interpolation issue and no amount of compose-level escaping
(`$$`) fixes it. That is the tell that separates this from the ordinary
compose-interpolation gotcha.

### Root cause

The fork renders the compose YAML with Mako, then writes it out by
interpolating it into a **double-quoted host shell string**:

```python
rendered = rendered.replace('"', r"\"")
rendered = "\\n".join(rendered.splitlines())
self.host_cmd(f'printf "{rendered}" >> {compose_path}', shell=True)
```

Escaping `"` handles quoting but not expansion, so the host shell expands the
compose file's own contents *before writing the file*:

| in the source compose file | what lands on disk |
| --- | --- |
| `$$i` (compose's escape for a literal `$i`) | `139182i` — the host shell's PID, then `i` |
| `$2` (an awk field reference) | *(blank — unset positional parameter)* |
| `$((i+1))` | `1` — real arithmetic expansion |

Reproduced byte-for-byte against a live container's baked-in `Config.Cmd`.
Any compose file containing `$`, a backtick, or `%` is affected — this is a
general correctness (and injection-shaped) bug, not specific to one image.

### Fix applied

Stop putting the content in a shell string at all: base64-encode it in Python
and decode on the remote side, so no byte of the compose file is ever parsed
by a shell as syntax.

```python
encoded = base64.b64encode(rendered.encode("utf-8")).decode("ascii")
self.host_cmd(f"echo {encoded} | base64 -d >> {compose_path}", shell=True)
```

Verified as an exact round-trip: `$$i`, `$2`, and `$((i+1))` all reach disk
verbatim. Pre-escaping on the ScenarioForge side was rejected as a fix —
correct escaping depends on shell context the writer can't see, and it would
have to be undone for any non-broken CORE.

### Verification status (2026-08-10, x86-64 VM, fork)

Fixes 1b and 2 applied together, `core-daemon` restarted, stale containers
cleared. `dataset-mixed-perimeter-identity_run03` — which had failed on every
prior attempt — then passed end to end: all four phases PASS, 7/7 artifact
checks pass (2 not-applicable skips), 4:05 elapsed. The ingress-nginx/k3s node
came up healthy, with k3s serving on 6443/10250 and traffic verified in both
directions. This was the run that had been failing as "CORE never finished
instantiating router-1, router-2" — a misleading message, since the actual
cause was a docker node's `startup()` raising in CORE's threadpool, which
leaves the whole session stuck in `CONFIGURATION_STATE`.

---

## 3. Lookalike, NOT patched: `adopt_iface`/`device_ns` — "RTNETLINK answers: No such process"

**Do not reflexively patch this one the same way as §1.** It produces the
same downstream symptom (session stuck in `CONFIGURATION_STATE`,
`scenarioforge-eval` reports "CORE never finished instantiating router-1,
router-2...") and a structurally similar traceback:

```
File ".../core/nodes/base.py", line 905, in adopt_iface
    self.net_client.device_ns(iface.name, str(self.pid))
File ".../core/nodes/netclient.py", line 99, in device_ns
    self.run(f"{IP} link set {device} netns {namespace}")
core.errors.CoreCommandError: command(ip link set veth12.0.1 netns 55084), status(2):
stderr: RTNETLINK answers: No such process
```

The shape looks identical to §1 — CORE trusting a `self.pid` that's gone
stale by the time it's used for a namespace operation. **But in both
instances actually traced (not just pattern-matched), the stale PID was
caused by the container itself crashing**, not CORE mis-timing a fresh
container's startup:

- Once: `docker logs` on the node showed `/bin/sh: can't open 'entrypoint.sh':
  No such file or directory`, repeating — the `ingress-nginx/CVE-2025-1974`
  vulhub image's own entrypoint is broken, nothing to do with CORE.
- Once: `docker logs` showed a Go runtime panic inside `asm_amd64.s` —
  an amd64-compiled binary crashing under qemu emulation on this arm64 host.
  `docker inspect --format '{{.RestartCount}}'` was already `3` by the time
  it was checked.

Both are the container dying on its own for reasons outside CORE's control;
CORE's link-wiring just happened to run during the gap before Docker's
restart policy relaunched it. A retry-with-fresh-pid patch here (same idea as
§1) would likely raise the *odds* of surviving a brief gap, but can't fix a
container that keeps crashing — so before patching this, check
`docker logs <node>` and `docker inspect <node> --format '{{.RestartCount}}
{{.State.ExitCode}}'` for the node named in the traceback. If it shows a real
crash loop, that's an image-compatibility problem (see the main session
history for the arm64/qemu-emulation findings), not a CORE bug, and patching
`adopt_iface` won't fix the actual cause.

If you hit this on x86 and the node it names turns out to be healthy
(`RestartCount: 0`, no crash in its logs) — that would mean it's a genuine,
narrower CORE-only race after all, worth patching the same way as §1. Hasn't
been observed under those conditions yet.

**One genuine CORE-side cause of this signature has since been found and
fixed**, so check this first before concluding it's a crashing container: a
`self.pid` of `0` (the unfixed §1 race) produces exactly this traceback, since
`ip link set <dev> netns 0` is what "No such process" is complaining about.
That path was still live in `PodmanNode.startup()` on the fork's `master` — it
fetched `.State.Pid` unguarded and, unlike the docker path, never read
`/proc/<pid>/environ`, so nothing forced the failure early and the bad pid
surfaced here instead. Both are fixed at source now (see "Upstream status").
So: if the traceback names a namespace/pid of `0`, it's §1, not a crash loop.

---

## Moving to a different CORE VM

All fixes above are local edits to a VM's filesystem (`/opt/core/venv/...`) —
they do not travel with the repo, and any new VM starts with stock, unpatched
CORE. Run the patch script there and it will report which variant it matched
and which fixes it applied:

```bash
sudo /opt/core/venv/bin/python3 scripts/patch_core_docker_pid_race.py
sudo systemctl restart core-daemon
```

It is idempotent and refuses to write when it can't match known pre-patch
text, so it's safe to run against an unknown CORE build to find out where you
stand. If it fails to match, the CORE version differs from both known
variants — check whether the bug is already fixed upstream before adapting
the patterns.

### What the arm64 → x86-64 move actually established

- **§1 is architecture-independent.** The pid race reproduced on x86 exactly
  as on arm64. It is not a qemu-emulation artifact and not VM-load-specific
  (reproduced on a freshly rebooted, otherwise idle VM).
- **§2 only exists on the raistlinJ/core fork**, since stock CORE has no
  compose branch in `startup()`. It is also architecture-independent.
- **Some earlier arm64 failures really were emulation artifacts** and simply
  disappeared on x86 (see §3's Go-runtime-panic case). Don't assume an arm64
  failure signature will reproduce — recheck rather than porting a fix
  blindly.
- **A stale container survives a VM reboot.** Docker's own restart policy
  brings orphaned scenario containers back after boot, where they consume
  memory and cause name conflicts (`Conflict. The container name "/docker-8"
  is already in use`) on the next run. After any reboot — or any interrupted
  run — clear them before trusting a result:

  ```bash
  sudo sh -c 'docker ps -aq --filter name=docker- | xargs -r docker rm -f'
  ```
