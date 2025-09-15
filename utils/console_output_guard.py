import threading
from collections import deque
from typing import Deque, Optional, Callable

# 全域 console 輸出保護器：
# - 確保比較表（大型表格）原子輸出（不中途插入其他訊息）
# - 表格期間的其他訊息會緩存，待表格結束後再 flush

_backend_print: Optional[Callable[[str], None]] = None
_print_lock = threading.RLock()
_printing_table_owner: Optional[int] = None
_buffer: Deque[str] = deque(maxlen=1000)


def set_backend_print(fn: Callable[[str], None]) -> None:
    """註冊底層輸出函式（通常是原生 print）。"""
    global _backend_print
    _backend_print = fn


def safe_print(line: str) -> None:
    """安全列印：
    - 有表格持有者時，非持有者的訊息將被緩存，避免插入表格中間。
    - 無持有者時，短暫加鎖直接輸出。
    """
    global _buffer
    me = threading.get_ident()
    # 表格進行中，且我不是持有者 → 嘗試非阻塞鎖；拿不到則緩存
    if _printing_table_owner is not None and _printing_table_owner != me:
        if not _print_lock.acquire(blocking=False):
            try:
                _buffer.append(line)
            except Exception:
                pass
            return
        try:
            if _backend_print:
                _backend_print(line)
            return
        finally:
            _print_lock.release()

    # 正常輸出路徑
    with _print_lock:
        if _backend_print:
            _backend_print(line)


def begin_table_output():
    """開始表格原子輸出（手動模式）。"""
    global _printing_table_owner
    _print_lock.acquire()
    _printing_table_owner = threading.get_ident()


def end_table_output():
    """結束表格原子輸出並 flush 緩存（手動模式）。"""
    global _printing_table_owner
    try:
        while _buffer:
            ln = _buffer.popleft()
            if _backend_print:
                _backend_print(ln)
    finally:
        _printing_table_owner = None
        _print_lock.release()


class print_table_block:
    """表格原子輸出區塊：開始時鎖住並標記持有者；結束時 flush 緩存並釋放鎖。"""
    def __enter__(self):
        global _printing_table_owner
        _print_lock.acquire()
        _printing_table_owner = threading.get_ident()
        return self

    def __exit__(self, exc_type, exc, tb):
        global _printing_table_owner
        try:
            # flush 期間允許其他執行緒追加（鎖仍由我持有）
            while _buffer:
                ln = _buffer.popleft()
                if _backend_print:
                    _backend_print(ln)
        finally:
            _printing_table_owner = None
            _print_lock.release()
