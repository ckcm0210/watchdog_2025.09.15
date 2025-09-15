# 輪巡與事件控制配置定義
# Polling and Event Control Configuration Definitions

print("[DEBUG-STEP2.2] 載入輪巡配置定義，配置項數量: 11")

# 輪巡與事件控制相關的配置項
POLLING_CONFIG = [
    # 防抖動
    {
        'key': 'DEBOUNCE_INTERVAL_SEC',
        'label': '防抖動間隔 (秒)',
        'help': '相同檔案在短時間內多次事件，會合併為一次。',
        'type': 'int',
    },
    
    # 輪詢大小分界和間隔
    {
        'key': 'POLLING_SIZE_THRESHOLD_MB',
        'label': '輪詢大小分界 (MB)',
        'help': '小於此大小的檔案採用較密集的輪詢間隔；大於則採用較稀疏的間隔。',
        'type': 'int',
    },
    {
        'key': 'DENSE_POLLING_INTERVAL_SEC',
        'label': '密集輪詢間隔 (秒)',
        'help': '適用於較小檔案的輪詢頻率。',
        'type': 'int',
    },
    {
        'key': 'DENSE_POLLING_DURATION_SEC',
        'label': '密集輪詢總時長 (秒)',
        'help': '沒有進一步變更時，密集輪詢會在總時長用盡後停止。',
        'type': 'int',
    },
    {
        'key': 'SPARSE_POLLING_INTERVAL_SEC',
        'label': '稀疏輪詢間隔 (秒)',
        'help': '適用於較大檔案的輪詢頻率。',
        'type': 'int',
    },
    {
        'key': 'SPARSE_POLLING_DURATION_SEC',
        'label': '稀疏輪詢總時長 (秒)',
        'help': '如需使用舊版 watcher 的稀疏輪詢策略可參考 legacy；現版本用自適應穩定檢查。',
        'type': 'int',
    },
    
    # 快速跳過和容差
    {
        'key': 'QUICK_SKIP_BY_STAT',
        'label': '快速跳過：mtime/size 未變時不讀取',
        'help': '啟用後，若來源檔案的修改時間與大小與基準線一致（含容差），直接判定無變更，跳過複製與讀取內容。',
        'type': 'bool',
    },
    {
        'key': 'MTIME_TOLERANCE_SEC',
        'label': 'mtime 容差（秒）',
        'help': '快速跳過時允許的修改時間容差（秒，可輸入小數）。',
        'type': 'text',
    },
    
    # 暫存鎖檔處理
    {
        'key': 'SKIP_WHEN_TEMP_LOCK_PRESENT',
        'label': '偵測暫存鎖檔 (~$) 時延後觸碰',
        'help': '當偵測到 Office 暫存鎖檔（~$開頭）存在時，延後複製與比較以避開 Excel 保存尾段。',
        'type': 'bool',
    },
    
    # 穩定檢查和冷靜期 (從 config/settings.py 補充)
    {
        'key': 'POLLING_STABLE_CHECKS',
        'label': '輪巡穩定檢查次數',
        'help': '輪巡：連續多少次「無變化」才算穩定。',
        'type': 'int',
    },
    {
        'key': 'POLLING_COOLDOWN_SEC',
        'label': '輪巡冷靜期 (秒)',
        'help': '每檔案成功比較後的冷靜期（秒）。',
        'type': 'int',
    },
]

# 配置項鍵名列表（用於驗證）
POLLING_KEYS = [
    'DEBOUNCE_INTERVAL_SEC', 'POLLING_SIZE_THRESHOLD_MB', 'DENSE_POLLING_INTERVAL_SEC', 'DENSE_POLLING_DURATION_SEC',
    'SPARSE_POLLING_INTERVAL_SEC', 'SPARSE_POLLING_DURATION_SEC', 'QUICK_SKIP_BY_STAT', 'MTIME_TOLERANCE_SEC',
    'SKIP_WHEN_TEMP_LOCK_PRESENT', 'POLLING_STABLE_CHECKS', 'POLLING_COOLDOWN_SEC'
]

print(f"[DEBUG-STEP2.2] 輪巡配置定義載入完成，包含配置項: {POLLING_KEYS}")