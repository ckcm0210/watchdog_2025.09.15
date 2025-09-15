import os
import time
import hashlib
import shutil
import logging
import re
import io
import csv
from datetime import datetime
import config.settings as settings

_MAX_WIN_FILENAME = 240  # conservative cap to avoid MAX_PATH issues
_HASH_LEN = 16
_PREFIX_SEP = '_'

def _is_in_cache(path: str) -> bool:
    try:
        cache_root = os.path.abspath(settings.CACHE_FOLDER)
        p = os.path.abspath(path)
        return os.path.commonpath([p, cache_root]) == cache_root
    except Exception:
        return False

_def_invalid = re.compile(r'[\\/:*?"<>|]')

def _safe_cache_basename(src_path: str) -> str:
    """Build a safe cache file name: <md5[:16]>_<sanitized-and-trimmed-basename>"""
    base = os.path.basename(src_path)
    base = _def_invalid.sub('_', base)
    name, ext = os.path.splitext(base)
    prefix = hashlib.md5(src_path.encode('utf-8')).hexdigest()[:_HASH_LEN] + _PREFIX_SEP
    # compute allowed length for name part
    allowed = _MAX_WIN_FILENAME - len(prefix) - len(ext)
    if allowed < 8:
        allowed = 8
    if len(name) > allowed:
        name = name[:allowed]
    return f"{prefix}{name}{ext}"

def _chunked_copy(src: str, dst: str, chunk_mb: int = 4):
    """Optional chunked copy to avoid long single-handle operations (best-effort)."""
    chunk_size = max(1, int(chunk_mb)) * 1024 * 1024
    with open(src, 'rb', buffering=1024 * 1024) as fsrc, open(dst, 'wb', buffering=1024 * 1024) as fdst:
        while True:
            # 支援停止時中斷
            try:
                if getattr(settings, 'force_stop', False):
                    raise OSError('Operation cancelled: stopping')
            except Exception:
                pass
            buf = fsrc.read(chunk_size)
            if not buf:
                break
            fdst.write(buf)
    try:
        shutil.copystat(src, dst)
    except Exception:
        pass


def _ops_log_copy_failure(network_path: str, error: Exception, attempts: int, strict_mode: bool):
    try:
        base_dir = os.path.join(settings.LOG_FOLDER, 'ops_log')
        os.makedirs(base_dir, exist_ok=True)
        fname = f"copy_failures_{datetime.now():%Y%m%d}.csv"
        fpath = os.path.join(base_dir, fname)
        new_file = not os.path.exists(fpath)
        with open(fpath, 'a', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(['Timestamp','Path','Error','Attempts','STRICT_NO_ORIGINAL_READ','COPY_CHUNK_SIZE_MB','BACKOFF_SEC'])
            w.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                network_path,
                str(error),
                attempts,
                bool(getattr(settings, 'STRICT_NO_ORIGINAL_READ', False)),
                int(getattr(settings, 'COPY_CHUNK_SIZE_MB', 0)),
                float(getattr(settings, 'COPY_RETRY_BACKOFF_SEC', 0.0)),
            ])
    except Exception:
        pass

def _ops_log_copy_success(network_path: str, duration: float, attempts: int, engine: str, chunk_mb: int):
    try:
        base_dir = os.path.join(settings.LOG_FOLDER, 'ops_log')
        os.makedirs(base_dir, exist_ok=True)
        fname = f"copy_success_{datetime.now():%Y%m%d}.csv"
        fpath = os.path.join(base_dir, fname)
        new_file = not os.path.exists(fpath)
        with open(fpath, 'a', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(['Timestamp','Path','SizeMB','DurationSec','Attempts','Engine','ChunkMB','StabilityChecks','StabilityInterval','StabilityMaxWait','STRICT_NO_ORIGINAL_READ'])
            size_mb = os.path.getsize(network_path)/(1024*1024) if os.path.exists(network_path) else ''
            w.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                network_path,
                f"{(size_mb or 0):.2f}" if size_mb != '' else '',
                f"{duration:.2f}",
                attempts,
                engine,
                int(chunk_mb),
                int(getattr(settings, 'COPY_STABILITY_CHECKS', 0)),
                float(getattr(settings, 'COPY_STABILITY_INTERVAL_SEC', 0.0)),
                float(getattr(settings, 'COPY_STABILITY_MAX_WAIT_SEC', 0.0)),
                bool(getattr(settings, 'STRICT_NO_ORIGINAL_READ', False)),
            ])
    except Exception:
        pass


