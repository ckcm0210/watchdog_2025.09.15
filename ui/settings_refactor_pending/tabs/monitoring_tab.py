# 監控範圍與啟動掃描分頁
# Monitoring and Startup Scan Tab

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .base_tab import BaseTab
import os

print("[DEBUG-STEP3.2] 載入監控分頁類")

class MonitoringTab(BaseTab):
    """監控範圍與啟動掃描設定分頁"""
    
    def __init__(self, parent: ttk.Notebook):
        """初始化監控分頁"""
        super().__init__(parent, '監控範圍與啟動掃描', 'monitoring')
        print(f"[DEBUG-STEP3.2] 監控分頁初始化完成")
    
    def _create_widgets(self):
        """創建監控專用的控件"""
        print(f"[DEBUG-STEP3.2] 開始創建監控分頁控件，配置項數量: {len(self.config_items)}")
        
        row = 0
        for config_item in self.config_items:
            self._create_monitoring_widget(config_item, row)
            row += 1
            
        print(f"[DEBUG-STEP3.2] 監控分頁控件創建完成，總計: {len(self.widgets)} 個控件")
    
    def _create_monitoring_widget(self, config_item: dict, row: int):
        """創建監控專用的控件，支持路徑選擇等特殊功能"""
        key = config_item['key']
        label_text = config_item.get('label', key)
        widget_type = config_item.get('type', 'text')
        path_kind = config_item.get('path_kind', None)
        
        # 創建標籤
        label = ttk.Label(self.scrollable_frame, text=label_text)
        label.grid(row=row, column=0, sticky='w', padx=5, pady=2)
        
        # 根據類型創建控件
        if widget_type == 'bool':
            widget = ttk.Checkbutton(self.scrollable_frame)
            
        elif widget_type == 'choice':
            choices = config_item.get('choices', [])
            widget = ttk.Combobox(self.scrollable_frame, values=choices, state='readonly')
            
        elif widget_type == 'int':
            widget = ttk.Entry(self.scrollable_frame, width=20)
            
        elif widget_type == 'multiline':
            widget = tk.Text(self.scrollable_frame, height=3, width=50)
            
        elif widget_type in ['path', 'paths']:
            # 路徑類型需要特殊處理
            widget_frame = ttk.Frame(self.scrollable_frame)
            widget_frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            
            if widget_type == 'paths':
                # 多路徑使用 Text 控件
                widget = tk.Text(widget_frame, height=3, width=40)
                widget.pack(side='left', fill='both', expand=True)
            else:
                # 單路徑使用 Entry 控件
                widget = ttk.Entry(widget_frame, width=40)
                widget.pack(side='left', fill='both', expand=True)
            
            # 添加瀏覽按鈕
            browse_btn = ttk.Button(widget_frame, text="瀏覽", 
                                  command=lambda: self._browse_path(key, path_kind))
            browse_btn.pack(side='right', padx=(5, 0))
            
            # 存儲瀏覽按鈕引用
            self.widgets[f"{key}_browse"] = browse_btn
            
        else:  # text
            widget = ttk.Entry(self.scrollable_frame, width=50)
        
        # 對於非路徑類型，正常設置grid
        if widget_type not in ['path', 'paths']:
            widget.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        
        # 添加幫助提示
        if config_item.get('help'):
            help_btn = ttk.Button(self.scrollable_frame, text="?", width=3,
                                command=lambda h=config_item['help']: self._show_help(h))
            help_btn.grid(row=row, column=2, padx=(5, 0))
            self.widgets[f"{key}_help"] = help_btn
        
        # 存儲控件引用
        self.widgets[key] = {
            'label': label,
            'widget': widget,
            'config': config_item
        }
        
        # 配置列寬
        self.scrollable_frame.columnconfigure(1, weight=1)
    
    def _browse_path(self, key: str, path_kind: str):
        """打開路徑選擇對話框"""
        try:
            if path_kind == 'dir':
                # 選擇資料夾
                path = filedialog.askdirectory(title=f"選擇資料夾 - {key}")
            elif path_kind == 'file':
                # 選擇文件
                path = filedialog.askopenfilename(title=f"選擇文件 - {key}")
            elif path_kind == 'save_file':
                # 保存文件
                path = filedialog.asksaveasfilename(title=f"選擇保存位置 - {key}")
            else:
                return
            
            if path:
                widget = self.widgets[key]['widget']
                widget_type = self.widgets[key]['config'].get('type')
                
                if widget_type == 'paths':
                    # 多路徑：添加到現有內容
                    current = widget.get('1.0', 'end-1c')
                    if current.strip():
                        widget.insert('end', f'\\n{path}')
                    else:
                        widget.insert('1.0', path)
                else:
                    # 單路徑：替換內容
                    widget.delete(0, 'end')
                    widget.insert(0, path)
                    
                print(f"[DEBUG-STEP3.2] 選擇路徑: {key} = {path}")
                
        except Exception as e:
            print(f"[DEBUG-STEP3.2] 路徑選擇錯誤: {e}")
            messagebox.showerror("錯誤", f"路徑選擇失敗: {e}")
    
    def _show_help(self, help_text: str):
        """顯示幫助信息"""
        messagebox.showinfo("說明", help_text)
    
    def get_monitoring_values(self) -> dict:
        """獲取監控分頁的所有設定值"""
        if not self.is_loaded:
            return {}
            
        values = {}
        for key, widget_info in self.widgets.items():
            if key.endswith('_browse') or key.endswith('_help'):
                continue  # 跳過按鈕
                
            try:
                widget = widget_info['widget']
                widget_type = widget_info['config'].get('type', 'text')
                
                if widget_type == 'bool':
                    values[key] = widget.instate(['selected'])
                elif widget_type == 'multiline' or widget_type == 'paths':
                    values[key] = widget.get('1.0', 'end-1c')
                else:
                    values[key] = widget.get()
                    
            except Exception as e:
                print(f"[DEBUG-STEP3.2] 獲取 {key} 值時出錯: {e}")
                values[key] = None
                
        print(f"[DEBUG-STEP3.2] 獲取監控設定值，共 {len(values)} 項")
        return values
    
    def set_monitoring_values(self, values: dict):
        """設置監控分頁的設定值"""
        if not self.is_loaded:
            print("[DEBUG-STEP3.2] 分頁未載入，無法設置值")
            return
            
        set_count = 0
        for key, value in values.items():
            if key in self.widgets and not key.endswith('_browse') and not key.endswith('_help'):
                try:
                    widget = self.widgets[key]['widget']
                    widget_type = self.widgets[key]['config'].get('type', 'text')
                    
                    if widget_type == 'bool':
                        if value:
                            widget.state(['selected'])
                        else:
                            widget.state(['!selected'])
                    elif widget_type == 'multiline' or widget_type == 'paths':
                        widget.delete('1.0', 'end')
                        widget.insert('1.0', str(value) if value else '')
                    else:
                        widget.delete(0, 'end')
                        widget.insert(0, str(value) if value else '')
                    
                    set_count += 1
                        
                except Exception as e:
                    print(f"[DEBUG-STEP3.2] 設置 {key} 值時出錯: {e}")
        
        print(f"[DEBUG-STEP3.2] 設置監控設定值，共 {set_count} 項")
    
    def validate_monitoring_settings(self) -> bool:
        """驗證監控設定的有效性"""
        if not self.is_loaded:
            return False
            
        values = self.get_monitoring_values()
        errors = []
        
        # 檢查必要的路徑設定
        watch_folders = values.get('WATCH_FOLDERS', '').strip()
        if not watch_folders:
            errors.append("必須設定至少一個監控資料夾")
        
        # 檢查文件類型設定
        supported_exts = values.get('SUPPORTED_EXTS', '').strip()
        if not supported_exts:
            errors.append("必須設定監控的文件類型")
        
        if errors:
            error_msg = "\\n".join(errors)
            messagebox.showerror("設定錯誤", f"監控設定有以下問題:\\n{error_msg}")
            print(f"[DEBUG-STEP3.2] 監控設定驗證失敗: {errors}")
            return False
        
        print("[DEBUG-STEP3.2] 監控設定驗證通過")
        return True

print("[DEBUG-STEP3.2] 監控分頁類定義完成")