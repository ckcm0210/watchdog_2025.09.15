# 基準線與壓縮/歸檔配置定義
# Baseline and Compression/Archive Configuration Definitions

print("[DEBUG-STEP2.2] 載入基準線與壓縮/歸檔配置定義，配置項數量: 8")

# 基準線與壓縮/歸檔相關的配置項
BASELINE_CONFIG = [
    # 壓縮格式設定
    {
        'key': 'DEFAULT_COMPRESSION_FORMAT',
        'label': '預設壓縮格式',
        'help': '基準線檔案的預設壓縮格式。',
        'type': 'choice',
        'choices': ['lz4', 'zstd', 'gzip', 'none']
    },
    {
        'key': 'LZ4_COMPRESSION_LEVEL',
        'label': 'LZ4 壓縮等級',
        'help': 'LZ4 壓縮的等級設定（1-12，數字越高壓縮率越好但速度越慢）。',
        'type': 'int',
    },
    {
        'key': 'ZSTD_COMPRESSION_LEVEL',
        'label': 'ZSTD 壓縮等級',
        'help': 'ZSTD 壓縮的等級設定（1-22，數字越高壓縮率越好但速度越慢）。',
        'type': 'int',
    },
    {
        'key': 'GZIP_COMPRESSION_LEVEL',
        'label': 'GZIP 壓縮等級',
        'help': 'GZIP 壓縮的等級設定（1-9，數字越高壓縮率越好但速度越慢）。',
        'type': 'int',
    },
    
    # 歸檔模式設定
    {
        'key': 'ENABLE_ARCHIVE_MODE',
        'label': '啟用歸檔模式',
        'help': '啟用後，舊的基準線檔案會被歸檔而不是直接覆蓋。',
        'type': 'bool',
    },
    {
        'key': 'ARCHIVE_AFTER_DAYS',
        'label': '歸檔天數',
        'help': '基準線檔案超過指定天數後會被歸檔。',
        'type': 'int',
    },
    {
        'key': 'ARCHIVE_COMPRESSION_FORMAT',
        'label': '歸檔壓縮格式',
        'help': '歸檔檔案使用的壓縮格式。',
        'type': 'choice',
        'choices': ['lz4', 'zstd', 'gzip', 'none']
    },
    
    # 壓縮統計
    {
        'key': 'SHOW_COMPRESSION_STATS',
        'label': '顯示壓縮統計資訊',
        'help': '在處理過程中顯示壓縮率和處理時間等統計資訊。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
BASELINE_KEYS = [
    'DEFAULT_COMPRESSION_FORMAT', 'LZ4_COMPRESSION_LEVEL', 'ZSTD_COMPRESSION_LEVEL', 'GZIP_COMPRESSION_LEVEL',
    'ENABLE_ARCHIVE_MODE', 'ARCHIVE_AFTER_DAYS', 'ARCHIVE_COMPRESSION_FORMAT', 'SHOW_COMPRESSION_STATS'
]

print(f"[DEBUG-STEP2.2] 基準線與壓縮/歸檔配置定義載入完成，包含配置項: {BASELINE_KEYS}")