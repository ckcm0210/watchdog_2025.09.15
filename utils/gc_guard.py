"""
GC 守護工具：在指定區塊內暫停循環垃圾回收（引用計數仍然生效），離開時恢復並可選擇觸發一次收集。
用法：

from utils.gc_guard import gc_guard
with gc_guard(enabled=True, do_collect=True):
    # openpyxl 解析或其他需避免 GC 插入的臨界區
    ...
"""
from contextlib import contextmanager
import gc
import threading

@contextmanager
def gc_guard(enabled: bool = True, do_collect: bool = True):
    """
    在 with 期間暫停循環 GC；離開時恢復原狀，並可選擇觸發一次 gc.collect()。
    注意：此為進程層級設定；請將守護區塊保持盡可能短。
    """
    if not enabled:
        yield
        return
    # 僅在主執行緒才暫停 GC，避免與 Tk/Tcl 內部的 async handler 發生意外交叉
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    was_enabled = gc.isenabled()
    try:
        if was_enabled:
            gc.disable()
        yield
    finally:
        try:
            if was_enabled:
                gc.enable()
            # 移除 gc.collect() 以避免在 XML 解析後立即觸發 GC 導致 0x80000003 崩潰
            # if do_collect:
            #     try:
            #         gc.collect()
            #     except Exception:
            #         pass
        except Exception:
            pass

@contextmanager
def gc_guard_any_thread(enabled: bool = True, do_collect: bool = False):
    """
    在任何執行緒中暫停循環 GC（引用計數仍生效）。
    - 僅用於極短、明確的關鍵區段（例如 openpyxl load/iter_rows、ElementTree feed）。
    - 預設不在離開時強制 gc.collect()。
    """
    if not enabled:
        yield
        return
    was_enabled = gc.isenabled()
    try:
        if was_enabled:
            gc.disable()
        yield
    finally:
        try:
            if was_enabled:
                gc.enable()
            # 預設不做強制收集，避免撞上 ET 的邊界行為
            if do_collect:
                try:
                    gc.collect()
                except Exception:
                    pass
        except Exception:
            pass
