# Analysis of dataset-segmented-firewall-pivot_run01 Failure

## Summary

The failure was caused by a **warning** in the artifact checks that was treated as a failure because the `--strict` mode was enabled.

## Details

### The Warning

The `pivot_access` check in the artifact checks reported a warning:

```
[PWARN ] Pivot providers reachable from the participant: 1 of 1 pivot provider(s) are opened to an address outside each walled-off subnet (no participant network is configured, so this does not prove the real participant network reaches them) by the rules, but were not confirmed on the wire: no router holds an interface on that source network, so there is no vantage to send from; in that topology the rule analysis above is the whole answer.

  - [WARN] docker-8 (172.30.218.4:80) for 172.30.218.0/24: an allow rule opens this provider from outside the walled-off subnet on port 80, but this was not confirmed on the wire: no router holds an interface on that source network, so there is no vantage to send from; in that topology the rule analysis above is the whole answer
```

### Root Cause

The scenario has a segmentation rule that opens access to `docker-8` (running a Drupal vulnerability) on port 80 from the subnet `172.30.218.0/24`. However, no router in the topology has an interface on this network, meaning there's no actual network path to verify that this pivot access works in practice.

This is captured in the `execute-check-artifacts.json`:
- The `pivot_access` check has `status: "warn"`
- The `overall` is `"warn"` 
- `ok` is `false`
- `strict` is `true`

### Why This Failed

Looking at the executor code (`scenarioforge_eval/executor.py`), specifically the `_check_artifacts_outcome` method (lines 887-920):

```python
if config['strict'] and warn_details:
    return (
        False,
        warnings,
        f"artifact checks reported warnings under strict mode: {'; '.join(warn_details)}",
    )
```

When `strict` mode is enabled (which is the default validation policy), any warnings in the artifact checks cause the entire execute phase to fail. This is the expected behavior - the warning is not a bug in the scenario generation, but a legitimate security topology concern that the scenario creator should be aware of.

### The Actual Error Message

The error was raised at line 2214-2215 of `executor.py`:

```python
if not passed:
    result['stages']['execute'] = 'FAIL'
    raise RuntimeError(failure_message or 'scenarioforge.cli execute failed. See execute.log')
```

With the failure message being:
```
artifact checks reported warnings under strict mode: Pivot providers reachable from the participant: 1 of 1 pivot provider(s) are opened to an address outside each walled-off subnet (no participant network is configured, so this does not prove the real participant network reaches them) by the rules, but were not confirmed on the wire: no router holds an interface on that source network, so there is no vantage to send from; in that topology the rule analysis above is the whole answer.
```

## Conclusion

This was **not an actual error** in the scenario generation or execution. It was a **warning** about pivot access topology that was treated as a failure due to `strict` mode being enabled. The scenario generated successfully, all containers ran, all services were accessible, and all required traffic flows worked correctly. The warning simply noted that one of the pivot access rules couldn't be verified on the wire because no router has an interface on the source network specified in the rule.
