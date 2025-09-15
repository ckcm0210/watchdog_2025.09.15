"""
比較和差異顯示功能 - 確保 TABLE 一定顯示
"""
import os
import csv
import gzip
import json
import time
import re
from datetime import datetime
from wcwidth import wcwidth
import config.settings as settings
from utils.console_logging import _get_display_width
from utils.helpers import get_file_mtime
from core.excel_parser import pretty_formula, extract_external_refs, get_excel_last_author
from core.baseline import load_baseline, baseline_file_path
import logging
import hashlib
import json as _json
import core.baseline as baseline

# 全局累積器：每次事件（file_path,event_number）收集所有工作表的顯示資料
_per_event_accum = {}
# 最近一次已輸出的「變更簽名」，用於抑制輪詢階段重覆表格
_last_render_sig_by_file = {}

# ... [print_aligned_console_diff 和其他輔助函數保持不變] ...
def print_aligned_console_diff(old_data, new_data, file_info=None, max_display_changes=0):
    # 全函式範圍原子輸出：確保表格中間不被插入其他訊息
    try:
        from utils.console_output_guard import begin_table_output, end_table_output
        begin_table_output()
    except Exception:
        begin_table_output = None
        end_table_output = None
    """
    三欄式顯示，能處理中英文對齊，並正確顯示 formula。
    Address 欄固定闊度，Baseline/Current 平均分配。
    """
    # 終端寬度：允許設定覆蓋
    try:
        term_width = int(getattr(settings, 'CONSOLE_TERM_WIDTH_OVERRIDE', 0)) or os.get_terminal_size().columns
    except Exception:
        term_width = int(getattr(settings, 'CONSOLE_TERM_WIDTH_OVERRIDE', 0)) or 120

    # Address 欄寬：0=自動，否則用設定值
    configured_addr_w = int(getattr(settings, 'ADDRESS_COL_WIDTH', 0))
    if configured_addr_w > 0:
        address_col_width = configured_addr_w
    else:
        # 自動：取本次要顯示變更的地址最長顯示寬度與 6 取大者，但不超過 16
        try:
            keys = list(set(old_data.keys()) | set(new_data.keys()))
            if keys:
                max_addr = max((_get_display_width(k) or len(str(k)) for k in keys))
                address_col_width = max(6, min(16, max_addr))
            else:
                address_col_width = 10
        except Exception:
            address_col_width = 10

    # 新增 Type 欄位（formula/value）
    type_col_width = int(getattr(settings, 'CONSOLE_TYPE_COL_WIDTH', 10) or 10)
    # 分隔符寬度：四欄有三個 " | " 分隔，各 3 字元
    separators_width = 3 * 3
    remaining_width = term_width - address_col_width - type_col_width - separators_width
    baseline_col_width = max(10, remaining_width // 2)
    current_col_width = baseline_col_width  # 強制左右等寬，確保視覺對稱

    def wrap_text(text, width):
        lines = []
        current_line = ""
        current_width = 0
        for char in str(text):
            char_width = wcwidth(char)
            if char_width < 0:
                continue
            if current_width + char_width > width:
                lines.append(current_line)
                current_line = char
                current_width = char_width
            else:
                current_line += char
                current_width += char_width
        if current_line:
            lines.append(current_line)
        return lines or ['']

    def pad_line(line, width):
        line_width = _get_display_width(line)
        if line_width is None:
            line_width = len(str(line))
        padding = width - line_width
        return str(line) + ' ' * padding if padding > 0 else str(line)

    def _strip_common_prefix(a: str, b: str):
        # 找出共同前綴，回傳 (prefix, a_rest, b_rest)
        i = 0
        la, lb = len(a), len(b)
        while i < la and i < lb and a[i] == b[i]:
            i += 1
        return a[:i], a[i:], b[i:]

    def _maybe_highlight_diff(a: str, b: str):
        if not getattr(settings, 'DIFF_HIGHLIGHT_ENABLED', True):
            return a, b
        try:
            prefix, ar, br = _strip_common_prefix(a, b)
            if ar == '' and br == '':
                # 完全相同
                return a, b
            # 用 «…» 標示差異區段開頭，保留共同前綴一小段（最多 16 字）
            keep = prefix[-16:] if len(prefix) > 16 else prefix
            pa = (keep + '«' + ar) if ar else keep
            pb = (keep + '«' + br) if br else keep
            return pa, pb
        except Exception:
            return a, b

    def format_cell(cell_value):
        if cell_value is None or cell_value == {}:
            return "(Empty)"
        if isinstance(cell_value, dict):
            formula = cell_value.get("formula")
            if formula is not None and formula != "":
                fstr = str(formula)
                # 避免重複等號：如果已經是以 '=' 開頭就不要再加
                return fstr if fstr.startswith('=') else f"={fstr}"
            if "value" in cell_value:
                return repr(cell_value["value"])
        return repr(cell_value)
    
    # 表格原子輸出區塊開始
    try:
        from utils.console_output_guard import print_table_block
    except Exception:
        print_table_block = None
    if print_table_block:
        with print_table_block():
            print()
            print("=" * term_width)
            if file_info:
                filename = file_info.get('filename', 'Unknown')
        worksheet = file_info.get('worksheet', '')
        event_number = file_info.get('event_number')
        file_path = file_info.get('file_path', filename)

        event_str = f"(事件#{event_number}) " if event_number else ""
        caption = f"{event_str}{file_path} [Worksheet: {worksheet}]" if worksheet else f"{event_str}{file_path}"
        for cap_line in wrap_text(caption, term_width):
            print(cap_line)
    print("=" * term_width)

    baseline_time = file_info.get('baseline_time', 'N/A')
    current_time = file_info.get('current_time', 'N/A')
    old_author = file_info.get('old_author', 'N/A')
    new_author = file_info.get('new_author', 'N/A')

    header_addr = pad_line("Address", address_col_width)
    header_type = pad_line("Type", type_col_width)
    # 把時間/作者資訊改到下一行（可由設定控制），讓第一行標頭更短，內容欄位更寬
    if getattr(settings, 'HEADER_INFO_SECOND_LINE', True):
        header_base = pad_line("Baseline", baseline_col_width)
        header_curr = pad_line("Current", current_col_width)
        print(f"{header_addr} | {header_type} | {header_base} | {header_curr}")
        # 第二行顯示時間/作者
        header2_base = pad_line(f"({baseline_time} by {old_author})", baseline_col_width)
        header2_curr = pad_line(f"({current_time} by {new_author})", current_col_width)
        print(f"{' ' * address_col_width} | {' ' * type_col_width} | {header2_base} | {header2_curr}")
    else:
        header_base = pad_line(f"Baseline ({baseline_time} by {old_author})", baseline_col_width)
        header_curr = pad_line(f"Current ({current_time} by {new_author})", current_col_width)
        print(f"{header_addr} | {header_type} | {header_base} | {header_curr}")
    print("-" * term_width)

    # 自然排序：A1, A2, A10（而非 A1, A10, A2）
    import re
    def _addr_key(k):
        m = re.match(r"^([A-Za-z]+)(\d+)$", str(k))
        if not m:
            return (str(k), 0)
        col, row = m.group(1), int(m.group(2))
        return (col.upper(), row)
    all_keys = sorted(list(set(old_data.keys()) | set(new_data.keys())), key=_addr_key)
    if not all_keys:
        print("(No cell changes)")
    else:
        displayed_changes_count = 0
        for key in all_keys:
            if max_display_changes > 0 and displayed_changes_count >= max_display_changes:
                print(f"...(僅顯示前 {max_display_changes} 個變更，總計 {len(all_keys)} 個變更)...")
                break

            old_cell = old_data.get(key) or {}
            new_cell = new_data.get(key) or {}

            def _fmt_formula(cell):
                f = cell.get('formula') if isinstance(cell, dict) else None
                if f is None or f == '':
                    return '(No formula)'
                s = str(f)
                return s if s.startswith('=') else f'={s}'

            def _disp_value(cell):
                if not isinstance(cell, dict):
                    return None
                v = cell.get('cached_value') if cell.get('cached_value') is not None else cell.get('value')
                return v

            def _fmt_value(cell):
                v = _disp_value(cell)
                if v is None or v == '':
                    return '(Empty)'
                try:
                    # 與原邏輯一致：字串加引號
                    return repr(v)
                except Exception:
                    return str(v)

            # 公式行
            old_formula_text = _fmt_formula(old_cell)
            new_formula_text = _fmt_formula(new_cell)
            old_formula_text, new_formula_text = _maybe_highlight_diff(str(old_formula_text), str(new_formula_text))

            gap = ' ' * int(getattr(settings, 'CONSOLE_ADDRESS_GAP', 0) or 0)
            addr_lines = [gap + ln if ln else gap for ln in wrap_text(key, address_col_width)]
            old_f_lines = wrap_text(old_formula_text, baseline_col_width)
            new_f_lines = wrap_text(new_formula_text, current_col_width)
            num_lines_f = max(len(addr_lines), len(old_f_lines), len(new_f_lines))
            for i in range(num_lines_f):
                a_line = addr_lines[i] if i < len(addr_lines) else ''
                t_line = 'formula' if i == 0 else ''
                o_line = old_f_lines[i] if i < len(old_f_lines) else ''
                n_line = new_f_lines[i] if i < len(new_f_lines) else ''
                formatted_a = pad_line(a_line, address_col_width)
                formatted_t = pad_line(t_line, type_col_width)
                formatted_o = pad_line(o_line, baseline_col_width)
                formatted_n = n_line
                print(f"{formatted_a} | {formatted_t} | {formatted_o} | {formatted_n}")

            # 值行
            old_val_text = _fmt_value(old_cell)
            new_val_text = _fmt_value(new_cell)
            old_val_text, new_val_text = _maybe_highlight_diff(str(old_val_text), str(new_val_text))
            old_v_lines = wrap_text(old_val_text, baseline_col_width)
            new_v_lines = wrap_text(new_val_text, current_col_width)
            num_lines_v = max(len(addr_lines), len(old_v_lines), len(new_v_lines))
            for i in range(num_lines_v):
                # 地址列第二行開始空白（避免重覆）
                a_line = ''
                t_line = 'value' if i == 0 else ''
                o_line = old_v_lines[i] if i < len(old_v_lines) else ''
                n_line = new_v_lines[i] if i < len(new_v_lines) else ''
                formatted_a = pad_line(a_line, address_col_width)
                formatted_t = pad_line(t_line, type_col_width)
                formatted_o = pad_line(o_line, baseline_col_width)
                formatted_n = n_line
                print(f"{formatted_a} | {formatted_t} | {formatted_o} | {formatted_n}")

            displayed_changes_count += 1
            # 每個地址之後畫一條分隔線（最後一組不畫）
            if displayed_changes_count < len(all_keys):
                print("-" * term_width)
    print("=" * term_width)
    print()
    # 全函式原子輸出結束：flush 期間緩存訊息
    try:
        if end_table_output:
            end_table_output()
    except Exception:
        pass

def format_timestamp_for_display(timestamp_str):
    if not timestamp_str or timestamp_str == 'N/A':
        return 'N/A'
    try:
        if 'T' in timestamp_str:
            if '.' in timestamp_str:
                timestamp_str = timestamp_str.split('.')[0]
            return timestamp_str.replace('T', ' ')
        return timestamp_str
    except ValueError as e:
        logging.error(f"格式化時間戳失敗: {timestamp_str}, 錯誤: {e}")
        return timestamp_str

def compare_excel_changes(file_path, silent=False, event_number=None, is_polling=False):
    """
    [最終修正版] 統一日誌記錄和顯示邏輯
    """
    try:
        from core.excel_parser import dump_excel_cells_with_timeout
        
        from utils.helpers import _baseline_key_for_path
        base_key = _baseline_key_for_path(file_path)
        
        old_baseline = load_baseline(base_key)
        # 快速跳過：只在「輪詢比較」時啟用；即時比較一律重新讀取，避免漏判
        if is_polling and settings.QUICK_SKIP_BY_STAT and old_baseline and \
           ("source_mtime" in old_baseline) and ("source_size" in old_baseline):
            try:
                cur_mtime = os.path.getmtime(file_path)
                cur_size  = os.path.getsize(file_path)
                base_mtime = float(old_baseline.get("source_mtime", 0))
                base_size  = int(old_baseline.get("source_size", -1))
                if (cur_size == base_size) and (abs(cur_mtime - base_mtime) <= float(getattr(settings,'MTIME_TOLERANCE_SEC',2.0))):
                    if not silent:
                        print(f"[快速通過] {os.path.basename(file_path)} mtime/size 未變，略過讀取。")
                    return False
            except Exception:
                pass
        if old_baseline is None:
            old_baseline = {}

        current_data = dump_excel_cells_with_timeout(file_path, show_sheet_detail=False, silent=True)
        if current_data is None:
            time.sleep(1)
            current_data = dump_excel_cells_with_timeout(file_path, show_sheet_detail=False, silent=True)
            if current_data is None:
                if not silent:
                    print(f"❌ 重試後仍無法讀取檔案: {os.path.basename(file_path)}")
                return False
        
        baseline_cells = old_baseline.get('cells', {})
        
        # 檢查是否為無變更情況
        has_content_changes = baseline_cells != current_data
        
        if not has_content_changes:
            # 如果是輪詢且無變化，則不顯示任何內容
            if is_polling:
                print(f"    [輪詢檢查] {os.path.basename(file_path)} 內容無變化。")
                return False
            
            # 非輪詢模式下，跳過工作表比較，直接記錄無變更事件
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"   [timeline-no-change] 偵測到無變更事件: {os.path.basename(file_path)}")
            any_sheet_has_changes = False
        else:
            any_sheet_has_changes = False
        
        old_author = old_baseline.get('last_author', 'N/A')
        try:
            new_author = get_excel_last_author(file_path)
        except Exception:
            new_author = 'Unknown'

        for worksheet_name in set(baseline_cells.keys()) | set(current_data.keys()):
            old_ws = baseline_cells.get(worksheet_name, {})
            new_ws = current_data.get(worksheet_name, {})
            
            if old_ws == new_ws:
                continue

            any_sheet_has_changes = True
            
            # 只有在非靜默模式下才顯示和記錄
            if not silent:
                baseline_timestamp = old_baseline.get('timestamp', 'N/A')
                current_timestamp = get_file_mtime(file_path)
                
                # 只顯示「有意義變更」（隱藏間接變更/無意義變更）
                # 即時比較（is_polling=False）不抑制純值變更，確保有表出來；輪詢比較才允許抑制
                meaningful_changes = analyze_meaningful_changes(old_ws, new_ws, allow_suppress=is_polling)
                if not meaningful_changes:
                    # 為了可視性：即時比較若沒有有意義變更，仍至少輸出表頭與 (No cell changes)
                    if not is_polling:
                        print_aligned_console_diff({}, {}, {
                            'filename': os.path.basename(file_path),
                            'file_path': file_path,
                            'event_number': event_number,
                            'worksheet': worksheet_name,
                            'baseline_time': format_timestamp_for_display(old_baseline.get('timestamp', 'N/A')),
                            'current_time': format_timestamp_for_display(get_file_mtime(file_path)),
                            'old_author': old_author,
                            'new_author': new_author,
                        }, max_display_changes=0)
                    continue
                addrs = [c['address'] for c in meaningful_changes]
                display_old = {addr: old_ws.get(addr) for addr in addrs}
                display_new = {addr: new_ws.get(addr) for addr in addrs}

                # 以簽名去重：抑制輪詢階段重覆輸出相同內容的表格
                try:
                    import hashlib as _hashlib
                    sig_payload = (
                        os.path.abspath(file_path),
                        worksheet_name,
                        tuple(sorted(display_old.keys())),
                        tuple(sorted(display_new.keys())),
                    )
                    sig = _hashlib.md5(str(sig_payload).encode('utf-8')).hexdigest()
                except Exception:
                    sig = None

                if is_polling and sig is not None:
                    try:
                        global _last_render_sig_by_file
                    except Exception:
                        _last_render_sig_by_file = {}
                    last = _last_render_sig_by_file.get((file_path, worksheet_name))
                    if last == sig:
                        # 輪詢且簽名相同：不再輸出重覆表格
                        continue
                    _last_render_sig_by_file[(file_path, worksheet_name)] = sig

                # 顯示比較表（僅有意義變更，用畫面上限）
                print_aligned_console_diff(
                    display_old,
                    display_new,
                    {
                        'filename': os.path.basename(file_path),
                        'file_path': file_path,
                        'event_number': event_number,
                        'worksheet': worksheet_name,
                        'baseline_time': format_timestamp_for_display(baseline_timestamp),
                        'current_time': format_timestamp_for_display(current_timestamp),
                        'old_author': old_author,
                        'new_author': new_author,
                    },
                    max_display_changes=settings.MAX_CHANGES_TO_DISPLAY
                )

                # 事件詳版輸出（不受畫面上限限制）
                try:
                    if getattr(settings, 'PER_EVENT_CONSOLE_ENABLED', True):
                        max_full = int(getattr(settings, 'PER_EVENT_CONSOLE_MAX_CHANGES', 0) or 0)
                        include_all = bool(getattr(settings, 'PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS', True))
                        # 若包含所有有變更的工作表，則延後到全部工作表處理完成後一次性寫檔；先收集
                        if include_all:
                            try:
                                global _per_event_accum
                            except Exception:
                                _per_event_accum = {}
                            key = (file_path, event_number)
                            _per_event_accum.setdefault(key, []).append((worksheet_name, display_old, display_new, baseline_timestamp, current_timestamp, old_author, new_author))
                            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                                try:
                                    print(f"   [event-txt] accumulate key={os.path.basename(file_path)}#evt{event_number} items={len(_per_event_accum.get(key, []))}")
                                except Exception:
                                    pass
                        else:
                            # 單一工作表立即寫一個文件
                            _write_full_event_console_file(file_path, event_number, worksheet_name, display_old, display_new, baseline_timestamp, current_timestamp, old_author, new_author, max_full)
                except Exception:
                    pass
                
                # 分析並記錄有意義的變更
                        # 分析並記錄有意義的變更（帶入設定控制）
                meaningful_changes = analyze_meaningful_changes(old_ws, new_ws)
                if meaningful_changes:
                    # 只在非輪詢的第一次檢查時記錄日誌，避免重複
                    if not is_polling:
                        log_meaningful_changes_to_csv(file_path, worksheet_name, meaningful_changes, new_author)

        # 如果沒有內容變更，取得作者與時間戳以供無變更事件使用
        if not has_content_changes:
            baseline_timestamp = old_baseline.get('timestamp', 'N/A')
            current_timestamp = get_file_mtime(file_path)

        # 事件詳版輸出：在所有工作表處理完後，如果啟用包含所有工作表，於此寫出完整檔
        per_event_file_path = ''
        try:
            if not silent and any_sheet_has_changes and getattr(settings, 'PER_EVENT_CONSOLE_ENABLED', True) and getattr(settings, 'PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS', True):
                key = (file_path, event_number)
                items = _per_event_accum.get(key, [])
                if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                    try:
                        print(f"   [event-txt] write-all key={os.path.basename(file_path)}#evt{event_number} sheets={len(items)}")
                    except Exception:
                        pass
                if items:
                    max_full = int(getattr(settings, 'PER_EVENT_CONSOLE_MAX_CHANGES', 0) or 0)
                    per_event_file_path = _write_full_event_console_file_multi(file_path, event_number, items, max_full)
                    if getattr(settings, 'SHOW_DEBUG_MESSAGES', False) and per_event_file_path:
                        try:
                            print(f"   [timeline-per-event] path={per_event_file_path}")
                        except Exception:
                            pass
                    try:
                        _per_event_accum.pop(key, None)
                    except Exception:
                        pass
        except Exception:
            pass

        # 任何可見的比較（非靜默）且確實有變更時，先保存歷史快照，再（如啟用）更新基準線
        if any_sheet_has_changes and not silent:
            # MVP：保存完整快照（timeline）
            try:
                from utils.history import save_history_snapshot, sync_history_to_git_repo, insert_event_index
                mc_count = 0
                try:
                    mc_count = sum(len(analyze_meaningful_changes(baseline_cells.get(ws, {}), current_data.get(ws, {}))) for ws in set(baseline_cells.keys()) | set(current_data.keys()))
                except Exception:
                    mc_count = 0
                # 準備 Timeline diffs（限量）
                diffs_for_timeline = []
                try:
                    _limit = int(getattr(settings, 'UI_TIMELINE_MAX_EVENT_DIFFS', 200) or 200)
                except Exception:
                    _limit = 200
                try:
                    ws_all = set(baseline_cells.keys()) | set(current_data.keys())
                    for _ws in ws_all:
                        diffs = analyze_meaningful_changes(baseline_cells.get(_ws, {}), current_data.get(_ws, {}))
                        for ch in diffs:
                            diffs_for_timeline.append({
                                'worksheet': _ws,
                                'address': ch.get('address'),
                                'old_value': ch.get('old_value'),
                                'new_value': ch.get('new_value'),
                                'old_formula': ch.get('old_formula'),
                                'new_formula': ch.get('new_formula'),
                            })
                            if len(diffs_for_timeline) >= _limit:
                                break
                        if len(diffs_for_timeline) >= _limit:
                            break
                except Exception:
                    pass
                # 1) 保存壓縮快照（LOG_FOLDER/history）
                snap_path = save_history_snapshot(file_path, current_data, last_author=new_author, event_number=event_number, meaningful_changes_count=mc_count)
                # 2) 同步純 JSON 到 excel_git_repo 並 commit（如 Git 可用）
                git_json_path = sync_history_to_git_repo(file_path, current_data, last_author=new_author, event_number=event_number, meaningful_changes_count=mc_count)
                # 3) 插入事件索引（SQLite）
                try:
                    old_cells = (baseline.load_baseline(base_key) or {}).get('cells', {})
                except Exception:
                    old_cells = baseline_cells or {}
                insert_event_index(file_path,
                                   old_cells=old_cells,
                                   new_cells=current_data,
                                   last_author=new_author,
                                   event_number=event_number,
                                   snapshot_path=snap_path,
                                   summary_path=None,
                                   git_commit_sha=None,
                                   db_path=None)
            except Exception:
                pass
            # Timeline 靜態 HTML（A - 原版 index.html）- 已停用，避免重複事件
            # 現在統一使用 Matrix 版本（index3）+ Index4
            # try:
            #     from utils.timeline_exporter import export_event as export_html_event
            #     export_html_event({...})
            # except Exception:
            #     pass
                
            # Timeline 靜態 HTML（V6/Index3 - Matrix風格 index3.html）
            try:
                from utils.timeline_exporter_index3 import export_event as export_html_event_v6
                export_html_event_v6({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'file': file_path,
                    'filename': os.path.basename(file_path),
                    'worksheet': 'all',
                    'changes': mc_count,
                    'author': new_author,
                    'event_number': event_number,
                    'baseline_time': format_timestamp_for_display(baseline_timestamp),
                    'current_time': format_timestamp_for_display(current_timestamp),
                    'snapshot_path': snap_path,
                    'per_event_path': per_event_file_path,
                    'diffs': diffs_for_timeline
                })
            except Exception:
                pass
            
            # 差異報告 HTML（新增）
            try:
                if getattr(settings, 'GENERATE_DIFF_REPORT', True):
                    from utils.diff_report_generator import generate_diff_report
                    diff_report_path = generate_diff_report(baseline_cells, current_data, file_path)
                    if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                        print(f"[diff-report] 差異報告已生成: {diff_report_path}")
            except Exception as e:
                if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                    print(f"[diff-report] 生成差異報告失敗: {e}")
            # Timeline Excel（B）
            try:
                from utils.timeline_excel import export_event as export_xlsx_event
                export_xlsx_event({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'file': file_path,
                    'filename': os.path.basename(file_path),
                    'worksheet': 'all',
                    'changes': mc_count,
                    'author': new_author,
                    'event_number': event_number,
                    'snapshot_path': snap_path,
                    'per_event_path': per_event_file_path
                })
            except Exception:
                pass
            if settings.AUTO_UPDATE_BASELINE_AFTER_COMPARE:
                print(f"🔄 自動更新基準線: {os.path.basename(file_path)}")
                cur_mtime = os.path.getmtime(file_path)
                cur_size  = os.path.getsize(file_path)
                updated_baseline = {
                    "last_author": new_author,
                    "content_hash": f"updated_{int(time.time())}",
                    "cells": current_data,
                    "timestamp": datetime.now().isoformat(),
                     "source_mtime": cur_mtime,
                     "source_size": cur_size
                }
                if not baseline.save_baseline(base_key, updated_baseline):
                    print(f"[WARNING] 基準線更新失敗: {os.path.basename(file_path)}")
        
        # 新增：記錄「無變更」的儲存事件到 Timeline
        if not any_sheet_has_changes and not silent and not is_polling:
            # 只在「非輪詢」且「非靜默」時記錄無變更事件
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"   [timeline-no-change] 準備記錄無變更事件: {os.path.basename(file_path)}, silent={silent}, is_polling={is_polling}")
            try:
                # 尋找該檔案最近的快照（如果有的話）
                previous_snapshot = None
                try:
                    from utils.history import find_latest_snapshot_for_file
                    previous_snapshot = find_latest_snapshot_for_file(file_path)
                except Exception:
                    pass
                
                # 匯出無變更事件到 Timeline（直接調用 Matrix clean，避免重複）
                from utils.timeline_exporter_matrix_clean import export_event as export_matrix_clean_event
                export_matrix_clean_event({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'file': file_path,
                    'filename': os.path.basename(file_path),
                    'worksheet': 'all',
                    'changes': 0,  # 無變更
                    'author': new_author or 'Unknown',
                    'event_number': event_number,
                    'baseline_time': '',  # 無比較，留空
                    'current_time': '',   # 無比較，留空
                    'snapshot_path': previous_snapshot or '',  # 最近的快照或空
                    'per_event_path': '',  # 無詳表
                    'diffs': []  # 無差異
                })
                # 同時處理 Index4（如果啟用且作者符合）
                try:
                    from utils.timeline_exporter_index4 import export_event as export_index4_event
                    export_index4_event({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'file': file_path,
                        'filename': os.path.basename(file_path),
                        'worksheet': 'all',
                        'changes': 0,
                        'author': new_author or 'Unknown',
                        'event_number': event_number,
                        'baseline_time': '',
                        'current_time': '',
                        'snapshot_path': previous_snapshot or '',
                        'per_event_path': '',
                        'diffs': []
                    })
                except Exception as e:
                    if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                        print(f"   [timeline-no-change] Index4 匯出失敗: {e}")
                
                # 手動觸發 index3 更新（因為我們直接調用了 matrix_clean）
                try:
                    from utils.timeline_exporter_index3 import _write_index3_from_index2
                    _write_index3_from_index2()
                except Exception as e:
                    if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                        print(f"   [timeline-no-change] index3 更新失敗: {e}")
                
                if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                    print(f"   [timeline-no-change] 記錄無變更儲存事件: {os.path.basename(file_path)} by {new_author or 'Unknown'}")
                    
            except Exception as e:
                if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                    print(f"   [timeline-no-change] 記錄無變更事件失敗: {e}")
        
        return any_sheet_has_changes
        
    except Exception as e:
        if not silent:
            logging.error(f"比較過程出錯: {e}")
        return False

