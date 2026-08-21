#!/usr/bin/env python3
"""Ask the real CORE daemon whether a generated session XML is loadable.

`open_xml(..., start=False)` makes CORE parse the file and build the session
definition without instantiating it, so nothing is brought up, no physical
interface is bound and no container is started. That is the strongest
runnability signal available without executing untrusted content, and it is the
one that separates "XML that looks right" from "XML CORE accepts".

Connection details and credentials come from the ScenarioForge checkout's
.scenarioforge.env; nothing is read from this repository and the password is
never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REMOTE_PROBE = r'''
import json, sys
from pathlib import Path
from core.api.grpc.client import CoreGrpcClient

path = Path(sys.argv[1])
out = {"path": str(path), "loaded": False}
client = CoreGrpcClient()
client.connect()
session_id = None
try:
    result = client.open_xml(path, start=False)
    session_id = result[1] if isinstance(result, (tuple, list)) else getattr(result, "session_id", None)
    out["loaded"] = True
    out["session_id"] = session_id
    try:
        session = client.get_session(session_id)
        nodes = list(getattr(session, "nodes", []) or [])
        out["nodes_created"] = len(nodes)
        out["node_types"] = sorted({str(getattr(n, "type", "")) for n in nodes})
    except Exception as exc:
        out["inspect_error"] = f"{type(exc).__name__}: {exc}"
finally:
    # Never leave a probe session behind; the host already carries leaked ones.
    if session_id is not None:
        try:
            client.delete_session(session_id)
            out["cleaned_up"] = True
        except Exception as exc:
            out["cleanup_error"] = f"{type(exc).__name__}: {exc}"
print(json.dumps(out))
'''


def connect():
    sys.path.insert(0, str(REPO_ROOT.parent / 'scenarioforge'))
    from webapp.env_loader import load_runtime_env_files
    load_runtime_env_files(base_dir=REPO_ROOT.parent / 'scenarioforge', include_example=False)
    import paramiko

    host = os.environ.get('CORE_SSH_HOST') or os.environ.get('CORE_HOST')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        port=int(os.environ.get('CORE_SSH_PORT') or 22),
        username=os.environ.get('CORE_SSH_USERNAME'),
        password=os.environ.get('CORE_SSH_PASSWORD'),
        timeout=20,
    )
    return client, host


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('xml', nargs='*', help='CORE session XML files to test')
    ap.add_argument('--glob', default='', help='glob of XML files, e.g. "armb-out/*/scenario.core.xml"')
    ap.add_argument('--remote-dir', default='/tmp/armb-load')
    ap.add_argument('--python', default='/opt/core/venv/bin/python')
    ap.add_argument('--json-out', type=Path, default=None)
    ap.add_argument('--list-sessions', action='store_true', help='list sessions and exit')
    ap.add_argument('--cleanup-empty', action='store_true',
                    help='delete sessions in DEFINITION state with no nodes')
    args = ap.parse_args()

    import glob as globmod
    paths = [Path(p) for p in (args.xml + (globmod.glob(args.glob) if args.glob else []))]

    client, host = connect()
    print(f'connected to {host}')

    def run(cmd: str, timeout: int = 120) -> str:
        _, out, err = client.exec_command(cmd, timeout=timeout)
        return (out.read().decode() + err.read().decode()).strip()

    if args.list_sessions or args.cleanup_empty:
        action = 'cleanup' if args.cleanup_empty else 'list'
        probe = (
            'from core.api.grpc.client import CoreGrpcClient\n'
            'c = CoreGrpcClient(); c.connect()\n'
            'removed = []\n'
            'for s in c.get_sessions():\n'
            '    d = c.get_session(s.id)\n'
            '    n = len(list(getattr(d, "nodes", []) or []))\n'
            '    print(s.id, s.state, n)\n'
            f'    if "{action}" == "cleanup" and n == 0:\n'
            '        c.delete_session(s.id); removed.append(s.id)\n'
            'print("removed:", removed)\n'
        )
        sftp = client.open_sftp()
        client.exec_command(f'mkdir -p {args.remote_dir}')[1].read()
        with sftp.open(posixpath.join(args.remote_dir, '_sessions.py'), 'w') as fh:
            fh.write(probe)
        sftp.close()
        print(run(f'{args.python} {posixpath.join(args.remote_dir, "_sessions.py")}', 180))
        client.close()
        return 0

    if not paths:
        print('no XML files given (use positional paths or --glob)', file=sys.stderr)
        client.close()
        return 1

    sftp = client.open_sftp()
    client.exec_command(f'mkdir -p {args.remote_dir}')[1].read()
    probe_remote = posixpath.join(args.remote_dir, '_probe.py')
    with sftp.open(probe_remote, 'w') as fh:
        fh.write(REMOTE_PROBE)

    results = []
    for path in paths:
        if not path.is_file():
            continue
        label = path.parent.name or path.stem
        remote = posixpath.join(args.remote_dir, f'{label}.xml')
        sftp.put(str(path), remote)
        raw = run(f'{args.python} {probe_remote} {remote}', 180)
        try:
            record = json.loads(raw.splitlines()[-1])
        except Exception:
            record = {'path': str(path), 'loaded': False, 'error': raw[-300:]}
        record['case'] = label
        results.append(record)
        status = 'LOADED' if record.get('loaded') else 'REJECTED'
        detail = (f"nodes={record.get('nodes_created', '?')}" if record.get('loaded')
                  else str(record.get('error', ''))[:120].replace('\n', ' '))
        print(f'{label:<32} {status:<9} {detail}')

    sftp.close()
    client.close()

    loaded = sum(1 for r in results if r.get('loaded'))
    print(f'\nloadable by CORE: {loaded}/{len(results)}')
    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f'wrote {args.json_out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
