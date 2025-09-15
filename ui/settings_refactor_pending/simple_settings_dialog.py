# 簡化設定界面 - 只包含監控分頁
# Simple Settings Dialog - Monitoring Tab Only

import tkinter as tk
from tkinter import ttk, messagebox
from .tabs.monitoring_tab import MonitoringTab
import config.settings as settings
from config.runtime import load_runtime_settings, save_runtime_settings, apply_to_settings

print("[DEBUG-INTEGRATION] 載入簡化設定界面")

class SimpleSettingsDialog:
    """簡化的設定界面，只包含監控分頁"""
    
    def __init__(self, master=None):
        print("[DEBUG-INTEGRATION] 初始化簡化設定界面")
        
        self.master = master
        self.root = tk.Toplevel(master) if master else tk.Tk()
        self.root.title('Excel Watchdog 設定 (監控範圍)')
        self.root.geometry('800x600')
        self.root.grab_set()
        
        # 載入運行時設定
        self._load_runtime_settings()
        
        # 創建界面
        self._create_interface()
        
        # 設定關閉事件
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        
        print("[DEBUG-INTEGRATION] 簡化設定界面初始化完成")
    
    def _load_runtime_settings(self):
        """載入運行時設定"""
        try:
            runtime_settings = load_runtime_settings()
            if runtime_settings:
                apply_to_settings(runtime_settings)
                print("[DEBUG-INTEGRATION] 運行時設定載入成功")
        except Exception as e:
            print(f"[DEBUG-INTEGRATION] 載入運行時設定失敗: {e}")
    
    def _create_interface(self):
        """創建界面元素"""
        print("[DEBUG-INTEGRATION] 創建界面元素")
        
        # 創建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 創建標題
        title_label = ttk.Label(main_frame, text="監控範圍與啟動掃描設定", 
                               font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 創建說明
        info_label = ttk.Label(main_frame, 
                              text="注意：這是簡化版設定界面，只包含監控相關設定。\\n其他設定請使用完整版設定界面。",
                              foreground='blue')
        info_label.pack(pady=(0, 10))
        
        # 創建 Notebook (雖然只有一個分頁，但保持一致性)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # 創建監控分頁
        self.monitoring_tab = MonitoringTab(self.notebook)
        
        # 載入分頁內容
        if self.monitoring_tab.load_tab():
            self.notebook.add(self.monitoring_tab.frame, text='監控範圍與啟動掃描')
            print("[DEBUG-INTEGRATION] 監控分頁載入成功")
        else:
            print("[DEBUG-INTEGRATION] 監控分頁載入失敗")
            messagebox.showerror("錯誤", "無法載入監控設定分頁")
            return
        
        # 載入當前設定值
        self._load_current_values()
        
        # 創建按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # 創建按鈕
        ttk.Button(button_frame, text="確定", command=self._on_ok).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side='right')
        ttk.Button(button_frame, text="套用", command=self._on_apply).pack(side='right', padx=(0, 5))
        
        print("[DEBUG-INTEGRATION] 界面元素創建完成")
    
    def _load_current_values(self):
        """載入當前的設定值"""
        try:
            print("[DEBUG-INTEGRATION] 載入當前設定值")
            
            # 從 settings 模組獲取當前值
            current_values = {}
            
            # 獲取監控相關的設定值
            monitoring_keys = [
                'WATCH_FOLDERS', 'WATCH_EXCLUDE_FOLDERS', 'MONITOR_ONLY_FOLDERS', 
                'MONITOR_ONLY_EXCLUDE_FOLDERS', 'SCAN_TARGET_FOLDERS', 
                'AUTO_SYNC_SCAN_TARGETS', 'SCAN_ALL_MODE', 'SUPPORTED_EXTS', 
                'MANUAL_BASELINE_TARGET'
            ]
            
            for key in monitoring_keys:
                if hasattr(settings, key):
                    value = getattr(settings, key)
                    # 處理列表類型的設定
                    if isinstance(value, list):
                        current_values[key] = '\\n'.join(value) if value else ''
                    else:
                        current_values[key] = value
            
            # 設定到監控分頁
            self.monitoring_tab.set_monitoring_values(current_values)
            
            print(f"[DEBUG-INTEGRATION] 載入了 {len(current_values)} 個設定值")
            
        except Exception as e:
            print(f"[DEBUG-INTEGRATION] 載入設定值失敗: {e}")
    
    def _on_apply(self):
        """套用設定"""
        try:
            print("[DEBUG-INTEGRATION] 套用設定")
            
            # 驗證設定
            if not self.monitoring_tab.validate_monitoring_settings():
                return
            
            # 獲取設定值
            values = self.monitoring_tab.get_monitoring_values()
            
            # 套用到 settings 模組
            for key, value in values.items():
                if hasattr(settings, key):
                    # 處理列表類型的設定
                    if key in ['WATCH_FOLDERS', 'WATCH_EXCLUDE_FOLDERS', 'MONITOR_ONLY_FOLDERS', 
                              'MONITOR_ONLY_EXCLUDE_FOLDERS', 'SCAN_TARGET_FOLDERS', 'MANUAL_BASELINE_TARGET']:
                        if isinstance(value, str) and value.strip():
                            setattr(settings, key, [line.strip() for line in value.split('\\n') if line.strip()])
                        else:
                            setattr(settings, key, [])
                    else:
                        setattr(settings, key, value)
            
            # 保存到運行時設定
            runtime_data = {}
            for key, value in values.items():
                runtime_data[key] = value
            
            save_runtime_settings(runtime_data)
            
            messagebox.showinfo("成功", "設定已套用並保存")
            print("[DEBUG-INTEGRATION] 設定套用成功")
            
        except Exception as e:
            print(f"[DEBUG-INTEGRATION] 套用設定失敗: {e}")
            messagebox.showerror("錯誤", f"套用設定失敗: {e}")
    
    def _on_ok(self):
        """確定按鈕"""
        self._on_apply()
        self._on_close()
    
    def _on_cancel(self):
        """取消按鈕"""
        self._on_close()
    
    def _on_close(self):
        """關閉對話框"""
        try:
            print("[DEBUG-INTEGRATION] 關閉簡化設定界面")
            
            # 卸載分頁以釋放記憶體
            if hasattr(self, 'monitoring_tab'):
                self.monitoring_tab.unload_tab()
            
            self.root.destroy()
            
        except Exception as e:
            print(f"[DEBUG-INTEGRATION] 關閉界面時出錯: {e}")

def show_simple_settings_ui(master=None):
    """顯示簡化設定界面的函數"""
    print("[DEBUG-INTEGRATION] 顯示簡化設定界面")
    
    try:
        dialog = SimpleSettingsDialog(master)
        
        # 如果沒有 master，需要運行主循環
        if master is None:
            print("[DEBUG-INTEGRATION] 運行主循環等待用戶操作")
            dialog.root.mainloop()
        
        return dialog
    except Exception as e:
        print(f"[DEBUG-INTEGRATION] 顯示設定界面失敗: {e}")
        messagebox.showerror("錯誤", f"無法打開設定界面: {e}")
        return None

print("[DEBUG-INTEGRATION] 簡化設定界面模組載入完成")