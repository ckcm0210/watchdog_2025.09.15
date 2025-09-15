import threading
import time
from typing import Callable, Optional, List
import config.settings as settings

try:
    from utils.observer_health import ObserverHealthMonitor
except Exception:
    ObserverHealthMonitor = None  # type: ignore

class Heartbeat:
    """
    心跳服務：
    - 每 HEARTBEAT_INTERVAL_SEC 秒輸出一次 [hb] alive 訊息（經 timestamped_print → safe_print）
    - 若啟用健康檢查，內部啟動 ObserverHealthMonitor 定期檢查並（如允許）自動重建 Observer
    """
    def __init__(self,
                 observer_getter: Callable[[], object],
                 restart_callback: Callable[[], bool],
                 watch_roots_getter: Callable[[], List[str]]):
        self._observer_getter = observer_getter
        self._restart_callback = restart_callback
        self._watch_roots_getter = watch_roots_getter
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._health: Optional[ObserverHealthMonitor] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        # 啟動健康檢查（如啟用且模組可用）
        if getattr(settings, 'ENABLE_OBSERVER_HEALTHCHECK', True) and ObserverHealthMonitor is not None:
            self._health = ObserverHealthMonitor(
                observer_getter=self._observer_getter,
                restart_callback=self._restart_callback,
                watch_roots_getter=self._watch_roots_getter,
            )
            self._health.start()
        # 啟動心跳背景執行緒
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='heartbeat', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        try:
            if self._health:
                self._health.stop()
        except Exception:
            pass

    def _run(self):
        interval = int(getattr(settings, 'HEARTBEAT_INTERVAL_SEC', 30) or 30)
        while not self._stop.is_set() and not getattr(settings, 'force_stop', False):
            try:
                # 心跳訊息：統一格式 [heartbeat] alive HH:MM:SS threads=N
                import datetime, threading as _th
                ts = datetime.datetime.now().strftime('%H:%M:%S')
                try:
                    ths = len(_th.enumerate())
                except Exception:
                    ths = 'N/A'
                print(f"[heartbeat] alive {ts} threads={ths}")
            except Exception:
                pass
            # 以較短步進 sleep，能更快響應停止
            for _ in range(interval):
                if self._stop.is_set() or getattr(settings, 'force_stop', False):
                    break
                time.sleep(1)
