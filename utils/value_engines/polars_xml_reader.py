import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import os

# 以 XML 解析 .xlsx 的 worksheet 值（cached），再交由上層使用（可配合 Polars 做後處理）
# 返回結構：{ sheet_name: { 'A1': value, ... } }

NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def _load_shared_strings(z: zipfile.ZipFile) -> list:
    sst = []
    try:
        if 'xl/sharedStrings.xml' not in z.namelist():
            return sst
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall(f'{{{NS_MAIN}}}si'):
            # 可能有多個 t
            text_parts = []
            # 先找 r/t（富文本）
            for t in si.findall(f'.//{{{NS_MAIN}}}t'):
                text_parts.append(t.text or '')
            if not text_parts:
                # 退回 si/t
                t = si.find(f'{{{NS_MAIN}}}t')
                if t is not None:
                    text_parts.append(t.text or '')
            sst.append(''.join(text_parts))
    except Exception:
        pass
    return sst


def _workbook_sheet_names(z: zipfile.ZipFile) -> list:
    names = []
    try:
        root = ET.fromstring(z.read('xl/workbook.xml'))
        for s in root.findall(f'.//{{{NS_MAIN}}}sheet'):
            nm = s.attrib.get('name')
            if nm:
                names.append(nm)
    except Exception:
        pass
    return names


def _col_letters_to_index(s: str) -> int:
    # 例如 'A'->1, 'Z'->26, 'AA'->27
    s = s.upper()
    n = 0
    for ch in s:
        if 'A' <= ch <= 'Z':
            n = n * 26 + (ord(ch) - ord('A') + 1)
        else:
            break
    return n


def _split_addr(addr: str):
    # 將 'A10' 拆成 ('A', 10)
    col = ''
    row = ''
    for ch in addr:
        if ch.isalpha():
            col += ch
        else:
            row += ch
    try:
        r = int(row)
    except Exception:
        r = 0
    return col, r


