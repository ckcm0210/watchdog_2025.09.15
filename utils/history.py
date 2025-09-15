"""
History snapshot utilities (MVP)
- Save a full workbook snapshot (cells) after each visible compare with changes.
- Maintain a per-file index (CSV gz) for quick timeline lookup.
"""
from __future__ import annotations
import os
import gzip
import json
from datetime import datetime
from typing import Dict, Any, Optional
import config.settings as settings

try:
    from utils.helpers import _baseline_key_for_path
except Exception:
    def _baseline_key_for_path(p: str) -> str:
        import os, hashlib
        norm = os.path.normcase(os.path.abspath(p))
        h = hashlib.sha1(norm.encode('utf-8')).hexdigest()[:8]
        return f"{os.path.basename(p)}__{h}"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _now_stamp() -> str:
    # High-resolution timestamp for unique filenames
    return datetime.now().strftime('%Y%m%d_%H%M%S_%f')


def find_latest_snapshot_for_file(file_path: str) -> Optional[str]:
    """
    尋找指定檔案最近的快照路徑（用於無變更事件的快照連結）
    """
    try:
        # 取得 base_key（與 baseline 相同邏輯）
        base_key = _baseline_key_for_path(file_path)
        
        # 搜尋該檔案專用的 history 子目錄
        file_history_dir = os.path.join(getattr(settings, 'LOG_FOLDER', '.'), 'history', base_key)
        if not os.path.exists(file_history_dir):
            return None
            
        # 尋找該目錄下的最新快照檔案
        snapshots = []
        
        for filename in os.listdir(file_history_dir):
            if filename.endswith('.cells.json') and ('lz4' in filename or 'gz' in filename or 'json' in filename):
                full_path = os.path.join(file_history_dir, filename)
                if os.path.isfile(full_path):
                    mtime = os.path.getmtime(full_path)
                    snapshots.append((mtime, full_path))
        
        if snapshots:
            # 按修改時間排序，返回最新的
            snapshots.sort(key=lambda x: x[0], reverse=True)
            return snapshots[0][1]  # 返回最新快照的完整路徑
            
        return None
        
    except Exception:
        return None


def save_history_snapshot(file_path: str,
                          cells: Dict[str, Dict[str, Any]],
                          *,
                          last_author: Optional[str] = None,
                          event_number: Optional[int] = None,
                          meaningful_changes_count: Optional[int] = None) -> Optional[str]:
    """
    Save a compressed JSON snapshot under LOG_FOLDER/history/<base_key>/.
    Returns the snapshot file path (with compression extension) or None on error.
    """
    try:
        if not getattr(settings, 'ENABLE_HISTORY_SNAPSHOT', True):
            return None
        base_key = _baseline_key_for_path(file_path)
        history_dir = os.path.join(settings.LOG_FOLDER, 'history', base_key)
        _ensure_dir(history_dir)
        # Build snapshot payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'file': os.path.abspath(file_path),
            'last_author': last_author or 'Unknown',
            'event_number': event_number,
            'cells': cells or {},
        }
        # File base (without compression extension)
        ts = _now_stamp()
        base_path = os.path.join(history_dir, f"{ts}.cells.json")
        # Use the same compression facility as baselines
        from utils.compression import save_compressed_file
        actual_file = save_compressed_file(base_path, payload, getattr(settings, 'DEFAULT_COMPRESSION_FORMAT', 'lz4'))
        # Append to index
        try:
            index_path = os.path.join(history_dir, 'index.csv.gz')
            exists = os.path.exists(index_path)
            with gzip.open(index_path, 'at', encoding='utf-8', newline='') as f:
                if not exists:
                    f.write('timestamp,event,last_author,changes_count,snapshot_file\n')
                f.write(f'"{payload["timestamp"]}",{event_number or ""},"{payload["last_author"]}",{meaningful_changes_count or 0},"{os.path.basename(actual_file)}"\n')
        except Exception:
            pass
        return actual_file
    except Exception:
        return None


