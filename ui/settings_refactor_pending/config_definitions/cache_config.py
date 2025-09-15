# 複製與快取配置定義
# Copy and Cache Configuration Definitions

print("[DEBUG-STEP2.2] 載入複製與快取配置定義，配置項數量: 14")

# 複製與快取相關的配置項
CACHE_CONFIG = [
    # 基本快取設定
    {
        'key': 'USE_LOCAL_CACHE',
        'label': '啟用本地快取',
        'help': '讀取網路檔前先複製到本地快取，提高穩定性與速度。',
        'type': 'bool',
    },
    {
        'key': 'STRICT_NO_ORIGINAL_READ',
        'label': '嚴格禁止讀取原始檔案',
        'help': '啟用後，絕不直接讀取原始檔案，一律先複製到快取再讀取。',
        'type': 'bool',
    },
    {
        'key': 'CACHE_FOLDER',
        'priority': 3,
        'label': '本地快取資料夾',
        'help': '設定本地快取位置。需具備讀寫權限。可透過「瀏覽」選擇資料夾。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'IGNORE_CACHE_FOLDER',
        'label': '忽略快取資料夾內的檔案變更',
        'help': '避免監控快取資料夾本身的檔案變更事件。',
        'type': 'bool',
    },
    
    # 複製重試設定
    {
        'key': 'COPY_RETRY_COUNT',
        'label': '複製重試次數',
        'help': '複製失敗時的重試次數。',
        'type': 'int',
    },
    {
        'key': 'COPY_RETRY_BACKOFF_SEC',
        'label': '複製重試間隔 (秒)',
        'help': '每次重試之間的等待時間。',
        'type': 'int',
    },
    {
        'key': 'COPY_CHUNK_SIZE_MB',
        'label': '複製區塊大小 (MB)',
        'help': '分塊複製時每個區塊的大小。',
        'type': 'int',
    },
    
    # 複製穩定性檢查
    {
        'key': 'COPY_STABILITY_CHECKS',
        'label': '複製穩定性檢查次數',
        'help': '複製後檢查檔案穩定性的次數。',
        'type': 'int',
    },
    {
        'key': 'COPY_STABILITY_INTERVAL_SEC',
        'label': '穩定性檢查間隔 (秒)',
        'help': '每次穩定性檢查之間的間隔。',
        'type': 'int',
    },
    {
        'key': 'COPY_STABILITY_MAX_WAIT_SEC',
        'label': '穩定性檢查最大等待 (秒)',
        'help': '穩定性檢查的最大等待時間。',
        'type': 'int',
    },
    {
        'key': 'COPY_POST_SLEEP_SEC',
        'label': '複製後等待時間 (秒)',
        'help': '複製完成後的額外等待時間。',
        'type': 'int',
    },
    
    # 複製引擎設定
    {
        'key': 'COPY_ENGINE',
        'label': '複製引擎（Windows）',
        'help': '選擇複製檔案所使用的引擎：python（內建）、powershell（Copy-Item）、robocopy（穩定、對網路良好）。',
        'type': 'choice',
        'choices': ['python','powershell','robocopy']
    },
    {
        'key': 'PREFER_SUBPROCESS_FOR_XLSM',
        'label': '對 .xlsm 一律使用子程序複製',
        'help': '對含巨集的 .xlsm 檔案優先使用系統子程序（robocopy/PowerShell）複製，以降低鎖檔風險。',
        'type': 'bool',
    },
    {
        'key': 'SUBPROCESS_ENGINE_FOR_XLSM',
        'label': '.xlsm 子程序複製引擎',
        'help': '當啟用「對 .xlsm 一律使用子程序複製」時，選擇 robocopy 或 PowerShell 作為引擎。',
        'type': 'choice',
        'choices': ['robocopy','powershell']
    },
    {
        'key': 'ROBOCOPY_ENABLE_Z',
        'label': 'Robocopy 啟用重新啟動模式',
        'help': '啟用 robocopy 的 /Z 參數，支援中斷重傳。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
CACHE_KEYS = [
    'USE_LOCAL_CACHE', 'STRICT_NO_ORIGINAL_READ', 'CACHE_FOLDER', 'IGNORE_CACHE_FOLDER', 'COPY_RETRY_COUNT', 'COPY_RETRY_BACKOFF_SEC',
    'COPY_CHUNK_SIZE_MB', 'COPY_STABILITY_CHECKS', 'COPY_STABILITY_INTERVAL_SEC', 'COPY_STABILITY_MAX_WAIT_SEC', 'COPY_POST_SLEEP_SEC',
    'COPY_ENGINE', 'PREFER_SUBPROCESS_FOR_XLSM', 'SUBPROCESS_ENGINE_FOR_XLSM', 'ROBOCOPY_ENABLE_Z'
]

print(f"[DEBUG-STEP2.2] 複製與快取配置定義載入完成，包含配置項: {CACHE_KEYS}")