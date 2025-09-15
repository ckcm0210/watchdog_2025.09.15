"""
增強版錯誤處理與日誌系統
- 可配置的錯誤日誌位置
- 詳細的操作記錄
- 可控開關
- 記憶體與資源監控
"""

import os
import sys
import traceback
from datetime import datetime
import logging
from typing import Optional, Dict, Any

# 全局配置
config = {
    "ERROR_LOG_FOLDER": None,  # 預設使用程式根目錄下的 error_logs
    "DETAILED_LOGGING": True,  # 是否啟用詳細日誌
    "MEMORY_MONITORING": True,  # 是否監控記憶體使用
    "RESOURCE_TRACKING": True,  # 是否追蹤資源使用
}

def configure(settings):
    """從設定檔更新配置"""
    global config
    
    # 如果設定檔有指定除錯日誌文件夾，使用它
    if hasattr(settings, 'DEBUG_LOG_FOLDER') and settings.DEBUG_LOG_FOLDER:
        config["ERROR_LOG_FOLDER"] = settings.DEBUG_LOG_FOLDER
    elif hasattr(settings, 'LOG_FOLDER') and settings.LOG_FOLDER:
        config["ERROR_LOG_FOLDER"] = os.path.join(settings.LOG_FOLDER, "error_logs")
    
    # 如果設定檔有啟用/禁用詳細日誌的選項
    if hasattr(settings, 'SHOW_DEBUG_MESSAGES'):
        config["DETAILED_LOGGING"] = bool(settings.SHOW_DEBUG_MESSAGES)
    
    # 如果設定檔有啟用/禁用記憶體監控的選項
    if hasattr(settings, 'DEBUG_SHOW_MEMORY_INFO'):
        config["MEMORY_MONITORING"] = bool(settings.DEBUG_SHOW_MEMORY_INFO)
    elif hasattr(settings, 'ENABLE_MEMORY_MONITOR'):
        config["MEMORY_MONITORING"] = bool(settings.ENABLE_MEMORY_MONITOR)
        
    # 如果設定檔有控制顯示檔案資訊的選項
    if hasattr(settings, 'DEBUG_SHOW_FILE_INFO'):
        config["SHOW_FILE_INFO"] = bool(settings.DEBUG_SHOW_FILE_INFO)
        
    # 如果設定檔有控制顯示垃圾回收資訊的選項
    if hasattr(settings, 'DEBUG_SHOW_GC_INFO'):
        config["SHOW_GC_INFO"] = bool(settings.DEBUG_SHOW_GC_INFO)

def get_error_log_folder() -> str:
    """獲取錯誤日誌資料夾路徑"""
    if config["ERROR_LOG_FOLDER"]:
        folder = config["ERROR_LOG_FOLDER"]
    else:
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_logs")
    
    # 確保資料夾存在
    os.makedirs(folder, exist_ok=True)
    return folder

def log_memory_usage(label: str) -> Optional[float]:
    """記錄當前記憶體使用量"""
    if not config["MEMORY_MONITORING"]:
        return None
    
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        if config["DETAILED_LOGGING"]:
            print(f"[MEMORY] {label}: {memory_mb:.2f} MB")
        
        return memory_mb
    except Exception as e:
        if config["DETAILED_LOGGING"]:
            print(f"[WARNING] 無法記錄記憶體使用: {e}")
        return None

def log_open_files() -> Optional[int]:
    """記錄當前打開的檔案數量"""
    if not config["RESOURCE_TRACKING"]:
        return None
    
    try:
        import psutil
        process = psutil.Process()
        open_files = process.open_files()
        count = len(open_files)
        
        if config["DETAILED_LOGGING"] and count > 10:  # 只在超過一定數量時記錄
            print(f"[RESOURCES] 當前打開檔案數: {count}")
            if count > 50:  # 打開檔案過多時記錄詳情
                print(f"[WARNING] 打開檔案數量過多 ({count})，可能存在資源洩漏")
                for i, file in enumerate(open_files[:5]):
                    print(f"  - {file.path}")
                print(f"  - ... (還有 {count-5} 個)")
        
        return count
    except Exception:
        return None

def log_operation(operation: str, details: Dict[str, Any] = None):
    """記錄操作詳情"""
    if not config["DETAILED_LOGGING"]:
        return
    
    msg = f"[OPERATION] {operation}"
    if details:
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        msg += f" ({detail_str})"
    
    print(msg)

