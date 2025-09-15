"""
基準線管理功能 - 支援 LZ4、Zstd 和 gzip 壓縮
"""
import os
import json
import gzip
import shutil
import time
import gc
import threading
from datetime import datetime, timedelta
import logging
import config.settings as settings
from utils.helpers import save_progress, load_progress
from utils.memory import check_memory_limit, get_memory_usage
from utils.compression import (
    CompressionFormat, 
    save_compressed_file, 
    load_compressed_file,
    get_compression_stats,
    migrate_baseline_format
)
from core.excel_parser import dump_excel_cells_with_timeout, hash_excel_content, get_excel_last_author

def baseline_file_path(base_name):
    """
    獲取基準線檔案路徑（不包含副檔名）
    """
    return os.path.join(settings.LOG_FOLDER, f"{base_name}.baseline.json")

def get_baseline_file_with_extension(base_name):
    """
    獲取實際存在的基準線檔案路徑（包含副檔名）
    """
    base_path = baseline_file_path(base_name)
    
    # 按優先順序檢查不同格式的檔案
    for format_type in [settings.DEFAULT_COMPRESSION_FORMAT, 'lz4', 'zstd', 'gzip']:
        ext = CompressionFormat.get_extension(format_type)
        test_path = base_path + ext
        if os.path.exists(test_path):
            return test_path
    
    return None

def load_baseline(baseline_file_or_base_name):
    """
    載入基準線檔案，支援多種壓縮格式
    """
    try:
        # 如果是基準名稱，轉換為檔案路徑
        if not os.path.sep in baseline_file_or_base_name and not baseline_file_or_base_name.endswith('.json'):
            base_path = baseline_file_path(baseline_file_or_base_name)
        else:
            base_path = baseline_file_or_base_name
            if base_path.endswith('.gz') or base_path.endswith('.lz4') or base_path.endswith('.zst'):
                base_path = base_path.rsplit('.', 1)[0]
        
        # 使用壓縮工具載入
        from utils.compression import load_compressed_file
        data = load_compressed_file(base_path)
        
        # 移除所有 [DEBUG] 載入基準線的訊息
        
        return data
        
    except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError, gzip.BadGzipFile) as e:
        logging.error(f"載入基準線失敗 {baseline_file_or_base_name}: {e}")
        return None

def save_baseline(baseline_file_or_base_name, data):
    """
    保存基準線檔案，使用設定的壓縮格式
    """
    try:
        # 如果是基準名稱，轉換為檔案路徑
        if not os.path.sep in baseline_file_or_base_name and not baseline_file_or_base_name.endswith('.json'):
            base_path = baseline_file_path(baseline_file_or_base_name)
        else:
            base_path = baseline_file_or_base_name
            if base_path.endswith('.gz') or base_path.endswith('.lz4') or base_path.endswith('.zst'):
                base_path = base_path.rsplit('.', 1)[0]
        
        # 移除： print(f"[DEBUG] 基準路徑: {base_path}")
        
        # 確保目錄存在
        dir_name = os.path.dirname(base_path)
        os.makedirs(dir_name, exist_ok=True)
        
        # 使用新的壓縮工具
        from utils.compression import save_compressed_file, get_compression_stats, CompressionFormat
        
        # 選擇壓縮格式
        compression_format = settings.DEFAULT_COMPRESSION_FORMAT
        # 移除： print(f"[DEBUG] 使用格式: {compression_format}")
        
        # 檢查是否需要清理舊格式的檔案
        for old_format in ['gzip', 'lz4', 'zstd']:
            if old_format != compression_format:
                old_ext = CompressionFormat.get_extension(old_format)
                old_file = base_path + old_ext
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except OSError as e:
                        logging.warning(f"清理舊檔案失敗: {e}")
        
        # 保存新檔案
        # 移除： print(f"[DEBUG] 開始保存壓縮檔案...")
        actual_file = save_compressed_file(base_path, data, compression_format)
        # 移除： print(f"[DEBUG] 保存完成: {actual_file}")
        
        # 簡化壓縮統計顯示
        if settings.SHOW_COMPRESSION_STATS:
            stats = get_compression_stats(actual_file)
            if stats:
                print(f"基準線保存: {os.path.basename(actual_file)} ({stats['format'].upper()}, {stats['compression_ratio']:.1f}%)")
        
        return True
        
    except (FileNotFoundError, PermissionError, OSError) as e:
        logging.error(f"保存基準線檔案失敗: {e}")
        return False

