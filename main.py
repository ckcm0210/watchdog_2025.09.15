"""
Excel Monitor 主執行檔案
多次 Thread Dump 版：
- 每次 Ctrl+C 產生獨立 timestamp thread dump 檔案
- 快速連按兩次 Ctrl+C (默認 1.5 秒內) 才真正停止程式
- 若第二次間隔超過時間窗口 → 視為新一次 dump，不停程式
- 保留：Heartbeat / Thread 數歷史（可開關） / 手動分析工具
"""

import os
os.environ['OPENPYXL_LXML'] = 'True'

import gc
gc.set_threshold(500000, 100, 100)  # 你設定的 GC 閾值

import sys
import signal
import threading
import time
import datetime
import logging
import faulthandler
import traceback
import atexit

# ========== 診斷 / 輸出設定區 ==========
ENABLE_STDOUT_LINE_BUFFERING = True
ENABLE_AUTO_FLUSH_PRINT = True

# Heartbeat
ENABLE_HEARTBEAT = True
HEARTBEAT_INTERVAL = 30
HEARTBEAT_SHOW_THREAD_COUNT = True

# Thread 數歷史紀錄
ENABLE_THREAD_COUNT_HISTORY = True
THREAD_COUNT_HISTORY_FILE = "thread_history.csv"
THREAD_COUNT_HISTORY_ON_CHANGE = True
THREAD_COUNT_HISTORY_INTERVAL_SEC = 300
THREAD_HISTORY_INCLUDE_MEMORY = True

# 多次 Ctrl+C Dump 設定
ENABLE_MULTI_SIGINT_THREAD_DUMP = True
THREAD_DUMP_DIR = "thread_dumps"
DUMP_FILE_PREFIX = "thread_dump"
INCLUDE_FULL_STACK_IN_DUMP = True
EXIT_DOUBLE_PRESS_WINDOW = 1.5   # 兩次 Ctrl+C 之間 <= 此秒數 視為要求結束
SHOW_EXIT_HINT_AFTER_DUMP = True
LIMIT_DUMP_FILE_ROTATE = 0       # 0 = 不限制；>0 則保留最新 N 個檔，超出刪最舊
PRINT_DUMP_PATH_ON_CREATE = True

# 若想改為「第 N 次 Ctrl+C 後才停」，可把下面開關設 True 並設定 MAX_SIGINT_DUMPS_BEFORE_EXIT
USE_FIXED_SIGINT_DUMP_COUNT_TO_EXIT = False
MAX_SIGINT_DUMPS_BEFORE_EXIT = 5  # 只在 USE_FIXED_SIGINT_DUMP_COUNT_TO_EXIT=True 時生效

# 其他（可選）
HEARTBEAT_DUMP_ON_THREAD_CHANGE = False

# 內部狀態
_sigint_last_time = 0.0
_sigint_dump_count = 0
_thread_history_last_write = 0.0

if ENABLE_STDOUT_LINE_BUFFERING:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

if ENABLE_AUTO_FLUSH_PRINT:
    import builtins as _b
    if not getattr(_b, "_ORIGINAL_PRINT_SAVED", False):
        _orig_print = _b.print
        def _auto_flush_print(*a, **kw):
            if 'flush' not in kw:
                kw['flush'] = True
            return _orig_print(*a, **kw)
        _b.print = _auto_flush_print
        _b._ORIGINAL_PRINT_SAVED = True

def _now_iso():
    try:
        return datetime.datetime.now().isoformat(timespec="seconds")
    except Exception:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

def _ensure_dump_dir():
    try:
        os.makedirs(THREAD_DUMP_DIR, exist_ok=True)
    except Exception as e:
        print(f"[dump-dir-error] {e}")

def _rotate_old_dumps():
    if LIMIT_DUMP_FILE_ROTATE <= 0:
        return
    try:
        files = []
        for n in os.listdir(THREAD_DUMP_DIR):
            if n.startswith(DUMP_FILE_PREFIX) and n.endswith(".txt"):
                path = os.path.join(THREAD_DUMP_DIR, n)
                try:
                    stat = os.stat(path)
                    files.append((stat.st_mtime, path))
                except Exception:
                    pass
        if len(files) > LIMIT_DUMP_FILE_ROTATE:
            files.sort()
            to_del = files[0: len(files) - LIMIT_DUMP_FILE_ROTATE]
            for _, p in to_del:
                try:
                    os.remove(p)
                except Exception:
                    pass
    except Exception:
        pass

