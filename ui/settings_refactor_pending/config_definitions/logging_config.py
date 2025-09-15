# 日誌與輸出配置定義
# Logging and Output Configuration Definitions

print("[DEBUG-STEP2.2] 載入日誌與輸出配置定義，配置項數量: 13")

# 日誌與輸出相關的配置項
LOGGING_CONFIG = [
    # 基本日誌設定
    {
        'key': 'LOG_FOLDER',
        'priority': 3,
        'label': '日誌資料夾',
        'help': '設定日誌檔案的存放位置。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'LOG_FILE_DATE',
        'label': '日誌檔案包含日期',
        'help': '在日誌檔案名稱中包含日期。',
        'type': 'bool',
    },
    {
        'key': 'CSV_LOG_FILE',
        'priority': 3,
        'label': 'CSV 日誌檔案路徑',
        'help': '變更記錄的 CSV 檔案路徑。',
        'type': 'path',
        'path_kind': 'save_file',
    },
    
    # 控制台文字日誌
    {
        'key': 'CONSOLE_TEXT_LOG_ENABLED',
        'label': '啟用控制台文字日誌',
        'help': '將控制台輸出同時寫入文字檔案。',
        'type': 'bool',
    },
    {
        'key': 'CONSOLE_TEXT_LOG_FILE',
        'priority': 3,
        'label': '控制台文字日誌檔案',
        'help': '控制台輸出的文字日誌檔案路徑。',
        'type': 'path',
        'path_kind': 'save_file',
    },
    {
        'key': 'CONSOLE_TEXT_LOG_ONLY_CHANGES',
        'label': '控制台日誌僅記錄變更',
        'help': '控制台文字日誌只記錄有變更的事件。',
        'type': 'bool',
    },
    
    # 去重和操作日誌
    {
        'key': 'LOG_DEDUP_WINDOW_SEC',
        'label': 'CSV 去重時間窗（秒）',
        'help': '在此秒數內，相同檔案＋工作表＋相同內容的變更只記錄一次至 CSV（避免短時間重覆記錄同一批變更）。',
        'type': 'int',
    },
    {
        'key': 'ENABLE_OPS_LOG',
        'label': '啟用操作日誌',
        'help': '記錄系統操作和錯誤的詳細日誌。',
        'type': 'bool',
    },
    {
        'key': 'IGNORE_LOG_FOLDER',
        'label': '忽略日誌資料夾變更',
        'help': '避免監控日誌資料夾本身的檔案變更。',
        'type': 'bool',
    },
    
    # 每事件控制台
    {
        'key': 'PER_EVENT_CONSOLE_ENABLED',
        'label': '啟用每事件控制台輸出',
        'help': '為每個變更事件生成獨立的控制台輸出檔案。',
        'type': 'bool',
    },
    {
        'key': 'PER_EVENT_CONSOLE_DIR',
        'priority': 3,
        'label': '每事件控制台輸出目錄',
        'help': '每事件控制台輸出檔案的存放目錄。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'PER_EVENT_CONSOLE_MAX_CHANGES',
        'label': '每事件控制台最大變更數',
        'help': '每個事件控制台輸出的最大變更數量限制。',
        'type': 'int',
    },
    {
        'key': 'PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS',
        'label': '每事件控制台包含所有工作表',
        'help': '在每事件控制台輸出中包含所有工作表的變更。',
        'type': 'bool',
    },
    {
        'key': 'PER_EVENT_CONSOLE_ADD_EVENT_ID',
        'label': '每事件控制台添加事件ID',
        'help': '在每事件控制台輸出中添加唯一的事件識別碼。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
LOGGING_KEYS = [
    'LOG_FOLDER', 'LOG_FILE_DATE', 'CSV_LOG_FILE', 'CONSOLE_TEXT_LOG_ENABLED', 'CONSOLE_TEXT_LOG_FILE', 'LOG_DEDUP_WINDOW_SEC',
    'ENABLE_OPS_LOG', 'IGNORE_LOG_FOLDER', 'CONSOLE_TEXT_LOG_ONLY_CHANGES',
    'PER_EVENT_CONSOLE_ENABLED', 'PER_EVENT_CONSOLE_DIR', 'PER_EVENT_CONSOLE_MAX_CHANGES', 'PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS', 'PER_EVENT_CONSOLE_ADD_EVENT_ID'
]

print(f"[DEBUG-STEP2.2] 日誌與輸出配置定義載入完成，包含配置項: {LOGGING_KEYS}")