def _wait_for_stable_mtime(path: str, checks: int, interval: float, max_wait: float) -> bool:
    try:
        if checks <= 1:
            return True
        last = None
        same = 0
        start = time.time()
        while True:
            # 允許在停止時立即退出等待
            try:
                if getattr(settings, 'force_stop', False):
                    return False
            except Exception:
                pass
            try:
                cur = os.path.getmtime(path)
            except Exception:
                return False
            if last is None:
                last = cur
                same = 1
            else:
                if cur == last:
                    same += 1
                else:
                    same = 1
                    last = cur
            if same >= checks:
                return True
            if max_wait is not None and (time.time() - start) >= max_wait:
                return False
            time.sleep(max(0.0, interval))
    except Exception:
        return False


def _run_subprocess_copy(src: str, dst: str, engine: str = 'robocopy'):
    """Run copy via subprocess engines (robocopy or powershell). dst is full file path.
    Returns the return code. Raises OSError on hard failures or post-copy validation failure.
    """
    import subprocess, shutil as _shutil
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    def _debug(msg: str, *, event_number: int | None = None, file_path: str | None = None, level_required: int = 1):
        try:
            from utils.debug import debug_print
            debug_print('copy', msg, level_required=level_required, event_number=event_number, file_path=file_path)
        except Exception:
            try:
                if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                    print(f"[copy] {msg}")
            except Exception:
                pass

    # 若正在停止，直接放棄
    try:
        if getattr(settings, 'force_stop', False):
            raise OSError('Operation cancelled: stopping')
    except Exception:
        pass

    if engine == 'robocopy':
        # ensure robocopy available
        try:
            if _shutil.which('robocopy') is None:
                raise FileNotFoundError('robocopy 不在 PATH（或系統缺失）')
        except Exception:
            # 如果 which 失敗，仍嘗試呼叫，讓系統自行決定
            pass
        # robocopy 需要目標目錄 + 檔名分開處理；實際上 robocopy 不能改名，只能複製為原檔名。
        # 因此：先複製到 dst_dir\src_name，再驗證，最後用 os.replace 重新命名為呼叫方期望的 dst（帶雜湊前綴）。
        src_dir = os.path.dirname(src)
        src_name = os.path.basename(src)
        dst_dir = os.path.dirname(dst)
        temp_dst = os.path.join(dst_dir, src_name)
        # /COPY:DAT 保留日期/屬性/時間；/NJH /NJS /NFL /NDL /NP 降噪；/R:2 /W:1 重試策略；/J 非緩衝 I/O（大檔更穩定）
        cmd = [
            'robocopy', src_dir, dst_dir, src_name,
            '/COPY:DAT', '/R:2', '/W:1', '/NJH', '/NJS', '/NFL', '/NDL', '/NP', '/J'
        ]
        # 可選 /Z
        try:
            if getattr(settings, 'ROBOCOPY_ENABLE_Z', False):
                cmd.append('/Z')
        except Exception:
            pass
        _debug(f"exec: {' '.join(cmd)}")
        # 捕捉 stdout/stderr 以利 debug
        proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        rc = proc.returncode
        if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            try:
                print(f"      [robocopy] rc={rc}\n      stdout=\n{(proc.stdout or '')[:2000]}\n      stderr=\n{(proc.stderr or '')[:2000]}")
            except Exception:
                pass
        _debug(f"robocopy rc={rc}")
        if rc > 7:
            raise OSError(f"robocopy rc={rc}")
        # Validate with short retry: ensure temp_dst exists and size >= src (allow SMB lag)
        try:
            s_sz = os.path.getsize(src)
            start = time.time()
            last_d_sz = -1
            while True:
                if not os.path.exists(temp_dst):
                    # create small sleep to wait for FS sync
                    time.sleep(0.05)
                else:
                    d_sz = os.path.getsize(temp_dst)
                    last_d_sz = d_sz
                    if d_sz >= s_sz:
                        break
                if time.time() - start > 3.0:
                    break
                time.sleep(0.1)
            if not os.path.exists(temp_dst):
                raise OSError('robocopy 回傳成功但目的檔不存在')
            if last_d_sz < s_sz:
                raise OSError(f'robocopy 回傳成功但目的檔大小異常 dst<{s_sz}>{last_d_sz}')
            # mtime check with tolerance (FAT/SMB granularity)
            try:
                s_mt = os.path.getmtime(src)
                d_mt = os.path.getmtime(temp_dst)
                if (s_mt - d_mt) > 2.2:  # allow ~2s tolerance
                    _debug(f"dst mtime older than src beyond tolerance: src={s_mt}, dst={d_mt}")
            except Exception:
                pass
            # Rename temp_dst -> dst if names differ (atomic replace)
            try:
                if os.path.normcase(temp_dst) != os.path.normcase(dst):
                    # 確保目標不存在或允許覆蓋
                    try:
                        if os.path.exists(dst):
                            os.remove(dst)
                    except Exception:
                        pass
                    os.replace(temp_dst, dst)
            except Exception as rn_err:
                # 若改名失敗，至少讓呼叫方能用 temp_dst；但為一致性回報錯誤（由上層重試）
                raise OSError(f'robocopy 複製成功但重新命名失敗: {rn_err}')
        except Exception as ve:
            raise OSError(str(ve))
        return rc
    elif engine == 'powershell':
        # ensure powershell available
        try:
            if _shutil.which('powershell') is None:
                raise FileNotFoundError('powershell 不在 PATH')
        except Exception:
            pass
        # 使用 PowerShell Copy-Item
        ps_cmd = f"Copy-Item -LiteralPath '{src}' -Destination '{dst}' -Force"
        cmd = ['powershell', '-NoProfile', '-Command', ps_cmd]
        try:
            from utils.debug import debug_print_cmd
            debug_print_cmd('copy', cmd, file_path=src)
        except Exception:
            _debug(f"exec: {' '.join(cmd)}")
        rc = subprocess.call(cmd, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        _debug(f"powershell rc={rc}")
        if rc != 0:
            raise OSError(f"powershell Copy-Item rc={rc}")
        # Validate
        try:
            if not os.path.exists(dst):
                raise OSError('PowerShell 回傳成功但目的檔不存在')
        except Exception as ve:
            raise OSError(str(ve))
        # Debug: post-copy validation info
        try:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                try:
                    s_sz = os.path.getsize(src)
                except Exception:
                    s_sz = ''
                try:
                    d_sz = os.path.getsize(dst)
                except Exception:
                    d_sz = ''
                try:
                    d_mt = os.path.getmtime(dst)
                except Exception:
                    d_mt = ''
                print(f"      [copy-ok] engine=powershell dst={dst} dst_size={d_sz} src_size={s_sz} dst_mtime={d_mt}")
        except Exception:
            pass
        return rc
    else:
        raise ValueError(f"Unknown subprocess copy engine: {engine}")


def copy_to_cache(network_path, silent=False):
    # 嚴格模式下，如果不使用本地快取，直接返回 None（不讀原檔）
    if not settings.USE_LOCAL_CACHE:
        if getattr(settings, 'STRICT_NO_ORIGINAL_READ', False):
            if not silent:
                print("   ⚠️ 嚴格模式啟用且未啟用本地快取：跳過讀取原檔。")
            return None
        return network_path

    try:
        os.makedirs(settings.CACHE_FOLDER, exist_ok=True)

        # If the source already under cache root, return as-is to avoid prefix duplication
        if _is_in_cache(network_path):
            return network_path

        if not os.path.exists(network_path):
            raise FileNotFoundError(f"網絡檔案不存在: {network_path}")
        if not os.access(network_path, os.R_OK):
            raise PermissionError(f"無法讀取網絡檔案: {network_path}")

        cache_file = os.path.join(settings.CACHE_FOLDER, _safe_cache_basename(network_path))

        # 若快取已新於來源，直接用快取檔
        if os.path.exists(cache_file):
            try:
                if os.path.getmtime(cache_file) >= os.path.getmtime(network_path):
                    return cache_file
            except OSError as e:
                logging.warning(f"獲取緩存檔案時間失敗: {e}")

        network_size = None
        try:
            network_size = os.path.getsize(network_path)
        except Exception:
            pass
        if not silent:
            sz = f" ({network_size/(1024*1024):.1f} MB)" if network_size else ""
            print(f"   📥 複製到緩存: {os.path.basename(network_path)}{sz}")

        retry = max(1, int(getattr(settings, 'COPY_RETRY_COUNT', 3)))
        backoff = max(0.0, float(getattr(settings, 'COPY_RETRY_BACKOFF_SEC', 0.5)))
        chunk_mb = max(0, int(getattr(settings, 'COPY_CHUNK_SIZE_MB', 0)))

        last_err = None
        for attempt in range(1, retry + 1):
            # 若正在停止，立即中止循環
            try:
                if getattr(settings, 'force_stop', False):
                    last_err = OSError('Operation cancelled: stopping')
                    break
            except Exception:
                pass
            # 複製前穩定性預檢
            st_checks = max(1, int(getattr(settings, 'COPY_STABILITY_CHECKS', 2)))
            st_interval = max(0.0, float(getattr(settings, 'COPY_STABILITY_INTERVAL_SEC', 1.0)))
            st_maxwait = float(getattr(settings, 'COPY_STABILITY_MAX_WAIT_SEC', 3.0))
            if st_checks > 1:
                stable_ok = _wait_for_stable_mtime(network_path, st_checks, st_interval, st_maxwait)
                if not stable_ok:
                    if not silent:
                        print(f"      ⏳ 源檔案仍在變動，延後複製（第 {attempt}/{retry} 次）")
                    time.sleep(backoff * attempt)
                    continue

            copy_start = time.time()
            try:
                # 子程序複製策略：.xlsm 或設定指定時優先
                use_sub = False
                sub_engine = getattr(settings, 'COPY_ENGINE', 'python')
                prefer_xlsm = bool(getattr(settings, 'PREFER_SUBPROCESS_FOR_XLSM', False))
                if sub_engine in ('robocopy', 'powershell'):
                    use_sub = True
                elif prefer_xlsm and str(network_path).lower().endswith('.xlsm'):
                    sub_engine = getattr(settings, 'SUBPROCESS_ENGINE_FOR_XLSM', 'robocopy')
                    use_sub = True

                used_engine = 'python'
                if use_sub:
                    _run_subprocess_copy(network_path, cache_file, engine=sub_engine)
                    used_engine = sub_engine
                else:
                    if chunk_mb > 0:
                        _chunked_copy(network_path, cache_file, chunk_mb=chunk_mb)
                    else:
                        shutil.copy2(network_path, cache_file)
                # 短暫等待，給檔案系統穩定
                time.sleep(getattr(settings, 'COPY_POST_SLEEP_SEC', 0.2))
                duration = time.time() - copy_start
                if not silent:
                    print(f"      複製完成，耗時 {duration:.1f} 秒（第 {attempt}/{retry} 次嘗試）")
                try:
                    _ops_log_copy_success(network_path, duration, attempt, engine=used_engine, chunk_mb=chunk_mb)
                except Exception:
                    pass
                return cache_file
            except (PermissionError, OSError) as e:
                last_err = e
                if not silent:
                    print(f"      ↻ 第 {attempt}/{retry} 次複製失敗：{e}")
                if attempt < retry:
                    time.sleep(backoff * attempt)
                else:
                    break

        # 若最終複製失敗
        if getattr(settings, 'STRICT_NO_ORIGINAL_READ', False):
            logging.error(f"嚴格模式：無法複製到緩存，跳過原檔讀取：{last_err}")
            try:
                _ops_log_copy_failure(network_path, last_err, attempt, True)
            except Exception:
                pass
            if not silent:
                print("   ❌ 複製到快取失敗（嚴格模式：不讀原檔），略過。")
            return None
        else:
            logging.error(f"緩存失敗 - 將回退為直接使用原檔（非嚴格模式）：{last_err}")
            try:
                _ops_log_copy_failure(network_path, last_err, attempt, False)
            except Exception:
                pass
            if not silent:
                print("   ⚠️ 緩存失敗：回退為直接讀原檔（非嚴格模式）")
            return network_path

    except FileNotFoundError as e:
        logging.error(f"緩存失敗 - 檔案未找到: {e}")
        if not silent:
            print(f"   ❌ 緩存失敗: {e}")
        return None if getattr(settings, 'STRICT_NO_ORIGINAL_READ', False) else network_path
    except PermissionError as e:
        logging.error(f"緩存失敗 - 權限不足: {e}")
        if not silent:
            print(f"   ❌ 緩存失敗: {e}")
        return None if getattr(settings, 'STRICT_NO_ORIGINAL_READ', False) else network_path
    except OSError as e:
        logging.error(f"緩存失敗 - 複製緩存檔案時發生 I/O 錯誤: {e}")
        if not silent:
            print(f"   ❌ 緩存失敗: {e}")
        return None if getattr(settings, 'STRICT_NO_ORIGINAL_READ', False) else network_path