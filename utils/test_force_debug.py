"""
強制顯示調試信息的測試腳本
"""
import os
import sys

# 獲取父目錄（項目根目錄）並添加到路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

print(f"項目根目錄: {parent_dir}")

# 設置環境變數，強制啟用調試信息
os.environ["WATCHDOG_FORCE_DEBUG"] = "1"

# 修改設定（在導入設定前）
import config.settings as settings
settings.SHOW_DEBUG_MESSAGES = True
settings.DEBUG_SHOW_FILE_INFO = True
settings.DEBUG_SHOW_MEMORY_INFO = True
settings.DEBUG_SHOW_GC_INFO = True

print("設定已修改:")
print(f"SHOW_DEBUG_MESSAGES = {settings.SHOW_DEBUG_MESSAGES}")

# 測試從設定檔獲取調試選項
print("\n測試從設定檔獲取調試選項:")
try:
    import config.settings as settings
    show_debug = getattr(settings, 'SHOW_DEBUG_MESSAGES', False)
    show_file_info = getattr(settings, 'DEBUG_SHOW_FILE_INFO', False)
    show_memory_info = getattr(settings, 'DEBUG_SHOW_MEMORY_INFO', False)
    show_gc_info = getattr(settings, 'DEBUG_SHOW_GC_INFO', False)
    
    print(f"SHOW_DEBUG_MESSAGES = {show_debug}")
    print(f"DEBUG_SHOW_FILE_INFO = {show_file_info}")
    print(f"DEBUG_SHOW_MEMORY_INFO = {show_memory_info}")
    print(f"DEBUG_SHOW_GC_INFO = {show_gc_info}")
except Exception as e:
    print(f"無法從設定檔獲取設定: {e}")

# 測試從 utils/enhanced_logging_and_error_handler.py 獲取設定
print("\n測試從增強日誌系統獲取設定:")
try:
    from utils.enhanced_logging_and_error_handler import config as log_config
    print(f"DETAILED_LOGGING = {log_config.get('DETAILED_LOGGING', False)}")
    print(f"SHOW_FILE_INFO = {log_config.get('SHOW_FILE_INFO', False)}")
    print(f"MEMORY_MONITORING = {log_config.get('MEMORY_MONITORING', False)}")
    print(f"SHOW_GC_INFO = {log_config.get('SHOW_GC_INFO', False)}")
except Exception as e:
    print(f"無法從增強日誌系統獲取設定: {e}")

# 直接測試 polars_xml_reader.py 中的檢查邏輯
print("\n直接測試 polars_xml_reader.py 中的檢查邏輯:")

def simulate_file_info_check():
    # 模擬 polars_xml_reader.py 中的檢查邏輯
    show_file_info = True  # 預設值
    try:
        from utils.enhanced_logging_and_error_handler import config
        show_file_info = config.get("SHOW_FILE_INFO", True)
        print(f"從增強日誌系統獲取 SHOW_FILE_INFO = {show_file_info}")
    except ImportError:
        # 嘗試直接從設定獲取
        try:
            import config.settings as settings
            if hasattr(settings, 'DEBUG_SHOW_FILE_INFO'):
                show_file_info = bool(settings.DEBUG_SHOW_FILE_INFO)
                print(f"從設定檔獲取 DEBUG_SHOW_FILE_INFO = {show_file_info}")
        except Exception as e:
            print(f"無法從設定檔獲取 DEBUG_SHOW_FILE_INFO: {e}")
    
    return show_file_info

show_file_info = simulate_file_info_check()
print(f"最終 show_file_info = {show_file_info}")

# 測試記憶體使用監控
print("\n測試記憶體使用監控:")
try:
    from utils.enhanced_logging_and_error_handler import log_memory_usage
    mem = log_memory_usage("測試")
    print(f"記憶體使用: {mem} MB")
except Exception as e:
    print(f"無法記錄記憶體使用: {e}")

# 測試顯示檔案信息
print("\n測試顯示檔案信息:")
test_file = __file__
try:
    file_size = os.path.getsize(test_file) / (1024 * 1024)
    modified_time = os.path.getmtime(test_file)
    access_time = os.path.getatime(test_file)
    
    from datetime import datetime
    print(f"[file-info] 大小: {file_size:.2f} MB")
    print(f"[file-info] 修改時間: {datetime.fromtimestamp(modified_time)}")
    print(f"[file-info] 存取時間: {datetime.fromtimestamp(access_time)}")
    print(f"[file-info] 存取間隔: {access_time - modified_time:.2f} 秒")
except Exception as e:
    print(f"無法顯示檔案信息: {e}")

print("\n測試完成!")