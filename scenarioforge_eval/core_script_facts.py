"""Read scenario facts out of a CORE Python API script.

Asked for "a scenario that runs on CORE", a frontier model answers with a
Python script against CORE's API far more readily than with any file format.
That is a legitimate answer -- CORE ships that API -- so grading it as
unreadable would measure the grader, not the model.

Nodes are recovered by name, including names built in a loop, because scripts
that emit a dozen hosts do it with `for i in range(1, 13)` and a name f-string.
Reading only literal `name="h1"` arguments would score those scripts as nearly
empty and would bias the comparison against exactly the larger scenarios.

Static on purpose: these scripts call CoreEmu and expect root, so running one to
count its nodes would mean executing untrusted generated code as root.
"""

from __future__ import annotations

import ast
import re
from typing import Any

FENCED_PYTHON = re.compile(r'```(?:python|py)?\s*(.*?)```', re.S)

ROUTER_PREFIXES = ('r', 'router', 'rtr')
HOST_PREFIXES = ('h', 'host', 'pc', 'client', 'server', 'workstation')
SWITCH_PREFIXES = ('sw', 'switch', 'lan', 'hub', 'br')

SERVICE_ALIASES = {
    'ssh': 'SSH', 'sshd': 'SSH', 'openssh': 'SSH',
    'http': 'HTTP', 'httpd': 'HTTP', 'apache': 'HTTP', 'nginx': 'HTTP',
    'https': 'HTTPS', 'tls': 'HTTPS',
}
ROUTING_SERVICES = {'zebra', 'ospfv2', 'ospfv3', 'ospf', 'bgp', 'rip', 'ripng', 'frr'}


def extract_python(text: str) -> str:
    """Return the largest fenced Python block, or the whole text if unfenced."""
    blocks = [b for b in FENCED_PYTHON.findall(text or '') if 'core' in b.lower()]
    if blocks:
        return max(blocks, key=len)
    return text or ''


class _Facts(ast.NodeVisitor):
    def __init__(self) -> None:
        self.constants: dict[str, int] = {}
        self.names: list[str] = []
        self.classes: list[str] = []
        self.services: set[str] = set()
        self.routing_services = False
        self.rj45 = False

    # `HOST_COUNT = 12` has to be resolved before the loop that uses it.
    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.constants[target.id] = node.value.value
        self.generic_visit(node)

    def _resolve(self, node: ast.AST) -> int | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.Name):
            return self.constants.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            left, right = self._resolve(node.left), self._resolve(node.right)
            if left is None or right is None:
                return None
            return left + right if isinstance(node.op, ast.Add) else left - right
        return None

    def _loop_count(self, node: ast.For) -> int | None:
        call = node.iter
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == 'range'):
            return None
        bounds = [self._resolve(a) for a in call.args]
        if any(b is None for b in bounds):
            return None
        if len(bounds) == 1:
            return max(0, bounds[0])
        if len(bounds) >= 2:
            return max(0, bounds[1] - bounds[0])
        return None

    def visit_For(self, node: ast.For) -> None:
        count = self._loop_count(node)
        if count:
            # Each name f-string inside the body stands for one node per pass.
            for inner in ast.walk(node):
                if isinstance(inner, ast.JoinedStr):
                    prefix = _joined_prefix(inner)
                    if prefix:
                        self.names.extend([f'{prefix}#'] * count)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', '')
        if name == 'add_node':
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    self.classes.append(arg.id)
                elif isinstance(arg, ast.Attribute):
                    self.classes.append(arg.attr)
        for keyword in node.keywords:
            if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    self.names.append(keyword.value.value)
            if keyword.arg in ('services', 'config_services') and isinstance(keyword.value, (ast.List, ast.Set, ast.Tuple)):
                for element in keyword.value.elts:
                    if isinstance(element, ast.Constant) and isinstance(element.value, str):
                        self._service(element.value)
        self.generic_visit(node)

    def _service(self, raw: str) -> None:
        token = raw.strip().lower()
        if token in ROUTING_SERVICES:
            self.routing_services = True
            return
        mapped = SERVICE_ALIASES.get(token)
        if mapped:
            self.services.add(mapped)


def _joined_prefix(node: ast.JoinedStr) -> str:
    """The literal head of an f-string, e.g. f"h{n}" -> "h"."""
    if not node.values or not isinstance(node.values[0], ast.Constant):
        return ''
    head = str(node.values[0].value or '').strip()
    return head if head and head[0].isalpha() else ''


def _bucket(name: str) -> str:
    token = re.sub(r'[^a-z]', '', str(name).lower())
    for prefix in SWITCH_PREFIXES:
        if token.startswith(prefix):
            return 'switch'
    for prefix in ROUTER_PREFIXES:
        if token.startswith(prefix):
            return 'router'
    for prefix in HOST_PREFIXES:
        if token.startswith(prefix):
            return 'host'
    return 'other'


def observe_core_script(text: str) -> dict[str, Any]:
    """Facts a CORE Python script declares, in the grader's vocabulary."""
    source = extract_python(text)
    facts: dict[str, Any] = {
        'parsed': False, 'routers': 0, 'hosts': 0, 'switches': 0,
        'services': [], 'segmentation': [], 'vulnerabilities': 0,
        'vulnerability_names': [], 'flag_node_generators': 0,
        'generator_names': [], 'traffic': False, 'hitl': False,
    }
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return facts

    visitor = _Facts()
    visitor.visit(tree)
    facts['parsed'] = True

    for name in visitor.names:
        bucket = _bucket(name)
        if bucket == 'router':
            facts['routers'] += 1
        elif bucket == 'host':
            facts['hosts'] += 1
        elif bucket == 'switch':
            facts['switches'] += 1

    facts['services'] = sorted(visitor.services)
    # An RJ45 node is CORE's hardware-in-the-loop attachment.
    facts['hitl'] = any('rj45' in c.lower() or c.lower() == 'rj' for c in visitor.classes) \
        or bool(re.search(r'Rj45Node|NodeTypes\.RJ45|NodeTypes\.RJ\b', source))
    facts['node_classes'] = sorted(set(visitor.classes))
    facts['routing_services'] = visitor.routing_services
    return facts
