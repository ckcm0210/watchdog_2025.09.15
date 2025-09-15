import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Dict, Optional
import time

import config.settings as settings

class CompareTaskQueue:
    """
    簡單比較任務佇列：
    - 限制同時並行的比較數量（MAX_CONCURRENT_COMPARES）
    - 支援同檔案的任務去重（只保留最新）
    - 提供 submit 與 stop 介面
    """
    def __init__(self, worker: Callable[[str, Optional[int]], bool]):
        self.worker = worker  # worker(file_path, event_number) -> bool
        self.max_workers = max(1, int(getattr(settings, 'MAX_CONCURRENT_COMPARES', 2)))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="compare")
        self.lock = threading.Lock()
        self.pending: Dict[str, Future] = {}  # file_path -> Future
        self.stopped = False

    def submit(self, file_path: str, event_number: Optional[int] = None) -> bool:
        if self.stopped:
            return False
        # 去重：同一檔已有未完成的任務，取消舊的，提交新的
        if getattr(settings, 'DEDUP_PENDING_EVENTS', True):
            with self.lock:
                old = self.pending.get(file_path)
                if old and not old.done():
                    try:
                        old.cancel()
                    except Exception:
                        pass
        def _run():
            try:
                return self.worker(file_path, event_number)
            finally:
                with self.lock:
                    try:
                        self.pending.pop(file_path, None)
                    except Exception:
                        pass
        fut = self.executor.submit(_run)
        with self.lock:
            self.pending[file_path] = fut
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            try:
                print(f"   [queue] submit file='{file_path}' evt={event_number} pending={len(self.pending)}")
            except Exception:
                pass
        return True

    def stop(self):
        self.stopped = True
        with self.lock:
            items = list(self.pending.items())
            self.pending.clear()
        # 取消所有未完成的任務
        for _, fut in items:
            try:
                fut.cancel()
            except Exception:
                pass
        self.executor.shutdown(wait=False, cancel_futures=True)

# 全域單例（按需初始化）
_compare_queue: Optional[CompareTaskQueue] = None


def get_compare_queue(worker: Callable[[str, Optional[int]], bool]) -> CompareTaskQueue:
    global _compare_queue
    if _compare_queue is None:
        _compare_queue = CompareTaskQueue(worker)
    return _compare_queue
