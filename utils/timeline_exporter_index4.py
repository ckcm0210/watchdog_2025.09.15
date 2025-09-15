"""
Index4 Timeline Exporter - 指定作者過濾版本
- 複用 timeline_exporter_matrix_clean 的 HTML 生成邏輯
- 讀取 events_index4.json 生成 index4.html
- 輸出到用戶指定的路徑（可為網路共享位置）
"""
import os
import json
from datetime import datetime
import config.settings as settings

# 從 Matrix Clean 共用 HTML 生成邏輯
from .timeline_exporter_matrix_clean import generate_html as _generate_html_clean

INDEX4_DIR = None
INDEX4_JSON = None
INDEX4_HTML = None

def _init_paths():
    """初始化 Index4 的路徑"""
    global INDEX4_DIR, INDEX4_JSON, INDEX4_HTML
    
    # 從設定讀取用戶指定的輸出路徑
    user_output_path = getattr(settings, 'INDEX4_OUTPUT_PATH', '')
    if user_output_path and os.path.exists(user_output_path):
        INDEX4_DIR = user_output_path
    else:
        # 預設回到本地 timeline 目錄
        INDEX4_DIR = os.path.join(getattr(settings, 'LOG_FOLDER', '.'), 'timeline')
    
    INDEX4_JSON = os.path.join(INDEX4_DIR, 'events_index4.json')
    INDEX4_HTML = os.path.join(INDEX4_DIR, 'index4.html')
    
    # 確保目錄存在
    os.makedirs(INDEX4_DIR, exist_ok=True)


def export_event(event: dict):
    """
    匯出事件到 Index4（只有符合目標作者的事件）
    """
    if not getattr(settings, 'INDEX4_ENABLED', False):
        return  # 功能未啟用
    
    if not event:
        return
    
    # 檢查作者是否在目標清單中
    author = event.get('author', '')
    if not _is_target_author(author):
        return  # 作者不在目標清單中，跳過
    
    try:
        _init_paths()
        
        # 讀取現有事件
        events = []
        if os.path.exists(INDEX4_JSON):
            try:
                with open(INDEX4_JSON, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            except Exception:
                events = []
        
        # 輕量去重：以 (file, event_number, timestamp) 為簽名
        sig = (event.get('file',''), event.get('event_number',''), event.get('timestamp',''))
        exists = any((e.get('file',''), e.get('event_number',''), e.get('timestamp','')) == sig for e in events)
        if not exists:
            events.append(event)
        
        # 寫回 JSON
        with open(INDEX4_JSON, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        # 生成 HTML（共用 matrix_clean 邏輯）
        _generate_html_clean(events, output_path=INDEX4_HTML, title_suffix=" - 指定作者")
        
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            print(f"   [index4] 已匯出事件: {os.path.basename(event.get('file', ''))} by {author} -> {INDEX4_HTML}")
            
    except Exception as e:
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            print(f"   [index4] 匯出失敗: {e}")


def _is_target_author(author: str) -> bool:
    """
    檢查作者是否在目標清單中
    """
    if not author:
        return False
    
    # 從設定讀取目標作者清單
    target_authors_str = getattr(settings, 'INDEX4_TARGET_AUTHORS', '')
    if not target_authors_str.strip():
        return False  # 沒有設定目標作者，不匯出任何事件
    
    # 解析作者清單：支援 "作者1", "作者2", "作者3" 格式
    target_authors = []
    try:
        # 簡單解析：分割逗號，移除引號和空白
        parts = target_authors_str.split(',')
        for part in parts:
            clean_author = part.strip().strip('"').strip("'").strip()
            if clean_author:
                target_authors.append(clean_author)
    except Exception:
        return False
    
    # 精確匹配
    return author in target_authors


def generate_html(events=None, output_path=None, title_suffix=""):
    """
    生成 Index4 HTML（共用 matrix_clean 邏輯）
    """
    if not getattr(settings, 'INDEX4_ENABLED', False):
        return
        
    try:
        _init_paths()
        
        if events is None:
            # 讀取 events_index4.json
            if os.path.exists(INDEX4_JSON):
                with open(INDEX4_JSON, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            else:
                events = []
        
        output_file = output_path or INDEX4_HTML
        _generate_html_clean(events, output_path=output_file, title_suffix=" - 指定作者")
        
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            print(f"   [index4] HTML 已生成: {output_file}")
            
    except Exception as e:
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            print(f"   [index4] HTML 生成失敗: {e}")