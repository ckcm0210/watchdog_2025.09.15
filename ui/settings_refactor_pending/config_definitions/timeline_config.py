# 時間線 / Timeline 配置定義
# Timeline Configuration Definitions

print("[DEBUG-STEP2.2] 載入時間線配置定義，配置項數量: 8")

# 時間線相關的配置項
TIMELINE_CONFIG = [
    # 基本時間線設定
    {
        'key': 'TIMELINE_ENABLED',
        'label': '啟用時間線功能',
        'help': '啟用時間線 HTML 輸出和事件追蹤功能。',
        'type': 'bool',
    },
    {
        'key': 'TIMELINE_OUTPUT_DIR',
        'priority': 3,
        'label': '時間線輸出目錄',
        'help': '時間線 HTML 檔案的輸出目錄。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'TIMELINE_MAX_EVENTS',
        'label': '時間線最大事件數',
        'help': '時間線中保留的最大事件數量。',
        'type': 'int',
    },
    
    # 時間線顯示設定
    {
        'key': 'TIMELINE_AUTO_REFRESH',
        'label': '時間線自動刷新',
        'help': '啟用時間線頁面的自動刷新功能。',
        'type': 'bool',
    },
    {
        'key': 'TIMELINE_REFRESH_INTERVAL',
        'label': '時間線刷新間隔（秒）',
        'help': '時間線頁面自動刷新的間隔時間。',
        'type': 'int',
    },
    {
        'key': 'TIMELINE_SHOW_DETAILS',
        'label': '時間線顯示詳細資訊',
        'help': '在時間線中顯示變更的詳細資訊。',
        'type': 'bool',
    },
    
    # 時間線過濾設定
    {
        'key': 'TIMELINE_FILTER_BY_USER',
        'label': '時間線按使用者過濾',
        'help': '啟用按使用者過濾時間線事件的功能。',
        'type': 'bool',
    },
    {
        'key': 'TIMELINE_FILTER_BY_FILE',
        'label': '時間線按檔案過濾',
        'help': '啟用按檔案過濾時間線事件的功能。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
TIMELINE_KEYS = [
    'TIMELINE_ENABLED', 'TIMELINE_OUTPUT_DIR', 'TIMELINE_MAX_EVENTS', 'TIMELINE_AUTO_REFRESH', 'TIMELINE_REFRESH_INTERVAL',
    'TIMELINE_SHOW_DETAILS', 'TIMELINE_FILTER_BY_USER', 'TIMELINE_FILTER_BY_FILE'
]

print(f"[DEBUG-STEP2.2] 時間線配置定義載入完成，包含配置項: {TIMELINE_KEYS}")