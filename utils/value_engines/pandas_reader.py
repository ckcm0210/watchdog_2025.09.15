from typing import Dict, Optional
from io import BytesIO
import subprocess
import sys
import os

# Pandas-based value reader via xlsx2csv -> CSV in-memory (fallback-friendly)

def _xlsx2csv_to_bytes(xlsx_path: str, sheet_count: int | None = None) -> Dict[str, bytes]:
    sheets: Dict[str, bytes] = {}
    try:
        cmd_list = [sys.executable, '-m', 'xlsx2csv', '--list-sheets', xlsx_path]
        proc = subprocess.run(cmd_list, capture_output=True, text=True)
        rc = proc.returncode
        out = proc.stdout or ''
        err = proc.stderr or ''
        names = [ln.strip() for ln in out.splitlines() if ln.strip()]
        print(f"   [pandas-xlsx2csv] list rc={rc} names={names} err={(err.strip()[:200] if err else '')}")
        if rc != 0 or not names:
            if sheet_count:
                print(f"   [pandas-xlsx2csv] fallback brute-force by index 1..{sheet_count}")
                for i in range(1, sheet_count+1):
                    cmd_fetch = [sys.executable, '-m', 'xlsx2csv', '-s', str(i), xlsx_path]
                    proc2 = subprocess.run(cmd_fetch, capture_output=True, text=False)
                    if proc2.returncode != 0:
                        e2 = (proc2.stderr.decode('utf-8', 'ignore') if proc2.stderr else '')
                        print(f"   [pandas-xlsx2csv] fetch sheet#{i} rc={proc2.returncode} err={e2[:200]}")
                        continue
                    sheets[f"sheet{i}"] = proc2.stdout
                return sheets
            return {}
        for i, name in enumerate(names, start=1):
            cmd_fetch = [sys.executable, '-m', 'xlsx2csv', '-s', str(i), xlsx_path]
            proc2 = subprocess.run(cmd_fetch, capture_output=True, text=False)
            if proc2.returncode != 0:
                e2 = (proc2.stderr.decode('utf-8', 'ignore') if proc2.stderr else '')
                print(f"   [pandas-xlsx2csv] fetch sheet#{i} rc={proc2.returncode} name='{name}' err={e2[:200]}")
                continue
            sheets[name] = proc2.stdout
    except Exception as e:
        print(f"   [pandas-xlsx2csv] exception: {e}")
    return sheets


def read_values_from_xlsx_via_pandas(xlsx_path: str, persist_csv: bool=False, persist_dir: Optional[str]=None, sheet_count: int | None = None) -> Dict[str, Dict[str, Optional[str]]]:
    import pandas as pd
    try:
        from utils.helpers import _baseline_key_for_path
    except Exception:
        _baseline_key_for_path = lambda p: os.path.basename(p)

    out: Dict[str, Dict[str, Optional[str]]] = {}
    sheets = _xlsx2csv_to_bytes(xlsx_path, sheet_count=sheet_count)
    combined_rows = []  # (sheet, address, value)

    def col_to_letters(n: int) -> str:
        s = ''
        while n > 0:
            n, r = divmod(n-1, 26)
            s = chr(65 + r) + s
        return s

    for name, csv_bytes in (sheets or {}).items():
        try:
            df = pd.read_csv(BytesIO(csv_bytes), header=None)
            if df.shape[0] == 0 or df.shape[1] == 0:
                out[name] = {}
                continue
            vals: Dict[str, Optional[str]] = {}
            for r in range(df.shape[0]):
                row = df.iloc[r]
                for c in range(len(row)):
                    v = row.iloc[c]
                    if pd.isna(v) or (isinstance(v, str) and v == ''):
                        continue
                    addr = f"{col_to_letters(c+1)}{r+1}"
                    vals[addr] = v
                    combined_rows.append((name, addr, '' if v is None else str(v)))
            out[name] = vals
        except Exception:
            out[name] = {}

    if persist_csv and persist_dir and combined_rows:
        try:
            base_key = _baseline_key_for_path(xlsx_path)
            values_dir = os.path.join(persist_dir, 'values')
            os.makedirs(values_dir, exist_ok=True)
            out_path = os.path.join(values_dir, f"{base_key}.values.csv")
            with open(out_path, 'w', encoding='utf-8', newline='') as f:
                f.write('sheet,address,value\n')
                for sheet, addr, val in combined_rows:
                    v = '' if val is None else str(val).replace('"','""')
                    f.write(f'"{sheet}","{addr}","{v}"\n')
        except Exception:
            pass

    return out
