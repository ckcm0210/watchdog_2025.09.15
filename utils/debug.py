import os
from typing import Any, Dict, List, Optional, Union, Tuple
import re
import shlex
import config.settings as settings

try:
    from utils.console_logging import wrap_text_with_cjk_support
except Exception:
    def wrap_text_with_cjk_support(text: str, width: int) -> List[str]:
        # 後備：簡單切段
        s = str(text)
        return [s[i:i+max(10, width)] for i in range(0, len(s), max(10, width))]

def _zero_pad_evt(evt: Optional[int]) -> str:
    try:
        if evt is None:
            return ''
        return f"[evt#{int(evt):04d}]"
    except Exception:
        return ''

def _bk_from_path(file_path: Optional[str]) -> str:
    if not file_path:
        return ''
    try:
        from utils.helpers import _baseline_key_for_path
        bk = _baseline_key_for_path(file_path)
        return f"[bk:{bk}]"
    except Exception:
        try:
            base = os.path.basename(file_path)
            return f"[bk:{base}]"
        except Exception:
            return ''

DefText = Union[str, List[str], Dict[str, Any]]

def debug_print(prefix: str,
                text: DefText,
                *,
                level_required: int = 1,
                event_number: Optional[int] = None,
                file_path: Optional[str] = None,
                repeat_prefix: Optional[bool] = None,
                max_items: Optional[int] = None,
                chunk: int = 10,
                key_align: int = 14,
                label: Optional[str] = None) -> None:
    """
    標準化的 Debug 輸出：
    - 依 DEBUG_LEVEL 與 SHOW_DEBUG_MESSAGES 控制輸出
    - 每行自動換行（CJK 寬度），每行可重覆 prefix
    - 支援 list/dict 格式化
    """
    try:
        if not getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            return
        cur_level = int(getattr(settings, 'DEBUG_LEVEL', 1) or 0)
        if cur_level < int(level_required):
            return

        # 參數預設
        if repeat_prefix is None:
            repeat_prefix = bool(getattr(settings, 'DEBUG_REPEAT_PREFIX_ON_WRAP', True))
        if max_items is None:
            max_items = int(getattr(settings, 'DEBUG_MAX_LIST_ITEMS', 20) or 20)
        width = int(getattr(settings, 'DEBUG_WRAP_WIDTH', 0) or 0)
        if width <= 0:
            width = int(getattr(settings, 'CONSOLE_TERM_WIDTH_OVERRIDE', 0) or 120)
        tag_evt = bool(getattr(settings, 'DEBUG_TAG_EVENT_ID', True))

        # 組合前綴（事件/基鍵）
        evt_tag = _zero_pad_evt(event_number) if tag_evt else ''
        bk_tag = '' if event_number is not None else _bk_from_path(file_path)
        base_prefix = f"{evt_tag}{bk_tag}[{prefix}]" if (evt_tag or bk_tag) else f"[{prefix}]"

        def _emit_line(s: str, is_first: bool = False):
            lines = wrap_text_with_cjk_support(s, width)
            for i, ln in enumerate(lines):
                if repeat_prefix or i == 0:
                    print(f"{base_prefix} {ln}")
                else:
                    print(f"  {ln}")

        # 字串
        if isinstance(text, str):
            _emit_line(text, True)
            return

        # list：分 chunk + 截斷
        if isinstance(text, list):
            total = len(text)
            if total == 0:
                print(f"{base_prefix} (no items)")
                return
            show_n = min(total, max_items if cur_level <= 2 else total)
            pages = (show_n + chunk - 1) // chunk
            _label = label or 'items'
            for p in range(pages):
                start = p * chunk
                end = min(start + chunk, show_n)
                seg = text[start:end]
                _emit_line(f"{_label}({p+1}/{pages}): {', '.join(str(x) for x in seg)}", p == 0)
            if show_n < total:
                print(f"{base_prefix} ... (+{total - show_n} more)")
            return

        # dict：每行 key=value
        if isinstance(text, dict):
            first = True
            for k in sorted(text.keys()):
                v = text.get(k)
                _emit_line(f"{str(k):<{key_align}} = {v}", first)
                first = False
            return

        # 其它：轉字串
        _emit_line(str(text), True)
    except Exception:
        # Debug 輸出不應影響主流程
        pass


