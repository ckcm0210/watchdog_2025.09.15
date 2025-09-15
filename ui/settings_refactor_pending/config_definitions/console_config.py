# Console 與 UI 配置定義
# Console and UI Configuration Definitions

print("[DEBUG-STEP2.2] 載入 Console 與 UI 配置定義，配置項數量: 11")

# Console 與 UI 相關的配置項
CONSOLE_CONFIG = [
    # 基本 Console 設定
    {
        'key': 'ENABLE_BLACK_CONSOLE',
        'label': '啟用黑色 Console 視窗',
        'help': '額外顯示一個即時輸出視窗。',
        'type': 'bool',
    },
    {
        'key': 'CONSOLE_POPUP_ON_COMPARISON',
        'label': '偵測到比較時彈出視窗',
        'help': '有比較輸出時自動帶到前景。',
        'type': 'bool',
    },
    {
        'key': 'CONSOLE_ALWAYS_ON_TOP',
        'label': '視窗保持最上層',
        'help': '讓 Console 視窗始終置頂。',
        'type': 'bool',
    },
    {
        'key': 'CONSOLE_TEMP_TOPMOST_DURATION',
        'label': '臨時置頂秒數',
        'help': '收到比較輸出時，視窗臨時置頂的時間。',
        'type': 'int',
    },
    {
        'key': 'CONSOLE_INITIAL_TOPMOST_DURATION',
        'label': '啟動初期置頂秒數',
        'help': '啟動後短暫置頂以避免被其他視窗遮住。',
        'type': 'int',
    },
    
    # Console 顯示設定
    {
        'key': 'CONSOLE_COLORIZE_TYPES',
        'label': '啟用 Console 類型顏色化',
        'help': '在 Console 中使用不同顏色顯示不同類型的變更。',
        'type': 'bool',
    },
    {
        'key': 'CONSOLE_FORMULA_COLOR',
        'label': 'Console 公式顏色',
        'help': '公式變更在 Console 中的顯示顏色。',
        'type': 'text',
    },
    {
        'key': 'CONSOLE_VALUE_COLOR',
        'label': 'Console 值變更顏色',
        'help': '值變更在 Console 中的顯示顏色。',
        'type': 'text',
    },
    
    # Console 字體設定
    {
        'key': 'CONSOLE_FONT_FAMILY',
        'label': 'Console 字體家族',
        'help': 'Console 視窗使用的字體家族。',
        'type': 'text',
    },
    {
        'key': 'CONSOLE_FONT_SIZE',
        'label': 'Console 字體大小',
        'help': 'Console 視窗的字體大小。',
        'type': 'int',
    },
    {
        'key': 'CONSOLE_WRAP_NONE',
        'label': 'Console 不自動換行',
        'help': '禁用 Console 視窗的自動換行功能。',
        'type': 'bool',
    },
]

# 配置項鍵名列表（用於驗證）
CONSOLE_KEYS = [
    'ENABLE_BLACK_CONSOLE', 'CONSOLE_POPUP_ON_COMPARISON', 'CONSOLE_ALWAYS_ON_TOP', 'CONSOLE_TEMP_TOPMOST_DURATION', 'CONSOLE_INITIAL_TOPMOST_DURATION',
    'CONSOLE_COLORIZE_TYPES', 'CONSOLE_FORMULA_COLOR', 'CONSOLE_VALUE_COLOR', 'CONSOLE_FONT_FAMILY', 'CONSOLE_FONT_SIZE', 'CONSOLE_WRAP_NONE'
]

print(f"[DEBUG-STEP2.2] Console 與 UI 配置定義載入完成，包含配置項: {CONSOLE_KEYS}")