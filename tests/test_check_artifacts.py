import tempfile
import unittest

from scenarioforge_eval.executor import Executor


SF_PATH = '/Users/jcacosta/Documents/GitHub/scenarioforge'


def _executor(check_artifacts=None, temp_dir='/tmp'):
    validation = {'policy': 'strict'}
    if check_artifacts is not None:
        validation['check_artifacts'] = check_artifacts
    spec = {'name': 'eval-scenario', 'seed': 1, 'validation': validation}
    return Executor(spec=spec, out_dir=temp_dir, sf_path=SF_PATH)


def _summary(*statuses, **extra):
    payload = {
        'ok': all(s not in ('fail', 'error') for s in statuses),
        'overall': 'fail' if any(s in ('fail', 'error') for s in statuses)
                   else ('warn' if 'warn' in statuses else 'pass'),
        'checks': [
            {'key': f'c{i}', 'label': f'Check {i}', 'status': s, 'summary': f'detail {i}'}
            for i, s in enumerate(statuses)
        ],
    }
    payload.update(extra)
    return payload


class CheckArtifactsConfigTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor(temp_dir=tmp)
            self.assertFalse(executor._check_artifacts_config()['enabled'])
            self.assertEqual(executor._check_artifacts_extra_args(), [])

    def test_enabled_adds_cli_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True, 'delay_seconds': 45}, temp_dir=tmp)
            self.assertEqual(
                executor._check_artifacts_extra_args(),
                ['--check-artifacts', '--check-artifacts-delay', '45.0'],
            )

    def test_strict_adds_strict_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True, 'strict': True}, temp_dir=tmp)
            args = executor._check_artifacts_extra_args()
            self.assertIn('--strict', args)
            # No delay flag when no delay was configured.
            self.assertNotIn('--check-artifacts-delay', args)

    def test_boolean_shorthand_enables(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor(True, temp_dir=tmp)
            self.assertTrue(executor._check_artifacts_config()['enabled'])

    def test_bad_delay_value_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True, 'delay_seconds': 'soon'}, temp_dir=tmp)
            self.assertEqual(executor._check_artifacts_config()['delay_seconds'], 0.0)


class CheckArtifactsOutcomeTests(unittest.TestCase):
    def test_no_op_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor(temp_dir=tmp)
            ok, warnings, failure = executor._check_artifacts_outcome({})
            self.assertTrue(ok)
            self.assertEqual(warnings, [])
            self.assertIsNone(failure)

    def test_missing_marker_when_enabled_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True}, temp_dir=tmp)
            ok, _warnings, failure = executor._check_artifacts_outcome({'check_artifacts_summary': None})
            self.assertFalse(ok)
            self.assertIn('CHECK_ARTIFACTS_SUMMARY_JSON', failure)

    def test_all_pass_is_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True}, temp_dir=tmp)
            ok, warnings, failure = executor._check_artifacts_outcome(
                {'check_artifacts_summary': _summary('pass', 'skip')})
            self.assertTrue(ok)
            self.assertEqual(warnings, [])
            self.assertIsNone(failure)

    def test_warn_records_warning_but_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True}, temp_dir=tmp)
            ok, warnings, failure = executor._check_artifacts_outcome(
                {'check_artifacts_summary': _summary('pass', 'warn')})
            self.assertTrue(ok)
            self.assertIsNone(failure)
            self.assertEqual(len(warnings), 1)
            self.assertIn('Check 1: detail 1', warnings[0])

    def test_warn_fails_under_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True, 'strict': True}, temp_dir=tmp)
            ok, warnings, failure = executor._check_artifacts_outcome(
                {'check_artifacts_summary': _summary('warn')})
            self.assertFalse(ok)
            self.assertIn('strict mode', failure)
            self.assertEqual(len(warnings), 1)

    def test_failed_check_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True}, temp_dir=tmp)
            ok, _warnings, failure = executor._check_artifacts_outcome(
                {'check_artifacts_summary': _summary('pass', 'fail')})
            self.assertFalse(ok)
            self.assertIn('Check 1: detail 1', failure)
            self.assertIn('execute-check-artifacts.json', failure)

    def test_job_level_error_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = _executor({'enabled': True}, temp_dir=tmp)
            summary = {'ok': False, 'overall': 'fail', 'checks': [],
                       'error': 'CORE session 9 is not running'}
            ok, _warnings, failure = executor._check_artifacts_outcome(
                {'check_artifacts_summary': summary})
            self.assertFalse(ok)
            self.assertIn('session 9 is not running', failure)


class CheckArtifactsMarkerParsingTests(unittest.TestCase):
    def test_marker_is_parsed_from_combined_output(self):
        text = (
            'CORE_SESSION_ID: 4\n'
            'VALIDATION_SUMMARY_JSON: {"ok": true}\n'
            'CHECK_ARTIFACTS_SUMMARY_JSON: {"ok": true, "overall": "pass"}\n'
        )
        parsed = Executor._extract_last_json_marker(text, 'CHECK_ARTIFACTS_SUMMARY_JSON:')
        self.assertEqual(parsed, {'ok': True, 'overall': 'pass'})

    def test_last_marker_wins(self):
        text = (
            'CHECK_ARTIFACTS_SUMMARY_JSON: {"overall": "stale"}\n'
            'CHECK_ARTIFACTS_SUMMARY_JSON: {"overall": "pass"}\n'
        )
        parsed = Executor._extract_last_json_marker(text, 'CHECK_ARTIFACTS_SUMMARY_JSON:')
        self.assertEqual(parsed['overall'], 'pass')


if __name__ == '__main__':
    unittest.main()
