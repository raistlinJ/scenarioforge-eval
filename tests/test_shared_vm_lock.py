"""Shared CORE VM lock: the half of the cross-repo contract that lives here.

This harness and the ScenarioForge web UI's background CLI jobs both drive the
same CORE VM, and both do daemon-level work that destroys in-memory CORE
sessions (`core-cleanup`, custom-service installs, `systemctl restart
core-daemon`). They exclude each other with an flock on a shared temp file.

The two derivations of that file's path are maintained in separate repos, so
each side pins the same golden vector: if either drifts, both still "lock",
just no longer against each other, and the damage resurfaces far from its
cause as a CORE session vanishing mid-run. The peer test is
`tests/test_shared_vm_lock.py` in the scenarioforge repo.
"""

import os
import tempfile
import unittest
from unittest import mock

from scenarioforge_eval import executor as executor_module
from scenarioforge_eval.executor import Executor


# Observed in real run metadata (`shared_vm_lock` in a *_result.json), and
# asserted identically by the scenarioforge side.
GOLDEN_KEY = '12.0.0.100:22:corevm'
GOLDEN_BASENAME = 'scenarioforge-eval-f26e50de670b546c.lock'


def _executor_with_attrs(attrs):
    """An Executor stub that reports fixed CoreConnection attributes."""
    executor = Executor.__new__(Executor)
    executor._core_connection_attrs = lambda xml_path: attrs  # type: ignore[method-assign]
    return executor


def _isolated_tempdir():
    """Redirect lock files into a scratch dir for the duration of a test.

    Tests must never flock the real path: the golden key is a live production
    VM, so acquiring it for real would both block on and block an in-progress
    evaluation run sharing this machine.
    """
    scratch = tempfile.TemporaryDirectory()
    patch = mock.patch.object(
        executor_module.tempfile, 'gettempdir', lambda: scratch.name
    )
    return scratch, patch


class SharedVmLockContractTests(unittest.TestCase):
    def test_lock_key_matches_golden_vector(self):
        executor = _executor_with_attrs({
            'ssh_host': '12.0.0.100', 'ssh_port': '22', 'ssh_username': 'corevm',
        })
        self.assertEqual(executor._shared_vm_lock_key('scenario.xml'), GOLDEN_KEY)

    def test_lock_path_matches_golden_vector(self):
        executor = _executor_with_attrs({
            'ssh_host': '12.0.0.100', 'ssh_port': '22', 'ssh_username': 'corevm',
        })
        scratch, patch = _isolated_tempdir()
        with scratch, patch:
            with executor._shared_vm_lock('scenario.xml') as info:
                self.assertEqual(info['key'], GOLDEN_KEY)
                self.assertEqual(os.path.basename(info['path']), GOLDEN_BASENAME)
                self.assertEqual(os.path.dirname(info['path']), scratch.name)

    def test_lock_key_falls_back_to_host_and_appends_vm_identifier(self):
        fallback = _executor_with_attrs({
            'host': '10.0.0.5', 'ssh_port': '22', 'ssh_username': 'u',
        })
        self.assertEqual(fallback._shared_vm_lock_key('s.xml'), '10.0.0.5:22:u')

        with_vmid = _executor_with_attrs({
            'ssh_host': 'h', 'ssh_port': '22', 'ssh_username': 'u', 'vmid': '900',
        })
        self.assertEqual(with_vmid._shared_vm_lock_key('s.xml'), 'h:22:u:900')

    def test_incomplete_ssh_target_takes_no_lock(self):
        # No resolved SSH target means no shared VM to serialize against.
        for attrs in (
            {},
            {'ssh_host': '12.0.0.100', 'ssh_port': '22'},
            {'ssh_port': '22', 'ssh_username': 'corevm'},
            {'ssh_host': '12.0.0.100', 'ssh_username': 'corevm'},
        ):
            with self.subTest(attrs=attrs):
                executor = _executor_with_attrs(attrs)
                self.assertIsNone(executor._shared_vm_lock_key('s.xml'))
                scratch, patch = _isolated_tempdir()
                with scratch, patch:
                    with executor._shared_vm_lock('s.xml') as info:
                        self.assertIsNone(info)


if __name__ == '__main__':
    unittest.main()