def _sanitize_filename_component(s: str) -> str:
    try:
        s = str(s or '').strip()
        s = re.sub(r'[\\/:*?"<>|]+', '_', s)
        s = s.replace('\n',' ').replace('\r',' ')
        return s
    except Exception:
        return 'Unknown'


def _write_full_event_console_file_multi(file_path, event_number, items, max_full=0):
    try:
        out_dir = getattr(settings, 'PER_EVENT_CONSOLE_DIR', None) or os.path.join(settings.LOG_FOLDER, 'console_details')
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # 取最後一張工作表的作者與時間作為檔名（或可合併成最晚一個）
        try:
            last = items[-1]
            _, _, _, baseline_timestamp, current_timestamp, old_author, new_author = last
        except Exception:
            baseline_timestamp = 'N/A'; current_timestamp='N/A'; old_author='N/A'; new_author='N/A'
        author = new_author or old_author or 'Unknown'
        ts = format_timestamp_for_display(current_timestamp).replace(' ', '_').replace(':','')
        if getattr(settings, 'PER_EVENT_CONSOLE_ADD_EVENT_ID', True) and event_number is not None:
            evt = f"_evt{event_number}"
        else:
            evt = ''
        fname = f"{_sanitize_filename_component(base_name)}_{_sanitize_filename_component(author)}_{ts}{evt}.txt"
        out_path = os.path.join(out_dir, fname)
        with open(out_path, 'w', encoding='utf-8-sig') as f:
            import builtins
            _orig_print = builtins.print
            try:
                builtins.print = lambda *a, **k: _orig_print(*a, **{**k, 'file': f})
                # 逐個工作表輸出（全量或按 max_full 切分）
                for (worksheet_name, display_old, display_new, baseline_timestamp, current_timestamp, old_author, new_author) in items:
                    print_aligned_console_diff(display_old, display_new,
                        {
                            'filename': os.path.basename(file_path),
                            'file_path': file_path,
                            'event_number': event_number,
                            'worksheet': worksheet_name,
                            'baseline_time': format_timestamp_for_display(baseline_timestamp),
                            'current_time': format_timestamp_for_display(current_timestamp),
                            'old_author': old_author,
                            'new_author': new_author,
                        },
                        max_display_changes=(0 if (not max_full or max_full<=0) else max_full))
            finally:
                builtins.print = _orig_print
        return out_path
    except Exception as e:
        logging.error(f"寫入完整 Console 檔失敗: {e}")
        return ''


