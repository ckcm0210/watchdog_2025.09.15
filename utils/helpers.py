"""
通用輔助函數
"""
import os
import time
import json
import threading
from datetime import datetime
import config.settings as settings
import logging
import hashlib

def get_file_mtime(filepath):
    """
    獲取檔案修改時間
    """
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
    except FileNotFoundError:
        logging.warning(f"檔案未找到: {filepath}")
        return "FileNotFound"
    except PermissionError:
        logging.error(f"權限不足，無法存取檔案: {filepath}")
        return "PermissionDenied"
    except OSError as e:
        logging.error(f"存取檔案時發生 I/O 錯誤: {filepath}，錯誤: {e}")
        return "IOError"

def human_readable_size(num_bytes):
    """
    轉換檔案大小為人類可讀格式
    """
    if num_bytes is None: 
        return "0 B"
    
    for unit in ['B','KB','MB','GB','TB']:
        if num_bytes < 1024.0: 
            return f"{num_bytes:,.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"

def _baseline_key_for_path(filepath: str) -> str:
    """
    基於完整路徑構造穩定 baseline key，避免不同資料夾同名檔案互相覆蓋。
    - 形式：<清理後的原始檔名>__<路徑哈希8>
    - 如果檔名前有快取前綴（例如 16位hex_），會移除所有重複的前綴，避免超長與視覺噪音。
    - 另外對極長檔名做保守截斷，保留副檔名。
    """
    try:
        import re
        MAX_BASE_NAME = 140  # 保守截斷，留空間給 __hash 與後綴
        fname = os.path.basename(filepath)
        # 去除多重 md5 前綴（16或32位hex），例如: abcd1234ef567890_...
        fname = re.sub(r'^(?:[0-9a-fA-F]{16,32}_)+', '', fname)
        # 截斷過長檔名（保留副檔名）
        name, ext = os.path.splitext(fname)
        if len(name) > MAX_BASE_NAME:
            name = name[:MAX_BASE_NAME]
        clean_fname = f"{name}{ext}"
        norm = os.path.normcase(os.path.abspath(filepath))
        h = hashlib.sha1(norm.encode('utf-8')).hexdigest()[:8]
        return f"{clean_fname}__{h}"
    except Exception:
        return os.path.basename(filepath)


def parse_path_mappings(raw) -> list:
    """
    將 PATH_MAPPINGS 設定（list 或多行字串）解析為 (from, to) 規則列表。
    格式：from => to
    """
    rules = []
    try:
        lines = []
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            for x in raw:
                if x is None:
                    continue
                lines.extend(str(x).splitlines())
        else:
            lines = str(raw).splitlines()
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if '=>' in s:
                left, right = s.split('=>', 1)
                from_p = left.strip()
                to_p = right.strip()
                if from_p:
                    rules.append((from_p, to_p))
        return rules
    except Exception:
        return []


essential_norm = os.path.normcase

def map_path_for_display(path: str) -> str:
    """
    依據 PATH_MAPPINGS 進行前綴映射，僅影響顯示；不改變實際路徑。
    """
    try:
        rules = parse_path_mappings(getattr(settings, 'PATH_MAPPINGS', []))
        p_norm = essential_norm(path)
        for src, dst in rules:
            if p_norm.startswith(essential_norm(src)):
                try:
                    suffix = path[len(src):]
                except Exception:
                    suffix = path
                return os.path.join(dst, suffix.lstrip('\\/'))
        return path
    except Exception:
        return path


def get_all_excel_files(folders):
    """
    獲取所有Excel檔案
    """
    all_files = []
    for folder in folders:
        if os.path.isfile(folder):
            if folder.lower().endswith(settings.SUPPORTED_EXTS) and not os.path.basename(folder).startswith('~$'):
                all_files.append(folder)
        elif os.path.isdir(folder):
            for dirpath, _, filenames in os.walk(folder):
                for f in filenames:
                    if f.lower().endswith(settings.SUPPORTED_EXTS) and not f.startswith('~$'):
                        all_files.append(os.path.join(dirpath, f))
    return all_files

def is_force_baseline_file(filepath):
    """
    檢查是否為強制baseline檔案
    """
    try:
        for pattern in settings.FORCE_BASELINE_ON_FIRST_SEEN:
            if pattern.lower() in filepath.lower(): 
                return True
        return False
    except TypeError as e: # 假設 pattern 或 filepath 可能不是字串
        logging.error(f"檢查強制基準線檔案時發生類型錯誤: {e}")
        return False

def save_progress(completed_files, total_files):
    """
    保存進度（具容錯）：若 RESUME_LOG_FILE 指向資料夾或為空，將回退到 LOG_FOLDER/resume_log/baseline_progress.log
    """
    if not settings.ENABLE_RESUME:
        return
    try:
        progress_data = {
            "timestamp": datetime.now().isoformat(),
            "completed": completed_files,
            "total": total_files,
        }
        # 決定實際路徑
        resume_path = getattr(settings, 'RESUME_LOG_FILE', None)
        try:
            if not resume_path or os.path.isdir(resume_path) or os.path.basename(resume_path) == '':
                base_dir = os.path.join(settings.LOG_FOLDER, 'resume_log')
                os.makedirs(base_dir, exist_ok=True)
                resume_path = os.path.join(base_dir, 'baseline_progress.log')
        except Exception:
            base_dir = os.path.join(settings.LOG_FOLDER, 'resume_log')
            os.makedirs(base_dir, exist_ok=True)
            resume_path = os.path.join(base_dir, 'baseline_progress.log')
        # 確保目錄存在
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        with open(resume_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError) as e:
        logging.error(f"無法儲存進度: {e}")

def load_progress():
    """
    載入進度
    """
    if not settings.ENABLE_RESUME or not os.path.exists(settings.RESUME_LOG_FILE): 
        return None
    
    try:
        with open(settings.RESUME_LOG_FILE, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logging.error(f"無法載入進度: {e}")
        return None

def timeout_handler():
    """
    超時處理器
    """
    while not settings.force_stop and not settings.baseline_completed:
        time.sleep(10)
        if settings.current_processing_file and settings.processing_start_time:
            elapsed = time.time() - settings.processing_start_time
            if elapsed > settings.FILE_TIMEOUT_SECONDS:
                print(f"\n超時：檔案處理超過 {settings.FILE_TIMEOUT_SECONDS}s (檔案: {settings.current_processing_file}, 已處理: {elapsed:.1f}s)")
                settings.current_processing_file = None
                settings.processing_start_time = None