def list_threads(to_file_path=None):
    """
    輕量 thread 名單
    """
    lines = []
    header = f"=== THREADS ({_now_iso()}) ==="
    lines.append(header)
    try:
        for t in threading.enumerate():
            lines.append(f"{t.name} (daemon={t.daemon}, id={t.ident})")
        lines.append("===============")
    except Exception as e:
        lines.append(f"[list_threads-error] {e}")

    # 輸出到 console
    for ln in lines:
        print(ln)

    if to_file_path:
        try:
            with open(to_file_path, "a", encoding="utf-8") as f:
                for ln in lines:
                    f.write(ln + "\n")
        except Exception as e:
            print(f"[list_threads-write-error] {e}")

def _dump_threads_full(to_file_path, reason="manual"):
    """
    完整 thread dump（含 stack）
    """
    try:
        frames = sys._current_frames()
        threads = list(threading.enumerate())
        header = f"==== THREAD DUMP ({_now_iso()} reason={reason}) ===="
        print("\n" + header)
        for th in threads:
            print(f"\n-- Thread: {th.name} (id={th.ident}, daemon={th.daemon})")
            fr = frames.get(th.ident)
            if INCLUDE_FULL_STACK_IN_DUMP and fr:
                for line in traceback.format_stack(fr):
                    print(line.rstrip())
        print("==== END DUMP ====\n")

        with open(to_file_path, "a", encoding="utf-8") as f:
            f.write(header + "\n")
            for th in threads:
                f.write(f"\n-- Thread: {th.name} (id={th.ident}, daemon={th.daemon})\n")
                fr = frames.get(th.ident)
                if INCLUDE_FULL_STACK_IN_DUMP and fr:
                    for line in traceback.format_stack(fr):
                        f.write(line)
            f.write("\n==== END DUMP ====\n")
    except Exception as e:
        print(f"[thread-dump-error] {e}")

def _create_timestamp_dump_file():
    """
    產生唯一檔案路徑：thread_dumps/thread_dump_YYYYMMDD_HHMMSS_<count>.txt
    """
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 避免同一秒多次：加 dump count
    fname = f"{DUMP_FILE_PREFIX}_{ts}_{_sigint_dump_count:03d}.txt"
    return os.path.join(THREAD_DUMP_DIR, fname)

def _record_thread_history(force=False, reason="change"):
    global _thread_history_last_write
    if not ENABLE_THREAD_COUNT_HISTORY:
        return
    try:
        now = time.time()
        if not force and (now - _thread_history_last_write) < 1.0:
            return
        cnt = len(threading.enumerate())
        mb = ""
        if THREAD_HISTORY_INCLUDE_MEMORY:
            try:
                import psutil
                mb = round(psutil.Process().memory_info().rss / (1024*1024), 2)
            except Exception:
                mb = ""
        new_file = not os.path.exists(THREAD_COUNT_HISTORY_FILE)
        with open(THREAD_COUNT_HISTORY_FILE, "a", encoding="utf-8") as f:
            if new_file:
                if THREAD_HISTORY_INCLUDE_MEMORY:
                    f.write("timestamp,threads,memory_mb,reason\n")
                else:
                    f.write("timestamp,threads,reason\n")
            if THREAD_HISTORY_INCLUDE_MEMORY:
                f.write(f"{_now_iso()},{cnt},{mb},{reason}\n")
            else:
                f.write(f"{_now_iso()},{cnt},{reason}\n")
        _thread_history_last_write = now
    except Exception as e:
        print(f"[thread-history-write-error] {e}")

# ====== 增強錯誤處理 (原有) ======
try:
    from utils.enhanced_logging_and_error_handler import setup_global_error_handler, configure, log_operation, log_memory_usage
    import config.settings as settings
    configure(settings)
    setup_global_error_handler()
    log_operation("程式啟動")
    log_memory_usage("啟動時")
except ImportError as e:
    print(f"注意: 無法導入增強日誌系統 ({e})")
except Exception as e:
    print(f"設置增強錯誤處理器時發生錯誤: {e}")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 其他模組
import config.settings as settings
from utils.console_logging import init_logging
from utils.memory import check_memory_limit
from utils.helpers import get_all_excel_files, timeout_handler
from utils.compression import CompressionFormat, test_compression_support
from ui.console import init_console
from core.baseline import create_baseline_for_files_robust
from core.watcher import active_polling_handler, ExcelFileEventHandler
from core.comparison import set_current_event_number
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