def archive_old_baselines():
    """
    歸檔舊的基準線檔案，轉換為高壓縮率格式
    """
    if not settings.ENABLE_ARCHIVE_MODE:
        return
    
    try:
        archive_threshold = datetime.now() - timedelta(days=settings.ARCHIVE_AFTER_DAYS)
        archive_count = 0
        
        for filename in os.listdir(settings.LOG_FOLDER):
            if not filename.endswith('.baseline.json.lz4'):
                continue
            
            filepath = os.path.join(settings.LOG_FOLDER, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if file_mtime < archive_threshold:
                print(f"[ARCHIVE] 歸檔舊基準線: {filename}")
                new_filepath = migrate_baseline_format(filepath, settings.ARCHIVE_COMPRESSION_FORMAT)
                if new_filepath:
                    archive_count += 1
                    print(f"[ARCHIVE] 完成: {os.path.basename(new_filepath)}")
        
        if archive_count > 0:
            print(f"[ARCHIVE] 共歸檔了 {archive_count} 個基準線檔案")
    
    except (OSError, shutil.Error) as e:
        logging.error(f"歸檔過程出錯: {e}")

def create_baseline_for_files_robust(xlsx_files, skip_force_baseline=True):
    """
    為多個檔案建立基準線
    """
    total = len(xlsx_files)
    if total == 0:
        print("[INFO] 沒有需要 baseline 的檔案。")
        settings.baseline_completed = True
        return
    
    print("\n" + "="*90 + "\n" + "BASELINE 建立程序".center(90) + "\n" + "="*90)
    
    # 檢查壓縮格式可用性
    available_formats = CompressionFormat.get_available_formats()
    print(f"🗜️  可用壓縮格式: {', '.join(available_formats)}")
    print(f"🚀 使用壓縮格式: {settings.DEFAULT_COMPRESSION_FORMAT.upper()}")
    
    if settings.DEFAULT_COMPRESSION_FORMAT not in available_formats:
        print(f"⚠️  警告: 預設格式 {settings.DEFAULT_COMPRESSION_FORMAT} 不可用，降級到 gzip")
        settings.DEFAULT_COMPRESSION_FORMAT = 'gzip'
    
    progress = load_progress()
    start_index = 0
    
    if progress and settings.ENABLE_RESUME:
        print(f"發現之前的進度記錄: 完成 {progress.get('completed', 0)}/{progress.get('total', 0)}")
        # 自動續跑：不再詢問
        start_index = progress.get('completed', 0)
    
    # 啟動超時處理
    if settings.ENABLE_TIMEOUT:
        from utils.helpers import timeout_handler
        timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
        timeout_thread.start()
        print(f"⏰ 啟用超時保護: {settings.FILE_TIMEOUT_SECONDS} 秒")
    
    if settings.ENABLE_MEMORY_MONITOR: 
        print(f"💾 啟用記憶體監控: {settings.MEMORY_LIMIT_MB} MB")
    
    print(f"🚀 啟用優化: {[opt for flag, opt in [(settings.USE_LOCAL_CACHE, '本地緩存'), (settings.ENABLE_FAST_MODE, '快速模式')] if flag]}")
    print(f"📂 Baseline 儲存位置: {os.path.abspath(settings.LOG_FOLDER)}")
    
    if settings.USE_LOCAL_CACHE: 
        print(f"💾 本地緩存位置: {os.path.abspath(settings.CACHE_FOLDER)}")
    
    print(f"📋 要處理的檔案: {total} 個 (從第 {start_index + 1} 個開始)")
    print(f"⏰ 開始時間: {datetime.now():%Y-%m-%d %H:%M:%S}\n" + "-"*90)
    
    os.makedirs(settings.LOG_FOLDER, exist_ok=True)
    if settings.USE_LOCAL_CACHE: 
        os.makedirs(settings.CACHE_FOLDER, exist_ok=True)
    
    success_count, skip_count, error_count = 0, 0, 0
    start_time = time.time()
    total_original_size = 0
    total_compressed_size = 0
    
    for i in range(start_index, total):
        if settings.force_stop:
            print("\n🛑 收到停止信號，正在安全退出...")
            save_progress(i, total)
            break
        
        file_path = xlsx_files[i]
        # 使用包含路徑哈希的 key，避免同名不同路徑覆蓋
        from utils.helpers import _baseline_key_for_path
        base_key = _baseline_key_for_path(file_path)
        display_name = os.path.basename(file_path)
        
        if check_memory_limit():
            print(f"⚠️ 記憶體使用量過高，暫停10秒...")
            time.sleep(10)
            if check_memory_limit(): 
                print(f"❌ 記憶體仍然過高，停止處理")
                save_progress(i, total)
                break

        file_start_time = time.time()
        print(f"[{i+1:>2}/{total}] 處理中: {display_name} (記憶體: {get_memory_usage():.1f}MB)")
        
        cell_data = None
        try:
            old_baseline = load_baseline(base_key)
            old_hash = old_baseline['content_hash'] if old_baseline and 'content_hash' in old_baseline else None
            
            cell_data = dump_excel_cells_with_timeout(file_path)
            
            if cell_data is None:
                if settings.current_processing_file is None and (time.time() - file_start_time) > settings.FILE_TIMEOUT_SECONDS:
                     print(f"  結果: [TIMEOUT]")
                else:
                     print(f"  結果: [READ_ERROR]")
                error_count += 1
            else:
                curr_hash = hash_excel_content(cell_data)
                if (not getattr(settings, 'FORCE_REBUILD_BASELINE_ON_SCAN', False)) and old_hash == curr_hash and old_hash is not None:
                    print(f"  結果: [SKIP] (Hash unchanged)")
                    skip_count += 1
                else:
                    curr_author = get_excel_last_author(file_path)
                    baseline_data = {
                        "source_mtime": os.path.getmtime(file_path),
                        "source_size": os.path.getsize(file_path),
                        "last_author": curr_author, 
                        "content_hash": curr_hash, 
                        "cells": cell_data
                    }
                    
                    if save_baseline(base_key, baseline_data):
                        print(f"  結果: [OK]")
                        success_count += 1
                        
                        # 統計壓縮效果
                        if settings.SHOW_COMPRESSION_STATS:
                            actual_file = get_baseline_file_with_extension(base_key)
                            if actual_file:
                                stats = get_compression_stats(actual_file)
                                if stats and stats['original_size']:
                                    total_original_size += stats['original_size']
                                    total_compressed_size += stats['compressed_size']
                    else:
                        print(f"  結果: [SAVE_ERROR]")
                        error_count += 1
            
            print(f"  耗時: {time.time() - file_start_time:.2f} 秒")
            print("")
            save_progress(i + 1, total)
            
        except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError) as e:
            logging.error(f"  結果: [UNEXPECTED_ERROR]\n  錯誤: {e}\n  耗時: {time.time() - file_start_time:.2f} 秒\n")
            error_count += 1
            save_progress(i + 1, total)
        finally:
            if cell_data is not None:
                del cell_data
            if 'old_baseline' in locals() and old_baseline is not None:
                del old_baseline
            # 移除顯式 gc.collect() 以避免在 GC 階段觸發底層崩潰（Python 3.11/3.12 + ElementTree）
            # 交由 Python 自然回收即可，必要時可改回設定式開關

    # 執行歸檔
    if settings.ENABLE_ARCHIVE_MODE:
        print("\n🗂️  檢查歸檔...")
        archive_old_baselines()

    settings.baseline_completed = True
    print("-" * 90 + f"\n🎯 BASELINE 建立完成! (總耗時: {time.time() - start_time:.2f} 秒)")
    print(f"✅ 成功: {success_count}, ⏭️  跳過: {skip_count}, ❌ 失敗: {error_count}")
    
    # 顯示壓縮統計
    if settings.SHOW_COMPRESSION_STATS and total_original_size > 0:
        overall_ratio = (1 - total_compressed_size / total_original_size) * 100
        savings_mb = (total_original_size - total_compressed_size) / (1024 * 1024)
        print(f"🗜️  總壓縮統計: 原始 {total_original_size/(1024*1024):.1f}MB → "
              f"壓縮 {total_compressed_size/(1024*1024):.1f}MB "
              f"(節省 {savings_mb:.1f}MB, 壓縮率 {overall_ratio:.1f}%)")
    
    if settings.ENABLE_RESUME and os.path.exists(settings.RESUME_LOG_FILE):
        try: 
            os.remove(settings.RESUME_LOG_FILE)
            print(f"🧹 清理進度檔案")
        except OSError as e:
            logging.error(f"清理進度檔案失敗: {e}")
    
    print("\n" + "=" * 90 + "\n")