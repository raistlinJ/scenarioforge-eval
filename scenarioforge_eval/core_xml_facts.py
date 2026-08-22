"""Read scenario facts out of a CORE session XML file.

This is CORE's own `save_xml` / `open_xml` format, which is what a model asked
for "a CORE scenario file" should produce. Unlike a CORE Python script, it
states node roles outright -- `<device type="router">` vs `type="docker">` --
so routers and hosts are read rather than inferred from naming.

The shapes here were taken from a real session saved off the CORE host, not
from the XSD, because the schema expresses attributes through shared complex
types and the live format is what the grader actually has to read.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

ROUTER_TYPES = {'router', 'mdr', 'prouter', 'ospfv2', 'ospfv3'}
HOST_TYPES = {'host', 'pc', 'docker', 'lxc', 'default', 'workstation', 'server'}
SWITCH_TYPES = {'switch', 'hub', 'wlan'}
RJ45_TYPES = {'rj45', 'rj', 'physical'}

SERVICE_ALIASES = {
    'ssh': 'SSH', 'sshd': 'SSH', 'openssh': 'SSH',
    'http': 'HTTP', 'httpd': 'HTTP', 'apache': 'HTTP', 'nginx': 'HTTP',
    'https': 'HTTPS', 'tls': 'HTTPS',
    'firewall': 'Firewall', 'iptables': 'Firewall', 'nftables': 'Firewall',
    'nat': 'NAT',
}
ROUTING_SERVICES = {'zebra', 'ospfv2', 'ospfv3', 'bgp', 'rip', 'ripng', 'frr', 'babel'}


def _service_names(element: ET.Element) -> list[str]:
    names = []
    for service in element.iter('service'):
        name = str(service.get('name') or '').strip()
        if name:
            names.append(name)
    return names


def _strip_namespaces(root: ET.Element) -> ET.Element:
    """Drop XML namespace prefixes from every tag in the tree.

    A generator that declares xmlns="http://coreemu.github.io/core" is being
    more correct, not less, but ElementTree then reports every tag as
    "{namespace}device" and a plain tag comparison silently matches nothing --
    scoring an entirely valid scenario as empty.
    """
    for element in root.iter():
        tag = element.tag
        if isinstance(tag, str) and tag.startswith('{'):
            element.tag = tag.rsplit('}', 1)[-1]
    return root


def _node_kind(element: ET.Element) -> str:
    """Node type, however this dialect spells it.

    CORE's XML has changed across releases and a model reproduces whichever
    variant it learned: `<device type="router">` in the current format,
    `<node><type>router</type></node>` in the older one. Reading only the
    attribute form scored entire scenarios as empty.
    """
    attr = str(element.get('type') or '').strip()
    if attr:
        return attr.lower()
    child = element.find('type')
    if child is not None and (child.text or '').strip():
        return child.text.strip().lower()
    model = element.find('model')
    if model is not None and (model.text or '').strip():
        return model.text.strip().lower()
    return str(element.get('model') or '').strip().lower()


def observe_core_xml(path: str) -> dict[str, Any]:
    """Facts a CORE session XML declares, in the grader's vocabulary."""
    facts: dict[str, Any] = {
        'parsed': False, 'routers': 0, 'hosts': 0, 'switches': 0,
        'services': [], 'segmentation': [], 'vulnerabilities': 0,
        'vulnerability_names': [], 'flag_node_generators': 0,
        'generator_names': [], 'traffic': False, 'hitl': False,
        'docker_images': [], 'compose_files': [], 'links': 0,
    }
    try:
        root = _strip_namespaces(ET.parse(path).getroot())
    except (OSError, ET.ParseError):
        return facts
    # Both roots occur in the wild: <scenario> in the current format and
    # <session> in the older session-file variant.
    if str(root.tag).lower() not in ('scenario', 'session'):
        return facts

    facts['parsed'] = True
    services: set[str] = set()
    segmentation: set[str] = set()
    images: list[str] = []
    composes: list[str] = []

    # `<device>` is current, `<node>` is the older spelling of the same thing.
    node_elements = list(root.iter('device')) + list(root.iter('node'))
    for device in node_elements:
        kind = _node_kind(device)
        klass = str(device.get('class') or '').strip().lower()
        if kind in RJ45_TYPES:
            facts['hitl'] = True
            continue
        node_services = [s.lower() for s in _service_names(device)]
        if kind in ROUTER_TYPES or any(s in ROUTING_SERVICES for s in node_services):
            facts['routers'] += 1
        elif kind in HOST_TYPES or klass == 'docker':
            facts['hosts'] += 1
        for raw in node_services:
            mapped = SERVICE_ALIASES.get(raw)
            if mapped in ('Firewall', 'NAT'):
                segmentation.add(mapped)
            elif mapped:
                services.add(mapped)
        # Docker-backed nodes carry the image or compose file they run.
        image = str(device.get('image') or '').strip()
        compose = str(device.get('compose') or '').strip()
        if image:
            images.append(image)
        if compose:
            composes.append(compose)

    for network in root.iter('network'):
        kind = _node_kind(network)
        if kind in RJ45_TYPES:
            facts['hitl'] = True
        elif kind in SWITCH_TYPES:
            facts['switches'] += 1

    if not facts['hitl']:
        # Some dialects express HITL only through the rj45 model/name.
        blob = ET.tostring(root, encoding='unicode')
        facts['hitl'] = bool(re.search(r'\brj45\b', blob, re.I))

    facts['links'] = len(list(root.iter('link')))
    facts['services'] = sorted(services)
    facts['segmentation'] = sorted(segmentation)
    facts['docker_images'] = sorted(set(images))
    facts['compose_files'] = sorted(set(composes))
    # A docker-backed node pointing at an image or compose file is how a
    # vulnerable service is expressed in this format.
    facts['vulnerabilities'] = len(set(images) | set(composes))
    facts['vulnerability_names'] = sorted(set(images))
    return facts
