"""
日誌和打印功能
"""
import builtins
import os
from datetime import datetime
from io import StringIO
from wcwidth import wcswidth, wcwidth
import config.settings as settings

# 保存原始 print 函數
_original_print = builtins.print

# 整合全域輸出保護器
try:
    from utils.console_output_guard import set_backend_print, safe_print
    set_backend_print(_original_print)
except Exception:
    safe_print = None

def timestamped_print(*args, **kwargs):
    """
    帶時間戳的打印函數
    """
    # 如果有 file=... 參數，直接用原生 print
    if 'file' in kwargs:
        _original_print(*args, **kwargs)
        return

    output_buffer = StringIO()
    _original_print(*args, file=output_buffer, **kwargs)
    message = output_buffer.getvalue()
    output_buffer.close()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 簡化邏輯：所有行都加時間戳記
    lines = message.rstrip().split('\n')
    timestamped_lines = []
    
    for line in lines:
        timestamped_lines.append(f"[{timestamp}] {line}")
    
    # Emoji 清理（如啟用）
    if getattr(settings, 'REMOVE_EMOJI', False):
        try:
            import re
            # 常見 Unicode emoji/符號區段過濾
            emoji_pattern = re.compile(
                '[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]+',
                flags=re.UNICODE
            )
            lines = [emoji_pattern.sub('', ln) for ln in timestamped_lines]
        except Exception:
            pass
    timestamped_message = '\n'.join(lines)
    if safe_print:
        safe_print(timestamped_message)
    else:
        _original_print(timestamped_message)
    
    # 追加寫入純文字日誌檔（若啟用）
    # 檢查是否為比較表格訊息
    is_comparison = any(keyword in message for keyword in [
        'Address', 'Baseline', 'Current', 
        '[SUMMARY]', '====', '----',
        '[MOD]', '[ADD]', '[DEL]'
    ])

    # 是否為變更橫幅等關鍵訊息
    change_banner = ('檔案變更偵測' in message) or ('偵測到變更' in message)

    # 根據設定決定是否寫入純文字日誌
    try:
        if getattr(settings, 'CONSOLE_TEXT_LOG_ENABLED', False):
            only_changes = getattr(settings, 'CONSOLE_TEXT_LOG_ONLY_CHANGES', False)
            should_write = (is_comparison or change_banner) if only_changes else True
            if should_write:
                log_path = getattr(settings, 'CONSOLE_TEXT_LOG_FILE', None)
                if not log_path:
                    # 後備：寫入 LOG_FOLDER 下以日期命名的檔
                    log_dir = getattr(settings, 'LOG_FOLDER', '.')
                    date_str = getattr(settings, 'LOG_FILE_DATE', datetime.now().strftime('%Y%m%d'))
                    log_path = os.path.join(log_dir, f"console_log_{date_str}.txt")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)

                # 從原始訊息嘗試提取 摘要資訊（事件編號、檔名、工作表）
                evt = 'N/A'
                fname = 'N/A'
                ws = 'N/A'
                try:
                    import re
                    for line in message.splitlines():
                        # 先嘗試表格標題樣式：(事件#12) C:\path\file.xlsx [Worksheet: Sheet1]
                        m = re.search(r"\(事件#(\d+)\)\s+(.+?)\s+\[Worksheet:\s*(.*?)\]", line)
                        if m:
                            evt = m.group(1)
                            # 取檔名
                            try:
                                fname = os.path.basename(m.group(2).strip())
                            except Exception:
                                fname = m.group(2).strip()
                            ws = m.group(3).strip()
                            break
                        # 再嘗試變更橫幅：🔔 檔案變更偵測: File.xlsx (事件 #12)
                        m2 = re.search(r"變更偵測:\s*(.+?)\s*\(事件\s*#(\d+)\)", line)
                        if m2:
                            evt = m2.group(2)
                            try:
                                fname = os.path.basename(m2.group(1).strip())
                            except Exception:
                                fname = m2.group(1).strip()
                            # worksheet 無，保持 N/A
                            break
                except Exception:
                    pass

                with open(log_path, 'a', encoding='utf-8-sig') as f:
                    f.write(timestamped_message)
                    f.write('\n')
                    # 僅在偵測到表格標題或變更橫幅時追加一次摘要行，避免每行都寫。
                    try:
                        global _last_summary_sig
                    except Exception:
                        _last_summary_sig = None
                    if (evt != 'N/A') or change_banner:
                        sig = f"{evt}|{fname}|{ws}"
                        if sig != _last_summary_sig:
                            summary = f"[{timestamp}] [SUMMARY] File={fname} | Worksheet={ws} | Event={evt}"
                            f.write(summary + '\n')
                            _last_summary_sig = sig
    except Exception:
        # 寫檔錯誤不影響正常輸出
        pass
    
    # 檢查是否為比較表格訊息
    is_comparison = any(keyword in message for keyword in [
        'Address', 'Baseline', 'Current', 
        '[SUMMARY]', '====', '----',
        '[MOD]', '[ADD]', '[DEL]'
    ])
    
    # 同時送到黑色 console - 使用延遲導入避免循環導入
    try:
        from ui.console import black_console
        if black_console and black_console.running:
            black_console.add_message(timestamped_message, is_comparison=is_comparison)
    except ImportError:
        pass

def init_logging():
    """
    初始化日誌系統
    """
    builtins.print = timestamped_print

def wrap_text_with_cjk_support(text, width):
    """
    自研的、支持 CJK 字符寬度的智能文本換行函數
    """
    lines = []
    line = ""
    current_width = 0
    for char in text:
        char_width = wcwidth(char)
        if char_width < 0: 
            continue # 跳過控制字符

        if current_width + char_width > width:
            lines.append(line)
            line = char
            current_width = char_width
        else:
            line += char
            current_width += char_width
    if line:
        lines.append(line)
    return lines or ['']

def _get_display_width(text):
    """
    精準計算一個字串的顯示闊度，處理 CJK 全形字元
    """
    return wcswidth(str(text))