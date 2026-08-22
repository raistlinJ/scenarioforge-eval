"""Progressive scaffolding levels for the free-text authoring arm.

Each rung adds only format or vocabulary knowledge -- never anything about the
answer itself -- so the rung number is the independent variable while the
scenario description stays constant across all of them. That is what makes the
result a curve ("how much scaffolding does a frontier model need to match the
tool?") rather than a single contested data point, and it heads off the usual
objection that the model was simply prompted badly.

Rung 2's XML shape was copied from a session saved off the live CORE host, not
from the XSD, because the schema hides attributes behind shared complex types
and the live format is what the model has to reproduce.
"""

from __future__ import annotations

_R0 = (
    "Generate a network scenario that will run on CORE (Common Open Research "
    "Emulator) and includes a HITL (hardware-in-the-loop) interface.\n\n"
    "The scenario should have: {description}"
)

_R1 = (
    "Generate a network scenario that will run on CORE (Common Open Research "
    "Emulator) and includes a HITL (hardware-in-the-loop) interface.\n\n"
    "Produce it as a CORE session XML file, the format CORE's open_xml API and "
    "the CORE GUI read. Output only the XML.\n\n"
    "The scenario should have: {description}"
)

_R2_HEAD = (
    "Generate a CORE session XML file describing a network scenario that "
    "includes a HITL (hardware-in-the-loop) interface. Output only the XML.\n\n"
    "The file has this structure:\n"
    "<scenario>\n"
    '  <networks>\n'
    '    <network id="7" name="sw1" type="SWITCH"><position x="500" y="500"/></network>\n'
    "  </networks>\n"
    "  <devices>\n"
    '    <device id="1" name="r1" type="router"><position x="100" y="100"/><services/></device>\n'
    "  </devices>\n"
    "  <links>\n"
    '    <link node1="1" node2="7">\n'
    '      <iface1 id="0" name="eth0" mac="02:00:00:00:00:01" ip4="10.0.0.1" ip4_mask="24"/>\n'
    '      <iface2 id="0" name="veth7.0.1" mac="02:00:00:00:00:02"/>\n'
    "    </link>\n"
    "  </links>\n"
    "</scenario>\n\n"
    "Every node needs a unique integer id, and links reference those ids through "
    "node1 and node2."
)

_R3_ADD = (
    "Node vocabulary:\n"
    '- A router is <device type="router">.\n'
    '- A plain host is <device type="host"> or <device type="PC">.\n'
    '- A container-backed host is <device type="docker" class="docker" image="IMAGE">.\n'
    '- A switch is <network type="SWITCH"> and a hub is <network type="HUB">.\n'
    '- A HITL interface is an RJ45 node: <device type="rj45" name="eth1">, named '
    "for a physical interface on the CORE host.\n"
    '- Services attach to a device as <services><service name="SSH"/></services>. '
    "Common names are SSH, DefaultRoute and IPForward, plus zebra and OSPFv2 on routers."
)

_R4_ADD = (
    "Segmentation vocabulary:\n"
    "- A firewall is a router-type device carrying a firewall service, placed "
    "between the subnets it separates.\n"
    "- A NAT gateway is a device carrying the NAT service on the boundary between "
    "an inside and an outside subnet.\n"
    "- Put each segment on its own switch and its own IPv4 subnet, and give the "
    "boundary device an interface in each."
)

_R5_ADD = (
    "Vulnerable services are container-backed nodes. Use "
    '<device type="docker" class="docker" image="IMAGE"> where IMAGE names a real, '
    "published container image for the vulnerable software. Prefer images from the "
    "vulhub/vulnhub collections where one exists, and give the exact image "
    "reference including its tag."
)

# Cumulative: every rung carries everything below it.
_TAIL = "\n\nThe scenario should have: {description}"
RUNGS: dict[int, str] = {
    0: _R0,
    1: _R1,
    2: _R2_HEAD + _TAIL,
    3: _R2_HEAD + "\n\n" + _R3_ADD + _TAIL,
    4: _R2_HEAD + "\n\n" + _R3_ADD + "\n\n" + _R4_ADD + _TAIL,
    5: _R2_HEAD + "\n\n" + _R3_ADD + "\n\n" + _R4_ADD + "\n\n" + _R5_ADD + _TAIL,
}

RUNG_LABELS = {
    0: 'bare (no format named)',
    1: 'format named (CORE session XML)',
    2: 'plus XML structure',
    3: 'plus node vocabulary',
    4: 'plus segmentation vocabulary',
    5: 'plus container image guidance',
}


def rung_prompt(rung: int, description: str) -> str:
    if rung not in RUNGS:
        raise KeyError(f'unknown rung {rung}; valid: {sorted(RUNGS)}')
    return RUNGS[rung].format(description=description)
