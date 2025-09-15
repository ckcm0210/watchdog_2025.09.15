import threading
import time
from typing import Callable, Optional
import os
import config.settings as settings

class ObserverHealthMonitor:
    """
    監控 Watchdog Observer 健康狀態：
    - 每 interval 秒檢查一次 is_alive() 與最近事件時間（LAST_DISPATCH_TS）
    - 可選 probe：在 watch 資料夾寫入一個臨時檔案驗證事件流是否正常
    - 異常時可自動重建（透過外部提供的 restart_callback）
    """
    def __init__(self,
                 observer_getter: Callable[[], object],
                 restart_callback: Callable[[], bool],
                 watch_roots_getter: Callable[[], list],
                 last_dispatch_getter: Optional[Callable[[], float]] = None,
                 interval_sec: Optional[float] = None,
                 stall_threshold_sec: Optional[float] = None,
                 probe_enabled: Optional[bool] = None,
                 probe_timeout_sec: Optional[float] = None,
                 auto_restart: Optional[bool] = None):
        self._observer_getter = observer_getter
        self._restart_callback = restart_callback
        self._watch_roots_getter = watch_roots_getter
        self._last_dispatch_getter = last_dispatch_getter or (lambda: float(getattr(settings, 'LAST_DISPATCH_TS', 0.0) or 0.0))
        self._interval = float(interval_sec if interval_sec is not None else getattr(settings, 'OBSERVER_HEALTHCHECK_INTERVAL_SEC', 5))
        self._stall_threshold = float(stall_threshold_sec if stall_threshold_sec is not None else getattr(settings, 'OBSERVER_STALL_THRESHOLD_SEC', 20))
        self._probe_enabled = bool(probe_enabled if probe_enabled is not None else getattr(settings, 'OBSERVER_PROBE_ENABLED', True))
        self._probe_timeout = float(probe_timeout_sec if probe_timeout_sec is not None else getattr(settings, 'OBSERVER_PROBE_TIMEOUT_SEC', 3))
        self._auto_restart = bool(auto_restart if auto_restart is not None else getattr(settings, 'ENABLE_AUTO_RESTART_OBSERVER', True))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='observer-health', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set() and not getattr(settings, 'force_stop', False):
            try:
                obs = self._observer_getter()
                alive = False
                try:
                    alive = bool(obs and getattr(obs, 'is_alive', lambda: False)())
                except Exception:
                    alive = False
                if not alive:
                    print('[health] [error] observer is not alive')
                    if self._auto_restart:
                        ok = self._restart_callback()
                        print(f"[health] [auto-restart] observer restart {'OK' if ok else 'FAILED'}")
                        # 重建後給點時間再檢查
                        time.sleep(self._interval)
                        continue

                # 檢查事件停滯
                last_ts = float(self._last_dispatch_getter() or 0.0)
                idle = (time.time() - last_ts) if last_ts > 0 else None
                if idle is not None and idle > self._stall_threshold:
                    print(f"[health] [warn] no events for {idle:.1f}s (threshold={self._stall_threshold}s)")
                    # Probe 驗證
                    if self._probe_enabled:
                        if not self._probe_once():
                            print('[health] [error] probe failed (no event captured)')
                            if self._auto_restart:
                                ok = self._restart_callback()
                                print(f"[health] [auto-restart] observer restart {'OK' if ok else 'FAILED'}")
                                time.sleep(self._interval)
                                continue
            except Exception:
                pass
            time.sleep(self._interval)

    def _probe_once(self) -> bool:
        try:
            roots = list(self._watch_roots_getter() or [])
            if not roots:
                return False
            root = None
            for r in roots:
                try:
                    if os.path.isdir(r):
                        root = r
                        break
                except Exception:
                    pass
            if not root:
                return False
            # 在根目錄建立一個臨時檔並立即刪除
            import uuid
            name = f"._probe_{uuid.uuid4().hex}.tmp"
            path = os.path.join(root, name)
            pre = float(self._last_dispatch_getter() or 0.0)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('probe')
            try:
                os.remove(path)
            except Exception:
                pass
            # 等待事件抵達（更新 last_dispatch）
            start = time.time()
            while time.time() - start < self._probe_timeout:
                cur = float(self._last_dispatch_getter() or 0.0)
                if cur > pre:
                    return True
                time.sleep(0.1)
            return False
        except Exception:
            return False
