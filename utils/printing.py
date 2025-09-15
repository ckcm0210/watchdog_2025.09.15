import threading
from collections import deque
from typing import Deque, Optional, Callable

# 全域輸出協調器：確保比較表原子輸出，其他訊息在表格期間緩存/延後

_backend_print: Optional[Callable[[str], None]] = None
_print_lock = threading.RLock()
_printing_table_owner: Optional[int] = None
_buffer: Deque[str] = deque(maxlen=500)


def set_backend_print(fn: Callable[[str], None]) -> None:
    global _backend_print
    _backend_print = fn


def safe_print(line: str) -> None:
    """對外的安全列印：在表格期間，非表格執行緒會緩存訊息；否則即時輸出。
    需由 timestamped_print 呼叫，以避免遞迴（_backend_print 應是原生 print）。
    """
    global _buffer
    me = threading.get_ident()
    # 正在表格輸出：若不是擁有者，嘗試非阻塞鎖；拿不到就緩存
    if _printing_table_owner is not None and _printing_table_owner != me:
        acquired = _print_lock.acquire(blocking=False)
        if not acquired:
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

    # 正常路徑：短暫鎖定輸出，避免交錯
    with _print_lock:
        if _backend_print:
            _backend_print(line)


class print_table_block:
    """表格原子輸出區塊：擁有鎖與 flush 緩存。"""
    def __enter__(self):
        global _printing_table_owner
        _print_lock.acquire()
        _printing_table_owner = threading.get_ident()
        return self

    def __exit__(self, exc_type, exc, tb):
        global _printing_table_owner
        try:
            # flush 緩存（其他執行緒在表格期間緩存的訊息）
            while _buffer:
                ln = _buffer.popleft()
                if _backend_print:
                    _backend_print(ln)
        finally:
            _printing_table_owner = None
            _print_lock.release()
