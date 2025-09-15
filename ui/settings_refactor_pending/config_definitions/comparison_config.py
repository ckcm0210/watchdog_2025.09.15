# 比較與變更檢測配置定義
# Comparison and Change Detection Configuration Definitions

print("[DEBUG-STEP2.2] 載入比較與變更檢測配置定義，配置項數量: 13")

# 比較與變更檢測相關的配置項
COMPARISON_CONFIG = [
    # 比較模式
    {
        'key': 'FORMULA_ONLY_MODE',
        'label': '只關注公式變更',
        'help': '啟用後，僅比較與顯示公式的變更。',
        'type': 'bool',
    },
    {
        'key': 'TRACK_DIRECT_VALUE_CHANGES',
        'label': '追蹤直接值變更',
        'help': '若某格為輸入文字/數字（非公式），其值變更會被記錄。',
        'type': 'bool',
    },
    {
        'key': 'TRACK_FORMULA_CHANGES',
        'label': '追蹤公式變更',
        'help': '只要儲存格的公式字串有改動（例如 =A1+B1 → =A1+B2）便會記錄。',
        'type': 'bool',
    },
    
    # 外部參照處理
    {
        'key': 'ENABLE_FORMULA_VALUE_CHECK',
        'label': '外部參照：值不變視為無變更',
        'help': '當外部參照公式的字串因刷新而有差異，但其儲存的數值（cached value）沒有改變時，忽略該變更（避免假警報）。只對快取副本進行 read-only 讀取。',
        'type': 'bool',
    },
    {
        'key': 'MAX_FORMULA_VALUE_CELLS',
        'label': '值比對的最大公式格數（跨表合計）',
        'help': '為了效能，只對前 N 個含公式的儲存格查詢其 cached value。超過此數量時跳過值比對（仍會比較公式字串）。',
        'type': 'int',
    },
    {
        'key': 'TRACK_EXTERNAL_REFERENCES',
        'label': '追蹤外部參照更新',
        'help': '公式不變、但外部連結刷新導致結果變更時記錄。',
        'type': 'bool',
    },
    {
        'key': 'IGNORE_INDIRECT_CHANGES',
        'label': '忽略間接影響變更',
        'help': '公式不變、僅因工作簿內其他儲存格改動導致結果變化時忽略。',
        'type': 'bool',
    },
    
    # 顯示設定
    {
        'key': 'MAX_CHANGES_TO_DISPLAY',
        'label': '畫面顯示變更上限 (0=不限制)',
        'help': '限制 console 表格一次展示的變更數，有助於大檔案閱讀。',
        'type': 'int',
    },
    {
        'key': 'AUTO_UPDATE_BASELINE_AFTER_COMPARE',
        'label': '比較後自動更新基準線',
        'help': '每次比較完成後自動將當前狀態設為新的基準線。',
        'type': 'bool',
    },
    
    # Console 表格顯示
    {
        'key': 'ADDRESS_COL_WIDTH',
        'label': 'Address 欄寬（0=自動）',
        'help': '設定 Address 欄位寬度（字元）。0 代表依據本次變更中最長的地址自動估算（6~16）。',
        'type': 'int',
    },
    {
        'key': 'CONSOLE_TERM_WIDTH_OVERRIDE',
        'label': 'Console 表格總寬度（0=自動偵測）',
        'help': '覆蓋 Console 表格的總寬度（字元）。0 代表自動偵測終端寬度或使用 120。',
        'type': 'int',
    },
    {
        'key': 'HEADER_INFO_SECOND_LINE',
        'label': '標題資訊顯示第二行',
        'help': '在比較結果標題中顯示額外的檔案資訊。',
        'type': 'bool',
    },
    {
        'key': 'DIFF_HIGHLIGHT_ENABLED',
        'label': '啟用差異高亮顯示',
        'help': '在控制台中高亮顯示變更的部分。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
COMPARISON_KEYS = [
    'FORMULA_ONLY_MODE', 'TRACK_DIRECT_VALUE_CHANGES', 'TRACK_FORMULA_CHANGES', 'ENABLE_FORMULA_VALUE_CHECK', 'MAX_FORMULA_VALUE_CELLS',
    'TRACK_EXTERNAL_REFERENCES', 'IGNORE_INDIRECT_CHANGES', 'MAX_CHANGES_TO_DISPLAY', 'AUTO_UPDATE_BASELINE_AFTER_COMPARE',
    'ADDRESS_COL_WIDTH', 'CONSOLE_TERM_WIDTH_OVERRIDE', 'HEADER_INFO_SECOND_LINE', 'DIFF_HIGHLIGHT_ENABLED'
]

print(f"[DEBUG-STEP2.2] 比較與變更檢測配置定義載入完成，包含配置項: {COMPARISON_KEYS}")