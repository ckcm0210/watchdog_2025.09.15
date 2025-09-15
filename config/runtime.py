"""
Runtime settings persistence and application utilities.
This module loads/saves a JSON file and applies values into config.settings safely.
"""
import os
import json
from typing import Any, Dict
import config.settings as settings

RUNTIME_JSON_PATH = os.path.join(os.path.dirname(__file__), 'runtime_settings.json')

_BOOLEAN_TRUE = {'1','true','t','yes','y','on','True','TRUE'}
_BOOLEAN_FALSE = {'0','false','f','no','n','off','False','FALSE'}


def _coerce_type(key: str, new_value: Any):
    """Coerce new_value to the same type as current settings.<"""
    if not hasattr(settings, key):
        return new_value
    cur = getattr(settings, key)
    # None: accept as-is
    if cur is None:
        return new_value
    # bool
    if isinstance(cur, bool):
        if isinstance(new_value, bool):
            return new_value
        if isinstance(new_value, (int, float)):
            return bool(new_value)
        if isinstance(new_value, str):
            v = new_value.strip()
            if v in _BOOLEAN_TRUE:
                return True
            if v in _BOOLEAN_FALSE:
                return False
        return bool(new_value)
    # int
    if isinstance(cur, int) and not isinstance(cur, bool):
        try:
            return int(float(new_value))
        except Exception:
            return cur
    # float
    if isinstance(cur, float):
        try:
            return float(new_value)
        except Exception:
            return cur
    # list/tuple
    if isinstance(cur, (list, tuple)):
        # preserve original container type (list vs tuple)
        to_tuple = isinstance(cur, tuple)
        # Build items list from new_value
        items = []
        if isinstance(new_value, (list, tuple)):
            items = [str(x).strip() for x in new_value]
        elif isinstance(new_value, str):
            # split by comma or newlines/semicolons
            s = new_value.replace('\r', '').replace(';', '\n').replace(',', '\n')
            items = [x.strip() for x in s.split('\n') if x.strip()]
        else:
            items = [str(new_value).strip()]
        # Special normalization for extension lists like SUPPORTED_EXTS
        if key.upper().endswith('EXTS') or key in {'SUPPORTED_EXTS'}:
            norm = []
            for x in items:
                if not x:
                    continue
                # normalize spacing, quotes and parentheses
                x = str(x).strip().lower()
                x = x.strip(" ' \"()[]{}")
                if not x:
                    continue
                if not x.startswith('.'):
                    x = '.' + x
                norm.append(x)
            # if result is empty, keep current value to avoid breaking logic
            if not norm:
                return cur
            items = norm
        # Return with original container type
        return tuple(items) if to_tuple else items
    # str or other
    return str(new_value)


def load_runtime_settings() -> Dict[str, Any]:
    if not os.path.exists(RUNTIME_JSON_PATH):
        return {}
    try:
        with open(RUNTIME_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_runtime_settings(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(RUNTIME_JSON_PATH), exist_ok=True)
    with open(RUNTIME_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_to_settings(data: Dict[str, Any]) -> None:
    """Apply runtime values into config.settings with type coercion."""
    for k, v in (data or {}).items():
        try:
            coerced = _coerce_type(k, v)
            setattr(settings, k, coerced)
        except Exception:
            # ignore bad keys silently to keep robustness
            pass
