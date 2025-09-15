# 基礎分頁類
# Base Tab Class for Settings UI

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Any, Optional
import gc

print("[DEBUG-STEP3.1] 載入基礎分頁類")

class BaseTab:
    """設定界面的基礎分頁類"""
    
    def __init__(self, parent: ttk.Notebook, tab_name: str, config_module_name: str):
        """
        初始化基礎分頁
        
        Args:
            parent: 父級 Notebook 控件
            tab_name: 分頁顯示名稱
            config_module_name: 對應的配置模組名稱
        """
        print(f"[DEBUG-STEP3.1] 初始化分頁: {tab_name}")
        
        self.parent = parent
        self.tab_name = tab_name
        self.config_module_name = config_module_name
        
        # 分頁狀態
        self.is_loaded = False
        self.frame: Optional[ttk.Frame] = None
        self.widgets: Dict[str, Any] = {}
        self.config_items: List[Dict] = []
        
        # 記憶體使用追蹤
        self.memory_before_load = 0
        self.memory_after_load = 0
        
        print(f"[DEBUG-STEP3.1] 分頁 {tab_name} 初始化完成")
    
    def load_config(self) -> bool:
        """按需載入配置定義"""
        if self.config_items:
            return True  # 已經載入過
            
        try:
            print(f"[DEBUG-STEP3.1] 載入配置模組: {self.config_module_name}")
            
            # 動態導入配置模組
            module_path = f"ui.settings.config_definitions.{self.config_module_name}_config"
            config_module = __import__(module_path, fromlist=[f"{self.config_module_name.upper()}_CONFIG"])
            
            # 獲取配置項列表
            config_attr_name = f"{self.config_module_name.upper()}_CONFIG"
            self.config_items = getattr(config_module, config_attr_name)
            
            print(f"[DEBUG-STEP3.1] 成功載入 {len(self.config_items)} 個配置項")
            return True
            
        except Exception as e:
            print(f"[DEBUG-STEP3.1] 載入配置失敗: {e}")
            return False
    
    def create_frame(self) -> ttk.Frame:
        """創建分頁框架"""
        if self.frame is None:
            print(f"[DEBUG-STEP3.1] 創建分頁框架: {self.tab_name}")
            self.frame = ttk.Frame(self.parent)
            
            # 添加滾動支持
            self._setup_scrollable_frame()
            
        return self.frame
    
    def _setup_scrollable_frame(self):
        """設置可滾動的框架"""
        # 創建 Canvas 和 Scrollbar
        self.canvas = tk.Canvas(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滾動
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
    
    def load_tab(self) -> bool:
        """按需載入分頁內容"""
        if self.is_loaded:
            print(f"[DEBUG-STEP3.1] 分頁 {self.tab_name} 已載入，跳過")
            return True
            
        try:
            # 記錄載入前記憶體
            self.memory_before_load = self._get_memory_usage()
            print(f"[DEBUG-STEP3.1] 載入前記憶體: {self.memory_before_load}MB")
            
            # 載入配置
            if not self.load_config():
                return False
            
            # 創建框架
            self.create_frame()
            
            # 創建控件
            self._create_widgets()
            
            # 記錄載入後記憶體
            self.memory_after_load = self._get_memory_usage()
            memory_diff = self.memory_after_load - self.memory_before_load
            print(f"[DEBUG-STEP3.1] 載入後記憶體: {self.memory_after_load}MB")
            print(f"[DEBUG-STEP3.1] 記憶體增加: {memory_diff}MB")
            
            self.is_loaded = True
            print(f"[DEBUG-STEP3.1] 分頁 {self.tab_name} 載入完成")
            return True
            
        except Exception as e:
            print(f"[DEBUG-STEP3.1] 載入分頁失敗: {e}")
            return False
    
    def _create_widgets(self):
        """創建控件（子類需要實現）"""
        print(f"[DEBUG-STEP3.1] 開始創建 {len(self.config_items)} 個控件")
        
        row = 0
        for config_item in self.config_items:
            self._create_single_widget(config_item, row)
            row += 1
            
        print(f"[DEBUG-STEP3.1] 完成創建 {len(self.widgets)} 個控件")
    
    def _create_single_widget(self, config_item: Dict, row: int):
        """創建單個控件"""
        key = config_item['key']
        label_text = config_item.get('label', key)
        widget_type = config_item.get('type', 'text')
        
        # 創建標籤
        label = ttk.Label(self.scrollable_frame, text=label_text)
        label.grid(row=row, column=0, sticky='w', padx=5, pady=2)
        
        # 根據類型創建控件
        if widget_type == 'bool':
            widget = ttk.Checkbutton(self.scrollable_frame)
        elif widget_type == 'choice':
            widget = ttk.Combobox(self.scrollable_frame, values=config_item.get('choices', []))
        elif widget_type == 'int':
            widget = ttk.Entry(self.scrollable_frame)
        elif widget_type == 'multiline':
            widget = tk.Text(self.scrollable_frame, height=3, width=40)
        else:  # text, path, paths
            widget = ttk.Entry(self.scrollable_frame, width=40)
        
        widget.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
        
        # 存儲控件引用
        self.widgets[key] = {
            'label': label,
            'widget': widget,
            'config': config_item
        }
        
        # 配置列寬
        self.scrollable_frame.columnconfigure(1, weight=1)
    
    def unload_tab(self):
        """卸載分頁以釋放記憶體"""
        if not self.is_loaded:
            return
            
        print(f"[DEBUG-STEP3.1] 卸載分頁: {self.tab_name}")
        
        try:
            # 清理控件
            if self.frame:
                for widget_info in self.widgets.values():
                    try:
                        widget_info['widget'].destroy()
                        widget_info['label'].destroy()
                    except:
                        pass
                
                self.frame.destroy()
                self.frame = None
            
            # 清理引用
            self.widgets.clear()
            
            # 移除強制垃圾回收以避免在 UI 清理時觸發 XML 相關崩潰
            # gc.collect()
            
            self.is_loaded = False
            
            # 記錄記憶體釋放
            current_memory = self._get_memory_usage()
            memory_freed = self.memory_after_load - current_memory
            print(f"[DEBUG-STEP3.1] 分頁卸載完成，釋放記憶體: {memory_freed}MB")
            
        except Exception as e:
            print(f"[DEBUG-STEP3.1] 卸載分頁時出錯: {e}")
    
    def _get_memory_usage(self) -> float:
        """獲取當前記憶體使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_values(self) -> Dict[str, Any]:
        """獲取分頁中所有控件的值"""
        if not self.is_loaded:
            return {}
            
        values = {}
        for key, widget_info in self.widgets.items():
            try:
                widget = widget_info['widget']
                widget_type = widget_info['config'].get('type', 'text')
                
                if widget_type == 'bool':
                    values[key] = widget.instate(['selected'])
                elif widget_type == 'multiline':
                    values[key] = widget.get('1.0', 'end-1c')
                else:
                    values[key] = widget.get()
                    
            except Exception as e:
                print(f"[DEBUG-STEP3.1] 獲取 {key} 值時出錯: {e}")
                values[key] = None
                
        return values
    
    def set_values(self, values: Dict[str, Any]):
        """設置分頁中控件的值"""
        if not self.is_loaded:
            return
            
        for key, value in values.items():
            if key in self.widgets:
                try:
                    widget = self.widgets[key]['widget']
                    widget_type = self.widgets[key]['config'].get('type', 'text')
                    
                    if widget_type == 'bool':
                        if value:
                            widget.state(['selected'])
                        else:
                            widget.state(['!selected'])
                    elif widget_type == 'multiline':
                        widget.delete('1.0', 'end')
                        widget.insert('1.0', str(value))
                    else:
                        widget.delete(0, 'end')
                        widget.insert(0, str(value))
                        
                except Exception as e:
                    print(f"[DEBUG-STEP3.1] 設置 {key} 值時出錯: {e}")

print("[DEBUG-STEP3.1] 基礎分頁類定義完成")