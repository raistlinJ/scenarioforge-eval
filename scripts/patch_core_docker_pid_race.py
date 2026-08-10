#!/usr/bin/env python3
"""Patch CORE's DockerNode fixes from docker-fixes.md.

Applies two independent fixes (see docker-fixes.md for full rationale):

  1. the docker-pid-race in DockerNode.startup()
  2. (raistlinJ/core fork only) shell-mangling of compose file contents in
     DockerNode.startup()'s compose branch

Run on the CORE VM as root (the installed package there is root-owned):

    sudo /opt/core/venv/bin/python3 scripts/patch_core_docker_pid_race.py
    sudo systemctl restart core-daemon   # required -- see docker-fixes.md

Verifies the exact pre-patch text is present before writing, so a version
mismatch fails loudly instead of silently no-op'ing or double-patching.
Backs up the original alongside itself as `docker.py.orig` (skipped if that
backup already exists, so re-running this script is safe).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

DEFAULT_TARGET = Path(
    "/opt/core/venv/lib/python3.11/site-packages/core/nodes/docker.py"
)

OLD_IMPORT = "import json\nimport logging\nimport os\nimport shlex\n"
NEW_IMPORT = "import json\nimport logging\nimport os\nimport shlex\nimport time\n"

OLD_BLOCK = '''            # retrieve pid and process environment for use in nsenter commands
            self.pid = self.host_cmd(
                f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.name}"
            )
            output = self.host_cmd(f"cat /proc/{self.pid}/environ")
            for line in output.split("\\x00"):
                if not line:
                    continue
                key, value = line.split("=", 1)
                self.env[key] = value
            logger.debug("node(%s) pid: %s", self.name, self.pid)
            self.up = True'''

NEW_BLOCK = '''            # retrieve pid and process environment for use in nsenter commands
            #
            # scenarioforge-eval patch, see docker-fixes.md: `docker run -td`
            # returns before the container's init process is guaranteed a
            # PID. Querying `.State.Pid` immediately after can race and
            # return "0" (docker's not-running placeholder), and
            # `cat /proc/0/environ` then fails outright -- upstream has no
            # retry here. Retry briefly instead of failing the whole node
            # (and therefore the whole session, which never leaves
            # CONFIGURATION_STATE) on a single unlucky poll.
            output = None
            last_exc: CoreCommandError | None = None
            for _attempt in range(10):
                self.pid = self.host_cmd(
                    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.name}"
                )
                if str(self.pid).strip() in ("", "0"):
                    time.sleep(0.3)
                    continue
                try:
                    output = self.host_cmd(f"cat /proc/{self.pid}/environ")
                    last_exc = None
                    break
                except CoreCommandError as exc:
                    last_exc = exc
                    time.sleep(0.3)
            if output is None:
                if last_exc is not None:
                    raise last_exc
                raise CoreCommandError(
                    1,
                    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.name}",
                    "",
                    f"node({self.name}) never reported a running pid after 10 attempts",
                )
            for line in output.split("\\x00"):
                if not line:
                    continue
                key, value = line.split("=", 1)
                self.env[key] = value
            logger.debug("node(%s) pid: %s", self.name, self.pid)
            self.up = True'''

# raistlinJ/core fork variant (seen on the x86 CORE VM): a heavier rewrite of
# startup() with compose/run_image_default support added, but the same
# unguarded `.State.Pid` + `cat /proc/<pid>/environ` pair, just spelled
# differently (`self.runtime_container` instead of `self.name`, `int(...)`
# conversion inline, no `.strip()` on the fetch return before use). Patch
# scope is deliberately narrower here -- only the two host_cmd calls that
# race -- because the surrounding code (compose cleanup, self.up = True,
# image_compatibility/run_image_default dispatch) differs enough from stock
# CORE that re-deriving the same wide block would be guessing, not verifying.
FORK_OLD_IMPORT = "import json\nimport logging\nimport os\nimport shlex\n"
FORK_NEW_IMPORT = "import json\nimport logging\nimport os\nimport shlex\nimport time\n"

FORK_OLD_BLOCK = '''            # retrieve pid and process environment for use in nsenter commands
            self.pid = int(
                self.host_cmd(
                    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.runtime_container}"
                ).strip()
            )
            output = self.host_cmd(f"cat /proc/{self.pid}/environ")'''

FORK_NEW_BLOCK = '''            # retrieve pid and process environment for use in nsenter commands
            #
            # scenarioforge-eval patch, see docker-fixes.md: `docker run -td`
            # (or `docker compose up -d`) returns before the container's
            # init process is guaranteed a PID. Querying `.State.Pid`
            # immediately after can race and return "0" (docker's
            # not-running placeholder), and `cat /proc/0/environ` then fails
            # outright -- upstream has no retry here. Retry instead of
            # failing the whole node (and therefore the whole session, which
            # never leaves CONFIGURATION_STATE) on a single unlucky poll.
            #
            # Budget is 90s here (vs. the plain `docker run -td` path's much
            # shorter race window) because this fork also supports a
            # `docker compose up -d` bring-up for self.compose nodes, and
            # that path was directly observed to need on that order for a
            # cold image pull/build plus a couple of early container
            # restarts before settling -- confirmed by watching the same
            # node recover cleanly (RestartCount 0, stable) once given ~60s
            # via scenarioforge-eval's own higher-level compose-restart
            # fallback, well past what a short race-only retry would cover.
            output = None
            last_exc: CoreCommandError | None = None
            for _attempt in range(90):
                pid_str = self.host_cmd(
                    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.runtime_container}"
                ).strip()
                if pid_str in ("", "0"):
                    time.sleep(1.0)
                    continue
                self.pid = int(pid_str)
                try:
                    output = self.host_cmd(f"cat /proc/{self.pid}/environ")
                    last_exc = None
                    break
                except CoreCommandError as exc:
                    last_exc = exc
                    time.sleep(1.0)
            if output is None:
                if last_exc is not None:
                    raise last_exc
                raise CoreCommandError(
                    1,
                    f"{DOCKER} inspect -f '{{{{.State.Pid}}}}' {self.runtime_container}",
                    "",
                    f"node({self.name}) never reported a running pid after 90 attempts",
                )'''


# raistlinJ/core fork only. Second, independent bug in the same method: the
# rendered compose YAML is interpolated straight into a double-quoted host
# shell string, so the *host shell* expands its contents before the file is
# ever written. Any `$`, backtick, or `%` in a compose file is corrupted:
#   `$$i`      -> the host shell's own PID followed by "i"  (e.g. "139182i")
#   `$2`       -> blank (unset positional parameter)
#   `$((i+1))` -> real arithmetic expansion, collapsing to "1"
# Reproduced exactly, byte-for-byte, against a live container's baked-in
# Config.Cmd. Escaping `"` (as the fork does) does not help -- the problem is
# `$`/backtick expansion, not quoting -- and no amount of pre-escaping on the
# ScenarioForge side is safe, since the correct escaping depends on shell
# context the writer can't see. Fix by never putting the content in a shell
# string: base64 it in Python (no shell metacharacters survive that) and
# decode it on the remote end.
FORK_COMPOSE_OLD_BLOCK = '''                rendered = rendered.replace('"', r"\\"")
                rendered = "\\\\n".join(rendered.splitlines())
                compose_path = self.directory / "docker-compose.yml"
                self.host_cmd(f'printf "{rendered}" >> {compose_path}', shell=True)'''

FORK_COMPOSE_NEW_BLOCK = '''                # scenarioforge-eval patch, see docker-fixes.md: the original
                # here interpolated the rendered compose YAML into a
                # double-quoted host shell string
                # (`printf "{rendered}" >> ...`), so the host shell expanded
                # the file's own contents before writing it -- `$$` became the
                # shell's PID, `$2` blanked out, `$((i+1))` was evaluated.
                # Round-trip through base64 instead so no byte of the compose
                # file is ever seen by a shell as syntax.
                compose_path = self.directory / "docker-compose.yml"
                encoded = base64.b64encode(rendered.encode("utf-8")).decode("ascii")
                self.host_cmd(
                    f"echo {encoded} | base64 -d >> {compose_path}", shell=True
                )'''

FORK_COMPOSE_OLD_IMPORT = "import json\nimport logging\n"
FORK_COMPOSE_NEW_IMPORT = "import base64\nimport json\nimport logging\n"


def _apply_fork_compose_fix(text: str) -> tuple[str, bool]:
    """Apply fix 2 if this file is the fork variant and isn't already fixed."""
    if "scenarioforge-eval patch, see docker-fixes.md: the original" in text:
        return text, False
    if text.count(FORK_COMPOSE_OLD_BLOCK) != 1:
        return text, False
    text = text.replace(FORK_COMPOSE_OLD_BLOCK, FORK_COMPOSE_NEW_BLOCK, 1)
    if "\nimport base64\n" not in text:
        if text.count(FORK_COMPOSE_OLD_IMPORT) != 1:
            raise SystemExit(
                "FAIL: compose fix matched but the import block did not; "
                "refusing to write a file that would NameError on base64."
            )
        text = text.replace(FORK_COMPOSE_OLD_IMPORT, FORK_COMPOSE_NEW_IMPORT, 1)
    return text, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"path to CORE's docker.py (default: {DEFAULT_TARGET})",
    )
    args = parser.parse_args()
    target: Path = args.target

    if not target.is_file():
        print(f"FAIL: {target} does not exist", file=sys.stderr)
        return 1

    text = target.read_text(encoding="utf-8")
    original_text = text

    # Fix 1: the pid race. Skipped if already applied, but that must not
    # short-circuit fix 2 -- the two are independent and an earlier run of
    # this script may predate fix 2 existing at all.
    pid_race_done = "scenarioforge-eval patch, see docker-fixes.md: `docker run -td`" in text
    stock_match = text.count(OLD_IMPORT) == 1 and text.count(OLD_BLOCK) == 1
    fork_match = text.count(FORK_OLD_IMPORT) == 1 and text.count(FORK_OLD_BLOCK) == 1

    if not pid_race_done and not stock_match and not fork_match:
        print(
            f"FAIL: neither known pre-patch variant (stock CORE or the "
            f"raistlinJ/core fork) was found exactly once in {target}. "
            "This CORE version's docker.py may differ from both this patch "
            "targets -- check docker-fixes.md and whether the race is already "
            "fixed upstream before adapting this script.",
            file=sys.stderr,
        )
        return 1

    backup = target.with_suffix(target.suffix + ".orig")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backed up original to {backup}")
    else:
        print(f"backup already exists at {backup}, leaving it as-is")

    if pid_race_done:
        print("fix 1 (pid race): already applied, skipping")
    elif stock_match:
        text = text.replace(OLD_IMPORT, NEW_IMPORT, 1)
        text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
        print("fix 1 (pid race): applied, stock CORE variant")
    else:
        text = text.replace(FORK_OLD_IMPORT, FORK_NEW_IMPORT, 1)
        text = text.replace(FORK_OLD_BLOCK, FORK_NEW_BLOCK, 1)
        print("fix 1 (pid race): applied, raistlinJ/core fork variant")

    text, compose_applied = _apply_fork_compose_fix(text)
    if compose_applied:
        print("fix 2 (compose shell mangling): applied, raistlinJ/core fork variant")
    else:
        print("fix 2 (compose shell mangling): not applicable or already applied")

    if text == original_text:
        print(f"SKIP: {target} already fully patched, nothing to write")
        return 0

    target.write_text(text, encoding="utf-8")
    print(f"OK: patched {target}")
    print("Now run: sudo systemctl restart core-daemon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
