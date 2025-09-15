"""
Excel 差異報告生成器
生成獨立的HTML報告，顯示Excel檔案的變更差異
"""
import os
import json
from datetime import datetime
import config.settings as settings


def generate_diff_report(old_data, new_data, file_path, output_dir=None):
    """
    生成HTML差異報告
    
    Args:
        old_data: 舊版本的Excel數據 (dict)
        new_data: 新版本的Excel數據 (dict) 
        file_path: Excel檔案路徑
        output_dir: 輸出目錄，如果為None則使用設定檔配置
    
    Returns:
        str: 生成的HTML檔案路徑
    """
    if output_dir is None:
        output_dir = getattr(settings, 'DIFF_REPORT_DIR', None)
        if output_dir is None:
            output_dir = os.path.join(getattr(settings, 'LOG_FOLDER', '.'), 'diff_reports')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 準備差異數據
    diff_data = prepare_diff_data(old_data, new_data)
    
    # 生成HTML內容
    html_content = generate_html_content(diff_data, file_path)
    
    # 生成檔案名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"diff_report_{os.path.splitext(os.path.basename(file_path))[0]}_{timestamp}.html"
    output_path = os.path.join(output_dir, filename)
    
    # 寫入檔案
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[diff-report] HTML差異報告已生成: {output_path}")
    return output_path


def prepare_diff_data(old_data, new_data):
    """
    準備差異數據，轉換為前端需要的格式
    """
    diff_list = []
    
    # 獲取所有工作表
    all_sheets = set(old_data.keys()) | set(new_data.keys())
    
    for sheet_name in all_sheets:
        old_sheet = old_data.get(sheet_name, {})
        new_sheet = new_data.get(sheet_name, {})
        
        # 獲取所有儲存格地址
        all_addresses = set(old_sheet.keys()) | set(new_sheet.keys())
        
        for address in all_addresses:
            old_cell = old_sheet.get(address, {})
            new_cell = new_sheet.get(address, {})
            
            # 檢查是否有變更
            if old_cell != new_cell:
                # 提取值和公式
                old_val = extract_display_value(old_cell)
                new_val = extract_display_value(new_cell)
                old_formula = old_cell.get('formula', '')
                new_formula = new_cell.get('formula', '')
                
                diff_item = {
                    'sheet': sheet_name,
                    'address': address,
                    'oldVal': old_val,
                    'newVal': new_val,
                    'oldFormula': old_formula,
                    'newFormula': new_formula
                }
                
                diff_list.append(diff_item)
    
    # 按工作表和地址排序
    diff_list.sort(key=lambda x: (x['sheet'], natural_sort_key(x['address'])))
    
    return diff_list


def extract_display_value(cell):
    """
    提取儲存格的顯示值
    優先順序: formula > cached_value > value
    """
    if not cell:
        return ""
    
    # 如果有公式，顯示公式
    formula = cell.get('formula')
    if formula:
        return f"={formula}" if not str(formula).startswith('=') else str(formula)
    
    # 否則顯示值
    value = cell.get('cached_value')
    if value is not None:
        return str(value)
    
    value = cell.get('value')
    if value is not None:
        return str(value)
    
    return ""


def natural_sort_key(address):
    """
    自然排序鍵，用於正確排序地址如 A1, A2, A10
    """
    import re
    match = re.match(r"^([A-Za-z]+)(\d+)$", str(address))
    if match:
        col, row = match.groups()
        return (col.upper(), int(row))
    return (str(address), 0)


def calculate_value_difference(old_val, new_val):
    """
    計算值差異
    - 如果都是數字，計算數值差異
    - 如果是文字，生成文字差異視覺化
    """
    # 嘗試轉換為數字
    try:
        old_num = float(old_val) if old_val and old_val != "" else 0
        new_num = float(new_val) if new_val and new_val != "" else 0
        diff = new_num - old_num
        if diff > 0:
            return f"+{diff}"
        elif diff < 0:
            return str(diff)
        else:
            return "0"
    except (ValueError, TypeError):
        # 不是數字，生成文字差異
        return generate_text_diff_html(str(old_val), str(new_val))


