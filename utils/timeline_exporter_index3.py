import os
from datetime import datetime
import config.settings as settings

# Reuse the clean Matrix exporter to guarantee identical JS behavior
from .timeline_exporter_matrix_clean import export_event as _export_event_clean, generate_html as _generate_html_clean

TIMELINE_DIR = None
INDEX2_HTML = None
INDEX3_HTML = None

def _init_paths():
    global TIMELINE_DIR, INDEX2_HTML, INDEX3_HTML
    if TIMELINE_DIR is None:
        TIMELINE_DIR = os.path.join(getattr(settings, 'LOG_FOLDER', '.'), 'timeline')
    if INDEX2_HTML is None:
        INDEX2_HTML = os.path.join(TIMELINE_DIR, 'index2.html')
    if INDEX3_HTML is None:
        INDEX3_HTML = os.path.join(TIMELINE_DIR, 'index3.html')
    os.makedirs(TIMELINE_DIR, exist_ok=True)


def _write_index3_from_index2():
    _init_paths()
    if not os.path.exists(INDEX2_HTML):
        return False
    try:
        with open(INDEX2_HTML, 'r', encoding='utf-8') as f:
            html = f.read()
        # Make index3 distinguishable (optional visual tweak)
        html = html.replace('<title>Excel Timeline - Matrix風格</title>',
                            '<title>Excel Timeline</title>')
        html = html.replace('>Excel Timeline - Matrix風格<', '>Excel Timeline<')
        html = html.replace('>Excel Timeline - Matrix v4<', '>Excel Timeline<')
        with open(INDEX3_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        # drop a workspace copy for debugging
        try:
            with open('tmp_rovodev_index3_debug.html', 'w', encoding='utf-8') as dbg:
                dbg.write(html)
        except Exception:
            pass
        return True
    except Exception:
        return False


def export_event(event: dict):
    """
    Append event via clean Matrix exporter (generates index2.html),
    then copy to index3.html (with minor title tweak) to guarantee identical JS behavior.
    Also export to Index4 if enabled and author matches target list.
    """
    try:
        # Reuse the proven clean exporter to update events.json and index2.html
        _export_event_clean(event or {})
        
        # Export to Index4 if enabled and author matches
        try:
            from .timeline_exporter_index4 import export_event as export_index4_event
            export_index4_event(event or {})
        except Exception as e:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"[timeline-matrix-v3] Index4 匯出失敗: {e}")
        
        # Now mirror to index3.html
        ok = _write_index3_from_index2()
        if ok:
            print(f"[timeline-matrix-v3] HTML 成功寫入: {INDEX3_HTML}")
        else:
            print(f"[timeline-matrix-v3] 警告: 未能從 index2.html 生成 index3.html")
    except Exception as e:
        try:
            print(f"[timeline-matrix-v3] 產生 index3 失敗: {e}")
        except Exception:
            pass


def generate_html(events=None):
    """Generate index2 via clean exporter, then mirror to index3."""
    try:
        _generate_html_clean(events)
        _write_index3_from_index2()
    except Exception:
        pass