def compute_change_counters(old_cells: Dict[str, Dict[str, Any]], new_cells: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """
    計算事件統計計數：dvc/fci/xrlc/xru/addc/delc/total_changes
    與 Compare_Logic 定義一致。
    """
    from core.comparison import classify_change_type
    counters = {k: 0 for k in ['dvc','fci','xrlc','xru','addc','delc']}
    total = 0
    sheets = set((old_cells or {}).keys()) | set((new_cells or {}).keys())
    for s in sheets:
        a = (old_cells or {}).get(s, {})
        b = (new_cells or {}).get(s, {})
        addrs = set(a.keys()) | set(b.keys())
        for addr in addrs:
            oa = a.get(addr, {})
            nb = b.get(addr, {})
            if oa == nb:
                continue
            total += 1
            t = classify_change_type(oa, nb,
                                     show_external_refresh=True,
                                     suppress_internal_same_value=False,
                                     formula_only_mode=False)
            if t == 'CELL_ADDED': counters['addc'] += 1
            elif t == 'CELL_DELETED': counters['delc'] += 1
            elif t == 'DIRECT_VALUE_CHANGE': counters['dvc'] += 1
            elif t == 'FORMULA_CHANGE_INTERNAL': counters['fci'] += 1
            elif t == 'EXTERNAL_REF_LINK_CHANGE': counters['xrlc'] += 1
            elif t == 'EXTERNAL_REFRESH_UPDATE': counters['xru'] += 1
            # 其他（INDIRECT/NO_CHANGE）不計入上述細項，但 total 仍計
    counters['total_changes'] = total
    return counters


def insert_event_index(file_path: str,
                        *,
                        old_cells: Dict[str, Dict[str, Any]] = None,
                        new_cells: Dict[str, Dict[str, Any]] = None,
                        last_author: Optional[str] = None,
                        event_number: Optional[int] = None,
                        snapshot_path: Optional[str] = None,
                        summary_path: Optional[str] = None,
                        git_commit_sha: Optional[str] = None,
                        db_path: Optional[str] = None) -> None:
    """
    根據 counters 與路徑資訊，插入一筆事件索引到 SQLite。
    """
    try:
        from utils.helpers import _baseline_key_for_path
        from utils.events_db import insert_event as _insert, ensure_db
        base_key = _baseline_key_for_path(file_path)
        ensure_db(db_path)
        counters = compute_change_counters(old_cells or {}, new_cells or {})
        # 檔案 stat
        try:
            excel_mtime = os.path.getmtime(file_path)
            source_size = os.path.getsize(file_path)
        except Exception:
            excel_mtime = None
            source_size = None
        evt = {
            'base_key': base_key,
            'file_path': os.path.abspath(file_path),
            'event_time': datetime.now().isoformat(),
            'excel_mtime': excel_mtime,
            'source_size': source_size,
            'last_author': last_author or 'Unknown',
            'git_commit_sha': git_commit_sha,
            'snapshot_path': snapshot_path or '',
            'summary_path': summary_path or '',
            **counters,
        }
        _insert(evt, db_path=db_path)
    except Exception:
        pass


def sync_history_to_git_repo(file_path: str, 
                             cells: Dict[str, Dict[str, Any]],
                             *,
                             last_author: Optional[str] = None,
                             event_number: Optional[int] = None,
                             meaningful_changes_count: Optional[int] = None,
                             repo_path: Optional[str] = None) -> Optional[str]:
    """
    Write a plain JSON snapshot into a Git repo and commit it.
    Returns the absolute path of the JSON written into the repo, or None on error.
    """
    try:
        if not getattr(settings, 'ENABLE_HISTORY_SNAPSHOT', True):
            return None
        # repo path default
        repo_root = repo_path or getattr(settings, 'HISTORY_GIT_REPO_PATH', None) or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'excel_git_repo')
        os.makedirs(repo_root, exist_ok=True)
        base_key = _baseline_key_for_path(file_path)
        target_dir = os.path.join(repo_root, 'history', base_key)
        _ensure_dir(target_dir)
        # Build payload
        payload = {
            'timestamp': datetime.now().isoformat(),
            'file': os.path.abspath(file_path),
            'last_author': last_author or 'Unknown',
            'event_number': event_number,
            'changes_count': meaningful_changes_count or 0,
            'cells': cells or {},
        }
        # Write plain JSON
        out_name = f"{_now_stamp()}.cells.json"
        out_path = os.path.join(target_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # 若已禁用 Git 整合，僅落地 JSON，不嘗試提交
        if getattr(settings, 'DISABLE_GIT_INTEGRATION', False):
            return out_path
        # Commit via GitPython if available
        try:
            import git
            try:
                repo = git.Repo(repo_root)
            except Exception:
                repo = git.Repo.init(repo_root)
            rel_path = os.path.relpath(out_path, repo_root)
            repo.index.add([rel_path])
            msg = f"history: {os.path.basename(file_path)} event={event_number} author={payload['last_author']} changes={payload['changes_count']}"
            repo.index.commit(msg)
        except Exception:
            # Git 不可用時，單純落地 JSON，不報錯
            pass
        return out_path
    except Exception:
        return None