def _write_full_event_console_file(file_path, event_number, worksheet_name, display_old, display_new, baseline_timestamp, current_timestamp, old_author, new_author, max_full=0):
    try:
        out_dir = getattr(settings, 'PER_EVENT_CONSOLE_DIR', None) or os.path.join(settings.LOG_FOLDER, 'console_details')
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        author = new_author or old_author or 'Unknown'
        ts = format_timestamp_for_display(current_timestamp).replace(' ', '_').replace(':','')
        if getattr(settings, 'PER_EVENT_CONSOLE_ADD_EVENT_ID', True) and event_number is not None:
            evt = f"_evt{event_number}"
        else:
            evt = ''
        fname = f"{_sanitize_filename_component(base_name)}_{_sanitize_filename_component(author)}_{ts}{evt}.txt"
        out_path = os.path.join(out_dir, fname)
        # 準備完整輸出（不受畫面上限限制/或按 max_full）
        term_width = int(getattr(settings, 'CONSOLE_TERM_WIDTH_OVERRIDE', 0)) or 120
        with open(out_path, 'w', encoding='utf-8-sig') as f:
            def _emit(old_map, new_map):
                # 將 print_aligned_console_diff 的輸出重定向到檔案
                import builtins
                _orig_print = builtins.print
                try:
                    builtins.print = lambda *a, **k: _orig_print(*a, **{**k, 'file': f})
                    print_aligned_console_diff(old_map, new_map,
                        {
                            'filename': os.path.basename(file_path),
                            'file_path': file_path,
                            'event_number': event_number,
                            'worksheet': worksheet_name,
                            'baseline_time': format_timestamp_for_display(baseline_timestamp),
                            'current_time': format_timestamp_for_display(current_timestamp),
                            'old_author': old_author,
                            'new_author': new_author,
                        },
                        max_display_changes=max_full)
                finally:
                    builtins.print = _orig_print
            # 若 max_full=0 → 不限；否則按上限切分
            if max_full and max_full > 0:
                keys = list(set(display_old.keys()) | set(display_new.keys()))
                import re
                def _addr_key(k):
                    m = re.match(r"^([A-Za-z]+)(\d+)$", str(k))
                    if not m: return (str(k), 0)
                    return (m.group(1).upper(), int(m.group(2)))
                all_keys = sorted(keys, key=_addr_key)
                for i in range(0, len(all_keys), max_full):
                    sub_old = {k: display_old.get(k) for k in all_keys[i:i+max_full]}
                    sub_new = {k: display_new.get(k) for k in all_keys[i:i+max_full]}
                    _emit(sub_old, sub_new)
            else:
                _emit(display_old, display_new)
    except Exception as e:
        logging.error(f"寫入完整 Console 檔失敗: {e}")