def setup_global_error_handler():
    """設置全局錯誤處理器"""
    def global_exception_handler(exctype, value, tb):
        """處理未捕捉的例外"""
        try:
            # 獲取錯誤日誌資料夾
            log_dir = get_error_log_folder()
            
            # 建立日誌檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"crash_{timestamp}.log")
            
            with open(log_file, "w", encoding="utf-8") as f:
                # 錯誤基本資訊
                f.write(f"====== 崩潰報告 ======\n")
                f.write(f"時間: {datetime.now()}\n")
                f.write(f"錯誤類型: {exctype.__name__}\n")
                f.write(f"錯誤信息: {value}\n\n")
                
                # 堆棧追蹤
                f.write("堆棧追蹤:\n")
                for line in traceback.format_tb(tb):
                    f.write(line)
                f.write("\n")
                
                # 系統資訊
                f.write("系統資訊:\n")
                f.write(f"Python 版本: {sys.version}\n")
                f.write(f"平台: {sys.platform}\n")
                f.write(f"執行路徑: {sys.executable}\n\n")
                
                # 記憶體資訊
                try:
                    import psutil
                    process = psutil.Process()
                    mem_info = process.memory_info()
                    f.write("記憶體資訊:\n")
                    f.write(f"使用量 (RSS): {mem_info.rss / 1024 / 1024:.2f} MB\n")
                    f.write(f"虛擬記憶體: {mem_info.vms / 1024 / 1024:.2f} MB\n\n")
                    
                    # CPU 使用量
                    f.write(f"CPU 使用量: {process.cpu_percent(interval=0.1)}%\n\n")
                except ImportError:
                    f.write("記憶體資訊: psutil 未安裝\n\n")
                except Exception as e:
                    f.write(f"記憶體資訊讀取失敗: {e}\n\n")
                    
                # 打開的文件
                try:
                    import psutil
                    process = psutil.Process()
                    open_files = process.open_files()
                    f.write("打開的檔案:\n")
                    for i, file in enumerate(open_files[:50]):  # 限制數量
                        f.write(f"  {i+1}. {file.path}\n")
                    if len(open_files) > 50:
                        f.write(f"  ... 還有 {len(open_files) - 50} 個檔案\n")
                    f.write("\n")
                except Exception as e:
                    f.write(f"打開檔案清單讀取失敗: {e}\n\n")
                
                # 專門針對 0x80000003 錯誤的診斷
                if "0x80000003" in str(value) or "access violation" in str(value).lower():
                    f.write("=== 0x80000003 錯誤專項診斷 ===\n")
                    f.write("這是一個記憶體存取違規錯誤，常見原因包括:\n")
                    f.write("1. 存取已釋放或無效的記憶體位置\n")
                    f.write("2. 多個處理序/線程同時存取同一資源\n")
                    f.write("3. 原生擴展模組存在 bug\n")
                    f.write("4. 檔案 I/O 操作中斷或不完整\n\n")
                    
                    # 嘗試收集與檔案操作相關的資訊
                    f.write("檔案操作相關:\n")
                    for line in traceback.format_tb(tb):
                        if "zipfile" in line or "open" in line or "read" in line or "write" in line:
                            f.write(f"  {line.strip()}\n")
                    f.write("\n")
            
            # 顯示消息
            print(f"\n發生嚴重錯誤，崩潰日誌已寫入: {log_file}", file=sys.stderr)
            
        except Exception as logging_error:
            print(f"錯誤處理器本身發生錯誤: {logging_error}", file=sys.stderr)
        
        # 調用原處理器
        sys.__excepthook__(exctype, value, tb)

    # 設置處理器
    sys.excepthook = global_exception_handler
    print(f"[INFO] 全局錯誤處理器已啟動，錯誤日誌將保存至: {get_error_log_folder()}")

def toggle_detailed_logging(enabled: bool):
    """開啟/關閉詳細日誌"""
    config["DETAILED_LOGGING"] = enabled
    print(f"[CONFIG] 詳細日誌已{'啟用' if enabled else '禁用'}")

def toggle_memory_monitoring(enabled: bool):
    """開啟/關閉記憶體監控"""
    config["MEMORY_MONITORING"] = enabled
    print(f"[CONFIG] 記憶體監控已{'啟用' if enabled else '禁用'}")

# 初始化
if __name__ == "__main__":
    setup_global_error_handler()
    
    # 示範使用
    log_operation("測試操作", {"檔案": "test.xlsx", "動作": "讀取"})
    log_memory_usage("操作前")
    
    # 做一些佔用記憶體的操作
    data = [i for i in range(1000000)]
    
    log_memory_usage("操作後")
    log_open_files()
    
    # 測試錯誤處理
    def test_error():
        x = 1 / 0
    
    test_error()