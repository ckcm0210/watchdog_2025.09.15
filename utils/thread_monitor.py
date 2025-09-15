"""
線程狀態監控工具
用於診斷線程卡住或阻塞的問題
"""
import threading
import time
import traceback
import sys
from typing import Dict, List, Any
import config.settings as settings


class ThreadMonitor:
    """線程狀態監控器"""
    
    def __init__(self):
        self.last_check_time = 0
        self.thread_states = {}
        self.stuck_threads = {}
    
    def check_all_threads(self) -> Dict[str, Any]:
        """檢查所有線程狀態"""
        current_time = time.time()
        thread_info = {
            'total_threads': 0,
            'active_threads': [],
            'stuck_threads': [],
            'new_threads': [],
            'dead_threads': []
        }
        
        try:
            current_threads = {}
            frames = sys._current_frames()
            
            for thread in threading.enumerate():
                thread_id = thread.ident
                thread_name = thread.name
                is_alive = thread.is_alive()
                is_daemon = thread.daemon
                
                current_threads[thread_id] = {
                    'name': thread_name,
                    'alive': is_alive,
                    'daemon': is_daemon,
                    'frame': frames.get(thread_id)
                }
                
                thread_info['total_threads'] += 1
                thread_info['active_threads'].append({
                    'id': thread_id,
                    'name': thread_name,
                    'alive': is_alive,
                    'daemon': is_daemon
                })
            
            # 檢查新線程
            for tid, info in current_threads.items():
                if tid not in self.thread_states:
                    thread_info['new_threads'].append(info['name'])
            
            # 檢查消失的線程
            for tid, old_info in self.thread_states.items():
                if tid not in current_threads:
                    thread_info['dead_threads'].append(old_info['name'])
            
            # 檢查卡住的線程
            self._check_stuck_threads(current_threads, thread_info)
            
            self.thread_states = current_threads
            self.last_check_time = current_time
            
        except Exception as e:
            thread_info['error'] = str(e)
        
        return thread_info
    
    def _check_stuck_threads(self, current_threads: Dict, thread_info: Dict):
        """檢查卡住的線程"""
        try:
            current_time = time.time()
            
            for tid, thread_data in current_threads.items():
                thread_name = thread_data['name']
                frame = thread_data['frame']
                
                if not frame:
                    continue
                
                # 獲取當前執行位置
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno
                function = frame.f_code.co_name
                location = f"{filename}:{lineno} in {function}"
                
                # 檢查是否在同一位置停留太久
                if tid in self.stuck_threads:
                    old_location = self.stuck_threads[tid]['location']
                    old_time = self.stuck_threads[tid]['time']
                    
                    if location == old_location:
                        stuck_duration = current_time - old_time
                        # 修復：忽略正常的等待狀態
                        if (stuck_duration > 60 and  # 超過 1 分鐘在同一位置
                            'time.sleep' not in location and  # 不是 sleep
                            'threading.py' not in location and  # 不是線程等待
                            'queue.py' not in location and  # 不是佇列等待
                            '_worker' not in function):  # 不是工作者等待
                            thread_info['stuck_threads'].append({
                                'name': thread_name,
                                'location': location,
                                'duration': stuck_duration,
                                'stack': self._get_thread_stack(frame)
                            })
                    else:
                        # 位置改變了，更新記錄
                        self.stuck_threads[tid] = {
                            'location': location,
                            'time': current_time
                        }
                else:
                    # 新記錄
                    self.stuck_threads[tid] = {
                        'location': location,
                        'time': current_time
                    }
        except Exception:
            pass
    
    def _get_thread_stack(self, frame, max_depth=10) -> List[str]:
        """獲取線程堆疊"""
        stack = []
        try:
            current_frame = frame
            depth = 0
            
            while current_frame and depth < max_depth:
                filename = current_frame.f_code.co_filename
                lineno = current_frame.f_lineno
                function = current_frame.f_code.co_name
                stack.append(f"  {filename}:{lineno} in {function}")
                current_frame = current_frame.f_back
                depth += 1
                
        except Exception:
            stack.append("  (無法獲取堆疊)")
        
        return stack
    
    def print_thread_summary(self):
        """輸出線程摘要"""
        try:
            info = self.check_all_threads()
            
            print(f"[thread-monitor] 總線程數: {info['total_threads']}")
            
            if info.get('new_threads'):
                print(f"[thread-monitor] 新線程: {', '.join(info['new_threads'])}")
            
            if info.get('dead_threads'):
                print(f"[thread-monitor] 結束線程: {', '.join(info['dead_threads'])}")
            
            if info.get('stuck_threads'):
                print(f"[thread-monitor] 卡住線程: {len(info['stuck_threads'])} 個")
                for stuck in info['stuck_threads']:
                    print(f"[thread-monitor] STUCK: {stuck['name']} 在 {stuck['location']} 已 {stuck['duration']:.1f} 秒")
                    if getattr(settings, 'DEBUG_LEVEL', 1) >= 2:
                        print("堆疊:")
                        for line in stuck['stack'][:5]:  # 只顯示前 5 層
                            print(line)
            
            # 列出關鍵線程
            key_threads = [t for t in info['active_threads'] 
                          if any(keyword in t['name'].lower() 
                                for keyword in ['main', 'observer', 'compare', 'xml-subproc', 'heartbeat'])]
            
            if key_threads:
                thread_names = [t['name'] for t in key_threads]
                print(f"[thread-monitor] 關鍵線程: {', '.join(thread_names)}")
                
        except Exception as e:
            print(f"[thread-monitor] 錯誤: {e}")


# 全域監控器
_thread_monitor = None

def get_thread_monitor() -> ThreadMonitor:
    """獲取線程監控器單例"""
    global _thread_monitor
    if _thread_monitor is None:
        _thread_monitor = ThreadMonitor()
    return _thread_monitor

def print_thread_status():
    """輸出線程狀態（供外部調用）"""
    monitor = get_thread_monitor()
    monitor.print_thread_summary()