def analyze_meaningful_changes(old_ws, new_ws, *, allow_suppress=True):
    """
    🧠 分析有意義的變更
    """
    meaningful_changes = []
    all_addresses = set(old_ws.keys()) | set(new_ws.keys())
    
    for addr in all_addresses:
        old_cell = old_ws.get(addr, {})
        new_cell = new_ws.get(addr, {})
        
        if old_cell == new_cell:
            continue

        change_type = classify_change_type(
            old_cell,
            new_cell,
            show_external_refresh=getattr(settings, 'SHOW_EXTERNAL_REFRESH_CHANGES', True),
            suppress_internal_same_value=getattr(settings, 'SUPPRESS_INTERNAL_FORMULA_CHANGE_WITH_SAME_VALUE', False),
            formula_only_mode=(getattr(settings, 'FORMULA_ONLY_MODE', False) if allow_suppress else False),
        )
        
        # 根據設定過濾變更
        if (
            change_type in ('FORMULA_CHANGE_INTERNAL', 'EXTERNAL_REF_LINK_CHANGE') and not settings.TRACK_FORMULA_CHANGES
        ) or (
            change_type == 'DIRECT_VALUE_CHANGE' and not settings.TRACK_DIRECT_VALUE_CHANGES
        ) or (
            change_type in ('EXTERNAL_REFRESH_UPDATE', 'EXTERNAL_REF_LINK_CHANGE') and not settings.TRACK_EXTERNAL_REFERENCES
        ) or (
            change_type == 'INDIRECT_CHANGE' and settings.IGNORE_INDIRECT_CHANGES
        ):
            continue

        # 將輸出值優先用 cached_value（若存在）
        def _disp(x):
            return x.get('cached_value') if x.get('cached_value') is not None else x.get('value')
        meaningful_changes.append({
            'address': addr,
            'old_value': _disp(old_cell),
            'new_value': _disp(new_cell),
            'old_formula': old_cell.get('formula'),
            'new_formula': new_cell.get('formula'),
            'change_type': change_type
        })
    
    return meaningful_changes

