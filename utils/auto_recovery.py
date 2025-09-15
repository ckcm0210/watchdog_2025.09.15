"""
自動恢復機制
檢測到系統卡住時自動重啟相關組件
"""
import threading
import time
from typing import Callable, Optional
import config.settings as settings


class AutoRecoveryManager:
    """自動恢復管理器"""
    
    def __init__(self, 
                 observer_getter: Callable[[], object],
                 observer_restart: Callable[[], bool],
                 queue_restart: Callable[[], bool]):
        self.observer_getter = observer_getter
        self.observer_restart = observer_restart
        self.queue_restart = queue_restart
        
        self.last_event_check = 0
        self.last_queue_check = 0
        self.recovery_count = 0
        self.max_recoveries = 5  # 最大恢復次數
        self.recovery_window = 3600  # 1小時內的恢復次數限制
        self.recovery_times = []
        
        self.enabled = bool(getattr(settings, 'ENABLE_AUTO_RECOVERY', True))
        self.check_interval = int(getattr(settings, 'AUTO_RECOVERY_CHECK_INTERVAL', 60))  # 檢查間隔
        self.event_timeout = int(getattr(settings, 'AUTO_RECOVERY_EVENT_TIMEOUT', 600))  # 10分鐘沒事件就檢查
        self.queue_timeout = int(getattr(settings, 'AUTO_RECOVERY_QUEUE_TIMEOUT', 300))   # 5分鐘佇列卡住就恢復
        
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """啟動自動恢復監控"""
        if not self.enabled:
            return
            
        if self._thread and self._thread.is_alive():
            return
            
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='auto-recovery', daemon=True)
        self._thread.start()
        print("[auto-recovery] 自動恢復監控已啟動")
    
    def stop(self):
        """停止自動恢復監控"""
        self._stop.set()
    
    def _run(self):
        """主監控循環"""
        while not self._stop.is_set() and not getattr(settings, 'force_stop', False):
            try:
                self._check_system_health()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"[auto-recovery] 監控錯誤: {e}")
                time.sleep(self.check_interval)
    
    def _check_system_health(self):
        """檢查系統健康狀態"""
        current_time = time.time()
        
        # 檢查事件流是否正常
        self._check_event_flow(current_time)
        
        # 檢查比較佇列是否卡住
        self._check_compare_queue(current_time)
        
        # 檢查 Observer 是否活著
        self._check_observer_status()
        
        # 清理過期的恢復記錄
        self._cleanup_recovery_history(current_time)
    
    def _check_event_flow(self, current_time: float):
        """檢查事件流"""
        try:
            last_event = float(getattr(settings, 'LAST_DISPATCH_TS', 0) or 0)
            
            if last_event == 0:
                return  # 還沒有事件，正常
            
            idle_time = current_time - last_event
            
            if idle_time > self.event_timeout:
                print(f"[auto-recovery] 檢測到事件流異常: 已 {idle_time/60:.1f} 分鐘沒有事件")
                
                # 檢查是否真的沒有檔案變更（可能是 Observer 卡住）
                if self._should_recover():
                    print("[auto-recovery] 嘗試重啟 Observer...")
                    if self._restart_observer():
                        print("[auto-recovery] Observer 重啟成功")
                    else:
                        print("[auto-recovery] Observer 重啟失敗")
                        
        except Exception as e:
            print(f"[auto-recovery] 檢查事件流錯誤: {e}")
    
    def _check_compare_queue(self, current_time: float):
        """檢查比較佇列"""
        try:
            from utils.task_queue import _compare_queue
            
            if _compare_queue is None:
                return
            
            # 檢查佇列是否有長時間未完成的任務
            if hasattr(_compare_queue, 'pending'):
                pending_count = len(_compare_queue.pending)
                
                if pending_count > 0:
                    # 如果有待處理任務，檢查是否卡住太久
                    if current_time - self.last_queue_check > self.queue_timeout:
                        print(f"[auto-recovery] 檢測到比較佇列可能卡住: {pending_count} 個待處理任務")
                        
                        if self._should_recover():
                            print("[auto-recovery] 嘗試重啟比較佇列...")
                            if self._restart_queue():
                                print("[auto-recovery] 比較佇列重啟成功")
                            else:
                                print("[auto-recovery] 比較佇列重啟失敗")
                    
                    self.last_queue_check = current_time
                else:
                    self.last_queue_check = current_time
                    
        except Exception as e:
            print(f"[auto-recovery] 檢查比較佇列錯誤: {e}")
    
    def _check_observer_status(self):
        """檢查 Observer 狀態"""
        try:
            obs = self.observer_getter()
            
            if not obs or not hasattr(obs, 'is_alive') or not obs.is_alive():
                print("[auto-recovery] 檢測到 Observer 已停止")
                
                if self._should_recover():
                    print("[auto-recovery] 嘗試重啟 Observer...")
                    if self._restart_observer():
                        print("[auto-recovery] Observer 重啟成功")
                    else:
                        print("[auto-recovery] Observer 重啟失敗")
                        
        except Exception as e:
            print(f"[auto-recovery] 檢查 Observer 狀態錯誤: {e}")
    
    def _should_recover(self) -> bool:
        """判斷是否應該進行恢復"""
        current_time = time.time()
        
        # 檢查恢復頻率限制
        recent_recoveries = [t for t in self.recovery_times if current_time - t < self.recovery_window]
        
        if len(recent_recoveries) >= self.max_recoveries:
            print(f"[auto-recovery] 恢復次數過多 ({len(recent_recoveries)}/{self.max_recoveries})，暫停自動恢復")
            return False
        
        return True
    
    def _restart_observer(self) -> bool:
        """重啟 Observer"""
        try:
            success = self.observer_restart()
            if success:
                self._record_recovery("observer")
            return success
        except Exception as e:
            print(f"[auto-recovery] 重啟 Observer 失敗: {e}")
            return False
    
    def _restart_queue(self) -> bool:
        """重啟比較佇列"""
        try:
            success = self.queue_restart()
            if success:
                self._record_recovery("queue")
            return success
        except Exception as e:
            print(f"[auto-recovery] 重啟比較佇列失敗: {e}")
            return False
    
    def _record_recovery(self, component: str):
        """記錄恢復操作"""
        current_time = time.time()
        self.recovery_times.append(current_time)
        self.recovery_count += 1
        print(f"[auto-recovery] 已記錄 {component} 恢復操作 (總計: {self.recovery_count})")
    
    def _cleanup_recovery_history(self, current_time: float):
        """清理過期的恢復記錄"""
        self.recovery_times = [t for t in self.recovery_times if current_time - t < self.recovery_window]
    
    def get_recovery_stats(self) -> dict:
        """獲取恢復統計"""
        current_time = time.time()
        recent_recoveries = [t for t in self.recovery_times if current_time - t < self.recovery_window]
        
        return {
            'total_recoveries': self.recovery_count,
            'recent_recoveries': len(recent_recoveries),
            'max_recoveries': self.max_recoveries,
            'recovery_window': self.recovery_window,
            'enabled': self.enabled
        }


# 全域恢復管理器
_auto_recovery_manager: Optional[AutoRecoveryManager] = None

def get_auto_recovery_manager() -> Optional[AutoRecoveryManager]:
    """獲取自動恢復管理器"""
    return _auto_recovery_manager

def init_auto_recovery(observer_getter: Callable[[], object],
                      observer_restart: Callable[[], bool],
                      queue_restart: Callable[[], bool]):
    """初始化自動恢復管理器"""
    global _auto_recovery_manager
    _auto_recovery_manager = AutoRecoveryManager(observer_getter, observer_restart, queue_restart)
    _auto_recovery_manager.start()
    return _auto_recovery_manager