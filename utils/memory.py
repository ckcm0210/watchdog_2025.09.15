"""
記憶體監控功能
"""
import psutil
import os
import gc
import logging
import config.settings as settings

def get_memory_usage():
    """
    獲取當前記憶體使用量 (MB)
    """
    try:
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except psutil.NoSuchProcess as e:
        logging.error(f"進程不存在，無法獲取內存使用量: {e}")
        return 0
    except psutil.AccessDenied as e:
        logging.warning(f"權限不足，無法獲取內存使用量: {e}")
        return 0
    except Exception as e:
        logging.error(f"獲取內存使用量時發生未知錯誤: {e}", exc_info=True)
        return 0

def check_memory_limit():
    """
    檢查記憶體使用是否超過限制
    """
    if not settings.ENABLE_MEMORY_MONITOR: 
        return False
    
    current_memory = get_memory_usage()
    if current_memory > settings.MEMORY_LIMIT_MB:
        print(f"⚠️ 記憶體使用量過高: {current_memory:.1f} MB > {settings.MEMORY_LIMIT_MB} MB")
        print("   正在執行垃圾回收...")
        # 降級為淺層收集（第 0 代），並提供設定開關
        # 移除 gc.collect(0) 以避免在記憶體監控時觸發 GC 導致 XML 解析崩潰
        # try:
        #     if getattr(settings, 'ENABLE_MEMORY_MONITOR_FORCE_GC', False):
        #         gc.collect(0)
        # except Exception:
        #     pass
        new_memory = get_memory_usage()
        print(f"   垃圾回收後: {new_memory:.1f} MB")
        return new_memory > settings.MEMORY_LIMIT_MB
    return False