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

TRAFFIC_PROFILES = {
    'light': {
        'density': 0.35,
        'items': [
            {
                'selected': 'TCP', 'v_count': 1, 'pattern': 'periodic',
                'rate_kbps': 32.0, 'period_s': 5.0, 'jitter_pct': 10.0,
                'content_type': 'text',
            },
        ],
    },
    'medium': {
        'density': 0.60,
        'items': [
            {
                'selected': 'TCP', 'v_count': 1, 'pattern': 'continuous',
                'rate_kbps': 128.0, 'period_s': 2.0, 'jitter_pct': 15.0,
                'content_type': 'text',
            },
            {
                'selected': 'UDP', 'v_count': 1, 'pattern': 'periodic',
                'rate_kbps': 64.0, 'period_s': 5.0, 'jitter_pct': 25.0,
                'content_type': 'audio',
            },
        ],
    },
    'heavy': {
        'density': 0.85,
        'items': [
            {
                'selected': 'TCP', 'v_count': 2, 'pattern': 'continuous',
                'rate_kbps': 512.0, 'period_s': 1.0, 'jitter_pct': 10.0,
                'content_type': 'video',
            },
            {
                'selected': 'UDP', 'v_count': 2, 'pattern': 'burst',
                'rate_kbps': 256.0, 'period_s': 2.0, 'jitter_pct': 20.0,
                'content_type': 'photo',
            },
        ],
    },
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

    def get_traffic_spec(self, rng: random.Random | None = None) -> dict:
        """Return concrete XML-ready traffic rows from a named or custom profile."""
        traffic = self.spec.get('traffic', {})
        profile = str(traffic.get('profile', '')).strip().lower()
        profile_definition = TRAFFIC_PROFILES.get(profile)
        raw_items = profile_definition['items'] if profile_definition else (traffic.get('items') or [])
        payload_types = [
            str(value).strip().lower()
            for value in (traffic.get('payload_types') or [])
            if str(value).strip().lower() in ('text', 'photo', 'audio', 'video', 'gibberish')
        ]
        items = []
        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                continue
            selected = str(raw_item.get('type', raw_item.get('selected', ''))).strip().upper()
            if selected not in ('TCP', 'UDP'):
                continue
            count = self._resolve_value(raw_item.get('count', raw_item.get('v_count', 1)), rng=rng)
            try:
                count = int(count)
            except (TypeError, ValueError):
                continue
            if count <= 0:
                continue
            item = {
                'selected': selected,
                'factor': raw_item.get('factor', 1.0),
                'v_metric': 'Count',
                'v_count': count,
                'pattern': str(raw_item.get('pattern', 'continuous')).strip() or 'continuous',
                'rate_kbps': raw_item.get('rate_kbps', 64.0),
                'period_s': raw_item.get('period_s', 1.0),
                'jitter_pct': raw_item.get('jitter_pct', 10.0),
                'content_type': str(raw_item.get('content_type', 'text')).strip() or 'text',
            }
            if payload_types:
                item['content_type'] = payload_types[index % len(payload_types)]
            items.append(item)
        density = traffic.get('density', profile_definition['density'] if profile_definition else 0.0)
        if 'enabled' in traffic:
            enabled = bool(traffic.get('enabled'))
        elif 'randomize' in traffic:
            enabled = bool(traffic.get('randomize')) or bool(profile_definition or items)
        else:
            enabled = bool(profile_definition or items)
        return {
            'enabled': enabled,
            'profile': profile or None,
            'payload_types': payload_types,
            'density': density,
            'items': items,
        }

    def get_vulns_spec(self, rng: random.Random | None = None) -> dict:
        v = self.spec.get('vulns', {})
        result = {
            'enabled': self._feature_enabled(v, activation_keys=('count', 'include', 'exclude', 'specific')),
            'count': self._resolve_value(v.get('count', [1, 3]), rng=rng),
            'include': self._normalize_string_list(v.get('include')),
            'exclude': self._normalize_string_list(v.get('exclude')),
        }
        specific = self._normalize_specific_entries(v.get('specific'), ('name', 'path', 'count'))
        if specific:
            result['specific'] = specific
        return result

    def get_flag_node_generators_spec(self, rng: random.Random | None = None) -> dict:
        """Return normalized topology-level flag-node-generator parameters."""
        generators = self.spec.get('flag_node_generators', {})
        result = {
            # Flag-node-generators are an opt-in topology feature.  Keeping an
            # omitted section disabled preserves the intent of existing specs
            # and avoids requiring an installed generator catalog unexpectedly.
            'enabled': self._feature_enabled(
                generators,
                activation_keys=('count', 'include', 'exclude', 'specific'),
                default=False,
            ),
            'count': self._resolve_value(generators.get('count', 0), rng=rng),
            'include': self._normalize_string_list(generators.get('include')),
            'exclude': self._normalize_string_list(generators.get('exclude')),
        }
        specific = self._normalize_specific_entries(generators.get('specific'), ('id', 'name', 'count'))
        if specific:
            result['specific'] = specific
        return result

    def get_flows_spec(self, rng: random.Random | None = None) -> dict:
        flows = self.spec.get('flows', {})
        return {
            'enabled': self._feature_enabled(flows, activation_keys=('chain_length', 'count')),
            'chain_length': self._resolve_value(flows.get('chain_length', flows.get('count', [3, 5])), rng=rng),
            'allow_duplicates': flows.get('allow_duplicates', False),
            # This is stored in FlowState for ScenarioForge's sequencing UI and
            # is ready for its corresponding CLI option when that is exposed.
            'include_all_topology_pivots': bool(flows.get('include_all_topology_pivots', False)),
        }

    def get_segmentation_spec(self, rng: random.Random | None = None) -> dict:
        seg = self.spec.get('segmentation', {})
        items = []
        for item in seg.get('items') or []:
            if not isinstance(item, dict):
                continue
            selected = str(item.get('type', item.get('selected', ''))).strip().lower()
            display_name = {'firewall': 'Firewall', 'nat': 'NAT'}.get(selected)
            if not display_name:
                continue
            count = self._resolve_value(item.get('count', 1), rng=rng)
            try:
                count = int(count)
            except (TypeError, ValueError):
                continue
            if count <= 0:
                continue
            normalized = {
                'selected': display_name,
                'v_metric': 'Count',
                'v_count': count,
                'factor': item.get('factor', 1.0),
                'pivot_enabled': bool(item.get('pivot_enabled', False)),
            }
            if normalized['pivot_enabled']:
                normalized['pivot_provider'] = str(item.get('pivot_provider', 'random')).strip() or 'random'
            for key in ('requires', 'produces'):
                if item.get(key) not in (None, ''):
                    normalized[key] = str(item[key]).strip()
            items.append(normalized)
        return {
            'enabled': self._feature_enabled(seg, activation_keys=('density', 'items')),
            'density': seg.get('density', 0.5),
            'items': items,
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

    @staticmethod
    def _normalize_specific_entries(values, allowed_keys: tuple[str, ...]) -> list[dict]:
        if not isinstance(values, list):
            return []
        normalized = []
        for value in values:
            if not isinstance(value, dict):
                continue
            entry = {key: value[key] for key in allowed_keys if key in value}
            if entry:
                normalized.append(entry)
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