console = None

def _cleanup_console():
    global console
    try:
        if console:
            console.stop()
            console = None
    except Exception:
        pass

def _cleanup_tkinter_vars():
    try:
        import gc
        # 移除 gc.collect() 以避免在 XML 解析相關清理時觸發 0x80000003 崩潰
        # gc.collect()
    except Exception:
        pass

atexit.register(_cleanup_console)
atexit.register(_cleanup_tkinter_vars)

def signal_handler(signum, frame):
    """
    多次 Ctrl+C：
      - 單按：dump -> 生成新檔 -> 提示「再快按一次結束」
      - 快速連按（雙擊）或達到 max 計數（若啟用固定模式）：停止程式
    """
    global _sigint_last_time, _sigint_dump_count

    now = time.time()
    interval = now - _sigint_last_time
    _sigint_last_time = now

    # 判斷是否「結束條件」
    if ENABLE_MULTI_SIGINT_THREAD_DUMP:
        # 模式 1：雙擊 (interval <= EXIT_DOUBLE_PRESS_WINDOW)
        double_press_exit = (interval <= EXIT_DOUBLE_PRESS_WINDOW and _sigint_dump_count > 0)

        # 模式 2：固定次數
        fixed_exit = False
        if USE_FIXED_SIGINT_DUMP_COUNT_TO_EXIT and _sigint_dump_count >= MAX_SIGINT_DUMPS_BEFORE_EXIT:
            fixed_exit = True

        if double_press_exit or fixed_exit:
            # 進入停止流程
            if not settings.force_stop:
                settings.force_stop = True
                print("\n🛑 偵測到結束（雙擊 Ctrl+C 或達次數限制），正在安全停止...")
                active_polling_handler.stop()
                _cleanup_console()
                print("   (再按一次 Ctrl+C 強制立即退出)")
            else:
                print("\n💥 強制退出")
                _cleanup_console()
                sys.exit(1)
            return

        # 未達退出條件 → 生成 dump
        _sigint_dump_count += 1
        _ensure_dump_dir()
        dump_path = _create_timestamp_dump_file()
        reason = f"SIGINT-{_sigint_dump_count}"
        _dump_threads_full(dump_path, reason=reason)
        list_threads(to_file_path=dump_path)
        _record_thread_history(force=True, reason="sigint-dump")
        _rotate_old_dumps()

        if PRINT_DUMP_PATH_ON_CREATE:
            print(f"[dump] 已輸出 thread dump: {dump_path}")

        if SHOW_EXIT_HINT_AFTER_DUMP:
            if USE_FIXED_SIGINT_DUMP_COUNT_TO_EXIT:
                remain = max(0, MAX_SIGINT_DUMPS_BEFORE_EXIT - _sigint_dump_count + 1)
                if remain > 0:
                    print(f"[提示] 再按 {remain} 次 Ctrl+C 才會停止（或快速連按兩次立即停止）")
                else:
                    print("[提示] 下一次 Ctrl+C 將停止")
            else:
                print(f"[提示] 若要停止：請在 {EXIT_DOUBLE_PRESS_WINDOW:.1f}s 內再按一次 Ctrl+C；或繼續單按以生成更多 dump")
        return

    # 備援：若功能關閉則使用舊式單次中斷邏輯
    if not settings.force_stop:
        settings.force_stop = True
        print("\n🛑 收到中斷信號，正在安全停止...")
        active_polling_handler.stop()
        _cleanup_console()
        print("   (再按一次 Ctrl+C 強制退出)")
    else:
        print("\n💥 強制退出")
        _cleanup_console()
        sys.exit(1)

