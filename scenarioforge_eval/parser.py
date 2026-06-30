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

    def get_topology_spec(self, rng: random.Random | None = None) -> dict:
        """Returns normalized topology parameters."""
        topo = self.spec.get('topology', {})
        res = {
            'routers': self._resolve_value(topo.get('routers', [2, 5]), rng=rng),
            'hosts': self._resolve_value(topo.get('hosts', [3, 10]), rng=rng),
        }
        return res

    def get_services_spec(self, rng: random.Random | None = None) -> dict:
        s = self.spec.get('services', {})
        return {
            'enabled': self._feature_enabled(s, activation_keys=('count', 'include', 'exclude')),
            'count': self._resolve_value(s.get('count', 3), rng=rng),
            'density': s.get('density', 1.0),
            'include': self._normalize_service_names(s.get('include')),
            'exclude': self._normalize_service_names(s.get('exclude')),
        }

    def get_vulns_spec(self, rng: random.Random | None = None) -> dict:
        v = self.spec.get('vulns', {})
        return {
            'enabled': self._feature_enabled(v, activation_keys=('count', 'include', 'exclude')),
            'count': self._resolve_value(v.get('count', [1, 3]), rng=rng),
            'include': self._normalize_string_list(v.get('include')),
            'exclude': self._normalize_string_list(v.get('exclude')),
        }

    def get_flows_spec(self, rng: random.Random | None = None) -> dict:
        flows = self.spec.get('flows', {})
        return {
            'enabled': self._feature_enabled(flows, activation_keys=('chain_length', 'count')),
            'chain_length': self._resolve_value(flows.get('chain_length', flows.get('count', [3, 5])), rng=rng),
            'allow_duplicates': flows.get('allow_duplicates', False)
        }

    def get_segmentation_spec(self) -> dict:
        seg = self.spec.get('segmentation', {})
        return {
            'enabled': self._feature_enabled(seg, activation_keys=('density',)),
            'density': seg.get('density', 0.5),
        }

    def get_hitl_spec(self) -> dict:
        return self.spec.get('hitl', {'use_env': True})

    def get_validation_spec(self) -> dict:
        validation = self.spec.get('validation', {})
        policy = str(validation.get('policy', 'strict')).strip() or 'strict'
        return {'policy': policy}

    def _resolve_value(self, val, *, rng: random.Random | None = None):
        """Resolves a value that could be a static int/string or a range [min, max]."""
        if isinstance(val, list) and len(val) == 2:
            chooser = rng or random
            return chooser.randint(val[0], val[1])
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

    def _normalize_string_list(self, values) -> list[str]:
        if not values:
            return []
        if isinstance(values, str):
            values = [values]

        normalized = []
        seen = set()
        for raw_value in values:
            if raw_value in (None, ''):
                continue
            value = str(raw_value).strip()
            if not value:
                continue
            if value in seen:
                continue
            normalized.append(value)
            seen.add(value)
        return normalized

    def _feature_enabled(self, section: dict, *, activation_keys: tuple[str, ...], default: bool = True) -> bool:
        if not isinstance(section, dict):
            return default
        if 'enabled' in section:
            return bool(section.get('enabled'))
        if 'randomize' in section:
            if bool(section.get('randomize')):
                return True
            return any(self._has_activation_value(section, key) for key in activation_keys)
        return default

    @staticmethod
    def _has_activation_value(section: dict, key: str) -> bool:
        if key not in section:
            return False
        value = section.get(key)
        if value in (None, ''):
            return False
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)
