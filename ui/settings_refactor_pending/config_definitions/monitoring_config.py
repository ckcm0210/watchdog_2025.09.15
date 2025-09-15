# 監控範圍與啟動掃描配置定義
# Monitoring and Startup Scan Configuration Definitions

print("[DEBUG-STEP2.2] 載入監控配置定義，配置項數量: 9")

# 監控範圍與啟動掃描相關的配置項
MONITORING_CONFIG = [
    # 監控與檔案類型
    {
        'key': 'WATCH_FOLDERS',
        'priority': 1,
        'label': '監控資料夾（可多個）',
        'help': '指定需要監控的資料夾（可多個）。支援網路磁碟。系統會遞迴監控子資料夾。可用下方「新增資料夾」按鈕加入。',
        'type': 'paths',
        'path_kind': 'dir',
    },
    {
        'key': 'SUPPORTED_EXTS',
        'label': '檔案類型 (Excel 為 .xlsx,.xlsm)',
        'help': '設定需要監控的檔案副檔名，逗號分隔（例如 .xlsx,.xlsm）。會自動正規化為小寫並加上點號。',
        'type': 'text',
    },
    {
        'key': 'MANUAL_BASELINE_TARGET',
        'priority': 3,
        'label': '手動建立基準線的檔案清單',
        'help': '啟動時會先對這些檔案建立基準線（可多個）。使用「新增檔案」加入。',
        'type': 'paths',
        'path_kind': 'file',
    },
    {
        'key': 'MONITOR_ONLY_FOLDERS',
        'priority': 4,
        'label': '只監控變更的根目錄（Issue B）',
        'help': '在此清單內的根目錄底下，第一次偵測到 Excel 檔變更時，系統只會記錄路徑、最後修改時間與最後儲存者，並建立首次基準線；下一次變更才進入普通比較流程。若某子資料夾同時在 WATCH_FOLDERS，則以 WATCH_FOLDERS 的即時比較為優先。',
        'type': 'paths',
        'path_kind': 'dir',
    },
    {
        'key': 'WATCH_EXCLUDE_FOLDERS',
        'priority': 2,
        'label': '即時比較的排除清單（子資料夾）',
        'help': '若在 WATCH_FOLDERS 中，這些子資料夾會被排除，不進行即時比較。',
        'type': 'paths',
        'path_kind': 'dir',
    },
    {
        'key': 'MONITOR_ONLY_EXCLUDE_FOLDERS',
        'priority': 5,
        'label': '只監控變更的排除清單（子資料夾）',
        'help': '若在 MONITOR_ONLY_FOLDERS 中，這些子資料夾會被排除，不進行 monitor-only。',
        'type': 'paths',
        'path_kind': 'dir',
    },
    {
        'key': 'SCAN_TARGET_FOLDERS',
        'priority': 3,
        'label': '啟動掃描的指定目錄（可多個）',
        'help': '啟動掃描時建立基準線的目錄清單。預設會以 WATCH_FOLDERS 全部為準；你可在此列表移除不想掃描的目錄或自行新增。',
        'type': 'paths',
        'path_kind': 'dir',
    },
    {
        'key': 'AUTO_SYNC_SCAN_TARGETS',
        'priority': 3,
        'label': '啟動掃描清單自動同步監控資料夾',
        'help': '開啟後，「啟動掃描的指定目錄」會自動與「監控資料夾」一致；關閉可手動指定子集。',
        'type': 'bool',
    },
    {
        'key': 'SCAN_ALL_MODE',
        'priority': 3,
        'label': '啟動時掃描所有 Excel 並建立基準線',
        'help': '開啟後，啟動時會掃描 WATCH_FOLDERS 內所有支援檔案並建立初始基準線。關閉可縮短大型磁碟啟動時間。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
MONITORING_KEYS = [
    'WATCH_FOLDERS', 'WATCH_EXCLUDE_FOLDERS', 'MONITOR_ONLY_FOLDERS', 'MONITOR_ONLY_EXCLUDE_FOLDERS',
    'SCAN_TARGET_FOLDERS', 'AUTO_SYNC_SCAN_TARGETS', 'SCAN_ALL_MODE', 'SUPPORTED_EXTS', 'MANUAL_BASELINE_TARGET'
]

print(f"[DEBUG-STEP2.2] 監控配置定義載入完成，包含配置項: {MONITORING_KEYS}")