def debug_print_cmd(prefix: str,
                    cmd: Union[str, List[str]],
                    *,
                    level_required: int = 2,
                    event_number: Optional[int] = None,
                    file_path: Optional[str] = None) -> None:
    """
    專用：命令列語義分行顯示（避免在路徑中間截斷）
    - 目前優先處理 powershell 命令（-NoProfile / -Command / Copy-Item / -LiteralPath / -Destination / -Force）
    - 其他命令以較簡單的規則分行（第一行程式 + 參數摘要，第二行其餘）
    """
    try:
        if not getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
            return
        cur_level = int(getattr(settings, 'DEBUG_LEVEL', 1) or 0)
        if cur_level < int(level_required):
            return
        # 取 wrap 與 prefix 組合
        width = int(getattr(settings, 'DEBUG_WRAP_WIDTH', 0) or getattr(settings, 'CONSOLE_TERM_WIDTH_OVERRIDE', 120) or 120)
        tag_evt = bool(getattr(settings, 'DEBUG_TAG_EVENT_ID', True))
        evt_tag = _zero_pad_evt(event_number) if tag_evt else ''
        bk_tag = '' if event_number is not None else _bk_from_path(file_path)
        base_prefix = f"{evt_tag}{bk_tag}[{prefix}]" if (evt_tag or bk_tag) else f"[{prefix}]"

        def _println(line: str):
            for ln in wrap_text_with_cjk_support(line, width):
                print(f"{base_prefix} {ln}")

        # 正規化 tokens
        tokens: List[str]
        if isinstance(cmd, str):
            try:
                tokens = shlex.split(cmd, posix=False)
            except Exception:
                tokens = cmd.split()
        else:
            tokens = list(cmd)

        if not tokens:
            return

        prog = tokens[0]
        # Powershell 專用邏輯
        if prog.lower() in ('powershell', 'pwsh'):
            # 例：['powershell','-NoProfile','-Command',"Copy-Item -LiteralPath 'X' -Destination 'Y' -Force"]
            header_flags: List[str] = []
            ps_inner: str = ''
            i = 1
            while i < len(tokens):
                t = tokens[i]
                if t.lower() in ('-noprofile',):
                    header_flags.append(t)
                elif t.lower() in ('-command', '-c'):
                    # 取下一個作為完整內部命令字串
                    if i + 1 < len(tokens):
                        ps_inner = tokens[i+1]
                        i += 1
                else:
                    header_flags.append(t)
                i += 1
            inner_tokens = []
            if ps_inner:
                try:
                    inner_tokens = shlex.split(ps_inner, posix=False)
                except Exception:
                    inner_tokens = ps_inner.split()
            # 組第一行：exec: powershell <flags> <verb>
            verb = inner_tokens[0] if inner_tokens else ''
            header = f"exec: {prog} {' '.join(header_flags)} {verb}".rstrip()
            _println(header)
            # 按參數邊界逐行輸出（-LiteralPath / -Destination / 其他）
            params: List[Tuple[str, Optional[str]]] = []
            j = 1
            while j < len(inner_tokens):
                p = inner_tokens[j]
                if p.startswith('-'):
                    val = None
                    if j + 1 < len(inner_tokens) and not inner_tokens[j+1].startswith('-'):
                        val = inner_tokens[j+1]
                        j += 1
                    params.append((p, val))
                else:
                    # 無前綴的裸值（較少見），獨立一行
                    params.append((p, None))
                j += 1
            for name, val in params:
                if val is None:
                    _println(f"{name}")
                else:
                    _println(f"{name} {val}")
            return

        # 其它命令：簡單分行（第一行程式+前幾個旗標，第二行其餘）
        head = [tokens[0]]
        tail = tokens[1:]
        headline = f"exec: {' '.join(head)}"
        _println(headline)
        if tail:
            _println(' '.join(tail))
    except Exception:
        pass
