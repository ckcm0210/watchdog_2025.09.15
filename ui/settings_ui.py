"""
Startup Settings UI (Tkinter)
- Provide detailed Chinese descriptions for each parameter.
- Load defaults from config.settings and config.runtime (JSON)
- Save to runtime JSON and apply to process.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, json, sys
from typing import Dict, Any
import config.settings as settings
import config.runtime as runtime
from config.runtime import load_runtime_settings, save_runtime_settings, apply_to_settings

PARAMS_SPEC = [
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

    # 快取與暫存
    {
        'key': 'USE_LOCAL_CACHE',
        'label': '啟用本地快取',
        'help': '讀取網路檔前先複製到本地快取，提高穩定性與速度。',
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

    # 超時/記憶體/恢復
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

    # 監視邏輯/防抖
    {
        'key': 'DEBOUNCE_INTERVAL_SEC',
        'label': '防抖動間隔 (秒)',
        'help': '相同檔案在短時間內多次事件，會合併為一次。',
        'type': 'int',
    },

    # 比較邏輯
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
    {
        'key': 'MAX_CHANGES_TO_DISPLAY',
        'label': '畫面顯示變更上限 (0=不限制)',
        'help': '限制 console 表格一次展示的變更數，有助於大檔案閱讀。',
        'type': 'int',
    },
    # Console 比較表格顯示
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
    # 值/公式引擎設定
    {
        'key': 'ENABLE_HEARTBEAT',
        'label': '啟用 Heartbeat（心跳）',
        'help': '每隔指定秒數輸出一次 [heartbeat] alive，用於確認程式仍在運作。',
        'type': 'bool',
    },
    {
        'key': 'HEARTBEAT_INTERVAL_SEC',
        'label': 'Heartbeat 間隔（秒）',
        'help': '心跳訊息輸出的間隔秒數。',
        'type': 'int',
    },
    {
        'key': 'ENABLE_OBSERVER_HEALTHCHECK',
        'label': '啟用 Observer 健康檢查',
        'help': '定期檢查 Watchdog 觀察者是否運作中，並判斷是否長時間無事件。',
        'type': 'bool',
    },
    {
        'key': 'OBSERVER_HEALTHCHECK_INTERVAL_SEC',
        'label': '健康檢查間隔（秒）',
        'help': '每隔幾秒檢查一次觀察者狀態（預設 5 秒）。',
        'type': 'int',
    },
    {
        'key': 'OBSERVER_STALL_THRESHOLD_SEC',
        'label': '無事件判定閾值（秒）',
        'help': '若超過此秒數仍沒有任何事件，視為停滯（預設 20 秒）。',
        'type': 'int',
    },
    {
        'key': 'OBSERVER_PROBE_ENABLED',
        'label': '啟用 Probe 驗證事件流',
        'help': '當判定停滯時，會在監控目錄寫入/刪除臨時檔案以驗證事件是否可到達。',
        'type': 'bool',
    },
    {
        'key': 'OBSERVER_PROBE_TIMEOUT_SEC',
        'label': 'Probe 超時（秒）',
        'help': '驗證事件是否到達的等待時間（預設 3 秒）。',
        'type': 'int',
    },
    {
        'key': 'ENABLE_AUTO_RESTART_OBSERVER',
        'label': '異常自動重啟 Observer',
        'help': '當檢測到觀察者死亡或停滯時，自動重建並重新註冊監控。',
        'type': 'bool',
    },

    {
        'key': 'DEBUG_LEVEL',
        'label': 'Debug 等級（0/1/2/3）',
        'help': '0=關閉；1=基本（路由/queue/引擎選擇/map 提供數/複製簡要/timeline 概要）；2=詳盡（map 前 N 項、exec/rc 摘要、stdout/stderr 截斷）；3=非常詳盡（更多 keys、更長 stdout/stderr）。',
        'type': 'int',
    },
    {
        'key': 'DEBUG_WRAP_WIDTH',
        'label': 'Debug 換行寬度（0=沿用 Console）',
        'help': '用於 Debug 分行的顯示寬度。0 表示沿用 CONSOLE_TERM_WIDTH_OVERRIDE 或 120。',
        'type': 'int',
    },
    {
        'key': 'DEBUG_MAX_LIST_ITEMS',
        'label': '列表顯示上限（keys/項目）',
        'help': '控制 [map] keys 列表或其他清單的最大輸出項目數，避免屏幕爆量。',
        'type': 'int',
    },
    {
        'key': 'DEBUG_TRUNCATE_BYTES',
        'label': '外部命令輸出截斷（位元組）',
        'help': '限制 robocopy/PowerShell stdout/stderr 的截斷長度。',
        'type': 'int',
    },
    {
        'key': 'DEBUG_REPEAT_PREFIX_ON_WRAP',
        'label': '多行時每行重覆 prefix',
        'help': '多行輸出時，每行是否重覆 [prefix]（例如 [map]、[copy]）。',
        'type': 'bool',
    },
    {
        'key': 'DEBUG_TAG_EVENT_ID',
        'label': '在每行加事件/群組標籤',
        'help': '每行可加 [evt#XXXX] 或 [bk:baseline_key] 以標示此訊息屬於哪一組事件。',
        'type': 'bool',
    },

    {
        'key': 'MAX_CONCURRENT_COMPARES',
        'label': '最大並行比較數',
        'help': '同時允許執行的比較任務數量（建議 2~4）。',
        'type': 'int',
    },
    {
        'key': 'DEDUP_PENDING_EVENTS',
        'label': '事件去重（保留最新）',
        'help': '同一檔案短時間內多次事件，只保留最新的比較任務，避免重覆出表與資源消耗。',
        'type': 'bool',
    },
    {
        'key': 'IMMEDIATE_COMPARE_ON_FIRST_EVENT',
        'label': '首次即時比較',
        'help': '事件觸發時立即執行一次比較（保持體感）；其後交由佇列限制並行與去重。',
        'type': 'bool',
    },

    # XML 子進程隔離設定
    {
        'key': 'USE_XML_SUBPROCESS',
        'label': '啟用 XML 子進程隔離',
        'help': '將 XML 解析工作交由獨立子進程處理，避免崩潰影響主程式。推薦開啟以提升穩定性。',
        'type': 'bool',
    },
    {
        'key': 'XML_SUBPROCESS_MAX_WORKERS',
        'label': '子進程最大工作者數量',
        'help': '同時運行的子進程數量。建議保持 1 以避免資源競爭和提升穩定性。',
        'type': 'int',
        'min': 1,
        'max': 4,
    },
    {
        'key': 'XML_SUBPROCESS_TIMEOUT_SEC',
        'label': '子進程超時時間（秒）',
        'help': '子進程執行任務的最大等待時間。超時後會強制終止並啟動安全模式重試。建議 120 秒以處理大型檔案。',
        'type': 'int',
        'min': 30,
        'max': 300,
    },
    {
        'key': 'XML_SUBPROCESS_SAFE_RETRY',
        'label': '啟用安全模式重試',
        'help': '當正常模式失敗時，使用更保守的單線程設定重試。推薦開啟。',
        'type': 'bool',
    },

    {
        'key': 'VALUE_ENGINE',
        'label': '值讀取引擎（polars/polars_xml/xml/pandas）',
        'help': 'polars：以 xlsx2csv+Polars 快速讀取各格結果值（預設；需安裝 polars/xlsx2csv）。xml：直接解析 .xlsx 的 XML 結構以取 cached 值。若未安裝 polars/xlsx2csv，會自動回退 xml。',
        'type': 'choice',
        'choices': ['polars','polars_xml','xml','pandas']
    },
    {
        'key': 'FORMULA_ENGINE',
        'label': '公式讀取引擎（openpyxl/xml）',
        'help': '目前預設 openpyxl 讀取公式；未來可提供 xml 讀公式以進一步提速。',
        'type': 'choice',
        'choices': ['openpyxl']
    },
    {
        'key': 'CSV_PERSIST',
        'label': 'CSV 落地保存（polars 模式）',
        'help': '預設 False 使用記憶體 BytesIO，不落地 CSV；打開後會將每個 worksheet 的 CSV 落到快取資料夾以利除錯，請注意空間使用。',
        'type': 'bool',
    },
    {
        'key': 'MAX_SHEET_WORKERS',
        'label': '最大並發 Sheet 讀取數',
        'help': '允許同時處理多個 worksheet 的數目（建議 4 或 CPU 核心數）。併發可顯著縮短大型檔案讀取時間。',
        'type': 'int',
    },
    {
        'key': 'HEADER_INFO_SECOND_LINE',
        'label': '將標頭時間/作者資訊移至下一行',
        'help': '開啟後，第一行標頭只顯示 Baseline/Current 字樣；時間與作者資訊會換行顯示，讓內容欄位更寬。',
        'type': 'bool',
    },
    {
       'key': 'DIFF_HIGHLIGHT_ENABLED',
       'label': '高亮顯示 Baseline/Current 內容差異',
       'help': '將左右內容的相同前綴淡化，僅用 «…» 標示差異區段，讓你更快看出變化之處。',
       'type': 'bool',
   },
   # Console 顏色設定（formula/value）
   {
       'key': 'CONSOLE_COLORIZE_TYPES',
       'label': '啟用 Type 著色（formula/value）',
       'help': '在黑色 Console 中以不同顏色顯示 formula/value 行（文字檔不著色）。',
       'type': 'bool',
   },
   {
       'key': 'CONSOLE_FORMULA_COLOR',
       'label': 'Formula 行顏色',
       'help': '顏色選項（含自定 Hex）。',
       'type': 'choice',
       'choices': ['#00bcd4','#00acc1','#26c6da','#4dd0e1','#80deea','#009688','Custom'],
   },
   {
       'key': 'CONSOLE_VALUE_COLOR',
       'label': 'Value 行顏色',
       'help': '顏色選項（含自定 Hex）。',
       'type': 'choice',
       'choices': ['#ffd54f','#ffc107','#ffca28','#ffe082','#fff176','#fdd835','Custom'],
   },
   # Console 字型與換行
   {
       'key': 'CONSOLE_FONT_FAMILY',
       'label': 'Console 字型（Font Family）',
       'help': '跟 cmd 一樣可用 Consolas；如要更佳 CJK 對齊，建議 Noto Sans Mono CJK 或 Sarasa Mono TC。',
       'type': 'choice',
       'choices': ['Consolas','Lucida Console','Cascadia Mono','Noto Sans Mono CJK','Sarasa Mono TC','Custom']
   },
   {
       'key': 'CONSOLE_FONT_SIZE',
       'label': 'Console 字型大小',
       'help': '字型大小（pt）。',
       'type': 'int',
   },
   {
       'key': 'CONSOLE_WRAP_NONE',
       'label': '停用自動換行（由表格自行換行）',
       'help': '啟用後，Tkinter 不會自動換行，避免破壞 CJK 對齊。',
       'type': 'bool',
   },
   {
       'key': 'AUTO_UPDATE_BASELINE_AFTER_COMPARE',
        'label': '比較後自動更新基準線',
        'help': '當偵測到變更後，是否自動以「目前內容」更新成新的基準線。',
        'type': 'bool',
    },

    {
        'key': 'DISABLE_GIT_INTEGRATION',
        'label': '停用 Git 整合（歷史同步/提交/Viewer）',
        'help': '啟用後，不會將歷史快照同步到 excel_git_repo，也不會嘗試使用 GitPython 提交。Viewer 仍可開啟純 JSON 歷史檔案瀏覽，不需安裝 Git。',
        'type': 'bool',
    },
    # 壓縮/歸檔
    {
        'key': 'DEFAULT_COMPRESSION_FORMAT',
        'label': '基準線壓縮格式',
        'help': '選擇基準線儲存格式：lz4 (讀寫快), zstd (壓縮高), gzip (相容性)。',
        'type': 'choice',
        'choices': ['lz4','zstd','gzip']
    },
    {
        'key': 'LZ4_COMPRESSION_LEVEL',
        'label': 'LZ4 壓縮等級 (0-16)',
        'help': '速度最快，讀取幾乎不受影響。等級越高壓縮率越好但寫入較慢：0-3 非常快、壓縮較低；4-9 折衝；10-16 壓縮更高但明顯變慢。',
        'type': 'int',
    },
    {
        'key': 'ZSTD_COMPRESSION_LEVEL',
        'label': 'Zstd 壓縮等級 (1-22)',
        'help': '高壓縮比通用首選：1-3 偏速度；4-9 折衝（常用 3-6）；10-18 更高壓縮但寫入耗時；19-22 極致壓縮、CPU時間很長（僅限空間極度敏感）。',
        'type': 'int',
    },
    {
        'key': 'GZIP_COMPRESSION_LEVEL',
        'label': 'gzip 壓縮等級 (1-9)',
        'help': '兼容性最佳：1-3 較快、壓縮一般；4-6 折衝（6 常用）；7-9 壓縮略升但耗時顯著，除非相容性/可攜性為先。',
        'type': 'int',
    },
    {
        'key': 'ENABLE_ARCHIVE_MODE',
        'label': '啟用歸檔模式',
        'help': '基準線建立一段時間後可轉存為較高壓縮格式以節省空間。',
        'type': 'bool',
    },
    {
        'key': 'ARCHIVE_AFTER_DAYS',
        'label': '轉為歸檔的天數',
        'help': '建立後超過此天數的基準線將轉為歸檔格式。',
        'type': 'int',
    },
    {
        'key': 'ARCHIVE_COMPRESSION_FORMAT',
        'label': '歸檔壓縮格式',
        'help': '歸檔時使用的壓縮格式。',
        'type': 'choice',
        'choices': ['lz4','zstd','gzip']
    },
    {
        'key': 'SHOW_COMPRESSION_STATS',
        'label': '顯示壓縮統計',
        'help': '在儲存/讀取基準線時顯示壓縮比與耗時。',
        'type': 'bool',
    },
    {
        'key': 'SHOW_DEBUG_MESSAGES',
        'label': '顯示除錯訊息',
        'help': '輸出較詳細的內部流程訊息。',
        'type': 'bool',
    },

    # 日誌/輸出
    {
        'key': 'LOG_FOLDER',
        'priority': 5,
        'label': '日誌資料夾（CSV/日誌輸出）',
        'help': '記錄 CSV 與其他日誌的資料夾。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'LOG_FILE_DATE',
        'label': '日誌日期（唯讀）',
        'help': '用於組合 CSV_LOG_FILE 的日期字串。',
        'type': 'readonly',
    },
    {
        'key': 'CSV_LOG_FILE',
        'label': 'CSV 記錄檔（唯讀）',
        'help': '比較結果輸出的壓縮 CSV 檔路徑，從 LOG_FOLDER + 日期組合而來。',
        'type': 'readonly',
    },
    {
        'key': 'CONSOLE_TEXT_LOG_ENABLED',
        'label': '將 Console 輸出寫入文字檔',
        'help': '將所有 Console 訊息（含表格）追加寫入指定的文字檔（UTF-8）。可用於長期留存或排查。',
        'type': 'bool',
    },
    {
       'key': 'CONSOLE_TEXT_LOG_FILE',
       'label': 'Console 文字檔路徑',
       'help': '預設為 LOG_FOLDER/console_log_YYYYMMDD.txt（依據日誌日期）。你亦可自訂儲存位置。',
       'type': 'path',
       'path_kind': 'save_file',
   },
   {
      'key': 'CONSOLE_TEXT_LOG_ONLY_CHANGES',
      'label': 'Console 文字檔僅記錄變更（表格/橫幅）',
      'help': '開啟後，只會把比較表格、變更橫幅等關鍵訊息寫入文字檔；關閉則「逐行影印」所有 Console 輸出。',
      'type': 'bool',
  },
  # 單檔事件完整輸出
  {
      'key': 'PER_EVENT_CONSOLE_ENABLED',
      'label': '為每次檔案變更輸出一份完整 Console 檔',
      'help': '以檔案為單位，輸出完整詳版表格（不受畫面顯示上限限制）。',
      'type': 'bool',
  },
  {
      'key': 'PER_EVENT_CONSOLE_DIR',
      'label': '完整 Console 檔輸出目錄',
      'help': '預設為 LOG_FOLDER/console_details。',
      'type': 'path',
      'path_kind': 'select_folder',
  },
  {
      'key': 'PER_EVENT_CONSOLE_MAX_CHANGES',
      'label': '完整 Console 檔每檔最大記錄數（0=不限）',
      'help': '為避免極端大檔案輸出過大，可設上限；0 表示不限，全部輸出。',
      'type': 'int',
  },
  {
      'key': 'PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS',
      'label': '完整 Console 檔包含所有有變更工作表',
      'help': '啟用後，該檔案所有有變更的工作表都會寫入完整 Console 檔。',
      'type': 'bool',
  },
  {
      'key': 'PER_EVENT_CONSOLE_ADD_EVENT_ID',
      'label': '檔名包含事件編號（_evtN 後綴）',
      'help': '例：New Test File 21_Michael Cheng_20250901_224943_evt3.txt',
      'type': 'bool',
  },

    # 快速模式
    {
        'key': 'ENABLE_FAST_MODE',
        'label': '啟用快速模式',
        'help': '針對常見情境優化，可能略過部分詳細檢查以加速。',
        'type': 'bool',
    },

    # 重試/臨時複本
    {
        'key': 'MAX_RETRY',
        'label': '失敗重試次數',
        'help': '讀取或比較失敗時最多重試次數。',
        'type': 'int',
    },
    {
        'key': 'RETRY_INTERVAL_SEC',
        'label': '重試間隔 (秒)',
        'help': '兩次重試之間等待的秒數。',
        'type': 'int',
    },
    {
        'key': 'USE_TEMP_COPY',
        'label': '使用暫存複本',
        'help': '比較前先複製檔案到暫存位置以避免占用與鎖檔。',
        'type': 'bool',
    },

    # 進階／穩定性（複製與嚴格模式）
    {
        'key': 'STRICT_NO_ORIGINAL_READ',
        'label': '嚴格模式：永不開原始檔',
        'help': '啟用後，任何讀取都必須來自本地快取副本；若複製到快取最終失敗，會略過本次處理，絕不打開原始檔（避免鎖檔）。',
        'type': 'bool',
    },
    {
        'key': 'IGNORE_CACHE_FOLDER',
        'label': '忽略快取資料夾事件',
        'help': '忽略 CACHE_FOLDER 內所有檔案事件，避免快取本身引起的監控噪音（建議啟用）。',
        'type': 'bool',
    },
    {
        'key': 'COPY_RETRY_COUNT',
        'label': '複製重試次數',
        'help': '將來源檔案複製到本地快取時的最大重試次數。來源檔案正被儲存／網路不穩時可提高此值。',
        'type': 'int',
    },
    {
        'key': 'COPY_RETRY_BACKOFF_SEC',
        'label': '重試退避（秒）',
        'help': '兩次重試之間的等待秒數（可輸入小數）。會按嘗試次數逐步增加等待，例如 1.0 → 2.0 → 3.0 秒。',
        'type': 'text',
    },
    {
        'key': 'COPY_CHUNK_SIZE_MB',
        'label': '分塊複製大小 (MB)',
        'help': '以較小區塊逐段讀寫來源檔，可降低一次性長時間把持來源句柄的風險。0 表示關閉。',
        'type': 'int',
    },
    {
        'key': 'COPY_POST_SLEEP_SEC',
        'label': '複製完成後短暫等待（秒）',
        'help': '複製完成後等待短暫時間（可輸入小數）讓檔案系統穩定，避免隨後讀取時競態。',
        'type': 'text',
    },
    {
        'key': 'COPY_STABILITY_CHECKS',
        'label': '複製前穩定性檢查次數',
        'help': '開始複製前，連續 N 次檢查來源檔的修改時間（mtime）一致才開始複製。',
        'type': 'int',
    },
    {
        'key': 'COPY_STABILITY_INTERVAL_SEC',
        'label': '穩定性檢查間隔（秒）',
        'help': '兩次 mtime 穩定性檢查之間的等待秒數（可輸入小數）。',
        'type': 'text',
    },
    {
        'key': 'COPY_STABILITY_MAX_WAIT_SEC',
        'label': '穩定性檢查最大等待（秒）',
        'help': '最多等待多少秒來達到所需的穩定檢查次數；超時則本次複製跳過。',
        'type': 'text',
    },
    # Phase 1 新增：快速跳過與鎖檔判斷
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
    {
        'key': 'SKIP_WHEN_TEMP_LOCK_PRESENT',
        'label': '偵測暫存鎖檔 (~$) 時延後觸碰',
        'help': '當偵測到 Office 暫存鎖檔（~$開頭）存在時，延後複製與比較以避開 Excel 保存尾段。',
        'type': 'bool',
    },
    # Phase 2：複製引擎
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

    # 日誌／去重
    {
        'key': 'LOG_DEDUP_WINDOW_SEC',
        'label': 'CSV 去重時間窗（秒）',
        'help': '在此秒數內，相同檔案＋工作表＋相同內容的變更只記錄一次至 CSV（避免短時間重覆記錄同一批變更）。',
        'type': 'int',
    },

    # 白名單
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

    # 輪詢
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

    # Console 視窗
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
    
    # Index4 (指定作者匯出) 相關設定
    {
        'key': 'INDEX4_ENABLED',
        'label': '啟用 Index4 指定作者匯出',
        'help': '開啟後，會額外生成一個只包含指定作者的 Timeline（index4.html），可放到共享位置給其他人查看。',
        'type': 'bool',
    },
    {
        'key': 'INDEX4_OUTPUT_PATH',
        'label': 'Index4 輸出資料夾',
        'help': '指定 index4.html 要存放的位置（例如：網路共享資料夾、內網伺服器路徑等）。',
        'type': 'path',
        'path_kind': 'dir',
    },
    {
        'key': 'INDEX4_TARGET_AUTHORS',
        'label': '目標作者清單',
        'help': '指定要包含在 Index4 中的作者名稱。格式：\"作者1\", \"作者2\", \"作者3\"（用引號和逗號）。只有這些作者的變更會出現在 index4.html 中。',
        'type': 'text',
    },
]

class SettingsDialog(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Excel Watchdog 設定')
        self.geometry('900x700')
        self.grab_set()
        self._widgets: Dict[str, Any] = {}
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        # Load defaults: apply last runtime into settings first, then read from settings only
        try:
            _rt = load_runtime_settings()
            if _rt:
                apply_to_settings(_rt)
        except Exception:
            pass

        # Tabs (Notebook)
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True)

        # Helper: treat empty strings/lists/dicts as blank, but keep 0/False
        def _is_blank(v):
            if v is None:
                return True
            if isinstance(v, str) and v.strip() == '':
                return True
            if isinstance(v, (list, tuple, dict)) and len(v) == 0:
                return True
            return False

        # Build a dict for quick lookup
        _spec_by_key = {s['key']: s for s in PARAMS_SPEC}

        # Define tabs and contained keys
        TABS = [
            ('監控範圍與啟動掃描', [
                'WATCH_FOLDERS','WATCH_EXCLUDE_FOLDERS','MONITOR_ONLY_FOLDERS','MONITOR_ONLY_EXCLUDE_FOLDERS',
                'SCAN_TARGET_FOLDERS','AUTO_SYNC_SCAN_TARGETS','SCAN_ALL_MODE','SUPPORTED_EXTS','MANUAL_BASELINE_TARGET'
            ]),
            ('輪巡與事件控制', [
               'DEBOUNCE_INTERVAL_SEC','POLLING_SIZE_THRESHOLD_MB','DENSE_POLLING_INTERVAL_SEC','DENSE_POLLING_DURATION_SEC',
               'SPARSE_POLLING_INTERVAL_SEC','SPARSE_POLLING_DURATION_SEC','QUICK_SKIP_BY_STAT','MTIME_TOLERANCE_SEC',
               'SKIP_WHEN_TEMP_LOCK_PRESENT','POLLING_STABLE_CHECKS','POLLING_COOLDOWN_SEC',
               'MAX_CONCURRENT_COMPARES','DEDUP_PENDING_EVENTS','IMMEDIATE_COMPARE_ON_FIRST_EVENT',
               'USE_XML_SUBPROCESS','XML_SUBPROCESS_MAX_WORKERS','XML_SUBPROCESS_TIMEOUT_SEC','XML_SUBPROCESS_SAFE_RETRY'
           ]),
            ('複製與快取', [
                'USE_LOCAL_CACHE','STRICT_NO_ORIGINAL_READ','CACHE_FOLDER','IGNORE_CACHE_FOLDER','COPY_RETRY_COUNT','COPY_RETRY_BACKOFF_SEC',
                'COPY_CHUNK_SIZE_MB','COPY_STABILITY_CHECKS','COPY_STABILITY_INTERVAL_SEC','COPY_STABILITY_MAX_WAIT_SEC','COPY_POST_SLEEP_SEC',
                'COPY_ENGINE','PREFER_SUBPROCESS_FOR_XLSM','SUBPROCESS_ENGINE_FOR_XLSM','ROBOCOPY_ENABLE_Z'
            ]),
            ('比較與變更檢測', [
                'FORMULA_ONLY_MODE','TRACK_DIRECT_VALUE_CHANGES','TRACK_FORMULA_CHANGES','ENABLE_FORMULA_VALUE_CHECK','MAX_FORMULA_VALUE_CELLS',
                'TRACK_EXTERNAL_REFERENCES','IGNORE_INDIRECT_CHANGES','MAX_CHANGES_TO_DISPLAY','AUTO_UPDATE_BASELINE_AFTER_COMPARE',
                'ADDRESS_COL_WIDTH','CONSOLE_TERM_WIDTH_OVERRIDE','HEADER_INFO_SECOND_LINE','DIFF_HIGHLIGHT_ENABLED'
            ]),
            ('基準線與壓縮/歸檔', [
                'DEFAULT_COMPRESSION_FORMAT','LZ4_COMPRESSION_LEVEL','ZSTD_COMPRESSION_LEVEL','GZIP_COMPRESSION_LEVEL',
                'ENABLE_ARCHIVE_MODE','ARCHIVE_AFTER_DAYS','ARCHIVE_COMPRESSION_FORMAT','SHOW_COMPRESSION_STATS'
            ]),
            ('日誌與輸出', [
               'LOG_FOLDER','LOG_FILE_DATE','CSV_LOG_FILE','CONSOLE_TEXT_LOG_ENABLED','CONSOLE_TEXT_LOG_FILE','LOG_DEDUP_WINDOW_SEC',
               'ENABLE_OPS_LOG','IGNORE_LOG_FOLDER','CONSOLE_TEXT_LOG_ONLY_CHANGES',
               'PER_EVENT_CONSOLE_ENABLED','PER_EVENT_CONSOLE_DIR','PER_EVENT_CONSOLE_MAX_CHANGES','PER_EVENT_CONSOLE_INCLUDE_ALL_SHEETS','PER_EVENT_CONSOLE_ADD_EVENT_ID',
               'DEBUG_LEVEL','DEBUG_WRAP_WIDTH','DEBUG_MAX_LIST_ITEMS','DEBUG_TRUNCATE_BYTES','DEBUG_REPEAT_PREFIX_ON_WRAP','DEBUG_TAG_EVENT_ID'
           ]),
            ('Console 與 UI', [
                'ENABLE_BLACK_CONSOLE','CONSOLE_POPUP_ON_COMPARISON','CONSOLE_ALWAYS_ON_TOP','CONSOLE_TEMP_TOPMOST_DURATION','CONSOLE_INITIAL_TOPMOST_DURATION','CONSOLE_COLORIZE_TYPES','CONSOLE_FORMULA_COLOR','CONSOLE_VALUE_COLOR','CONSOLE_FONT_FAMILY','CONSOLE_FONT_SIZE','CONSOLE_WRAP_NONE'
            ]),
           ('值/公式讀取引擎', [
               'VALUE_ENGINE','FORMULA_ENGINE','CSV_PERSIST','MAX_SHEET_WORKERS'
           ]),
            ('時間線 / Timeline', [
               'UI_TIMELINE_DEFAULT_DAYS','UI_TIMELINE_PAGE_SIZE','UI_TIMELINE_MAX_PAGE_SIZE','UI_TIMELINE_WARN_DAYS',
               'UI_TIMELINE_GROUP_BY_BASEKEY','PATH_MAPPINGS','ENABLE_TIMELINE_SERVER','TIMELINE_SERVER_HOST','TIMELINE_SERVER_PORT','OPEN_TIMELINE_ON_START','DISABLE_GIT_INTEGRATION'
            ]),
            ('Index4 指定作者匯出', [
               'INDEX4_ENABLED', 'INDEX4_OUTPUT_PATH', 'INDEX4_TARGET_AUTHORS',
            ]),
            ('可靠性與資源', [
               'ENABLE_TIMEOUT','FILE_TIMEOUT_SECONDS','ENABLE_MEMORY_MONITOR','MEMORY_LIMIT_MB','ENABLE_RESUME','RESUME_LOG_FILE',
               'MAX_RETRY','RETRY_INTERVAL_SEC','WHITELIST_USERS','LOG_WHITELIST_USER_CHANGE','FORCE_BASELINE_ON_FIRST_SEEN','SHOW_DEBUG_MESSAGES',
               'ENABLE_HEARTBEAT','HEARTBEAT_INTERVAL_SEC',
               'ENABLE_OBSERVER_HEALTHCHECK','OBSERVER_HEALTHCHECK_INTERVAL_SEC','OBSERVER_STALL_THRESHOLD_SEC','OBSERVER_PROBE_ENABLED','OBSERVER_PROBE_TIMEOUT_SEC','ENABLE_AUTO_RESTART_OBSERVER'
           ]),
        ]

        # Helper to create a scrollable frame
        def make_scrollable(parent):
            frm = ttk.Frame(parent)
            canvas = tk.Canvas(frm)
            vbar = ttk.Scrollbar(frm, orient='vertical', command=canvas.yview)
            inner = ttk.Frame(canvas)
            inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.create_window((0, 0), window=inner, anchor='nw')
            canvas.configure(yscrollcommand=vbar.set)
            canvas.pack(side='left', fill='both', expand=True)
            vbar.pack(side='right', fill='y')
            # mouse wheel（每個分頁自身處理，避免全域干擾）
            def _on_mousewheel(event, step=None):
                try:
                    delta = step if step is not None else int(-1 * (event.delta / 120))
                except Exception:
                    delta = -1 if getattr(event, 'delta', 120) > 0 else 1
                canvas.yview_scroll(delta, 'units')
                return 'break'
            # 僅針對此分頁綁定，支援 Linux 滾輪按鈕
            try:
                inner.bind('<MouseWheel>', _on_mousewheel)
                inner.bind('<Button-4>', lambda e: _on_mousewheel(e, -1))
                inner.bind('<Button-5>', lambda e: _on_mousewheel(e, 1))
                canvas.bind('<MouseWheel>', _on_mousewheel)
                canvas.bind('<Button-4>', lambda e: _on_mousewheel(e, -1))
                canvas.bind('<Button-5>', lambda e: _on_mousewheel(e, 1))
            except Exception:
                pass
            return frm, inner

        # Render controls into tabs
        for tab_title, keys in TABS:
            tab = ttk.Frame(nb)
            nb.add(tab, text=tab_title)
            frame, holder = make_scrollable(tab)
            frame.pack(fill='both', expand=True)
            for k in keys:
                if k not in _spec_by_key:
                    continue
                spec = _spec_by_key[k]
                row = ttk.Frame(holder)
                row.pack(fill='x', padx=10, pady=6)
                ttk.Label(row, text=spec['label']).pack(anchor='w')
                help_lbl = ttk.Label(row, text=spec['help'], foreground='#666', wraplength=820, justify='left')
                help_lbl.pack(anchor='w')
                key = spec['key']
                cur_val = getattr(settings, key, '')
                w = None
                if spec['type'] == 'text':
                    display_val = ''
                    if key == 'SUPPORTED_EXTS':
                        if isinstance(cur_val, (list, tuple)):
                            display_val = ','.join([str(x) for x in cur_val])
                        else:
                            display_val = str(cur_val)
                    else:
                        display_val = str(cur_val)
                    var = tk.StringVar(master=self, value=display_val)
                    w = ttk.Entry(row, textvariable=var, width=80)
                    w.pack(anchor='w', fill='x')
                elif spec['type'] == 'multiline':
                    text = tk.Text(row, height=4, width=80)
                    if isinstance(cur_val, (list, tuple)):
                        text.insert('1.0', '\n'.join(cur_val))
                    else:
                        text.insert('1.0', str(cur_val))
                    text.pack(anchor='w', fill='x')
                    w = text
                elif spec['type'] == 'watch_subselect':
                    frame2 = ttk.Frame(row)
                    frame2.pack(anchor='w', fill='x')
                    vars_list = []
                    rt = runtime.load_runtime_settings()
                    watch_list = rt.get('WATCH_FOLDERS') if rt.get('WATCH_FOLDERS') else getattr(settings, 'WATCH_FOLDERS', [])
                    cur_selected = set(cur_val or [])
                    if not cur_selected:
                        cur_selected = set(watch_list)
                    for path in watch_list:
                        var = tk.BooleanVar(master=self, value=(path in cur_selected))
                        cb = ttk.Checkbutton(frame2, text=os.path.normpath(path), variable=var)
                        cb.pack(anchor='w')
                        vars_list.append((path, var))
                    def sync_from_watch():
                        nonlocal vars_list
                        for child in frame2.winfo_children():
                            child.destroy()
                        vars_list = []
                        rt2 = runtime.load_runtime_settings()
                        watch_list2 = rt2.get('WATCH_FOLDERS') if rt2.get('WATCH_FOLDERS') else getattr(settings, 'WATCH_FOLDERS', [])
                        for path in watch_list2:
                            var = tk.BooleanVar(master=self, value=True)
                            cb = ttk.Checkbutton(frame2, text=os.path.normpath(path), variable=var)
                            cb.pack(anchor='w')
                            vars_list.append((path, var))
                    ttk.Button(row, text='從監控資料夾同步', command=sync_from_watch).pack(anchor='w', pady=4)
                    frame2.vars_list = vars_list
                    w = frame2
                elif spec['type'] == 'paths':
                    frame2 = ttk.Frame(row)
                    frame2.pack(anchor='w', fill='x')
                    listbox = tk.Listbox(frame2, height=5, width=80, selectmode=tk.EXTENDED)
                    listbox.pack(side='left', fill='both', expand=True)
                    for v in (cur_val or []):
                        try:
                            listbox.insert('end', os.path.normpath(v))
                        except Exception:
                            listbox.insert('end', str(v))
                    btns = ttk.Frame(frame2)
                    btns.pack(side='left', padx=6)
                    def _live_sync_scan_targets():
                        try:
                            auto_spec, auto_widget = self._widgets.get('AUTO_SYNC_SCAN_TARGETS', (None, None))
                            auto_on = bool(auto_widget.var.get()) if auto_widget and hasattr(auto_widget, 'var') else False
                            if not auto_on:
                                return
                            if key != 'WATCH_FOLDERS':
                                return
                            tgt_spec, tgt_widget = self._widgets.get('SCAN_TARGET_FOLDERS', (None, None))
                            if not tgt_widget:
                                return
                            items = list(listbox.get(0, 'end'))
                            tgt_widget.delete(0, 'end')
                            for it in items:
                                tgt_widget.insert('end', it)
                        except Exception:
                            pass
                    def add_path(lb=listbox, sp=spec):
                        if sp.get('path_kind') == 'file':
                            p = filedialog.askopenfilename()
                        else:
                            p = filedialog.askdirectory()
                        if p:
                            p = os.path.normpath(p)
                            lb.insert('end', p)
                            _live_sync_scan_targets()
                    def remove_selected(lb=listbox):
                        sel = list(lb.curselection())
                        sel.reverse()
                        for idx in sel:
                            lb.delete(idx)
                        _live_sync_scan_targets()
                    def clear_all(lb=listbox):
                        lb.delete(0, 'end')
                        _live_sync_scan_targets()
                    ttk.Button(btns, text='新增', command=add_path).pack(fill='x')
                    ttk.Button(btns, text='移除選取', command=remove_selected).pack(fill='x', pady=2)
                    ttk.Button(btns, text='全部清除', command=clear_all).pack(fill='x')
                    w = listbox
                elif spec['type'] == 'path':
                    frame2 = ttk.Frame(row)
                    frame2.pack(anchor='w', fill='x')
                    var = tk.StringVar(value=str(cur_val))
                    entry = ttk.Entry(frame2, textvariable=var, width=70)
                    entry.pack(side='left', fill='x', expand=True)
                    def browse():
                        kind = spec.get('path_kind')
                        if kind == 'file':
                            p = filedialog.askopenfilename()
                        elif kind == 'save_file':
                            p = filedialog.asksaveasfilename()
                        else:
                            p = filedialog.askdirectory()
                        if p:
                            var.set(os.path.normpath(p))
                    ttk.Button(frame2, text='瀏覽...', command=browse).pack(side='left', padx=6)
                    w = entry
                elif spec['type'] == 'bool':
                    var = tk.BooleanVar(master=self, value=bool(cur_val))
                    w = ttk.Checkbutton(row, variable=var, text='啟用/勾選')
                    w.var = var
                    w.pack(anchor='w')
                elif spec['type'] == 'int':
                    var = tk.StringVar(value=str(cur_val))
                    w = ttk.Entry(row, textvariable=var, width=20)
                    w.pack(anchor='w')
                elif spec['type'] == 'choice':
                    var = tk.StringVar(value=str(cur_val))
                    w = ttk.Combobox(row, textvariable=var, values=spec['choices'], state='readonly', width=20)
                    w.pack(anchor='w')
                self._widgets[key] = (spec, w)

        # 保證空白欄位會自動填入 settings.py 的預設值
        self._ensure_defaults_filled()
        # 若啟用自動同步，保持 SCAN_TARGET_FOLDERS 與 WATCH_FOLDERS 一致
        try:
            rt0 = runtime.load_runtime_settings()
            auto = rt0.get('AUTO_SYNC_SCAN_TARGETS', False)
        except Exception:
            auto = False
        if auto:
            spec_targets, widget_targets = self._widgets.get('SCAN_TARGET_FOLDERS', (None, None))
            spec_watch, widget_watch = self._widgets.get('WATCH_FOLDERS', (None, None))
            if widget_targets and widget_watch and spec_targets['type'] == 'paths' and spec_watch['type'] == 'paths':
                # 清空並以 WATCH_FOLDERS 內容填入
                widget_targets.delete(0, 'end')
                for v in list(widget_watch.get(0, 'end')):
                    widget_targets.insert('end', v)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill='x', padx=10, pady=10)
        ttk.Button(btn_row, text='載入預設', command=self._reset_defaults).pack(side='left')
        ttk.Button(btn_row, text='載入設定檔...', command=self._load_preset).pack(side='left', padx=6)
        ttk.Button(btn_row, text='匯出設定檔...', command=self._save_preset).pack(side='left')
        ttk.Button(btn_row, text='儲存並開始', command=self._save_and_apply).pack(side='right')

    def _reset_defaults(self):
        for key, (spec, widget) in self._widgets.items():
            val = getattr(settings, key, '')
            if spec['type'] == 'text':
                widget.delete(0, 'end')
                widget.insert(0, str(val))
            elif spec['type'] == 'multiline':
                widget.delete('1.0', 'end')
                if isinstance(val, (list, tuple)):
                    widget.insert('1.0', '\n'.join(val))
                else:
                    widget.insert('1.0', str(val))
            elif spec['type'] == 'paths':
                widget.delete(0, 'end')
                for v in (val or []):
                    try:
                        widget.insert('end', os.path.normpath(v))
                    except Exception:
                        widget.insert('end', str(v))
            elif spec['type'] == 'bool':
                widget.var.set(bool(val))
            elif spec['type'] == 'int':
                widget.delete(0, 'end')
                widget.insert(0, str(val))
            elif spec['type'] == 'choice':
                widget.set(str(val))

    def _ensure_defaults_filled(self):
        # 將畫面上仍為空白的欄位填入 settings.py 的預設值
        for key, (spec, widget) in self._widgets.items():
            val = getattr(settings, key, '')
            if spec['type'] == 'text' and widget.get().strip() == '':
                widget.insert(0, str(val))
            elif spec['type'] == 'multiline':
                raw = widget.get('1.0', 'end').strip()
                if raw == '':
                    if isinstance(val, (list, tuple)):
                        widget.insert('1.0', '\n'.join(val))
                    else:
                        widget.insert('1.0', str(val))
            elif spec['type'] == 'paths':
                if widget.size() == 0:
                    for v in (val or []):
                        try:
                            widget.insert('end', os.path.normpath(v))
                        except Exception:
                            widget.insert('end', str(v))
            elif spec['type'] == 'path':
                if widget.get().strip() == '' and val:
                    try:
                        widget.delete(0, 'end')
                        widget.insert(0, os.path.normpath(val))
                    except Exception:
                        widget.insert(0, str(val))
            elif spec['type'] == 'bool':
                # 不覆蓋既有勾選狀態
                pass
            elif spec['type'] == 'int' and widget.get().strip() == '':
                widget.insert(0, str(val))
            elif spec['type'] == 'choice' and not widget.get().strip():
                widget.set(str(val))

    def _collect_values(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for key, (spec, widget) in self._widgets.items():
            if spec['type'] in ('text','int','choice'):
                data[key] = widget.get().strip()
            elif spec['type'] == 'path':
                val = widget.get().strip()
                if val:
                    try:
                        import os
                        val = os.path.normpath(val)
                    except Exception:
                        pass
                data[key] = val
            elif spec['type'] == 'multiline':
                raw = widget.get('1.0', 'end').strip()
                lines = [l.strip() for l in raw.split('\n') if l.strip()]
                data[key] = lines
            elif spec['type'] == 'paths':
                items = list(widget.get(0, 'end'))
                data[key] = items
            elif spec['type'] == 'watch_subselect':
                # collect checked subset
                items = []
                for path, var in getattr(widget, 'vars_list', []):
                    if bool(var.get()):
                        items.append(path)
                data[key] = items
            elif spec['type'] == 'bool':
                data[key] = bool(widget.var.get())
        # normalize SUPPORTED_EXTS string to tuple-like list
        exts = data.get('SUPPORTED_EXTS')
        if isinstance(exts, str):
            items = [x.strip() for x in exts.replace(';', ',').split(',') if x.strip()]
            norm = []
            for x in items:
                x = x.strip(" ' \"()[]{}").lower()
                if not x:
                    continue
                if not x.startswith('.'):
                    x = '.' + x
                norm.append(x)
            if norm:
                data['SUPPORTED_EXTS'] = norm
            else:
                # Do not override if user left it blank
                data.pop('SUPPORTED_EXTS', None)
        return data

    def _save_and_apply(self):
        try:
            new_data = self._collect_values()
            # 合併保存：以畫面值覆蓋 runtime JSON，空值不覆蓋
            def _is_blank(v):
                if v is None: return True
                if isinstance(v, str) and v.strip() == '': return True
                if isinstance(v, (list, tuple, dict)) and len(v) == 0: return True
                return False
            old_data = load_runtime_settings() or {}
            merged = dict(old_data)
            for k, v in (new_data or {}).items():
                # 對於集合型別（list/tuple/dict），即使為空也視為「使用者明確清空」，必須覆蓋
                if isinstance(v, (list, tuple, dict)):
                    merged[k] = v
                    continue
                # 文字型別空白代表「不變更」，不覆蓋
                if _is_blank(v):
                    continue
                merged[k] = v
            # 按下儲存並開始：確保移除取消旗標
            if 'STARTUP_CANCELLED' in merged:
                merged.pop('STARTUP_CANCELLED', None)
            save_runtime_settings(merged)
            apply_to_settings(merged)
            self.destroy()
        except Exception as e:
            messagebox.showerror('錯誤', f'儲存設定失敗: {e}')

    def _on_close(self):
        # 使用者按視窗右上角關閉：視為取消，停止 watchdog 啟動
        try:
            # 傳回一個特殊旗標到 runtime json，讓 main 判斷不要繼續執行
            data = runtime.load_runtime_settings() or {}
            data['STARTUP_CANCELLED'] = True
            save_runtime_settings(data)
        except Exception:
            pass
        self.destroy()

    def _save_preset(self):
        try:
            data = self._collect_values()
            path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files','*.json')])
            if not path:
                return
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('完成', '已儲存為範本')
        except Exception as e:
            messagebox.showerror('錯誤', f'儲存範本失敗: {e}')

    def _load_preset(self):
        try:
            path = filedialog.askopenfilename(filetypes=[('JSON Files','*.json')])
            if not path:
                return
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 將值套到畫面（不直接 apply 到 settings）
            for key, (spec, widget) in self._widgets.items():
                if key not in data:
                    continue
                val = data[key]
                if spec['type'] == 'text':
                    widget.delete(0, 'end')
                    widget.insert(0, str(val))
                elif spec['type'] == 'int':
                    widget.delete(0, 'end')
                    widget.insert(0, str(val))
                elif spec['type'] == 'choice':
                    widget.set(str(val))
                elif spec['type'] == 'multiline':
                    widget.delete('1.0', 'end')
                    if isinstance(val, (list, tuple)):
                        widget.insert('1.0', '\n'.join(val))
                    else:
                        widget.insert('1.0', str(val))
                elif spec['type'] == 'paths':
                    widget.delete(0, 'end')
                    for v in val or []:
                        widget.insert('end', v)
                elif spec['type'] == 'bool':
                    widget.var.set(bool(val))
            messagebox.showinfo('完成', '已載入範本內容（尚未套用，請按「儲存並開始」）。')
        except Exception as e:
            messagebox.showerror('錯誤', f'載入範本失敗: {e}')


def show_settings_ui():
    import threading
    import sys
    import gc
    
    # 檢查是否在主線程中運行
    if threading.current_thread() is not threading.main_thread():
        print("錯誤：GUI 必須在主線程中運行")
        # 設置取消啟動標誌
        try:
            data = runtime.load_runtime_settings() or {}
            data['STARTUP_CANCELLED'] = True
            save_runtime_settings(data)
        except Exception:
            pass
        return
    
    root = None
    dlg = None
    try:
        # 創建根視窗
        root = tk.Tk()
        root.withdraw()
        
        # 創建對話框
        if getattr(runtime, 'load_runtime_settings', None):
            try:
                print(f"[ui] settings dialog open thread={threading.current_thread().name}")
            except Exception:
                pass
        dlg = SettingsDialog(root)
        
        # 等待對話框關閉
        root.wait_window(dlg)
        if getattr(runtime, 'load_runtime_settings', None):
            try:
                print(f"[ui] settings dialog close thread={threading.current_thread().name}")
            except Exception:
                pass
        
    except Exception as e:
        print(f"GUI 啟動失敗: {e}")
        # 設置取消啟動標誌
        try:
            data = runtime.load_runtime_settings() or {}
            data['STARTUP_CANCELLED'] = True
            save_runtime_settings(data)
        except Exception:
            pass
    finally:
        # 清理資源
        if dlg:
            try:
                dlg.destroy()
            except Exception:
                pass
        if root:
            try:
                # 清理所有 tkinter 變數
                _cleanup_all_tkinter_vars(root)
                root.quit()
                root.destroy()
            except Exception:
                pass
        
        #（移除強制垃圾回收）由 Python 自然回收即可

def _cleanup_all_tkinter_vars(root):
    """清理所有 tkinter 變數"""
    try:
        import gc
        
        # 清理所有 tkinter 變數
        for obj in gc.get_objects():
            if hasattr(obj, '__class__') and 'tkinter' in str(type(obj)):
                try:
                    if hasattr(obj, '_tk') and obj._tk:
                        obj._tk = None
                except Exception:
                    pass
        
        # 清理根視窗
        if root and hasattr(root, '_tk'):
            try:
                root._tk = None
            except Exception:
                pass
                
    except Exception:
        pass
