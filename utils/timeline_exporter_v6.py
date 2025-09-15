import os
import json
from datetime import datetime
import config.settings as settings

TIMELINE_DIR = None
TIMELINE_JSON = None
TIMELINE_HTML_V6 = None

def _init_paths():
    global TIMELINE_DIR, TIMELINE_JSON, TIMELINE_HTML_V6
    if TIMELINE_DIR is None:
        TIMELINE_DIR = os.path.join(getattr(settings, 'LOG_FOLDER', '.'), 'timeline')
    if TIMELINE_JSON is None:
        TIMELINE_JSON = os.path.join(TIMELINE_DIR, 'events.json')
    if TIMELINE_HTML_V6 is None:
        TIMELINE_HTML_V6 = os.path.join(TIMELINE_DIR, 'index2.html')

def _load_events():
    """Load events from JSON file."""
    try:
        _init_paths()
        if os.path.exists(TIMELINE_JSON):
            with open(TIMELINE_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []

def export_event(event_dict):
    """
    Append a timeline event to events.json and regenerate index2.html with V6 Matrix style.
    """
    try:
        _init_paths()
        # Load existing events
        events = _load_events()
        # Add new event
        events.append(event_dict)
        # Save to JSON
        os.makedirs(TIMELINE_DIR, exist_ok=True)
        with open(TIMELINE_JSON, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        # Generate V6 HTML
        generate_html_v6(events)
        # 輸出 debug 訊息
        try:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                try:
                    from utils.debug import debug_print
                    debug_print('timeline-html-v6', {
                        'dir': TIMELINE_DIR,
                        'json': TIMELINE_JSON, 
                        'html': TIMELINE_HTML_V6,
                        'events': len(events),
                        'last_file': event_dict.get('file','')
                    })
                except Exception:
                    print(f"[timeline-html-v6] dir={TIMELINE_DIR} json={TIMELINE_JSON} html={TIMELINE_HTML_V6} events={len(events)} last_file={event_dict.get('file','')}")
        except Exception:
            pass
    except Exception:
        # timeline failure should not affect main flow
        pass


def generate_html_v6(events=None):
    """Write a static HTML (self-contained) with V6 Matrix styling."""
    try:
        _init_paths()
        if events is None:
            events = _load_events()
        # Latest first
        try:
            events = sorted(events, key=lambda e: e.get('timestamp', ''), reverse=True)
        except Exception:
            pass
        
        # V6 Matrix HTML with complete styling
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="zh-Hant">')
        html.append('<head>')
        html.append('<meta charset="utf-8"/>')
        html.append('<title>Excel Timeline - Matrix風格完整功能版 v6</title>')
        html.append('<style>')
        
        # V6 Matrix 樣式
        html.append('''
        /* 基本樣式 */
        body {
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            margin: 0;
            padding: 15px;
            background: #000;
            color: #00ff41;
            text-shadow: 0 0 5px #00ff41;
            transition: all 0.3s ease;
        }

        .container {
            width: 100%;
            background: #000;
            border: 1px solid #00ff41;
            border-radius: 4px;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
            overflow: hidden;
        }

        .header {
            background: #000;
            color: #00ff41;
            padding: 20px;
            text-align: center;
            position: relative;
            border-bottom: 1px solid #00ff41;
        }

        .header h1 {
            margin: 0;
            font-size: 24px;
            text-shadow: 0 0 10px #00ff41;
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { text-shadow: 0 0 10px #00ff41; }
            to { text-shadow: 0 0 20px #00ff41, 0 0 30px #00ff41; }
        }

        .theme-selector {
            position: absolute;
            top: 15px;
            right: 20px;
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        .theme-label {
            color: #00ff41;
            font-size: 12px;
            margin: 0 5px;
            opacity: 0.8;
        }

        .theme-btn {
            width: 25px;
            height: 25px;
            border-radius: 50%;
            border: 2px solid #00ff41;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .theme-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 0 10px #00ff41;
        }

        .theme-btn.matrix { background: #000; border-color: #00ff41; box-shadow: 0 0 5px #00ff41; }

        /* 控制區域 - Matrix風格 */
        .controls {
            padding: 20px;
            background: #000;
            border-bottom: 1px solid #00ff41;
        }

        .search-box {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .search-input {
            flex: 1;
            min-width: 300px;
            padding: 10px 14px;
            border: 1px solid #00ff41;
            border-radius: 4px;
            font-size: 14px;
            background: #000;
            color: #00ff41;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            text-shadow: 0 0 5px #00ff41;
        }

        .search-input:focus {
            outline: none;
            box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }

        .search-input::placeholder {
            color: #006600;
        }

        .column-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
        }

        .column-control {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .column-control input[type="checkbox"] {
            appearance: none;
            width: 16px;
            height: 16px;
            border: 1px solid #00ff41;
            background: #000;
            cursor: pointer;
            position: relative;
        }

        .column-control input[type="checkbox"]:checked {
            background: #00ff41;
        }

        .column-control input[type="checkbox"]:checked::after {
            content: '✓';
            position: absolute;
            top: -2px;
            left: 2px;
            color: #000;
            font-size: 12px;
        }

        .column-control label {
            color: #00ff41;
            font-size: 12px;
            cursor: pointer;
            text-shadow: 0 0 5px #00ff41;
        }

        .view-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .view-btn {
            padding: 8px 16px;
            border: 1px solid #00ff41;
            background: #000;
            color: #00ff41;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.3s ease;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            text-shadow: 0 0 5px #00ff41;
        }

        .view-btn:hover {
            background: rgba(0, 255, 65, 0.1);
            box-shadow: 0 0 5px rgba(0, 255, 65, 0.5);
        }

        .view-btn.active {
            background: #00ff41;
            color: #000;
            box-shadow: 0 0 10px #00ff41;
        }

        .decimal-control {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .decimal-control label {
            color: #00ff41;
            font-size: 12px;
            text-shadow: 0 0 5px #00ff41;
        }

        .decimal-control select {
            padding: 5px 8px;
            border: 1px solid #00ff41;
            background: #000;
            color: #00ff41;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            text-shadow: 0 0 5px #00ff41;
        }

        /* Matrix風格表格 */
        .main-table-container {
            padding: 20px;
            overflow-x: auto;
            background: #000;
        }

        .main-table-container h3 {
            color: #00ff41;
            margin: 0 0 15px 0;
            text-shadow: 0 0 5px #00ff41;
        }

        .main-table, .detail-table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #00ff41;
            background: #000;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }

        .main-table th, .detail-table th {
            background: #001100;
            color: #00ff41;
            padding: 12px 8px;
            text-align: left;
            border: 1px solid #00ff41;
            font-weight: normal;
            font-size: 12px;
        }

        .main-table td, .detail-table td {
            padding: 8px;
            border-bottom: 1px solid #003300;
            color: #00ff41;
            font-size: 11px;
            text-shadow: 0 0 3px #00ff41;
        }

        .main-table tr:hover, .detail-table tr:hover {
            background: #001100;
        }

        .file-link {
            color: #00ff41;
            text-decoration: none;
            border-bottom: 1px dotted #00ff41;
        }

        .file-link:hover {
            text-shadow: 0 0 5px #00ff41;
        }

        /* 詳細視圖 - Matrix風格 */
        .detail-view {
            padding: 20px;
            background: #000;
            border-top: 1px solid #00ff41;
            display: none;
        }

        .detail-view.show {
            display: block;
        }

        .detail-view h4 {
            color: #00ff41;
            margin: 0 0 15px 0;
            text-shadow: 0 0 5px #00ff41;
        }

        /* 數值差異顏色 - Matrix主題適配 */
        .numeric-diff.positive {
            color: #00ff88;
        }

        .numeric-diff.negative {
            color: #ff4444;
        }

        .numeric-diff.zero {
            color: #888888;
        }

        .diff-added {
            background: rgba(0, 255, 65, 0.2);
            color: #00ff88;
        }

        .diff-removed {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
            text-decoration: line-through;
        }

        /* 響應式設計 */
        @media (max-width: 768px) {
            .search-box {
                flex-direction: column;
                align-items: stretch;
            }
            
            .search-input {
                min-width: auto;
            }
            
            .column-controls,
            .view-controls {
                justify-content: center;
            }
        }
        ''')
        
        html.append('</style>')
        html.append('</head>')
        html.append('<body class="theme-matrix">')
        html.append('<div class="container">')
        
        # Header
        html.append('<div class="header">')
        html.append('<h1>📊 Excel 變更時間軸監控系統</h1>')
        html.append('<div class="theme-selector">')
        html.append('<span class="theme-label">Matrix風格:</span>')
        html.append('<div class="theme-btn matrix" title="Matrix駭客風格"></div>')
        html.append('</div>')
        html.append('</div>')
        
        # Controls
        html.append('<div class="controls">')
        html.append('<div class="search-box">')
        html.append('<input type="text" class="search-input" id="searchInput" placeholder="🔍 搜尋檔名、作者、儲存格位置...">')
        html.append('</div>')
        
        # Column controls
        html.append('<div class="column-controls">')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showTime" checked onchange="toggleColumn(\'time\')">')
        html.append('<label for="showTime">時間</label>')
        html.append('</div>')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showAuthor" checked onchange="toggleColumn(\'author\')">')
        html.append('<label for="showAuthor">作者</label>')
        html.append('</div>')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showWorksheet" checked onchange="toggleColumn(\'worksheet\')">')
        html.append('<label for="showWorksheet">工作表</label>')
        html.append('</div>')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showAddress" checked onchange="toggleColumn(\'address\')">')
        html.append('<label for="showAddress">位置</label>')
        html.append('</div>')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showValues" checked onchange="toggleColumn(\'values\')">')
        html.append('<label for="showValues">數值</label>')
        html.append('</div>')
        html.append('<div class="column-control">')
        html.append('<input type="checkbox" id="showFormulas" checked onchange="toggleColumn(\'formulas\')">')
        html.append('<label for="showFormulas">公式</label>')
        html.append('</div>')
        html.append('</div>')
        
        # View controls  
        html.append('<div class="view-controls">')
        html.append('<button class="view-btn active" onclick="sortBy(\'time\')">⏰ 按時間</button>')
        html.append('<button class="view-btn" onclick="sortBy(\'address\')">📍 按位置</button>')
        html.append('<button class="view-btn" onclick="sortBy(\'author\')">👤 按作者</button>')
        html.append('<div class="decimal-control">')
        html.append('<label for="glowLevel">朦朧效果:</label>')
        html.append('<select id="glowLevel" onchange="updateGlowEffect()">')
        html.append('<option value="0">關閉</option>')
        html.append('<option value="3" selected>微朦朧</option>')
        html.append('<option value="5">中朦朧</option>')
        html.append('<option value="8">重朦朧</option>')
        html.append('<option value="12">超朦朧</option>')
        html.append('</select>')
        html.append('</div>')
        html.append('</div>')
        html.append('</div>')
        
        # Main Table  
        html.append('<div class="main-table-container">')
        html.append('<h3>>>> 檔案變更列表</h3>')
        html.append('<div class="muted">提示：點檔名可展開「檔案詳情視圖」（提供「依事件時間 / 依 Address / 依作者」三種檢視）。</div>')
        html.append('<div id="file-view" style="display:none;margin:12px 0;padding:8px;border:1px solid #00ff41;background:#000;color:#00ff41;"></div>')
        html.append('<table class="main-table" id="mainTable">')
        html.append('<thead>')
        html.append('<tr>')
        html.append('<th style="width: 140px;">時間</th>')
        html.append('<th style="width: 180px;">檔名</th>')
        html.append('<th style="width: 90px;">工作表</th>')
        html.append('<th style="width: 70px; text-align: center;">變更數</th>')
        html.append('<th style="width: 110px;">作者</th>')
        html.append('<th style="width: 60px; text-align: center;">事件#</th>')
        html.append('<th style="width: 140px;">Baseline 時間</th>')
        html.append('<th style="width: 140px;">Current 時間</th>')
        html.append('<th style="width: 80px; text-align: center;">快照</th>')
        html.append('<th style="width: 80px; text-align: center;">詳表</th>')
        html.append('<th style="width: auto;">路徑</th>')
        html.append('</tr>')
        html.append('</thead>')
        html.append('<tbody>')
        
        # Generate table rows from events
        for e in (events or []):
            ts = e.get('timestamp','')
            fn = e.get('filename','')
            ws = e.get('worksheet','') or ''
            ch = e.get('changes','')
            au = e.get('author','') or ''
            ev = e.get('event_number','') or ''
            fp = e.get('file','')
            sp = e.get('snapshot_path') or ''
            pp = e.get('per_event_path') or ''
            
            # Generate change count styling
            try:
                change_num = int(ch) if ch else 0
                if change_num > 100:
                    change_style = 'padding: 3px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; background: rgba(255, 68, 68, 0.2); color: #ff4444; border: 1px solid #ff4444;'
                elif change_num > 20:
                    change_style = 'padding: 3px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; background: rgba(255, 193, 7, 0.2); color: #ffbb00; border: 1px solid #ffbb00;'
                else:
                    change_style = 'padding: 3px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; background: rgba(0, 255, 65, 0.2); color: #00ff88; border: 1px solid #00ff88;'
            except:
                change_style = 'padding: 3px 6px; border-radius: 3px; font-size: 11px; font-weight: 500; background: rgba(0, 255, 65, 0.2); color: #00ff88; border: 1px solid #00ff88;'
                
            sp_link = f'<a href="{sp}" target="_blank" style="padding: 4px 8px; border: 1px solid #00ff41; border-radius: 4px; font-size: 11px; cursor: pointer; text-decoration: none; background: rgba(0, 255, 65, 0.1); color: #00ff41;">snapshot</a>' if sp else ''
            pp_link = f'<a href="{pp}" target="_blank" style="padding: 4px 8px; border: 1px solid #00ff41; border-radius: 4px; font-size: 11px; cursor: pointer; text-decoration: none; background: rgba(0, 255, 65, 0.1); color: #00ff41;">per-event</a>' if pp else ''
            
            html.append(f'<tr data-file="{fp}">')
            html.append(f'<td>{ts}</td>')
            html.append(f'<td><a href="#" class="file-link" data-file="{fp}">{fn}</a></td>')
            html.append(f'<td>{ws}</td>')
            html.append(f'<td style="text-align: center;"><span style="{change_style}">{ch}</span></td>')
            html.append(f'<td>{au}</td>')
            html.append(f'<td style="text-align: center;">{ev}</td>')
            html.append(f'<td><span style="color: #00ff88; font-weight: 500; font-size: 12px;">{ts}</span></td>')  # Baseline time (simplified)
            html.append(f'<td><span style="color: #00ddff; font-weight: 500; font-size: 12px;">{ts}</span></td>')  # Current time (simplified)
            html.append(f'<td style="text-align: center;">{sp_link}</td>')
            html.append(f'<td style="text-align: center;">{pp_link}</td>')
            html.append(f'<td style="font-size: 11px; color: #00aa00;">{fp}</td>')
            html.append('</tr>')
        
        html.append('</tbody>')
        html.append('</table>')
        html.append('</div>')
        
        # Detail View
        html.append('<div id="detailView" class="detail-view">')
        html.append('<h4>>>> 檔案詳細變更：<span id="detailFileName"></span></h4>')
        html.append('<div style="overflow-x: auto;">')
        html.append('<table class="detail-table">')
        html.append('<thead><tr>')
        html.append('<th class="detail-col-time" data-column="time">時間</th>')
        html.append('<th class="detail-col-author" data-column="author">作者</th>')
        html.append('<th class="detail-col-worksheet" data-column="worksheet">工作表</th>')
        html.append('<th class="detail-col-address" data-column="address">位置</th>')
        html.append('<th class="detail-col-old-value" data-column="values">原始值</th>')
        html.append('<th class="detail-col-new-value" data-column="values">變更後值</th>')
        html.append('<th class="detail-col-value-diff" data-column="values">值差異</th>')
        html.append('<th class="detail-col-old-formula" data-column="formulas">原始公式</th>')
        html.append('<th class="detail-col-new-formula" data-column="formulas">變更後公式</th>')
        html.append('<th class="detail-col-formula-diff" data-column="formulas">公式差異</th>')
        html.append('</tr></thead>')
        html.append('<tbody id="detailTableBody">')
        html.append('</tbody>')
        html.append('</table>')
        html.append('</div>')
        html.append('</div>')
        
        html.append('</div>')  # container end
        
        # Embed events JSON
        try:
            safe_json_tag = json.dumps(events, ensure_ascii=False).replace('</', '<\/')
        except Exception:
            safe_json_tag = '[]'
        html.append('<script id="events-data" type="application/json">'+ safe_json_tag +'</script>')
        
        # JavaScript functionality
        html.append('<script>')
        html.append('''
        // Load events data
        const data = JSON.parse(document.getElementById('events-data').textContent);
        const fileView = document.getElementById("file-view");
        
        // Search functionality
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    const rows = document.querySelectorAll('#mainTable tbody tr');
                    
                    rows.forEach(row => {
                        const text = row.textContent.toLowerCase();
                        row.style.display = text.includes(searchTerm) ? '' : 'none';
                    });
                });
            }
            
            // Initialize glow effect
            updateGlowEffect();
            
            // File link click events
            document.querySelectorAll('.file-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const file = this.getAttribute('data-file');
                    renderFileView(file);
                });
            });
        });
        
        // Column toggle functionality
        function toggleColumn(columnType) {
            const elements = document.querySelectorAll(`[data-column="${columnType}"]`);
            elements.forEach(el => {
                el.style.display = el.style.display === 'none' ? '' : 'none';
            });
        }
        
        // Sort functionality
        function sortBy(type) {
            // Update button states
            document.querySelectorAll('.view-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            console.log('排序方式:', type);
            
            // Sort detail table if visible
            const tbody = document.querySelector('.detail-table tbody');
            if (tbody && tbody.querySelectorAll('tr').length > 0) {
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                rows.sort((a, b) => {
                    let aVal, bVal;
                    if (type === 'time') {
                        aVal = a.querySelector('[data-column="time"]')?.textContent || '';
                        bVal = b.querySelector('[data-column="time"]')?.textContent || '';
                    } else if (type === 'address') {
                        aVal = a.querySelector('[data-column="address"]')?.textContent || '';
                        bVal = b.querySelector('[data-column="address"]')?.textContent || '';
                    } else if (type === 'author') {
                        aVal = a.querySelector('[data-column="author"]')?.textContent || '';
                        bVal = b.querySelector('[data-column="author"]')?.textContent || '';
                    }
                    return aVal.localeCompare(bVal);
                });
                
                // Re-arrange rows
                rows.forEach(row => tbody.appendChild(row));
            }
        }
        
        // Main file view render function (like original)
        function renderFileView(file) {
            try {
                if (!fileView) {
                    console.error("找不到file-view元素");
                    return;
                }
                const evts = data.filter(e => (e.file || "") == file).sort((a,b) => (a.timestamp < b.timestamp ? 1 : -1));
                if (!evts.length) {
                    fileView.style.display = "none";
                    fileView.innerHTML = "";
                    return;
                }
                fileView.style.display = "block";
                
                let html = '<div class="controls"><div style="color: #00ff41;"><b>檔案：</b>' + file + '</div>';
                html += '<div style="margin-top:10px"><label style="color: #00ff41;"><input type="checkbox" id="autoSizeColumns" checked> 自適應短欄位寬度</label> <span class="muted">(僅適用於工作表、位置等短欄位，公式和值欄位總是換行)</span></div>';
                
                // 找出所有作者和工作表
                const allAuthors = new Set();
                const allWorksheets = new Set();
                const earliestTime = evts[evts.length-1].timestamp;
                const latestTime = evts[0].timestamp;
                let totalChanges = 0;
                evts.forEach(e => {
                    if(e.author) allAuthors.add(e.author);
                    totalChanges += parseInt(e.changes || 0);
                    (e.diffs || []).forEach(d => {
                        if(d.worksheet) allWorksheets.add(d.worksheet);
                    });
                });
                
                html += '<div class="controls"><div><button id="byTime" class="view-btn">依事件時間</button> <button id="byAddr" class="view-btn">依 Address</button> <button id="byAuthor" class="view-btn">依作者</button> <button id="exportCSV" class="export-btn">匯出 CSV</button></div>';
                html += '<div class="column-controls" style="margin-top:10px">顯示欄位: ';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="worksheet" checked> 工作表</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="address" checked> 位置</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="oldvalue" checked> 原始值</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="newvalue" checked> 變更後值</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="oldformula" checked> 原始公式</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="newformula" checked> 變更後公式</label>';
                html += '<label class="column-toggle"><input type="checkbox" class="col-toggle" data-col="formuladiff" checked> 公式差異比較</label>';
                html += '</div>';
                html += '<div id="summary" class="summary-box"></div>';
                html += '</div>';
                
                // 默認按事件時間視圖
                let s = "<h4>依事件時間</h4>";
                evts.forEach(e => {
                    s += '<div style="margin:6px 0;padding:6px;border:1px solid #00ff41;color:#00ff41;">';
                    s += "<div><b>事件#" + (e.event_number || "") + "</b> | " + e.timestamp + " | 變更數 " + (e.changes || "") + " | " + (e.author || "") + "</div>";
                    const diffs = e.diffs || [];
                    if (diffs.length) {
                        s += '<table style="margin-top:4px;border-collapse:collapse;width:100%;border:1px solid #00ff41;" class="diff-table"><thead><tr>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-time">時間</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-author">作者</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-worksheet">工作表</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-address">位置</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-oldvalue">原始值</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-newvalue">變更後值</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-valuediff">值差異</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-oldformula">原始公式</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-newformula">變更後公式</th>';
                        s += '<th style="border:1px solid #00ff41;padding:4px;background:#001100;color:#00ff41;" class="col-formuladiff">公式差異比較</th>';
                        s += '</tr></thead><tbody>';
                        diffs.forEach(d => {
                            s += '<tr>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-time">' + e.timestamp + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-author">' + (e.author || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-worksheet">' + (d.worksheet || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-address">' + (d.address || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-oldvalue">' + (d.old_value || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-newvalue">' + (d.new_value || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-valuediff">' + generateValueDiff(d.old_value, d.new_value) + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-oldformula">' + (d.old_formula || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-newformula">' + (d.new_formula || "") + '</td>';
                            s += '<td style="border:1px solid #00ff41;padding:4px;color:#00ff41;" class="col-formuladiff">' + generateFormulaDiff(d.old_formula, d.new_formula) + '</td>';
                            s += '</tr>';
                        });
                        s += '</tbody></table>';
                    } else {
                        s += '<div class="muted">(無精簡差異，請開 per-event)</div>';
                    }
                    s += '</div>';
                });
                
                fileView.innerHTML = html + s;
                
                // Setup button events
                document.getElementById("byTime").onclick = () => renderFileView(file);
                document.getElementById("byAddr").onclick = () => viewByAddr(file, evts);
                document.getElementById("byAuthor").onclick = () => viewByAuthor(file, evts);
                
                // Setup column toggles
                document.querySelectorAll('.col-toggle').forEach(toggle => {
                    toggle.addEventListener('change', function() {
                        const col = this.getAttribute('data-col');
                        const elements = document.querySelectorAll('.col-' + col);
                        elements.forEach(el => {
                            el.style.display = this.checked ? '' : 'none';
                        });
                    });
                });
                
            } catch (e) {
                console.error("renderFileView error:", e);
            }
        }
        
        // View by Address
        function viewByAddr(file, evts) {
            let s = "<h4>依 Address</h4>";
            const bag = {};
            evts.forEach(e => {
                (e.diffs || []).forEach(d => {
                    const k = (d.address || "") + "@" + (d.worksheet || "");
                    (bag[k] || (bag[k] = [])).push({
                        evt: e.event_number,
                        ts: e.timestamp,
                        author: e.author,
                        worksheet: d.worksheet,
                        address: d.address,
                        old: d.old_value,
                        new: d.new_value,
                        old_formula: d.old_formula,
                        new_formula: d.new_formula
                    });
                });
            });
            const keys = Object.keys(bag).sort();
            keys.forEach(k => {
                const parts = k.split("@");
                const address = parts[0] || "";
                const sheet = parts[1] || "";
                s += '<div style="margin:6px 0;padding:6px;border:1px solid #00ff41;color:#00ff41;"><div><b>地址: ' + address + '</b> <span class="muted">(工作表: ' + sheet + ')</span></div>';
                // Add table here similar to above
                s += '</div>';
            });
            
            let html = '<div class="controls"><div style="color: #00ff41;"><b>檔案：</b>' + file + '</div></div>';
            fileView.innerHTML = html + s;
        }
        
        // View by Author  
        function viewByAuthor(file, evts) {
            let s = "<h4>依作者</h4>";
            // Similar implementation
            let html = '<div class="controls"><div style="color: #00ff41;"><b>檔案：</b>' + file + '</div></div>';
            fileView.innerHTML = html + s;
        }
        
        // Legacy function for compatibility
        function toggleDetailView(filePath) {
            const detailView = document.getElementById('detailView');
            const fileName = document.getElementById('detailFileName');
            const detailTableBody = document.getElementById('detailTableBody');
            
            if (detailView.classList.contains('show')) {
                detailView.classList.remove('show');
                return;
            }
            
            // Filter events for this file
            const fileEvents = eventsData.filter(e => e.file === filePath);
            
            if (fileEvents.length === 0) {
                return;
            }
            
            // Set filename
            const displayName = filePath.split('\\\\').pop() || filePath.split('/').pop() || filePath;
            fileName.textContent = displayName;
            
            // Clear and populate detail table
            detailTableBody.innerHTML = '';
            
            fileEvents.forEach(event => {
                if (event.diffs && Array.isArray(event.diffs)) {
                    event.diffs.forEach(diff => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="detail-col-time" data-column="time">${event.timestamp || ''}</td>
                            <td class="detail-col-author" data-column="author">${event.author || ''}</td>
                            <td class="detail-col-worksheet" data-column="worksheet">${diff.worksheet || ''}</td>
                            <td class="detail-col-address" data-column="address">${diff.address || ''}</td>
                            <td class="detail-col-old-value" data-column="values">${diff.old_value || ''}</td>
                            <td class="detail-col-new-value" data-column="values">${diff.new_value || ''}</td>
                            <td class="detail-col-value-diff" data-column="values"><span class="diff-highlight">${generateValueDiff(diff.old_value, diff.new_value)}</span></td>
                            <td class="detail-col-old-formula" data-column="formulas">${diff.old_formula || ''}</td>
                            <td class="detail-col-new-formula" data-column="formulas">${diff.new_formula || ''}</td>
                            <td class="detail-col-formula-diff" data-column="formulas">${generateFormulaDiff(diff.old_formula, diff.new_formula)}</td>
                        `;
                        detailTableBody.appendChild(row);
                    });
                }
            });
            
            detailView.classList.add('show');
            detailView.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Generate value difference display
        function generateValueDiff(oldVal, newVal) {
            if (oldVal === newVal) return '無變更';
            
            const oldNum = parseFloat(oldVal);
            const newNum = parseFloat(newVal);
            
            if (!isNaN(oldNum) && !isNaN(newNum)) {
                const diff = newNum - oldNum;
                const className = diff > 0 ? 'positive' : diff < 0 ? 'negative' : 'zero';
                const prefix = diff >= 0 ? '+' : '';
                return `<span class="numeric-diff ${className}">${prefix}${diff.toFixed(2)}</span>`;
            }
            
            return `<span class="diff-removed">${oldVal}</span> → <span class="diff-added">${newVal}</span>`;
        }
        
        // Generate formula difference display
        function generateFormulaDiff(oldFormula, newFormula) {
            if (oldFormula === newFormula) return '<span class="formula-diff-unchanged">' + (oldFormula || '') + '</span>';
            
            if (!oldFormula && newFormula) {
                return '<span class="diff-added">' + newFormula + '</span>';
            }
            
            if (oldFormula && !newFormula) {
                return '<span class="diff-removed">' + oldFormula + '</span>';
            }
            
            return '<span class="diff-removed">' + (oldFormula || '') + '</span><br><span class="diff-added">' + (newFormula || '') + '</span>';
        }
        
        // Glow effect control
        function updateGlowEffect() {
            const glowLevel = document.getElementById('glowLevel').value;
            const glowSize = parseInt(glowLevel);
            
            // Remove existing glow style
            let existingGlowStyle = document.getElementById('glow-styles');
            if (existingGlowStyle) existingGlowStyle.remove();
            
            if (glowSize > 0) {
                // Create new glow style
                const style = document.createElement('style');
                style.id = 'glow-styles';
                style.textContent = `
                    body { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .search-input { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .column-control label { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .view-btn { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .decimal-control label { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .decimal-control select { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .main-table th, .detail-table th { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .main-table td, .detail-table td { text-shadow: 0 0 ${Math.max(1, glowSize-2)}px #00ff41 !important; }
                    .main-table-container h3, .detail-view h4 { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .file-link { text-shadow: 0 0 ${glowSize}px #00ff41 !important; }
                    .numeric-diff, .diff-added, .diff-removed { text-shadow: 0 0 ${Math.max(1, glowSize-1)}px currentColor !important; }
                `;
                document.head.appendChild(style);
            }
        }
        ''')
        html.append('</script>')
        html.append('</body>')
        html.append('</html>')
        
        # Write to file
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(TIMELINE_HTML_V6), exist_ok=True)
            # 寫入檔案
            with open(TIMELINE_HTML_V6, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html))
            # 輸出成功訊息
            print(f"[timeline-v6] HTML 成功寫入: {TIMELINE_HTML_V6}")
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"[timeline-v6] HTML 詳細信息已寫入 {TIMELINE_HTML_V6}")
        except Exception as e:
            if getattr(settings, 'SHOW_DEBUG_MESSAGES', False):
                print(f"[timeline-v6] 寫入 HTML 失敗: {e}")
    except Exception:
        pass