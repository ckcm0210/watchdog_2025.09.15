# -*- coding: utf-8 -*-
"""
SQLite 事件索引（timeline index）
- 單一職責：建立/寫入/查詢事件索引，不參與快照或 Git 同步細節。
"""
from __future__ import annotations
import os
import sqlite3
from typing import Optional, Iterable, Dict, Any
import config.settings as settings

DEFAULT_DB_NAME = 'events.sqlite'


def get_db_path(preferred: Optional[str] = None) -> str:
    if preferred and preferred.strip():
        return preferred
    # 預設放在 LOG_FOLDER 下
    try:
        return os.path.join(settings.LOG_FOLDER, DEFAULT_DB_NAME)
    except Exception:
        return os.path.abspath(DEFAULT_DB_NAME)


def ensure_db(db_path: Optional[str] = None) -> str:
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              base_key TEXT NOT NULL,
              file_path TEXT NOT NULL,
              event_time TEXT,
              excel_mtime REAL,
              source_size INTEGER,
              last_author TEXT,
              git_commit_sha TEXT,
              snapshot_path TEXT,
              summary_path TEXT,
              total_changes INTEGER,
              dvc INTEGER,
              fci INTEGER,
              xrlc INTEGER,
              xru INTEGER,
              addc INTEGER,
              delc INTEGER
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_basekey_time ON events(base_key, event_time DESC)")
        conn.commit()
    finally:
        conn.close()
    return path


def insert_event(event: Dict[str, Any], db_path: Optional[str] = None) -> None:
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO events (
              base_key, file_path, event_time, excel_mtime, source_size, last_author,
              git_commit_sha, snapshot_path, summary_path,
              total_changes, dvc, fci, xrlc, xru, addc, delc
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event.get('base_key'),
                event.get('file_path'),
                event.get('event_time'),
                event.get('excel_mtime'),
                event.get('source_size'),
                event.get('last_author'),
                event.get('git_commit_sha'),
                event.get('snapshot_path'),
                event.get('summary_path'),
                int(event.get('total_changes') or 0),
                int(event.get('dvc') or 0),
                int(event.get('fci') or 0),
                int(event.get('xrlc') or 0),
                int(event.get('xru') or 0),
                int(event.get('addc') or 0),
                int(event.get('delc') or 0),
            )
        )
        conn.commit()
    finally:
        conn.close()


def query_events_by_base_key(base_key: str, db_path: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM events WHERE base_key=? ORDER BY event_time ASC, id ASC", (base_key,))
        for row in cur.fetchall():
            yield dict(row)
    finally:
        conn.close()


def get_event_by_id(event_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM events WHERE id=?", (int(event_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_neighbor_event(base_key: str, event_time: str, *, before: bool = True, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    取得同一 base_key 在指定時間點前一筆或後一筆事件。
    """
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        if before:
            cur.execute("SELECT * FROM events WHERE base_key=? AND event_time < ? ORDER BY event_time DESC, id DESC LIMIT 1", (base_key, event_time))
        else:
            cur.execute("SELECT * FROM events WHERE base_key=? AND event_time > ? ORDER BY event_time ASC, id ASC LIMIT 1", (base_key, event_time))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# --- 高階查詢 Helpers（篩選、分頁、彙總）---

def _build_where_clause(filters: Dict[str, Any], params: list) -> str:
    where = []
    # base_key exact
    bk = (filters or {}).get('base_key')
    if bk:
        where.append('base_key = ?')
        params.append(bk)
    # q on file_path/base_key
    q = (filters or {}).get('q')
    if q:
        where.append('(LOWER(file_path) LIKE ? OR LOWER(base_key) LIKE ?)')
        s = f"%{str(q).lower()}%"
        params.extend([s, s])
    # author substring
    author = (filters or {}).get('author')
    if author:
        where.append('LOWER(last_author) LIKE ?')
        params.append(f"%{str(author).lower()}%")
    # date range (ISO strings)
    from_ts = (filters or {}).get('from')
    to_ts = (filters or {}).get('to')
    if from_ts:
        where.append('event_time >= ?')
        params.append(from_ts)
    if to_ts:
        where.append('event_time <= ?')
        params.append(to_ts)
    # min_total
    min_total = (filters or {}).get('min_total')
    if isinstance(min_total, (int, float)):
        where.append('total_changes >= ?')
        params.append(int(min_total))
    # has_snapshot tri-state: True => not null/empty; False => null or empty
    hs = (filters or {}).get('has_snapshot')
    if hs is True:
        where.append('(snapshot_path IS NOT NULL AND snapshot_path != "")')
    elif hs is False:
        where.append('(snapshot_path IS NULL OR snapshot_path = "")')
    # has_summary tri-state
    hsum = (filters or {}).get('has_summary')
    if hsum is True:
        where.append('(summary_path IS NOT NULL AND summary_path != "")')
    elif hsum is False:
        where.append('(summary_path IS NULL OR summary_path = "")')
    # types: any counter > 0
    types = (filters or {}).get('types') or []
    valid_cols = {'dvc','fci','xrlc','xru','addc','delc'}
    cols = [t for t in types if t in valid_cols]
    if cols:
        where.append('(' + ' OR '.join([f'{c} > 0' for c in cols]) + ')')
    return ('WHERE ' + ' AND '.join(where)) if where else ''


def query_events(
    *,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    limit: int = 50,
    sort: str = 'DESC',
    count_total: bool = True,
    aggregates: bool = True,
    top_authors: int = 3,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query events with filters, pagination, and optional aggregates.
    Returns dict: { items, total, sums, top_authors }
    """
    path = ensure_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        params: list = []
        where_sql = _build_where_clause(filters or {}, params)
        # page/limit
        limit = max(1, min(int(limit or 50), 200))
        page = max(1, int(page or 1))
        offset = (page - 1) * limit
        order = 'DESC' if str(sort).upper() == 'DESC' else 'ASC'
        # items
        sql_items = f"SELECT * FROM events {where_sql} ORDER BY event_time {order}, id {order} LIMIT ? OFFSET ?"
        cur.execute(sql_items, params + [limit, offset])
        items = [dict(r) for r in cur.fetchall()]
        # total
        total = None
        if count_total:
            sql_cnt = f"SELECT COUNT(*) AS c FROM events {where_sql}"
            cur.execute(sql_cnt, params)
            row = cur.fetchone()
            total = int(row['c']) if row else 0
        # aggregates
        sums = None
        top = None
        if aggregates:
            sql_sum = (
                "SELECT "
                "SUM(total_changes) AS total_changes, "
                "SUM(dvc) AS dvc, SUM(fci) AS fci, SUM(xrlc) AS xrlc, SUM(xru) AS xru, "
                "SUM(addc) AS addc, SUM(delc) AS delc, "
                "COUNT(DISTINCT base_key) AS files "
                f"FROM events {where_sql}"
            )
            cur.execute(sql_sum, params)
            r = cur.fetchone()
            if r:
                sums = {k: (int(r[k]) if r[k] is not None else 0) for k in r.keys()}
            # top authors
            if (top_authors or 0) > 0:
                sql_top = f"SELECT last_author, COUNT(*) AS c FROM events {where_sql} GROUP BY last_author ORDER BY c DESC LIMIT ?"
                cur.execute(sql_top, params + [int(top_authors)])
                top = [{'last_author': rr['last_author'], 'count': int(rr['c'])} for rr in cur.fetchall()]
        return {'items': items, 'total': total, 'sums': sums, 'top_authors': top}
    finally:
        conn.close()
