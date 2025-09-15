from typing import List, Tuple, Dict, Set
import os
import re


def _get_version_by_importlib(package_name: str) -> str:
    try:
        try:
            from importlib.metadata import version, PackageNotFoundError, packages_distributions  # py3.8+
        except Exception:
            from importlib_metadata import version, PackageNotFoundError, packages_distributions  # type: ignore
        try:
            return version(package_name)
        except PackageNotFoundError:
            return 'MISSING'
        except Exception:
            return 'N/A'
    except Exception:
        return 'N/A'


def _module_to_distribution_map() -> Dict[str, List[str]]:
    try:
        try:
            from importlib.metadata import packages_distributions  # py3.8+
        except Exception:
            from importlib_metadata import packages_distributions  # type: ignore
        return packages_distributions() or {}
    except Exception:
        return {}

# (display_name, distribution_name)
DEFAULT_PACKAGES: List[Tuple[str, str]] = [
    ('openpyxl', 'openpyxl'),
    ('polars', 'polars'),
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('xlsx2csv', 'xlsx2csv'),
    ('wcwidth', 'wcwidth'),
    ('watchdog', 'watchdog'),
    ('psutil', 'psutil'),
    ('lz4', 'lz4'),
    ('zstandard', 'zstandard'),
    ('lxml', 'lxml'),
    ('pywin32', 'pywin32'),
    ('colorama', 'colorama'),
    ('rich', 'rich'),
]


def get_packages_versions(packages: List[Tuple[str, str]] = None) -> List[Tuple[str, str]]:
    pkgs = packages or DEFAULT_PACKAGES
    out: List[Tuple[str, str]] = []
    for disp, dist in pkgs:
        ver = _get_version_by_importlib(dist)
        out.append((disp, ver))
    return out


def format_packages_versions_line(prefix: str = '[env]', width: int = 160, packages: List[Tuple[str, str]] = None) -> List[str]:
    try:
        from utils.logging import wrap_text_with_cjk_support
    except Exception:
        wrap_text_with_cjk_support = None
    pairs = get_packages_versions(packages)
    content = ', '.join([f"{name}={ver}" for name, ver in pairs])
    line = f"{prefix} packages: {content}"
    if wrap_text_with_cjk_support:
        return wrap_text_with_cjk_support(line, width)
    return [line]

# ------------------ 動態掃描（源碼）以擴充清單 ------------------
_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)")


def _scan_source_top_modules(root: str) -> Set[str]:
    mods: Set[str] = set()
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        m = _IMPORT_RE.match(line)
                        if not m:
                            continue
                        mod = m.group(1).split('.')[0]
                        if mod and mod not in ('__future__',):
                            mods.add(mod)
            except Exception:
                pass
    return mods


def detect_third_party_packages_versions(workspace_root: str = '.') -> List[Tuple[str, str]]:
    """
    從源碼掃描 import，映射為分發套件並取版本；只返回能取到版本的第三方。
    """
    mod2dist = _module_to_distribution_map()
    modules = _scan_source_top_modules(workspace_root)
    dists: Set[str] = set()
    for m in modules:
        try:
            dist_names = mod2dist.get(m) or []
            for dn in dist_names:
                dists.add(dn)
        except Exception:
            pass
    pairs: List[Tuple[str, str]] = []
    for dn in sorted(dists):
        ver = _get_version_by_importlib(dn)
        if ver not in ('MISSING', 'N/A'):
            pairs.append((dn, ver))
    return pairs


def format_detected_packages_versions_line(prefix: str = '[env]', width: int = 160, workspace_root: str = '.') -> List[str]:
    try:
        from utils.logging import wrap_text_with_cjk_support
    except Exception:
        wrap_text_with_cjk_support = None
    pairs = detect_third_party_packages_versions(workspace_root)
    if not pairs:
        return []
    content = ', '.join([f"{name}={ver}" for name, ver in pairs])
    line = f"{prefix} detected-packages: {content}"
    if wrap_text_with_cjk_support:
        return wrap_text_with_cjk_support(line, width)
    return [line]
