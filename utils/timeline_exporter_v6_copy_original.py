import os
import json
from datetime import datetime
import config.settings as settings

# 直接複製原版timeline_exporter.py的所有邏輯，只改CSS為Matrix風格

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
    Append a timeline event to events.json and regenerate index2.html.
    """
    try:
        _init_paths()
        # Load existing events
        events = _load_events()
        # Add new event
        events.append(event_dict)
        # Save to JSON (shared with original)
        os.makedirs(TIMELINE_DIR, exist_ok=True)
        with open(TIMELINE_JSON, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        # Generate V6 HTML
        generate_html(events)
        # Debug messages
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


def generate_html(events=None):
    """Write a static HTML (self-contained) that lists events with simple filtering."""
    try:
        _init_paths()
        if events is None:
            events = _load_events()
        # Latest first
        try:
            events = sorted(events, key=lambda e: e.get('timestamp', ''), reverse=True)
        except Exception:
            pass
        # Minimal self-contained HTML + vanilla JS (no CDN)
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="zh-Hant">')
        html.append('<head><meta charset="utf-8"/>')
        html.append('<title>Excel Timeline - Matrix風格</title>')
        html.append('<style>')
        
        # Matrix風格CSS (保留原版class結構，只改顏色和字體)
        html.append('  body{font-family: Consolas, Monaco, Courier New, monospace; margin:16px; background:#000; color:#00ff41; text-shadow: 0 0 3px #00ff41;}')
        html.append('  table{border-collapse:collapse;width:100%; border:1px solid #00ff41; background:#000;}')
        html.append('  th,td{border:1px solid #00ff41;padding:6px;word-break:break-all;overflow:hidden;min-width:60px; color:#00ff41; text-shadow: 0 0 2px #00ff41;}')
        html.append('  th{background:#001100;position:sticky;top:0;cursor:default;}')
        html.append('  th:hover{background:#002200;}')
        html.append('  .muted{color:#006600;font-size:12px}')
        html.append('  input{padding:6px;margin:4px 8px 12px 0; background:#000; color:#00ff41; border:1px solid #00ff41; text-shadow: 0 0 3px #00ff41;}')
        html.append('  .formula-cell{color:#00ddaa;}')
        html.append('  .formula-diff-deleted{background-color:rgba(255,68,68,0.2);text-decoration:line-through;color:#ff4444;}')
        html.append('  .formula-diff-added{background-color:rgba(0,255,65,0.2);color:#00ff88;}')
        html.append('  .formula-diff-unchanged{color:#888888;}')
        html.append('  button{padding:5px 10px;margin-right:5px;cursor:pointer; background:#000; color:#00ff41; border:1px solid #00ff41; text-shadow: 0 0 3px #00ff41;}')
        html.append('  button:hover{background:rgba(0,255,65,0.1);}')
        html.append('  .author-filter, .worksheet-filter{margin:5px 0;}')
        html.append('  .author-tag, .worksheet-tag{display:inline-block;padding:3px 6px;margin:2px;background:rgba(0,255,65,0.1);border:1px solid #00ff41;border-radius:3px;cursor:pointer; color:#00ff41;}')
        html.append('  .author-highlight{background:rgba(255,255,0,0.2);}')
        html.append('  .controls{margin:10px 0;padding:10px;background:#000;border:1px solid #00ff41;border-radius:4px;}')
        html.append('  .column-toggle{margin-right:10px;white-space:nowrap; color:#00ff41;}')
        html.append('  .summary-box{margin:10px 0;padding:10px;background:#000;border:1px solid #00ff41;border-radius:4px; color:#00ff41;}')
        html.append('  .export-btn{background:#000;color:#00ff41;border:1px solid #00ff41;padding:6px 12px;border-radius:4px;}')
        html.append('  .filters-container{display:flex;flex-direction:column;gap:5px;}')
        html.append('  /* 動態寬度將由 JavaScript 計算 */')
        html.append('  .col-time {min-width:120px; max-width:150px;}')
        html.append('  .col-author {min-width:60px; max-width:120px;}')
        html.append('  .col-worksheet {min-width:60px; max-width:100px;}')
        html.append('  .col-address {min-width:50px; max-width:80px;}')
        html.append('  .col-oldvalue, .col-newvalue {min-width:80px; max-width:200px;}')
        html.append('  .col-oldformula, .col-newformula, .col-formuladiff {min-width:250px; width:250px; max-width:250px;}')
        html.append('  /* 自適應列寬度樣式 */')
        html.append('  table.auto-size-columns .col-worksheet,')
        html.append('  table.auto-size-columns .col-address,')
        html.append('  table.auto-size-columns .col-event,')
        html.append('  table.auto-size-columns .col-time,')
        html.append('  table.auto-size-columns .col-author {')
        html.append('    white-space: nowrap;')
        html.append('    max-width: none;')
        html.append('  }')
        html.append('  /* 公式列總是換行，避免表格過寬 */')
        html.append('  .col-oldformula, .col-newformula, .col-formuladiff {')
        html.append('    word-break: break-word;')
        html.append('    min-width: 150px;')
        html.append('    max-width: 350px;')
        html.append('  }')
        html.append('  /* 值列總是換行，但給予適當空間 */')
        html.append('  .col-oldvalue, .col-newvalue {')
        html.append('    word-break: break-word;')
        html.append('    min-width: 120px;')
        html.append('    max-width: 300px;')
        html.append('  }')
        html.append('  a{color:#00ff41; text-shadow: 0 0 3px #00ff41; text-decoration: none; border-bottom: 1px dotted #00ff41;}')
        html.append('  a:hover{text-shadow: 0 0 8px #00ff41;}')
        html.append('  h2{color:#00ff41; text-shadow: 0 0 10px #00ff41;}')
        html.append('  /* 朦朧效果控制 */')
        html.append('  select{background:#000; color:#00ff41; border:1px solid #00ff41; text-shadow: 0 0 3px #00ff41;}')
        
        html.append('</style>')
        html.append('</head><body>')
        html.append('<h2>Excel Timeline - Matrix風格</h2>')
        
        # 朦朧效果控制
        html.append('<div style="margin-bottom:10px; color:#00ff41;">朦朧效果: <select id="glowLevel" onchange="updateGlowEffect()"><option value="0">關閉</option><option value="3" selected>微朦朧</option><option value="5">中朦朧</option><option value="8">重朦朧</option><option value="12">超朦朧</option></select></div>')
        
        # 完全複製原版HTML結構
        html.append('<div class="muted">提示：點檔名可展開「檔案詳情視圖」（提供「依事件時間 / 依 Address / 依作者」三種檢視）。</div>')
        html.append('<div>快速篩選：<input id="q" placeholder="關鍵字（檔名/路徑/作者/工作表）" style="width:360px"/></div>')
        html.append('<div id="file-view" style="display:none;margin:12px 0;padding:8px;border:1px solid #00ff41;background:#000;color:#00ff41;"></div>')
        html.append('<table id="tbl">')
        html.append('<thead><tr><th>時間</th><th>檔名</th><th>工作表</th><th>變更數</th><th>作者</th><th>事件#</th><th>快照</th><th>詳表</th><th class="muted">路徑</th></tr></thead>')
        html.append('<tbody>')
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
            sp_link = f'<a href="{sp}" target="_blank">snapshot</a>' if sp else ''
            pp_link = f'<a href="{pp}" target="_blank">per-event</a>' if pp else ''
            html.append(f'<tr data-file="{fp}"><td>{ts}</td><td><a href="#" class="file-link" data-file="{fp}">{fn}</a></td><td>{ws}</td><td>{ch}</td><td>{au}</td><td>{ev}</td><td>{sp_link}</td><td>{pp_link}</td><td class="muted">{fp}</td></tr>')
        html.append('</tbody></table>')
        
        # 內嵌 events JSON，避免在 JS 字串中處理跳脫/關閉標籤
        try:
            safe_json_tag = json.dumps(events, ensure_ascii=False).replace('</', '<\\/')
        except Exception:
            safe_json_tag = '[]'
        html.append('<script id="events-data" type="application/json">'+ safe_json_tag +'</script>')
        html.append('<script>')
        
        # 朦朧效果控制函數
        html.append('function updateGlowEffect() {')
        html.append('  const glowLevel = document.getElementById("glowLevel").value;')
        html.append('  const glowSize = parseInt(glowLevel);')
        html.append('  let existingGlowStyle = document.getElementById("glow-styles");')
        html.append('  if (existingGlowStyle) existingGlowStyle.remove();')
        html.append('  if (glowSize > 0) {')
        html.append('    const style = document.createElement("style");')
        html.append('    style.id = "glow-styles";')
        html.append('    style.textContent = ')
        html.append('      "body { text-shadow: 0 0 " + glowSize + "px #00ff41 !important; }" +')
        html.append('      "th, td { text-shadow: 0 0 " + Math.max(1, glowSize-1) + "px #00ff41 !important; }" +')
        html.append('      "input, button, select { text-shadow: 0 0 " + glowSize + "px #00ff41 !important; }" +')
        html.append('      "a { text-shadow: 0 0 " + glowSize + "px #00ff41 !important; }" +')
        html.append('      "h2 { text-shadow: 0 0 " + (glowSize+2) + "px #00ff41 !important; }" +')
        html.append('      ".controls, .summary-box { text-shadow: 0 0 " + Math.max(1, glowSize-1) + "px #00ff41 !important; }";')
        html.append('    document.head.appendChild(style);')
        html.append('  }')
        html.append('}')
        
        # 完整複製原版的所有JavaScript邏輯，只改CSS顏色為Matrix風格
        
        html.append('const q=document.getElementById("q");')
        html.append('q.addEventListener("input",()=>{const v=q.value.toLowerCase();document.querySelectorAll("#tbl tbody tr").forEach(tr=>{tr.style.display=tr.innerText.toLowerCase().includes(v)?"":"none";});});')
        html.append("const data = JSON.parse(document.getElementById('events-data').textContent);")
        html.append('const fileView=document.getElementById("file-view");')
        
        # 完整複製原版的renderFileView函數
        html.append('function renderFileView(file){')
        html.append('  try {')
        html.append('    const fileView = document.getElementById("file-view");')
        html.append('    if (!fileView) {')
        html.append('      console.error("找不到file-view元素");')
        html.append('      return;')
        html.append('    }')
        html.append('    const evts=data.filter(e=> (e.file||"")==file).sort((a,b)=> (a.timestamp<b.timestamp?1:-1));')
        html.append('    if(!evts.length){fileView.style.display="none";fileView.innerHTML="";return;}')
        html.append('    fileView.style.display="block";')
        html.append('    let html="<div class=\\\"controls\\\"><div style=\\\"color:#00ff41;\\\"><b>檔案：</b>"+file+"</div>";')
        html.append('    html+="<div style=\\\"margin-top:10px;color:#00ff41;\\\"><label><input type=\\\"checkbox\\\" id=\\\"autoSizeColumns\\\" checked> 自適應短欄位寬度</label> <span class=\\\"muted\\\">(僅適用於工作表、位置等短欄位，公式和值欄位總是換行)</span></div>";')
        
        # 複製所有原版的JavaScript邏輯（完整版）
        html.append('  // 找出所有作者和工作表')
        html.append('  const allAuthors = new Set();')
        html.append('  const allWorksheets = new Set();')
        html.append('  const earliestTime = evts[evts.length-1].timestamp;')
        html.append('  const latestTime = evts[0].timestamp;')
        html.append('  let totalChanges = 0;')
        html.append('  evts.forEach(e => {')
        html.append('    if(e.author) allAuthors.add(e.author);')
        html.append('    totalChanges += parseInt(e.changes || 0);')
        html.append('    (e.diffs || []).forEach(d => {')
        html.append('      if(d.worksheet) allWorksheets.add(d.worksheet);')
        html.append('    });')
        html.append('  });')
        html.append('  html+="<div class=\\\"controls\\\"><div><button id=\\\"byTime\\\">依事件時間</button> <button id=\\\"byAddr\\\">依 Address</button> <button id=\\\"byAuthor\\\">依作者</button> <button id=\\\"exportCSV\\\" class=\\\"export-btn\\\">匯出 CSV</button></div>";')
        html.append('  html+="<div class=\\\"column-controls\\\" style=\\\"margin-top:10px;color:#00ff41;\\\">顯示欄位: "+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"worksheet\\\" checked> 工作表</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"address\\\" checked> 位置</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"oldvalue\\\" checked> 原始值</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"newvalue\\\" checked> 變更後值</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"oldformula\\\" checked> 原始公式</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"newformula\\\" checked> 變更後公式</label>"+')
        html.append('         "<label class=\\\"column-toggle\\\"><input type=\\\"checkbox\\\" class=\\\"col-toggle\\\" data-col=\\\"formuladiff\\\" checked> 公式差異比較</label>"+')
        html.append('         "</div>";')
        html.append('  html+="<div class=\\\"filters-container\\\"><div id=\\\"authorFilter\\\" class=\\\"author-filter\\\"></div><div id=\\\"worksheetFilter\\\" class=\\\"worksheet-filter\\\"></div></div>";')
        html.append('  html+="<div id=\\\"summary\\\" class=\\\"summary-box\\\"></div>";')
        html.append('  html+="</div>";')
        
        # 複製所有輔助函數
        html.append('  function formatFormula(formula) {')
        html.append('    if (formula === undefined || formula === null) return "";')
        html.append('    let str = JSON.stringify(formula);')
        html.append('    if (str.startsWith("\\"") && str.endsWith("\\"")) {')
        html.append('      str = str.slice(1, -1);')
        html.append('    }')
        html.append('    str = str.replace(/\\\\\\\\"/g, \'"\').replace(/\\\\\\\\n/g, \'\\n\').replace(/\\\\\\\\t/g, \'\\t\');')
        html.append('    return str;')
        html.append('  }')
        
        html.append('  function formatFormulaDiff(oldFormula, newFormula) {')
        html.append('    const oldStr = formatFormula(oldFormula);')
        html.append('    const newStr = formatFormula(newFormula);')
        html.append('    if (oldStr === newStr) {')
        html.append('      return "<span class=\\"formula-diff-unchanged\\">" + oldStr + "</span>";')
        html.append('    }')
        html.append('    const oldNum = parseFloat(oldStr);')
        html.append('    const newNum = parseFloat(newStr);')
        html.append('    if (!isNaN(oldNum) && !isNaN(newNum)) {')
        html.append('      const diff = newNum - oldNum;')
        html.append('      let diffStr = "";')
        html.append('      if (diff > 0) {')
        html.append('        diffStr = "<span style=\\"color: #00ff88; font-weight: bold;\\">+" + diff.toLocaleString() + "</span>";')
        html.append('      } else if (diff < 0) {')
        html.append('        diffStr = "<span style=\\"color: #ff4444; font-weight: bold;\\">" + diff.toLocaleString() + "</span>";')
        html.append('      } else {')
        html.append('        diffStr = "<span style=\\"color: #888888;\\">0</span>";')
        html.append('      }')
        html.append('      return "<span class=\\"formula-diff-deleted\\">" + oldStr + "</span> → <span class=\\"formula-diff-added\\">" + newStr + "</span><br><small>差值: " + diffStr + "</small>";')
        html.append('    }')
        html.append('    return "<span class=\\"formula-diff-deleted\\">" + oldStr + "</span> → <span class=\\"formula-diff-added\\">" + newStr + "</span>";')
        html.append('  }')
        
        html.append('  function rowDiff(d, ts, auth) {')
        html.append('    return "<tr>"+')
        html.append('      "<td class=\\"col-time\\">"+ts+"</td>"+')
        html.append('      "<td class=\\"col-author author-cell\\">"+(auth||"")+"</td>"+')
        html.append('      "<td class=\\"col-worksheet\\">"+(d.worksheet||"")+"</td>"+')
        html.append('      "<td class=\\"col-address\\">"+(d.address||"")+"</td>"+')
        html.append('      "<td class=\\"col-oldvalue\\">"+formatFormula(d.old_value)+"</td>"+')
        html.append('      "<td class=\\"col-newvalue\\">"+formatFormula(d.new_value)+"</td>"+')
        html.append('      "<td class=\\"col-valuediff\\">"+formatFormulaDiff(d.old_value,d.new_value)+"</td>"+')
        html.append('      "<td class=\\"col-oldformula formula-cell\\">"+formatFormula(d.old_formula)+"</td>"+')
        html.append('      "<td class=\\"col-newformula formula-cell\\">"+formatFormula(d.new_formula)+"</td>"+')
        html.append('      "<td class=\\"col-formuladiff formula-cell\\">"+formatFormulaDiff(d.old_formula,d.new_formula)+"</td>"+')
        html.append('      "</tr>";')
        html.append('  }')
        
        # 原版的viewByTime函數
        html.append('  function viewByTime(){')
        html.append('    let s="<h4 style=\\"color:#00ff41;\\">依事件時間</h4>";')
        html.append('    evts.forEach(e => {')
        html.append('      s+="<div style=\\"margin:6px 0;padding:6px;border:1px solid #00ff41;color:#00ff41;\\">";')
        html.append('      s+="<div><b>事件#"+(e.event_number||"")+"</b> | "+e.timestamp+" | 變更數 "+(e.changes||"")+" | "+(e.author||"")+"</div>";')
        html.append('      const diffs=e.diffs||[];')
        html.append('      if(diffs.length){')
        html.append('        s+="<table style=\\"margin-top:4px;border:1px solid #00ff41;background:#000;\\" class=\\"diff-table\\"><thead><tr>"+')
        html.append('          "<th class=\\"col-time\\">時間</th>"+')
        html.append('          "<th class=\\"col-author\\">作者</th>"+')
        html.append('          "<th class=\\"col-worksheet\\">工作表</th>"+')
        html.append('          "<th class=\\"col-address\\">位置</th>"+')
        html.append('          "<th class=\\"col-oldvalue\\">原始值</th>"+')
        html.append('          "<th class=\\"col-newvalue\\">變更後值</th>"+')
        html.append('          "<th class=\\"col-valuediff\\">值差異</th>"+')
        html.append('          "<th class=\\\"col-oldformula\\\">原始公式</th>"+')
        html.append('          "<th class=\\\"col-newformula\\\">變更後公式</th>"+')
        html.append('          "<th class=\\\"col-formuladiff\\\">公式差異比較</th>"+')
        html.append('          "</tr></thead><tbody>";')
        html.append('        diffs.forEach(d=>{s+=rowDiff(d, e.timestamp, e.author)});')
        html.append('        s+="</tbody></table>";')
        html.append('      }else{ s+="<div class=muted>(無精簡差異，請開 per-event)</div>"; }')
        html.append('      s+="</div>";')
        html.append('    });')
        html.append('    fileView.innerHTML=html+s;')
        html.append('    document.getElementById("byTime").onclick=viewByTime;')
        html.append('    document.getElementById("byAddr").onclick=viewByAddr;')
        html.append('    document.getElementById("byAuthor").onclick=viewByAuthor;')
        html.append('    setupControlEvents();')
        html.append('  }')
        
        # 原版的viewByAddr函數（簡化版）  
        html.append('  function viewByAddr(){')
        html.append('    let s="<h4 style=\\"color:#00ff41;\\">依 Address</h4>";')
        html.append('    const bag={};')
        html.append('    evts.forEach(e => {')
        html.append('      (e.diffs || []).forEach(d => {')
        html.append('        const k = (d.address || "") + "@" + (d.worksheet || "");')
        html.append('        (bag[k] || (bag[k] = [])).push({')
        html.append('          evt: e.event_number, ts: e.timestamp, author: e.author,')
        html.append('          worksheet: d.worksheet, address: d.address, old: d.old_value,')
        html.append('          new: d.new_value, old_formula: d.old_formula, new_formula: d.new_formula')
        html.append('        });')
        html.append('      });')
        html.append('    });')
        html.append('    Object.keys(bag).sort().forEach(k=>{ ')
        html.append('      const parts = k.split("@");')
        html.append('      s+="<div style=\\"margin:6px 0;padding:6px;border:1px solid #00ff41;color:#00ff41;\\"><div><b>地址: "+parts[0]+"</b> <span class=\\"muted\\">(工作表: "+parts[1]+")</span></div>";')
        html.append('      s+="<table style=\\"margin-top:4px;border:1px solid #00ff41;background:#000;\\" class=\\"diff-table\\"><thead><tr>";')
        html.append('      s+="<th>事件#</th><th>時間</th><th>作者</th><th>原始值</th><th>變更後值</th><th>原始公式</th><th>變更後公式</th></tr></thead><tbody>";')
        html.append('      bag[k].forEach(r=>{ s+="<tr><td>"+(r.evt||"")+"</td><td>"+r.ts+"</td><td>"+(r.author||"")+"</td><td>"+formatFormula(r.old)+"</td><td>"+formatFormula(r.new)+"</td><td class=\\"formula-cell\\">"+formatFormula(r.old_formula)+"</td><td class=\\"formula-cell\\">"+formatFormula(r.new_formula)+"</td></tr>"; });')
        html.append('      s+="</tbody></table></div>";')
        html.append('    });')
        html.append('    fileView.innerHTML=html+s;')
        html.append('    document.getElementById("byTime").onclick=viewByTime;')
        html.append('    document.getElementById("byAddr").onclick=viewByAddr;')
        html.append('    document.getElementById("byAuthor").onclick=viewByAuthor;')
        html.append('    setupControlEvents();')
        html.append('  }')
        
        # 原版的viewByAuthor函數（簡化版）
        html.append('  function viewByAuthor(){')
        html.append('    let s="<h4 style=\\"color:#00ff41;\\">依作者</h4>";')
        html.append('    const authorBag = {};')
        html.append('    evts.forEach(e => {')
        html.append('      const author = e.author || "未知";')
        html.append('      if (!authorBag[author]) authorBag[author] = [];')
        html.append('      authorBag[author].push(e);')
        html.append('    });')
        html.append('    Object.keys(authorBag).sort().forEach(author => {')
        html.append('      s += "<div style=\\"margin:10px 0;padding:10px;border:1px solid #00ff41;color:#00ff41;\\"><h4>" + author + "</h4>";')
        html.append('      authorBag[author].forEach(e => {')
        html.append('        s += "<div style=\\"margin:6px 0;padding:6px;border:1px solid #003300;\\">";')
        html.append('        s += "<div><b>事件#" + (e.event_number || "") + "</b> | " + e.timestamp + " | 變更數 " + (e.changes || "") + "</div>";')
        html.append('        const diffs = e.diffs || [];')
        html.append('        if(diffs.length) {')
        html.append('          s += "<table style=\\"margin-top:4px;border:1px solid #00ff41;background:#000;\\" class=\\"diff-table\\"><thead><tr>";')
        html.append('          s += "<th>時間</th><th>工作表</th><th>位置</th><th>原始值</th><th>變更後值</th></tr></thead><tbody>";')
        html.append('          diffs.forEach(d => { s += "<tr><td>"+e.timestamp+"</td><td>"+(d.worksheet||"")+"</td><td>"+(d.address||"")+"</td><td>"+formatFormula(d.old_value)+"</td><td>"+formatFormula(d.new_value)+"</td></tr>"; });')
        html.append('          s += "</tbody></table>";')
        html.append('        }')
        html.append('        s += "</div>";')
        html.append('      });')
        html.append('      s += "</div>";')
        html.append('    });')
        html.append('    fileView.innerHTML = html + s;')
        html.append('    document.getElementById("byTime").onclick = viewByTime;')
        html.append('    document.getElementById("byAddr").onclick = viewByAddr;')
        html.append('    document.getElementById("byAuthor").onclick = viewByAuthor;')
        html.append('    setupControlEvents();')
        html.append('  }')
        
        # 設置控制事件
        html.append('  function setupControlEvents() {')
        html.append('    const checkboxes = document.querySelectorAll(".col-toggle");')
        html.append('    checkboxes.forEach(checkbox => {')
        html.append('      checkbox.addEventListener("change", function() {')
        html.append('        const colClass = "col-" + this.getAttribute("data-col");')
        html.append('        const display = this.checked ? "" : "none";')
        html.append('        document.querySelectorAll("." + colClass).forEach(cell => {')
        html.append('          cell.style.display = display;')
        html.append('        });')
        html.append('      });')
        html.append('    });')
        html.append('  }')
        
        # 初始化
        html.append('  viewByTime();')
        html.append('  } catch (e) {')
        html.append('    console.error("渲染檔案視圖時出錯:", e);')
        html.append('  }')
        html.append('}')
        
        # 頁面初始化
        html.append("function initializePage() {")
        html.append("  document.querySelectorAll('a.file-link').forEach(a=>{ ")
        html.append("    a.addEventListener('click', function(ev) {")
        html.append("      ev.preventDefault();") 
        html.append("      renderFileView(this.getAttribute('data-file'));")
        html.append("    });")
        html.append("  });")
        html.append("}")
        html.append("")
        html.append("if (document.readyState === 'loading') {")
        html.append("  document.addEventListener('DOMContentLoaded', function() {")
        html.append("    initializePage();")
        html.append("    updateGlowEffect();")
        html.append("  });")
        html.append("} else {")
        html.append("  initializePage();")
        html.append("  updateGlowEffect();")
        html.append("}")
        try:
            os.makedirs(os.path.dirname(TIMELINE_HTML_V6), exist_ok=True)
            with open(TIMELINE_HTML_V6, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html))
            print(f"[timeline-v6] HTML 成功寫入: {TIMELINE_HTML_V6}")
        except Exception as e:
            print(f"[timeline-v6] 寫入 HTML 失敗: {e}")
    except Exception:
        pass