def read_values_from_xlsx_via_polars_xml(xlsx_path: str) -> Dict[str, Dict[str, Optional[str]]]:
    out: Dict[str, Dict[str, Optional[str]]] = {}
    
    # 嘗試導入增強型日誌系統
    try:
        from enhanced_logging_and_error_handler import log_operation, log_memory_usage
        has_enhanced_logging = True
        log_operation("開始讀取 Excel 檔案", {"路徑": xlsx_path, "引擎": "polars_xml"})
        log_memory_usage("讀取開始前")
    except ImportError:
        has_enhanced_logging = False
    
    # 增強輸入驗證與錯誤捕捉
    if not xlsx_path:
        print("   [error] 路徑為空")
        return {}
    
    if not isinstance(xlsx_path, str):
        print(f"   [error] 路徑不是字串，而是 {type(xlsx_path)}")
        return {}
        
    if not os.path.exists(xlsx_path):
        print(f"   [error] 路徑不存在: {xlsx_path}")
        return {}
    
    # 記錄檔案資訊
    try:
        file_size = os.path.getsize(xlsx_path) / (1024 * 1024)
        modified_time = os.path.getmtime(xlsx_path)
        access_time = os.path.getatime(xlsx_path)
        
        from datetime import datetime
        print(f"   [file-info] 大小: {file_size:.2f} MB")
        print(f"   [file-info] 修改時間: {datetime.fromtimestamp(modified_time)}")
        print(f"   [file-info] 存取時間: {datetime.fromtimestamp(access_time)}")
        print(f"   [file-info] 存取間隔: {access_time - modified_time:.2f} 秒")
    except Exception as e:
        print(f"   [warning] 無法取得檔案資訊: {e}")
    
    # 記錄記憶體使用
    if not has_enhanced_logging:
        try:
            import psutil
            process = psutil.Process()
            print(f"   [memory] 讀取前: {process.memory_info().rss / 1024 / 1024:.2f} MB")
        except:
            pass
    
    try:
        # 智能快取：檢查是否已在快取中，避免重複快取
        from utils.cache import copy_to_cache, _is_in_cache
        import socket
        
        # 檢查路徑是否已經在快取資料夾中
        if _is_in_cache(xlsx_path):
            local_path = xlsx_path  # 如果已經是快取檔案，直接使用
            print(f"   [info] 路徑已在快取中，直接使用: {xlsx_path}")
        else:
            local_path = copy_to_cache(xlsx_path, silent=True)
            if not local_path:
                return {}
                
        # 設定超時
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)  # 30秒超時
        
        with zipfile.ZipFile(local_path, 'r') as z:
            sst = _load_shared_strings(z)
            sheets = _workbook_sheet_names(z)
            # 順序依 workbook.xml
            for i, name in enumerate(sheets, start=1):
                sheet_path = f'xl/worksheets/sheet{i}.xml'
                if sheet_path not in z.namelist():
                    continue
                try:
                    xml = z.read(sheet_path)
                    root = ET.fromstring(xml)
                    vals: Dict[str, Optional[str]] = {}
                    for c in root.findall(f'.//{{{NS_MAIN}}}c'):
                        addr = c.attrib.get('r')
                        if not addr:
                            continue
                        t = c.attrib.get('t')  # s=sharedString, b=boolean, str=string, inlineStr, etc.
                        v_node = c.find(f'{{{NS_MAIN}}}v')
                        if v_node is None:
                            # inlineStr 支援
                            is_node = c.find(f'{{{NS_MAIN}}}is')
                            if is_node is not None:
                                tnode = is_node.find(f'.//{{{NS_MAIN}}}t')
                                vals[addr] = (tnode.text if tnode is not None else '')
                            continue
                        raw = v_node.text
                        if raw is None:
                            vals[addr] = None
                        elif t == 's':
                            # shared string
                            try:
                                idx = int(raw)
                                vals[addr] = sst[idx] if 0 <= idx < len(sst) else ''
                            except Exception:
                                vals[addr] = ''
                        elif t == 'b':
                            vals[addr] = True if raw in ('1', 'true', 'TRUE') else False
                        else:
                            # 數值或一般字串，先原樣返回（上層如需再做型別轉換）
                            vals[addr] = raw
                    out[name] = vals
                except Exception as e:
                    # 單張表失敗不影響其他表
                    out[name] = {}
    except zipfile.BadZipFile as e:
        handle_zipfile_error(e)
        return {}
    except Exception as e:
        print(f"   [error] 頂層例外: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {}
    finally:
        # 恢復超時設定
        try:
            socket.setdefaulttimeout(old_timeout)
        except:
            pass
        
        # （移除顯式垃圾回收）避免在 Python 3.11/3.12 的 GC 階段觸發底層崩潰（ElementTree/C 擴展）
        # 記錄最終記憶體使用
        try:
            from enhanced_logging_and_error_handler import log_memory_usage, log_open_files, log_operation
            log_memory_usage("讀取完成後")
            log_open_files()
            log_operation("Excel 讀取完成", {"路徑": xlsx_path, "工作表數": len(out)})
        except ImportError:
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                print(f"   [memory] 讀取後: {memory_mb:.2f} MB")
                
                # 檢查記憶體增長是否過大
                try:
                    # 尋找上一個記憶體記錄
                    import re
                    for line in reversed(open(sys.stderr.name, "r").readlines()[-100:]):
                        match = re.search(r"\[memory\] 讀取前: (\d+\.\d+) MB", line)
                        if match:
                            start_mb = float(match.group(1))
                            increase = memory_mb - start_mb
                            if increase > 100:  # 超過100MB增長
                                print(f"   [warning] 記憶體增長過大: +{increase:.2f} MB")
                            break
                except:
                    pass
                
                # 檢查打開的檔案數
                try:
                    open_files = len(process.open_files())
                    if open_files > 50:  # 超過50個檔案
                        print(f"   [warning] 打開檔案數過多: {open_files}")
                except:
                    pass
            except:
                pass
    
    return out
