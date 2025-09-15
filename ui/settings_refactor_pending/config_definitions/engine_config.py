# 值/公式讀取引擎配置定義
# Value/Formula Reading Engine Configuration Definitions

print("[DEBUG-STEP2.2] 載入值/公式讀取引擎配置定義，配置項數量: 6")

# 值/公式讀取引擎相關的配置項
ENGINE_CONFIG = [
    # 主要引擎設定
    {
        'key': 'VALUE_ENGINE',
        'label': '值讀取引擎（polars/polars_xml/xml/pandas）',
        'help': 'polars：以 xlsx2csv+Polars 快速讀取各格結果值（預設；需安裝 polars/xlsx2csv）。xml：直接解析 .xlsx 的 XML 結構以取 cached 值。若未安裝 polars/xlsx2csv，會自動回退 xml。',
        'type': 'choice',
        'choices': ['polars','polars_xml','xml','pandas']
    },
    {
        'key': 'FORMULA_ENGINE',
        'label': '公式讀取引擎（xml/openpyxl）',
        'help': 'xml：直接解析 .xlsx 的 XML 結構以取公式（快速）。openpyxl：使用 openpyxl 庫讀取公式（較慢但相容性佳）。',
        'type': 'choice',
        'choices': ['xml','openpyxl']
    },
    
    # 引擎降級設定
    {
        'key': 'ENGINE_FALLBACK_ENABLED',
        'label': '啟用引擎自動降級',
        'help': '當主要引擎失敗時，自動嘗試使用備用引擎。',
        'type': 'bool',
    },
    {
        'key': 'ENGINE_FALLBACK_ORDER',
        'label': '引擎降級順序',
        'help': '引擎失敗時的降級順序，以逗號分隔。',
        'type': 'text',
    },
    
    # 引擎性能設定
    {
        'key': 'ENGINE_TIMEOUT_SECONDS',
        'label': '引擎處理超時（秒）',
        'help': '單個引擎處理檔案的最大時間限制。',
        'type': 'int',
    },
    {
        'key': 'ENGINE_RETRY_COUNT',
        'label': '引擎重試次數',
        'help': '引擎處理失敗時的重試次數。',
        'type': 'int',
    },
]

# 配置項鍵名列表（用於驗證）
ENGINE_KEYS = [
    'VALUE_ENGINE', 'FORMULA_ENGINE', 'ENGINE_FALLBACK_ENABLED', 'ENGINE_FALLBACK_ORDER', 'ENGINE_TIMEOUT_SECONDS', 'ENGINE_RETRY_COUNT'
]

print(f"[DEBUG-STEP2.2] 值/公式讀取引擎配置定義載入完成，包含配置項: {ENGINE_KEYS}")