def classify_change_type(old_cell, new_cell, *, show_external_refresh=True, suppress_internal_same_value=False, formula_only_mode=False):
    """
    🔍 分類變更類型
    """
    old_val = old_cell.get('cached_value') if old_cell.get('cached_value') is not None else old_cell.get('value')
    new_val = new_cell.get('cached_value') if new_cell.get('cached_value') is not None else new_cell.get('value')
    old_formula = old_cell.get('formula')
    new_formula = new_cell.get('formula')
    old_ext = bool(old_cell.get('external_ref', False))
    new_ext = bool(new_cell.get('external_ref', False))
    is_external = old_ext or new_ext or has_external_reference(old_formula) or has_external_reference(new_formula)

    if not old_cell and new_cell:
        return 'CELL_ADDED'
    if old_cell and not new_cell:
        return 'CELL_DELETED'

    # 公式變更：外部 vs 內部
    if old_formula != new_formula:
        if is_external:
            return 'EXTERNAL_REF_LINK_CHANGE'
        # 內部公式變更：可選擇是否抑制同值
        if suppress_internal_same_value and (old_val == new_val):
            return 'NO_CHANGE'
        return 'FORMULA_CHANGE_INTERNAL'

    # 公式未變：外部 refresh vs 內部間接
    if old_formula and new_formula and old_val != new_val:
        if is_external:
            return 'EXTERNAL_REFRESH_UPDATE' if show_external_refresh else 'NO_CHANGE'
        else:
            return 'INDIRECT_CHANGE'

    # 純值變更（非公式）
    if not old_formula and not new_formula and old_val != new_val:
        if formula_only_mode:
            return 'NO_CHANGE'
        return 'DIRECT_VALUE_CHANGE'

    return 'NO_CHANGE'

