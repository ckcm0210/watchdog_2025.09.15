from typing import Dict, Optional
from io import BytesIO
import subprocess
import sys
import os

# Polars-based value reader via xlsx2csv -> CSV in-memory

def _xlsx2csv_to_bytes(xlsx_path: str, sheet_count: int | None = None) -> Dict[str, bytes]:
    """
    Convert each worksheet to CSV bytes via xlsx2csv.
    Returns: { sheet_name: csv_bytes }
    Prints diagnostic info (rc/stdout/stderr) for troubleshooting.
    """
    sheets: Dict[str, bytes] = {}
    # List sheets
    try:
        # Try list-sheets first
        cmd_list = [sys.executable, '-m', 'xlsx2csv', '--list-sheets', xlsx_path]
        proc = subprocess.run(cmd_list, capture_output=True, text=True)
        rc = proc.returncode
        out = proc.stdout or ''
        err = proc.stderr or ''
        names = [ln.strip() for ln in out.splitlines() if ln.strip()]
        print(f"   [polars-xlsx2csv] list rc={rc} names={names} err={(err.strip()[:200] if err else '')}")
        if rc != 0 or not names:
            # Fallback: brute-force by index if sheet_count provided
            if sheet_count:
                print(f"   [polars-xlsx2csv] fallback brute-force by index 1..{sheet_count}")
                for i in range(1, sheet_count+1):
                    cmd_fetch = [sys.executable, '-m', 'xlsx2csv', '-s', str(i), xlsx_path]
                    proc2 = subprocess.run(cmd_fetch, capture_output=True, text=False)
                    rc2 = proc2.returncode
                    if rc2 != 0:
                        e2 = (proc2.stderr.decode('utf-8', 'ignore') if proc2.stderr else '')
                        print(f"   [polars-xlsx2csv] fetch sheet#{i} rc={rc2} err={e2[:200]}")
                        continue
                    sheets[f"sheet{i}"] = proc2.stdout
                return sheets
            return {}
        # Fetch each sheet by discovered names
        for i, name in enumerate(names, start=1):
            cmd_fetch = [sys.executable, '-m', 'xlsx2csv', '-s', str(i), xlsx_path]
            proc2 = subprocess.run(cmd_fetch, capture_output=True, text=False)
            rc2 = proc2.returncode
            if rc2 != 0:
                e2 = (proc2.stderr.decode('utf-8', 'ignore') if proc2.stderr else '')
                print(f"   [polars-xlsx2csv] fetch sheet#{i} rc={rc2} name='{name}' err={e2[:200]}")
                continue
            sheets[name] = proc2.stdout
    except Exception as e:
        print(f"   [polars-xlsx2csv] exception: {e}")
    return sheets


def read_values_from_xlsx_via_polars(xlsx_path: str, persist_csv: bool=False, persist_dir: Optional[str]=None, sheet_count: int | None = None) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Read display values using xlsx2csv + polars.
    Returns: { sheet_name: { 'A1': value, ... }, ... }
    If persist_csv=True and persist_dir provided, save ONE combined CSV per workbook at:
      <persist_dir>/values/<baseline_key>.values.csv
    CSV columns: sheet,address,value
    """
    import polars as pl
    try:
        from utils.helpers import _baseline_key_for_path
    except Exception:
        _baseline_key_for_path = lambda p: os.path.basename(p)

    out: Dict[str, Dict[str, Optional[str]]] = {}
    sheets = _xlsx2csv_to_bytes(xlsx_path, sheet_count=sheet_count)
    combined_rows = []  # (sheet, address, value)
    for name, csv_bytes in (sheets or {}).items():
        try:
            # Read CSV into Polars (in-memory)
            df = pl.read_csv(BytesIO(csv_bytes), has_header=False)
            if df.height == 0 or df.width == 0:
                out[name] = {}
                continue
            # wide -> long with addresses
            # rows: 1..N ; cols: 1..M -> address like A1, B2
            def col_to_letters(n: int) -> str:
                s = ''
                while n > 0:
                    n, r = divmod(n-1, 26)
                    s = chr(65 + r) + s
                return s
            long_rows = []
            for r in range(df.height):
                row = df.row(r)
                for c in range(len(row)):
                    v = row[c]
                    if v is None or (isinstance(v, str) and v == ''):
                        continue  # skip blanks to align with openpyxl behaviour
                    addr = f"{col_to_letters(c+1)}{r+1}"
                    # 保留原型別避免假差異
                    sval = v
                    long_rows.append((addr, sval))
                    # 合併 CSV 需字串化
                    csv_v = '' if v is None else str(v).replace('"','""')
                    combined_rows.append((name, addr, csv_v))
            out[name] = {addr: val for addr, val in long_rows}
        except Exception:
            out[name] = {}
    # Persist ONE combined CSV if requested
    if persist_csv and persist_dir and combined_rows:
        try:
            base_key = _baseline_key_for_path(xlsx_path)
            values_dir = os.path.join(persist_dir, 'values')
            os.makedirs(values_dir, exist_ok=True)
            out_path = os.path.join(values_dir, f"{base_key}.values.csv")
            with open(out_path, 'w', encoding='utf-8', newline='') as f:
                f.write('sheet,address,value\n')
                for sheet, addr, val in combined_rows:
                    # escape quotes and commas if necessary (basic CSV)
                    v = '' if val is None else str(val).replace('"','""')
                    f.write(f'"{sheet}","{addr}","{v}"\n')
        except Exception:
            pass
    return out
