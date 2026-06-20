import yaml
import random


SERVICE_NAME_ALIASES = {
    'ssh': 'SSH',
    'http': 'HTTP',
    'https': 'HTTP',
    'web': 'HTTP',
    'dhcp': 'DHCPClient',
    'dhcpclient': 'DHCPClient',
}

class SpecParser:
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec = self._load()

    def _load(self) -> dict:
        with open(self.spec_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_name(self) -> str:
        return self.spec.get('name', 'eval-scenario')

    def get_topology_spec(self) -> dict:
        """Returns normalized topology parameters."""
        topo = self.spec.get('topology', {})
        res = {
            'type': topo.get('type', 'star'),
            'routers': self._resolve_value(topo.get('routers', [2, 5])),
            'hosts': self._resolve_value(topo.get('hosts', [3, 10])),
        }
        return res

    def get_services_spec(self) -> dict:
        s = self.spec.get('services', {})
        return {
            'enabled': s.get('enabled', s.get('randomize', True)),
            'count': self._resolve_value(s.get('count', 3)),
            'density': s.get('density', 1.0),
            'include': self._normalize_service_names(s.get('include')),
            'exclude': self._normalize_service_names(s.get('exclude')),
        }

    def get_vulns_spec(self) -> dict:
        v = self.spec.get('vulns', {})
        return {'enabled': v.get('enabled', v.get('randomize', True)), 'count': self._resolve_value(v.get('count', [1, 3]))}

    def get_flows_spec(self) -> dict:
        flows = self.spec.get('flows', {})
        return {
            'enabled': flows.get('enabled', flows.get('randomize', True)),
            'chain_length': self._resolve_value(flows.get('chain_length', [3, 5])),
            'allow_duplicates': flows.get('allow_duplicates', False)
        }

    def get_segmentation_spec(self) -> dict:
        seg = self.spec.get('segmentation', {})
        return {'enabled': seg.get('enabled', seg.get('randomize', True)), 'density': seg.get('density', 0.5)}

    def get_hitl_spec(self) -> dict:
        return self.spec.get('hitl', {'use_env': True})

    def _resolve_value(self, val):
        """Resolves a value that could be a static int/string or a range [min, max]."""
        if isinstance(val, list) and len(val) == 2:
            return random.randint(val[0], val[1])
        return val

    def _normalize_service_names(self, names) -> list[str]:
        if not names:
            return []
        if isinstance(names, str):
            names = [names]

        normalized = []
        seen = set()
        for raw_name in names:
            if raw_name in (None, ''):
                continue
            name = str(raw_name).strip()
            if not name:
                continue
            canonical = SERVICE_NAME_ALIASES.get(name.lower(), name)
            if canonical in seen:
                continue
            normalized.append(canonical)
            seen.add(canonical)
        return normalized