def main():
    global console

    init_logging()

    # 初始化 thread history 檔案
    if ENABLE_THREAD_COUNT_HISTORY and not os.path.exists(THREAD_COUNT_HISTORY_FILE):
        with open(THREAD_COUNT_HISTORY_FILE, "w", encoding="utf-8") as f:
            if THREAD_HISTORY_INCLUDE_MEMORY:
                f.write("timestamp,threads,memory_mb,reason\n")
            else:
                f.write("timestamp,threads,reason\n")
    _record_thread_history(force=True, reason="initial")

    try:
        py = sys.version.split()[0]
        exe = sys.executable
        ve = getattr(settings, 'VALUE_ENGINE', 'polars')
        csvp = getattr(settings, 'CSV_PERSIST', False)
        print(f"[env] python={py} | VALUE_ENGINE={ve} | CSV_PERSIST={csvp} | exe={exe}")
    except Exception:
        pass

    print("Excel Monitor (multi-dump edition) 啟動中...")
    test_compression_support()

    # UI 設定
    try:
        from ui.settings_ui import show_settings_ui
        show_settings_ui()
        from config.runtime import load_runtime_settings
        if (load_runtime_settings() or {}).get('STARTUP_CANCELLED'):
            print("使用者取消啟動，退出。")
            return
    except Exception as e:
        print(f"設定 UI 啟動失敗: {e}")

    console = init_console()

    # Timeline Server（如開啟）
    try:
        if getattr(settings, 'ENABLE_TIMELINE_SERVER', True):
            def _run_timeline_server():
                try:
                    import git_viewer
                    host = getattr(settings, 'TIMELINE_SERVER_HOST', '127.0.0.1')
                    port = int(getattr(settings, 'TIMELINE_SERVER_PORT', 5000))
                    print(f"[timeline] http://{host}:{port}/ui/timeline")
                    git_viewer.app.run(host=host, port=port, debug=False, use_reloader=False)
                except Exception as e2:
                    print(f"[timeline] 啟動失敗: {e2}")
            threading.Thread(target=_run_timeline_server, daemon=True).start()
    except Exception:
        pass

    signal.signal(signal.SIGINT, signal_handler)

    if getattr(settings, 'ENABLE_TIMEOUT', False):
        threading.Thread(target=timeout_handler, daemon=True).start()

    available_formats = CompressionFormat.get_available_formats()
    print(f"🗜️  壓縮支援: {', '.join(available_formats)}")
    validated = CompressionFormat.validate_format(settings.DEFAULT_COMPRESSION_FORMAT)
    if validated != settings.DEFAULT_COMPRESSION_FORMAT:
        print(f"⚠️ 調整壓縮格式 {settings.DEFAULT_COMPRESSION_FORMAT} -> {validated}")
        settings.DEFAULT_COMPRESSION_FORMAT = validated

    print(f"📁 監控資料夾: {settings.WATCH_FOLDERS}")
    if getattr(settings, 'MONITOR_ONLY_FOLDERS', None):
        print(f"🛈  只監控變更根: {settings.MONITOR_ONLY_FOLDERS}")
    print(f"📊 支援格式: {settings.SUPPORTED_EXTS}")

    # 手動基準線
    manual_files = []
    if settings.MANUAL_BASELINE_TARGET:
        print(f"📋 手動基準線目標: {len(settings.MANUAL_BASELINE_TARGET)}")
        for tpath in settings.MANUAL_BASELINE_TARGET:
            if os.path.exists(tpath):
                manual_files.append(tpath)
                print(f"   ✅ {os.path.basename(tpath)}")
            else:
                print(f"   ❌ {tpath} 不存在")

    # 掃描
    all_files = []
    if settings.SCAN_ALL_MODE:
        print("\n🔍 掃描中...")
        try:
            from config.runtime import load_runtime_settings
            rt_cfg = load_runtime_settings() or {}
        except Exception:
            rt_cfg = {}
        rt_list = [r for r in (rt_cfg.get('SCAN_TARGET_FOLDERS', []) or []) if r]
        st_list = [r for r in (getattr(settings, 'SCAN_TARGET_FOLDERS', []) or []) if r]
        if rt_list:
            roots = list(dict.fromkeys(rt_list)); src_reason = "runtime"
        elif st_list:
            roots = list(dict.fromkeys(st_list)); src_reason = "settings"
        else:
            roots = list(dict.fromkeys(list(settings.WATCH_FOLDERS or []))); src_reason = "WATCH_FOLDERS"
        all_files = get_all_excel_files(roots)
        print(f"找到 {len(all_files)} 個 Excel 檔案（來源: {src_reason} 根目錄: {roots}）")

    total_files = list(set(all_files + manual_files))
    if total_files:
        print(f"\n📊 建立基準線：{len(total_files)} 個檔案")
        create_baseline_for_files_robust(total_files)

    # 啟動 Watchdog
    print("\n👀 啟動檔案監控...")
    event_handler = ExcelFileEventHandler(active_polling_handler)

    # 啟動心跳與健康檢查（在 observer 啟動後）
    hb = None
    try:
        from utils.heartbeat import Heartbeat
        def _get_observer():
            return observer
        def _restart_observer():
            try:
                # 停止舊 observer
                try:
                    observer.stop()
                    observer.join(timeout=3)
                except Exception:
                    pass
                # 重新建立 observer（沿用目前選擇的 backend 與 watch_roots）
                try:
                    from watchdog.observers import Observer
                    from watchdog.observers.polling import PollingObserver
                    _obs = PollingObserver() if chosen_backend == 'polling' else Observer()
                except Exception:
                    from watchdog.observers.polling import PollingObserver
                    _obs = PollingObserver()
                # 重新註冊監控
                for folder in watch_roots:
                    if os.path.exists(folder):
                        try:
                            _obs.schedule(event_handler, folder, recursive=True)
                        except Exception:
                            pass
                _obs.start()
                print('[auto-restart] observer restarted')
                return True
            except Exception as e:
                print(f"[auto-restart] observer restart failed: {e}")
                return False
        def _get_watch_roots():
            return list(watch_roots or [])
        if getattr(settings, 'ENABLE_HEARTBEAT', True):
            hb = Heartbeat(_get_observer, _restart_observer, _get_watch_roots)
            hb.start()
    except Exception as e:
        print(f"[hb] 啟動失敗: {e}")
    watch_roots = list(dict.fromkeys(
        list(settings.WATCH_FOLDERS or []) +
        list(getattr(settings, 'MONITOR_ONLY_FOLDERS', []) or [])
    ))

    def _is_unc_or_drive_root(p: str) -> bool:
        try:
            if not p: return False
            q = os.path.abspath(p)
            if q.startswith('\\\\'): return True
            d, tail = os.path.splitdrive(q)
            return bool(d and (tail in ('\\','/')))
        except Exception:
            return False

    backend = getattr(settings, 'OBSERVER_BACKEND', 'auto')
    if os.environ.get('WATCHDOG_FORCE_POLLING'):
        backend = 'polling'

    chosen_backend = 'native'
    if backend.lower() == 'polling':
        chosen_backend = 'polling'
    elif backend.lower() == 'auto':
        if any(_is_unc_or_drive_root(r) for r in (watch_roots or [])):
            chosen_backend = 'polling'

    try:
        observer_ref = {'obj': (PollingObserver() if chosen_backend == 'polling' else Observer())}
        observer = observer_ref['obj']
        print(f"   使用後端: { 'PollingObserver' if chosen_backend=='polling' else 'Observer'}")
    except Exception as e:
        print(f"   後端建立失敗 {e} → 回退 PollingObserver")
        observer = PollingObserver()
        chosen_backend = 'polling'

    for root in watch_roots:
        if os.path.exists(root):
            try:
                observer.schedule(event_handler, root, recursive=True)
                print(f"   監控: {root}")
            except Exception as se:
                print(f"   ⚠️ 註冊失敗 {se} → 回退 PollingObserver")
                try: observer.stop()
                except Exception: pass
                observer = PollingObserver()
                observer.schedule(event_handler, root, recursive=True)
                chosen_backend = 'polling'
        else:
            print(f"   ⚠️ 不存在: {root}")

    observer.start()
    # 啟動後一次性打開 Timeline HTML（若存在）
    try:
        import webbrowser
        # Open original (index.html) AND Matrix v3 (index3.html) together.
        base_dir = getattr(settings, 'LOG_FOLDER', '.')
        timeline_dir = os.path.join(base_dir, 'timeline')
        timeline_html = os.path.join(timeline_dir, 'index.html')
        timeline_html_v2 = os.path.join(timeline_dir, 'index2.html')
        timeline_html_v3 = os.path.join(timeline_dir, 'index3.html')

        # Ensure index3 exists (try to generate it once at startup)
        try:
            if not os.path.exists(timeline_html_v3):
                # Attempt to generate index3 from events/index2
                from utils.timeline_exporter_index3 import generate_html as _gen_idx3
                _gen_idx3()  # this will mirror index2 -> index3 if possible
        except Exception:
            pass
        
        opened_files = []
        # Always open index3 if exists
        if os.path.exists(timeline_html_v3):
            webbrowser.open(timeline_html_v3)
            opened_files.append("Matrix v3")
        # Always open original if exists
        if os.path.exists(timeline_html):
            webbrowser.open(timeline_html)
            opened_files.append("原版")
        # 不再自動打開 index2，避免混淆（如需可手動開啟）
        
        if opened_files:
            print(f"[main] 已打開: {', '.join(opened_files)}")
        else:
            print("[main] 尚未有可開啟的 timeline HTML，待有事件後會自動產生。")
    except Exception:
        pass

    print("\n✅ Excel Monitor 已啟動")
    print(f"   - 後端: {chosen_backend}")
    print(f"   - 公式模式: {'開啟' if settings.FORMULA_ONLY_MODE else '關閉'}")
    print(f"   - 白名單: {'開啟' if settings.WHITELIST_USERS else '關閉'}")
    print(f"   - 本地緩存: {'開啟' if settings.USE_LOCAL_CACHE else '關閉'}")
    print(f"   - 記憶體監控: {'開啟' if settings.ENABLE_MEMORY_MONITOR else '關閉'}")
    print(f"   - 歸檔模式: {'開啟' if settings.ENABLE_ARCHIVE_MODE else '關閉'}")
    print(f"   - Dump 雙擊 Ctrl+C 停止（窗口 {EXIT_DOUBLE_PRESS_WINDOW}s）")
    if USE_FIXED_SIGINT_DUMP_COUNT_TO_EXIT:
        print(f"   - 或達 {MAX_SIGINT_DUMPS_BEFORE_EXIT} 次 Ctrl+C 後停止")
    print("\n按 Ctrl+C 產生 thread dump；快速連按兩次停止。")

    last_hb = 0.0
    prev_thread_count = len(threading.enumerate())
    interval_anchor = time.time()

    try:
        while not settings.force_stop:
            now = time.time()

            # Heartbeat
            if ENABLE_HEARTBEAT and (now - last_hb >= HEARTBEAT_INTERVAL):
                try:
                    cur_threads = len(threading.enumerate())
                    if HEARTBEAT_SHOW_THREAD_COUNT:
                        print(f"[heartbeat] alive {time.strftime('%H:%M:%S')} threads={cur_threads}")
                    else:
                        print(f"[heartbeat] alive {time.strftime('%H:%M:%S')}")
                    if HEARTBEAT_DUMP_ON_THREAD_CHANGE and cur_threads != prev_thread_count:
                        list_threads()
                    last_hb = now
                except Exception:
                    pass

            # Thread 數紀錄
            cur_threads = len(threading.enumerate())
            changed = (cur_threads != prev_thread_count)
            if ENABLE_THREAD_COUNT_HISTORY:
                if THREAD_COUNT_HISTORY_ON_CHANGE and changed:
                    _record_thread_history(force=True, reason="change")
                if (now - interval_anchor) >= THREAD_COUNT_HISTORY_INTERVAL_SEC:
                    _record_thread_history(force=True, reason="interval")
                    interval_anchor = now
            if changed:
                prev_thread_count = cur_threads

            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🔄 正在停止...")
        observer.stop()
        observer.join()
        active_polling_handler.stop()
        try:
            from utils.task_queue import get_compare_queue
            q = get_compare_queue(lambda p, evt: False)
            q.stop()
        except Exception:
            pass
        _cleanup_console()
        print("✅ 監控已停止")

if __name__ == "__main__":
    log_directory = r"C:\temp\python_logs"
    os.makedirs(log_directory, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    error_log = os.path.join(log_directory, f"python_crash_{ts}.log")

    try:
        with open(error_log, 'w', encoding='utf-8') as log_file:
            log_file.write(f"程式啟動: {datetime.datetime.now()}\n")
            log_file.write(f"Python版本: {sys.version}\n")
            log_file.write(f"執行環境: {'Jupyter' if 'ipykernel' in sys.modules else 'Standard Python'}\n")
            log_file.write("=" * 50 + "\n\n")
            log_file.flush()
            faulthandler.enable(file=log_file, all_threads=True)
            print("faulthandler 已啟用")
            print(f"錯誤記錄檔案: {error_log}")
            main()
    except Exception as e:
        print(f"程式錯誤: {type(e).__name__}: {e}")
        traceback.print_exc()
        with open(error_log, 'a', encoding='utf-8') as f:
            f.write(f"\nPython 例外錯誤:\n時間: {datetime.datetime.now()}\n錯誤: {type(e).__name__}: {e}\n")
            traceback.print_exc(file=f)
        sys.exit(1)