def generate_text_diff_html(old_text, new_text):
    """
    生成文字差異的HTML，類似公式差異但用於文字
    """
    if old_text == new_text:
        return '<span class="no-change">無變化</span>'
    
    # 簡單的單詞級別差異
    old_words = old_text.split()
    new_words = new_text.split()
    
    # 如果差異太大，使用並列顯示
    if len(old_words) == 0 or len(new_words) == 0 or abs(len(old_words) - len(new_words)) > max(len(old_words), len(new_words)) * 0.5:
        return f'<span class="diff-deleted">{old_text}</span> <span class="diff-added">{new_text}</span>'
    
    # 否則嘗試單詞級別的差異
    result = []
    max_len = max(len(old_words), len(new_words))
    
    for i in range(max_len):
        old_word = old_words[i] if i < len(old_words) else ""
        new_word = new_words[i] if i < len(new_words) else ""
        
        if old_word == new_word:
            if old_word:
                result.append(old_word)
        else:
            if old_word:
                result.append(f'<span class="diff-deleted">{old_word}</span>')
            if new_word:
                result.append(f'<span class="diff-added">{new_word}</span>')
    
    return ' '.join(result)


def generate_block_level_formula_diff(old_formula, new_formula):
    """
    生成區塊級別的公式差異，而不是字符級別
    """
    if old_formula == new_formula:
        return '<span class="no-change">無變化</span>'
    
    # 檢查是否是完全不同的公式類型
    old_func = extract_main_function(old_formula)
    new_func = extract_main_function(new_formula)
    
    if old_func != new_func:
        # 不同函數，使用並列顯示
        return f'<span class="diff-deleted">{old_formula}</span><br><span class="diff-added">{new_formula}</span>'
    
    # 相同函數，嘗試參數級別的差異
    old_parts = parse_formula_parts(old_formula)
    new_parts = parse_formula_parts(new_formula)
    
    if len(old_parts) != len(new_parts):
        # 參數數量不同，使用並列顯示
        return f'<span class="diff-deleted">{old_formula}</span><br><span class="diff-added">{new_formula}</span>'
    
    # 參數級別比較
    result_parts = []
    has_changes = False
    
    for i, (old_part, new_part) in enumerate(zip(old_parts, new_parts)):
        if old_part == new_part:
            result_parts.append(old_part)
        else:
            has_changes = True
            result_parts.append(f'<span class="diff-deleted">{old_part}</span><span class="diff-added">{new_part}</span>')
    
    if has_changes:
        return ''.join(result_parts)
    else:
        return old_formula