def has_external_reference(formula):
    if not formula:
        return False
    try:
        import re
        s = str(formula)
        # 命中 [n]Sheet!A1
        if re.search(r"\[(\d+)\][^!\]]+!", s):
            return True
        # 命中 '...\\[Book.xlsx]Sheet'!
        if re.search(r"'[^']*\\\[[^\\\]]+\][^']*'!", s):
            return True
        # 命中 [Book.xlsx]Sheet!A1（無引號）
        if re.search(r"\[[^\]]+\][^!]+!", s):
            return True
        return False
    except Exception:
        return False

_recent_log_signatures = {}

def log_meaningful_changes_to_csv(file_path, worksheet_name, changes, current_author):
    """
    📝 記錄有意義的變更到 CSV (最終統一版)
    - 增加過去一段時間內的去重：相同內容在 LOG_DEDUP_WINDOW_SEC 內不會重複記錄
    """
    if not current_author or current_author == 'N/A' or not changes:
        return

    # 構建變更的穩定簽名（檔名+表名+變更內容）
    try:
        # 規範化 changes 項目（避免相同內容不同順序造成簽名不同）
        def _norm(x):
            return (
                str(x.get('address','')),
                str(x.get('change_type','')),
                _json.dumps(x.get('old_value', ''), ensure_ascii=False, sort_keys=True),
                _json.dumps(x.get('new_value', ''), ensure_ascii=False, sort_keys=True),
                str(x.get('old_formula','')),
                str(x.get('new_formula','')),
            )
        normalized_changes = sorted([_norm(c) for c in (changes or [])])
        payload = {
            'file': os.path.abspath(file_path),
            'sheet': worksheet_name,
            'changes': normalized_changes,
        }
        sig = hashlib.md5(_json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        now = time.time()
        window = float(getattr(settings, 'LOG_DEDUP_WINDOW_SEC', 300))
        # 清理過期的簽名
        for k in list(_recent_log_signatures.keys()):
            if now - _recent_log_signatures[k] > window:
                _recent_log_signatures.pop(k, None)
        # 如果簽名仍在時間窗內，跳過記錄
        if sig in _recent_log_signatures:
            return
        _recent_log_signatures[sig] = now
    except Exception:
        pass

    try:
        os.makedirs(os.path.dirname(settings.CSV_LOG_FILE), exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file_exists = os.path.exists(settings.CSV_LOG_FILE)
        
        with gzip.open(settings.CSV_LOG_FILE, 'at', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    'Timestamp', 'Filename', 'Worksheet', 'Cell', 'Change_Type',
                    'Old_Value', 'New_Value', 'Old_Formula', 'New_Formula', 'Last_Author'
                ])
            
            for change in changes:
                writer.writerow([
                    timestamp,
                    os.path.basename(file_path),
                    worksheet_name,
                    change['address'],
                    change['change_type'],
                    change.get('old_value', ''),
                    change.get('new_value', ''),
                    change.get('old_formula', ''),
                    change.get('new_formula', ''),
                    current_author
                ])
        
        print(f"📝 {len(changes)} 項變更已記錄到 CSV")
        
        # 額外輸出一份 UTF-8 BOM 的純 CSV，便於 Excel 正確讀取中文
        try:
            if getattr(settings, 'CSV_LOG_EXPORT_PLAIN_UTF8_BOM', True):
                plain_csv = os.path.splitext(settings.CSV_LOG_FILE)[0] + '.csv'
                new_file = not os.path.exists(plain_csv)
                with open(plain_csv, 'a', encoding='utf-8-sig', newline='') as f2:
                    writer2 = csv.writer(f2)
                    if new_file:
                        writer2.writerow([
                            'Timestamp', 'Filename', 'Worksheet', 'Cell', 'Change_Type',
                            'Old_Value', 'New_Value', 'Old_Formula', 'New_Formula', 'Last_Author'
                        ])
                    for change in changes:
                        writer2.writerow([
                            timestamp,
                            os.path.basename(file_path),
                            worksheet_name,
                            change['address'],
                            change['change_type'],
                            change.get('old_value', ''),
                            change.get('new_value', ''),
                            change.get('old_formula', ''),
                            change.get('new_formula', ''),
                            current_author
                        ])
        except Exception as ee:
            logging.error(f"輸出 UTF-8 BOM CSV 失敗: {ee}")
        
    except (OSError, csv.Error) as e:
        logging.error(f"記錄有意義的變更到 CSV 時發生錯誤: {e}")

# 輔助函數
def set_current_event_number(event_number):
    # 這個函數可能不再需要，但暫時保留
    pass