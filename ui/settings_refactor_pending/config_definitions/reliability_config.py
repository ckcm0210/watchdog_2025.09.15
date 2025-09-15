# 可靠性與資源配置定義
# Reliability and Resource Configuration Definitions

print("[DEBUG-STEP2.2] 載入可靠性與資源配置定義，配置項數量: 10")

# 可靠性與資源相關的配置項
RELIABILITY_CONFIG = [
    # 超時設定
    {
        'key': 'ENABLE_TIMEOUT',
        'label': '啟用檔案處理超時保護',
        'help': '當單一檔案處理超過 FILE_TIMEOUT_SECONDS 時中止該檔處理，避免長時間卡住。',
        'type': 'bool',
    },
    {
        'key': 'FILE_TIMEOUT_SECONDS',
        'label': '單檔超時秒數',
        'help': '超過此秒數仍未完成讀取/比較會視為超時。',
        'type': 'int',
    },
    
    # 記憶體監控
    {
        'key': 'ENABLE_MEMORY_MONITOR',
        'label': '啟用記憶體監控',
        'help': '當行程記憶體超過限制時自動觸發垃圾回收並告警。',
        'type': 'bool',
    },
    {
        'key': 'MEMORY_LIMIT_MB',
        'label': '記憶體上限 (MB)',
        'help': '超過此數值時會嘗試釋放記憶體並提示。',
        'type': 'int',
    },
    {
        'key': 'MEMORY_CHECK_INTERVAL',
        'label': '記憶體檢查間隔（秒）',
        'help': '記憶體使用量檢查的間隔時間。',
        'type': 'int',
    },
    
    # 進度恢復
    {
        'key': 'ENABLE_RESUME',
        'label': '啟用進度恢復',
        'help': '建立大量基準線時，將進度寫入 RESUME_LOG_FILE，重新啟動可續傳。',
        'type': 'bool',
    },
    {
        'key': 'RESUME_LOG_FILE',
        'priority': 4,
        'label': '進度紀錄檔路徑',
        'help': '保存基準線建立進度的檔案路徑，建議放在本機磁碟。',
        'type': 'path',
        'path_kind': 'save_file',
    },
    
    # 白名單設定
    {
        'key': 'WHITELIST_USERS',
        'label': '使用者白名單 (每行一個)',
        'help': '在白名單內的使用者修改可選擇不顯示或單獨記錄。',
        'type': 'multiline',
    },
    {
        'key': 'LOG_WHITELIST_USER_CHANGE',
        'label': '記錄白名單使用者變更',
        'help': '啟用後，白名單使用者的變更也會寫入記錄。',
        'type': 'bool',
    },
    {
        'key': 'FORCE_BASELINE_ON_FIRST_SEEN',
        'label': '首次遇見即強制建立基準線 (每行一個關鍵字)',
        'help': '支援關鍵字或部分路徑比對。若檔案路徑包含其一，第一次掃描或偵測到時即建立基準線。',
        'type': 'multiline',
    },
]

# 配置項鍵名列表（用於驗證）
RELIABILITY_KEYS = [
    'ENABLE_TIMEOUT', 'FILE_TIMEOUT_SECONDS', 'ENABLE_MEMORY_MONITOR', 'MEMORY_LIMIT_MB', 'MEMORY_CHECK_INTERVAL',
    'ENABLE_RESUME', 'RESUME_LOG_FILE', 'WHITELIST_USERS', 'LOG_WHITELIST_USER_CHANGE', 'FORCE_BASELINE_ON_FIRST_SEEN'
]

print(f"[DEBUG-STEP2.2] 可靠性與資源配置定義載入完成，包含配置項: {RELIABILITY_KEYS}")