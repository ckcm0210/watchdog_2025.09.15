import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Optional

# Minimal XML reader that maps sheet name -> { address: value }
# Fast path for cached values (v) and formulas (f) if needed later.

def read_values_from_xlsx_via_xml(xlsx_path: str) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Read display values (cached values) for all sheets using raw XML parsing.
    Returns: { sheet_name: { 'A1': value, ... }, ... }
    Note: sharedStrings and basic types handled; dates kept as raw numbers for speed.
    """
    # 安全性修正：確保使用快取副本而非直接讀取原始檔案
    from utils.cache import copy_to_cache
    local_path = copy_to_cache(xlsx_path, silent=True)
    if not local_path:
        return {}
    
    with zipfile.ZipFile(local_path, 'r') as z:
        # Build shared strings (if any)
        shared_strings = []
        try:
            if 'xl/sharedStrings.xml' in z.namelist():
                ss_xml = z.read('xl/sharedStrings.xml')
                root = ET.fromstring(ss_xml)
                ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('a:si', ns):
                    # concatenate all t nodes
                    text_parts = []
                    for t in si.findall('.//a:t', ns):
                        text_parts.append(t.text or '')
                    shared_strings.append(''.join(text_parts))
        except Exception:
            shared_strings = []
        # Map sheet id -> name and relationships
        sheet_names = []
        try:
            wb_xml = z.read('xl/workbook.xml')
            wroot = ET.fromstring(wb_xml)
            ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for s in wroot.findall('a:sheets/a:sheet', ns):
                sheet_names.append(s.attrib.get('name', f'Sheet{len(sheet_names)+1}'))
        except Exception:
            # Fallback: generate generic names
            pass

        result: Dict[str, Dict[str, Optional[str]]] = {}
        for idx, name in enumerate(sheet_names, start=1):
            path = f'xl/worksheets/sheet{idx}.xml'
            if path not in z.namelist():
                continue
            try:
                xml = z.read(path)
                root = ET.fromstring(xml)
                ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                values: Dict[str, Optional[str]] = {}
                for c in root.findall('.//a:c', ns):
                    addr = c.attrib.get('r')
                    if not addr:
                        continue
                    t = c.attrib.get('t')  # type
                    v_node = c.find('a:v', ns)
                    if v_node is None:
                        continue
                    raw = v_node.text
                    if raw is None:
                        val = None
                    elif t == 's':
                        try:
                            idx = int(raw)
                            val = shared_strings[idx] if 0 <= idx < len(shared_strings) else ''
                        except Exception:
                            val = ''
                    elif t == 'b':
                        val = 'TRUE' if raw in ('1', 'true', 'TRUE') else 'FALSE'
                    else:
                        # number or general
                        val = raw
                    values[addr] = val
                result[name] = values
            except Exception:
                continue
        return result