def extract_main_function(formula):
    """
    提取公式的主要函數名稱
    """
    import re
    if not formula:
        return ""
    
    formula_str = str(formula)
    if formula_str.startswith('='):
        formula_str = formula_str[1:]
    
    match = re.match(r'^([A-Z_]+)\s*\(', formula_str, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""


def parse_formula_parts(formula):
    """
    簡單解析公式的各個部分
    這是一個簡化版本，可以根據需要改進
    """
    if not formula:
        return []
    
    # 移除開頭的等號
    formula_str = str(formula)
    if formula_str.startswith('='):
        formula_str = formula_str[1:]
    
    # 簡單的分割方式，可以改進
    import re
    
    # 找到函數名和括號
    func_match = re.match(r'^([A-Z_]+)\s*\((.*)\)\s*$', formula_str, re.IGNORECASE)
    if func_match:
        func_name = func_match.group(1)
        params = func_match.group(2)
        
        # 簡單分割參數（不處理嵌套括號）
        param_parts = [p.strip() for p in params.split(',')]
        
        return [f"{func_name}("] + [f"{p}," if i < len(param_parts)-1 else p for i, p in enumerate(param_parts)] + [")"]
    
    return [formula_str]


def generate_html_content(diff_data, file_path):
    """
    生成完整的HTML內容
    """
    # 轉換數據為JSON
    json_data = json.dumps(diff_data, ensure_ascii=False)
    
    # 檔案資訊
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_template = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>Excel 差異報告 - {filename}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1400px;
            margin: 20px auto;
            padding: 0 15px;
        }}
        h1 {{ text-align: center; color: #2c3e50; }}
        .file-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            table-layout: fixed;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
            word-wrap: break-word;
        }}
        th {{ 
            background-color: #f8f8f8; 
            font-weight: bold;
            position: sticky;
            top: 0;
        }}
        
        col.sheet {{ width: 8%; }}
        col.address {{ width: 8%; }}
        col.old-val, col.new-val {{ width: 22%; }}
        col.value-diff {{ width: 15%; }}
        col.visualize {{ width: 25%; }}

        .diff-deleted {{
            background-color: #ffebe9;
            text-decoration: line-through;
            color: #c00;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .diff-added {{
            background-color: #e6ffed;
            color: #080;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .no-change {{
            color: #666;
            font-style: italic;
        }}
        .mono {{
            font-family: Consolas, 'Courier New', monospace;
        }}
        .visualize-cell {{
            font-family: Consolas, 'Courier New', monospace;
            background: #f9f9f9;
            font-size: 0.9em;
        }}
        .value-diff-cell {{
            font-family: Consolas, 'Courier New', monospace;
            text-align: center;
            font-weight: bold;
        }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .zero {{ color: #6c757d; }}
        
        .summary {{
            background: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }}
    </style>
</head>
<body>

    <h1>Excel 差異報告</h1>
    
    <div class="file-info">
        <strong>檔案:</strong> {filename}<br>
        <strong>報告生成時間:</strong> {timestamp}<br>
        <strong>檔案路徑:</strong> {file_path}
    </div>
    
    <div class="summary" id="summary">
        <strong>變更摘要:</strong> <span id="change-count">載入中...</span>
    </div>

    <table>
        <colgroup>
            <col class="sheet">
            <col class="address">
            <col class="old-val">
            <col class="new-val">
            <col class="value-diff">
            <col class="visualize">
        </colgroup>
        <thead>
            <tr>
                <th>工作表</th>
                <th>儲存格</th>
                <th>舊值 / 舊公式</th>
                <th>新值 / 新公式</th>
                <th>值差異</th>
                <th>視覺化差異</th>
            </tr>
        </thead>
        <tbody id="report-body">
            <!-- 數據將由JavaScript填入 -->
        </tbody>
    </table>

    <script>
        // 差異數據
        const diffData = {json_data};

        // 計算值差異
        function calculateValueDifference(oldVal, newVal) {{
            // 移除公式前綴進行數值比較
            let oldNum = oldVal;
            let newNum = newVal;
            
            // 如果是公式，嘗試提取數值部分（簡化處理）
            if (typeof oldVal === 'string' && oldVal.startsWith('=')) {{
                oldNum = oldVal;
            }}
            if (typeof newVal === 'string' && newVal.startsWith('=')) {{
                newNum = newVal;
            }}
            
            // 嘗試轉換為數字
            const oldNumber = parseFloat(oldNum);
            const newNumber = parseFloat(newNum);
            
            if (!isNaN(oldNumber) && !isNaN(newNumber)) {{
                const diff = newNumber - oldNumber;
                if (diff > 0) {{
                    return `<span class="positive">+${{diff.toLocaleString()}}</span>`;
                }} else if (diff < 0) {{
                    return `<span class="negative">${{diff.toLocaleString()}}</span>`;
                }} else {{
                    return `<span class="zero">0</span>`;
                }}
            }}
            
            // 不是數字，生成文字差異
            return generateTextDiff(String(oldVal), String(newVal));
        }}

        // 生成文字差異
        function generateTextDiff(oldText, newText) {{
            if (oldText === newText) {{
                return '<span class="no-change">無變化</span>';
            }}
            
            // 簡單的文字差異顯示
            if (oldText.length === 0) {{
                return `<span class="diff-added">${{newText}}</span>`;
            }}
            if (newText.length === 0) {{
                return `<span class="diff-deleted">${{oldText}}</span>`;
            }}
            
            // 如果差異很大，使用並列顯示
            const similarity = calculateSimilarity(oldText, newText);
            if (similarity < 0.3) {{
                return `<span class="diff-deleted">${{oldText}}</span><br><span class="diff-added">${{newText}}</span>`;
            }}
            
            // 否則嘗試單詞級別差異
            return generateWordLevelDiff(oldText, newText);
        }}

        // 計算文字相似度
        function calculateSimilarity(str1, str2) {{
            const longer = str1.length > str2.length ? str1 : str2;
            const shorter = str1.length > str2.length ? str2 : str1;
            
            if (longer.length === 0) {{
                return 1.0;
            }}
            
            const editDistance = levenshteinDistance(longer, shorter);
            return (longer.length - editDistance) / longer.length;
        }}

        // 計算編輯距離
        function levenshteinDistance(str1, str2) {{
            const matrix = [];
            
            for (let i = 0; i <= str2.length; i++) {{
                matrix[i] = [i];
            }}
            
            for (let j = 0; j <= str1.length; j++) {{
                matrix[0][j] = j;
            }}
            
            for (let i = 1; i <= str2.length; i++) {{
                for (let j = 1; j <= str1.length; j++) {{
                    if (str2.charAt(i - 1) === str1.charAt(j - 1)) {{
                        matrix[i][j] = matrix[i - 1][j - 1];
                    }} else {{
                        matrix[i][j] = Math.min(
                            matrix[i - 1][j - 1] + 1,
                            matrix[i][j - 1] + 1,
                            matrix[i - 1][j] + 1
                        );
                    }}
                }}
            }}
            
            return matrix[str2.length][str1.length];
        }}

        // 生成單詞級別差異
        function generateWordLevelDiff(oldText, newText) {{
            const oldWords = oldText.split(/\\s+/);
            const newWords = newText.split(/\\s+/);
            
            const result = [];
            const maxLen = Math.max(oldWords.length, newWords.length);
            
            for (let i = 0; i < maxLen; i++) {{
                const oldWord = i < oldWords.length ? oldWords[i] : '';
                const newWord = i < newWords.length ? newWords[i] : '';
                
                if (oldWord === newWord && oldWord !== '') {{
                    result.push(oldWord);
                }} else {{
                    if (oldWord !== '') {{
                        result.push(`<span class="diff-deleted">${{oldWord}}</span>`);
                    }}
                    if (newWord !== '') {{
                        result.push(`<span class="diff-added">${{newWord}}</span>`);
                    }}
                }}
            }}
            
            return result.join(' ');
        }}

        // 生成區塊級別公式差異
        function generateBlockLevelFormulaDiff(oldVal, newVal) {{
            if (oldVal === newVal) {{
                return '<span class="no-change">無變化</span>';
            }}
            
            const oldIsFormula = String(oldVal).startsWith('=');
            const newIsFormula = String(newVal).startsWith('=');
            
            // 如果一個是公式一個不是，或者是完全不同的公式類型
            if (oldIsFormula !== newIsFormula || 
                (oldIsFormula && newIsFormula && getMainFunction(oldVal) !== getMainFunction(newVal))) {{
                return `<span class="diff-deleted">${{oldVal}}</span><br><span class="diff-added">${{newVal}}</span>`;
            }}
            
            // 相同類型，嘗試更細緻的比較
            if (oldIsFormula && newIsFormula) {{
                return generateFormulaParameterDiff(oldVal, newVal);
            }}
            
            // 都不是公式，使用文字差異
            return generateTextDiff(String(oldVal), String(newVal));
        }}

        // 提取主要函數名稱
        function getMainFunction(formula) {{
            const match = String(formula).match(/^=\\s*([A-Z_]+)\\s*\\(/i);
            return match ? match[1].toUpperCase() : '';
        }}

        // 生成公式參數差異
        function generateFormulaParameterDiff(oldFormula, newFormula) {{
            // 簡化處理：如果公式太複雜，直接並列顯示
            if (String(oldFormula).length > 100 || String(newFormula).length > 100) {{
                return `<span class="diff-deleted">${{oldFormula}}</span><br><span class="diff-added">${{newFormula}}</span>`;
            }}
            
            // 嘗試參數級別比較
            const oldParams = extractParameters(oldFormula);
            const newParams = extractParameters(newFormula);
            
            if (oldParams.length !== newParams.length) {{
                return `<span class="diff-deleted">${{oldFormula}}</span><br><span class="diff-added">${{newFormula}}</span>`;
            }}
            
            // 參數級別比較
            let hasChanges = false;
            const resultParts = [];
            
            const funcName = getMainFunction(oldFormula);
            resultParts.push(`=${{funcName}}(`);
            
            for (let i = 0; i < oldParams.length; i++) {{
                if (i > 0) resultParts.push(', ');
                
                if (oldParams[i] === newParams[i]) {{
                    resultParts.push(oldParams[i]);
                }} else {{
                    hasChanges = true;
                    resultParts.push(`<span class="diff-deleted">${{oldParams[i]}}</span><span class="diff-added">${{newParams[i]}}</span>`);
                }}
            }}
            
            resultParts.push(')');
            
            return hasChanges ? resultParts.join('') : oldFormula;
        }}

        // 提取公式參數（簡化版本）
        function extractParameters(formula) {{
            const match = String(formula).match(/^=\\s*[A-Z_]+\\s*\\((.*)\\)\\s*$/i);
            if (!match) return [];
            
            const paramStr = match[1];
            // 簡單分割，不處理嵌套括號
            return paramStr.split(',').map(p => p.trim());
        }}

        // 頁面初始化
        window.onload = function() {{
            const tbody = document.getElementById('report-body');
            const summary = document.getElementById('change-count');
            
            summary.textContent = `共 ${{diffData.length}} 項變更`;
            
            diffData.forEach((item, index) => {{
                const tr = document.createElement('tr');
                
                const valueDiffHtml = calculateValueDifference(item.oldVal, item.newVal);
                const visualDiffHtml = generateBlockLevelFormulaDiff(item.oldVal, item.newVal);
                
                tr.innerHTML = `
                    <td>${{item.sheet}}</td>
                    <td class="mono">${{item.address}}</td>
                    <td class="mono">${{item.oldVal}}</td>
                    <td class="mono">${{item.newVal}}</td>
                    <td class="value-diff-cell">${{valueDiffHtml}}</td>
                    <td class="visualize-cell">${{visualDiffHtml}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }};
    </script>

</body>
</html>"""

    return html_template