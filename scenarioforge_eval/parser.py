import yaml
import random

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
        return self.spec.get('services', {'randomize': True})

    def get_vulns_spec(self) -> dict:
        return self.spec.get('vulns', {'randomize': True, 'count': self._resolve_value([1, 3])})

    def get_flows_spec(self) -> dict:
        return self.spec.get('flows', {'randomize': True})

    def _resolve_value(self, val):
        """Resolves a value that could be a static int/string or a range [min, max]."""
        if isinstance(val, list) and len(val) == 2:
            return random.randint(val[0], val[1])
        return val
