"""
XML 子進程隔離模組
將 XML 解析工作交由獨立子進程處理，避免崩潰影響主程式
"""
import os
import sys
import time
import json
import subprocess
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError
import config.settings as settings


class XMLSubprocessManager:
    """
    XML 子進程管理器
    負責管理 XML 解析子進程的生命週期、任務分派和錯誤處理
    """
    
    def __init__(self):
        self.max_workers = max(1, int(getattr(settings, 'XML_SUBPROCESS_MAX_WORKERS', 1)))
        self.timeout_sec = float(getattr(settings, 'XML_SUBPROCESS_TIMEOUT_SEC', 15))
        self.safe_retry = bool(getattr(settings, 'XML_SUBPROCESS_SAFE_RETRY', True))
        self.enabled = bool(getattr(settings, 'USE_XML_SUBPROCESS', True))
        
        self.executor = None
        self.worker_counter = 0
        self.lock = threading.Lock()
        
        # 效能和穩定性監控
        self.stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'timeout_tasks': 0,
            'safe_retry_tasks': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'last_reset': time.time()
        }
        
        if self.enabled:
            self.executor = ThreadPoolExecutor(
                max_workers=self.max_workers, 
                thread_name_prefix="xml-subproc"
            )
            self._debug(f"initialized max_workers={self.max_workers} timeout={self.timeout_sec}s safe_retry={self.safe_retry}")
            self._debug(f"monitoring enabled: stats tracking, performance analysis")
    
    def _debug(self, message: str, level: int = 1):
        """輸出 debug 訊息"""
        try:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False) and getattr(settings, 'DEBUG_LEVEL', 1) >= level:
                print(f"[xml-subproc] {message}")
        except Exception:
            pass
    
    def _update_stats(self, task_type: str, success: bool, elapsed: float, timeout: bool = False, safe_retry: bool = False):
        """更新統計資訊"""
        try:
            with self.lock:
                self.stats['total_tasks'] += 1
                self.stats['total_time'] += elapsed
                
                if success:
                    self.stats['successful_tasks'] += 1
                else:
                    self.stats['failed_tasks'] += 1
                
                if timeout:
                    self.stats['timeout_tasks'] += 1
                
                if safe_retry:
                    self.stats['safe_retry_tasks'] += 1
                
                # 計算平均時間
                if self.stats['total_tasks'] > 0:
                    self.stats['avg_time'] = self.stats['total_time'] / self.stats['total_tasks']
                
                # 每 10 個任務輸出一次統計
                if self.stats['total_tasks'] % 10 == 0:
                    self._print_stats()
        except Exception:
            pass
    
    def _print_stats(self):
        """輸出統計資訊"""
        try:
            total = self.stats['total_tasks']
            success = self.stats['successful_tasks']
            failed = self.stats['failed_tasks']
            timeout = self.stats['timeout_tasks']
            safe_retry = self.stats['safe_retry_tasks']
            avg_time = self.stats['avg_time']
            
            success_rate = (success / total * 100) if total > 0 else 0
            timeout_rate = (timeout / total * 100) if total > 0 else 0
            retry_rate = (safe_retry / total * 100) if total > 0 else 0
            
            self._debug(f"stats: total={total} success={success}({success_rate:.1f}%) failed={failed} timeout={timeout}({timeout_rate:.1f}%) safe_retry={safe_retry}({retry_rate:.1f}%) avg_time={avg_time:.2f}s")
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        with self.lock:
            stats_copy = self.stats.copy()
            if stats_copy['total_tasks'] > 0:
                stats_copy['success_rate'] = stats_copy['successful_tasks'] / stats_copy['total_tasks'] * 100
                stats_copy['timeout_rate'] = stats_copy['timeout_tasks'] / stats_copy['total_tasks'] * 100
                stats_copy['retry_rate'] = stats_copy['safe_retry_tasks'] / stats_copy['total_tasks'] * 100
            else:
                stats_copy['success_rate'] = 0
                stats_copy['timeout_rate'] = 0
                stats_copy['retry_rate'] = 0
            return stats_copy
    
    def _get_worker_script_path(self) -> str:
        """取得子進程工作腳本路徑"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'xml_subproc_worker.py')
    
    def _run_subprocess_task(self, task_type: str, task_data: Dict[str, Any], worker_id: int, safe_mode: bool = False) -> Dict[str, Any]:
        """
        執行子進程任務
        
        Args:
            task_type: 任務類型 ('extract_refs', 'read_values', 'read_formulas')
            task_data: 任務資料
            worker_id: 工作者 ID
            safe_mode: 是否使用安全模式（單線程、保守設定）
        
        Returns:
            任務結果字典
        """
        worker_script = self._get_worker_script_path()
        if not os.path.exists(worker_script):
            raise FileNotFoundError(f"子進程工作腳本不存在: {worker_script}")
        
        # 準備任務輸入
        task_input = {
            'task_type': task_type,
            'task_data': task_data,
            'safe_mode': safe_mode,
            'worker_id': worker_id
        }
        
        file_path = task_data.get('file_path', 'unknown')
        mode_str = 'safe' if safe_mode else 'normal'
        
        self._debug(f"start worker_id={worker_id} task={task_type} file={os.path.basename(file_path)} mode={mode_str} timeout={self.timeout_sec}s")
        self._debug(f"subprocess_timeout_info worker_id={worker_id}: 子進程有 {self.timeout_sec} 秒時間完成工作，超時將強制終止並啟動安全模式重試")
        
        start_time = time.time()
        
        try:
            # 啟動子進程
            process = subprocess.Popen(
                [sys.executable, worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            )
            
            # 發送任務資料
            input_json = json.dumps(task_input, ensure_ascii=False)
            stdout, stderr = process.communicate(input=input_json, timeout=self.timeout_sec)
            
            elapsed = time.time() - start_time
            
            if process.returncode == 0:
                # 成功完成
                try:
                    result = json.loads(stdout)
                    result_size = len(stdout.encode('utf-8'))
                    self._debug(f"ok worker_id={worker_id} elapsed={elapsed:.1f}s result_size={result_size}bytes")
                    return result
                except json.JSONDecodeError as e:
                    self._debug(f"failed worker_id={worker_id} json_decode_error: {e}")
                    raise RuntimeError(f"子進程返回無效 JSON: {e}")
            else:
                # 子進程失敗
                self._debug(f"failed worker_id={worker_id} exit_code={process.returncode} elapsed={elapsed:.1f}s")
                if stderr:
                    self._debug(f"stderr worker_id={worker_id}: {stderr[:500]}")
                raise RuntimeError(f"子進程失敗 (exit_code={process.returncode}): {stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            # 超時
            elapsed = time.time() - start_time
            self._debug(f"timeout worker_id={worker_id} after {elapsed:.1f}s")
            try:
                process.kill()
                process.wait(timeout=3)
            except Exception:
                pass
            raise TimeoutError(f"子進程超時 ({self.timeout_sec}s)")
        
        except Exception as e:
            elapsed = time.time() - start_time
            self._debug(f"error worker_id={worker_id} elapsed={elapsed:.1f}s error={type(e).__name__}: {e}")
            raise
    
    def execute_task(self, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行 XML 解析任務（帶重試機制）
        
        Args:
            task_type: 任務類型
            task_data: 任務資料
            
        Returns:
            解析結果
        """
        if not self.enabled:
            raise RuntimeError("XML 子進程未啟用")
        
        if not self.executor:
            raise RuntimeError("XML 子進程執行器未初始化")
        
        with self.lock:
            self.worker_counter += 1
            worker_id = self.worker_counter
        
        file_path = task_data.get('file_path', 'unknown')
        start_time = time.time()
        
        # 記憶體監控
        try:
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            self._debug(f"memory_before={memory_before:.1f}MB worker_id={worker_id}", level=2)
        except Exception:
            memory_before = None
        
        # 第一次嘗試：正常模式
        try:
            future = self.executor.submit(
                self._run_subprocess_task, 
                task_type, 
                task_data, 
                worker_id, 
                safe_mode=False
            )
            result = future.result(timeout=self.timeout_sec + 5)  # 額外 5 秒緩衝
            
            # 統計更新：成功
            elapsed = time.time() - start_time
            
            # 記憶體監控（完成後）
            try:
                if memory_before is not None:
                    memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    memory_diff = memory_after - memory_before
                    self._debug(f"memory_after={memory_after:.1f}MB diff={memory_diff:+.1f}MB worker_id={worker_id}", level=2)
            except Exception:
                pass
            
            self._update_stats(task_type, success=True, elapsed=elapsed)
            
            return result
            
        except TimeoutError as e:
            elapsed = time.time() - start_time
            self._debug(f"normal_mode_timeout worker_id={worker_id} elapsed={elapsed:.1f}s timeout_limit={self.timeout_sec}s")
            self._debug(f"timeout_explanation worker_id={worker_id}: 子進程超過 {self.timeout_sec} 秒未完成，已強制終止。這是正常的保護機制，避免卡死。")
            self._update_stats(task_type, success=False, elapsed=elapsed, timeout=True)
            
            # 第二次嘗試：安全模式（如果啟用）
            if self.safe_retry:
                return self._try_safe_mode(task_type, task_data, worker_id, file_path, start_time, [e])
            else:
                raise e
                
        except Exception as e:
            elapsed = time.time() - start_time
            self._debug(f"normal_mode_failed worker_id={worker_id} error={type(e).__name__}: {e}")
            self._update_stats(task_type, success=False, elapsed=elapsed)
            
            # 第二次嘗試：安全模式（如果啟用）
            if self.safe_retry:
                return self._try_safe_mode(task_type, task_data, worker_id, file_path, start_time, [e])
            else:
                raise e
    
    def _try_safe_mode(self, task_type: str, task_data: Dict[str, Any], original_worker_id: int, file_path: str, original_start_time: float, errors: List[Exception]):
        """嘗試安全模式重試"""
        with self.lock:
            self.worker_counter += 1
            safe_worker_id = self.worker_counter
        
        self._debug(f"safe_retry_start worker_id={safe_worker_id} file={os.path.basename(file_path)} timeout={self.timeout_sec + 10}s")
        self._debug(f"safe_mode_timeout_info worker_id={safe_worker_id}: 安全模式子進程有 {self.timeout_sec + 10} 秒時間（比正常模式多 10 秒），使用更保守設定重試")
        
        safe_start_time = time.time()
        
        try:
            future = self.executor.submit(
                self._run_subprocess_task, 
                task_type, 
                task_data, 
                safe_worker_id, 
                safe_mode=True
            )
            result = future.result(timeout=self.timeout_sec + 10)  # 安全模式給更多時間
            
            # 統計更新：安全模式成功
            safe_elapsed = time.time() - safe_start_time
            total_elapsed = time.time() - original_start_time
            self._update_stats(task_type, success=True, elapsed=total_elapsed, safe_retry=True)
            self._debug(f"safe_retry_ok worker_id={safe_worker_id} elapsed={safe_elapsed:.1f}s total_elapsed={total_elapsed:.1f}s")
            
            return result
            
        except Exception as safe_e:
            safe_elapsed = time.time() - safe_start_time
            total_elapsed = time.time() - original_start_time
            
            is_timeout = isinstance(safe_e, TimeoutError)
            self._update_stats(task_type, success=False, elapsed=total_elapsed, timeout=is_timeout, safe_retry=True)
            
            self._debug(f"safe_retry_failed worker_id={safe_worker_id} error={type(safe_e).__name__}: {safe_e}")
            
            # 保存崩潰資訊
            self._save_crash_dump(task_type, task_data, errors + [safe_e])
            
            # 重新拋出原始錯誤
            raise errors[0]
    
    def _save_crash_dump(self, task_type: str, task_data: Dict[str, Any], errors: List[Exception]):
        """保存崩潰資訊到日誌"""
        try:
            log_folder = getattr(settings, 'LOG_FOLDER', '.')
            error_log_dir = os.path.join(log_folder, 'xml_subprocess_crashes')
            os.makedirs(error_log_dir, exist_ok=True)
            
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            crash_file = os.path.join(error_log_dir, f'xml_crash_{timestamp}.log')
            
            with open(crash_file, 'w', encoding='utf-8') as f:
                f.write(f"XML 子進程崩潰報告\n")
                f.write(f"時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"任務類型: {task_type}\n")
                f.write(f"檔案路徑: {task_data.get('file_path', 'unknown')}\n")
                f.write(f"設定: max_workers={self.max_workers}, timeout={self.timeout_sec}s\n")
                f.write(f"\n錯誤詳情:\n")
                
                for i, error in enumerate(errors, 1):
                    f.write(f"\n嘗試 {i}: {type(error).__name__}\n")
                    f.write(f"訊息: {str(error)}\n")
            
            self._debug(f"crash_dump_saved path={crash_file}")
            
        except Exception as e:
            self._debug(f"crash_dump_save_failed error={e}")
    
    def shutdown(self):
        """關閉子進程管理器"""
        if self.executor:
            self._debug("shutting_down")
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.executor = None


# 全域單例
_xml_subprocess_manager: Optional[XMLSubprocessManager] = None


def get_xml_subprocess_manager() -> XMLSubprocessManager:
    """取得 XML 子進程管理器單例"""
    global _xml_subprocess_manager
    if _xml_subprocess_manager is None:
        _xml_subprocess_manager = XMLSubprocessManager()
    return _xml_subprocess_manager


def is_xml_subprocess_enabled() -> bool:
    """檢查 XML 子進程是否啟用"""
    return bool(getattr(settings, 'USE_XML_SUBPROCESS', True))


def extract_external_refs_subprocess(file_path: str) -> Dict[int, str]:
    """
    使用子進程提取外部參照
    
    Args:
        file_path: Excel 檔案路徑
        
    Returns:
        外部參照映射 {index: path}
    """
    if not is_xml_subprocess_enabled():
        raise RuntimeError("XML 子進程未啟用")
    
    manager = get_xml_subprocess_manager()
    task_data = {'file_path': file_path}
    
    result = manager.execute_task('extract_refs', task_data)
    external_refs = result.get('external_refs', {})
    
    # 修復：確保鍵是整數類型（JSON 序列化會將整數鍵轉為字符串）
    if external_refs and isinstance(external_refs, dict):
        try:
            # 將字符串鍵轉回整數
            fixed_refs = {}
            for k, v in external_refs.items():
                try:
                    int_key = int(k)
                    fixed_refs[int_key] = v
                except (ValueError, TypeError):
                    # 如果轉換失敗，保留原鍵
                    fixed_refs[k] = v
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"[xml-subproc] external_refs converted keys: {list(external_refs.keys())} -> {list(fixed_refs.keys())}")
            return fixed_refs
        except Exception as e:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"[xml-subproc] external_refs key conversion failed: {e}")
            return external_refs
    
    return external_refs


def read_values_subprocess(file_path: str, engine: str = 'xml') -> Dict[str, Dict[str, Any]]:
    """
    使用子進程讀取儲存格值
    
    Args:
        file_path: Excel 檔案路徑
        engine: 值引擎類型
        
    Returns:
        工作表資料 {sheet_name: {address: value}}
    """
    if not is_xml_subprocess_enabled():
        raise RuntimeError("XML 子進程未啟用")
    
    manager = get_xml_subprocess_manager()
    task_data = {
        'file_path': file_path,
        'engine': engine
    }
    
    result = manager.execute_task('read_values', task_data)
    return result.get('values_by_sheet', {})