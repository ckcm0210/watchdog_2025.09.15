"""
黑色控制台視窗
"""
import tkinter as tk
from tkinter import scrolledtext
import queue
import threading
import time
import config.settings as settings
import logging

class BlackConsoleWindow:
    def __init__(self):
        self.root = None
        self.text_widget = None
        self.message_queue = queue.Queue()
        self.running = False
        self.is_minimized = False
        self.popup_on_comparison = settings.CONSOLE_POPUP_ON_COMPARISON
        self.is_topmost = False
        self.topmost_timer = None
        self._ui_thread = None
        self._ready_evt = threading.Event()
        self._tkinter_vars = []  # 追蹤 tkinter 變數

    def create_window(self):
        """創建黑色 console 視窗（只在 UI 線程中調用）"""
        self.root = tk.Tk()
        self.root.title("Excel Watchdog Console")
        self.root.geometry("1200x1000")
        self.root.configure(bg='black')

        # 啟動時短暫置頂
        self.root.attributes('-topmost', True)
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass
        self.is_topmost = True
        self.schedule_disable_topmost(3000)

        # 監控視窗狀態
        self.root.bind('<Unmap>', self.on_minimize)
        self.root.bind('<Map>', self.on_restore)

        # 滾動文字區域
        self.text_widget = scrolledtext.ScrolledText(
            self.root,
            bg='black',
            fg='white',
            font=(getattr(settings, 'CONSOLE_FONT_FAMILY', 'Consolas'), int(getattr(settings, 'CONSOLE_FONT_SIZE', 10))),
            insertbackground='white',
            selectbackground='darkgray',
            wrap=(tk.NONE if getattr(settings, 'CONSOLE_WRAP_NONE', True) else tk.WORD)
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 定義著色 tags
        if getattr(settings, 'CONSOLE_COLORIZE_TYPES', True):
            try:
                self.text_widget.tag_config('formula_line', foreground=getattr(settings, 'CONSOLE_FORMULA_COLOR', '#00bcd4'))
                self.text_widget.tag_config('value_line', foreground=getattr(settings, 'CONSOLE_VALUE_COLOR', '#ffd54f'))
            except Exception:
                pass

        # 關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.running = True
        self._ready_evt.set()
        self.check_messages()

    def schedule_disable_topmost(self, delay_ms):
        """安排取消置頂 - 避免重複計時器"""
        if self.topmost_timer:
            try:
                self.root.after_cancel(self.topmost_timer)
            except Exception:
                pass
        self.topmost_timer = self.root.after(delay_ms, self.disable_topmost)

    def disable_topmost(self):
        """取消置頂狀態"""
        if self.root and self.running and self.is_topmost:
            try:
                self.root.attributes('-topmost', False)
            except Exception:
                pass
            self.is_topmost = False
            self.topmost_timer = None

    def on_minimize(self, event):
        self.is_minimized = True

    def on_restore(self, event):
        self.is_minimized = False

    def popup_window(self):
        """彈出視窗到最上層 - 有新訊息時（只在 UI 線程調用）"""
        if self.root and self.running:
            try:
                self.root.deiconify()
                self.root.attributes('-topmost', True)
                self.root.lift()
                try:
                    self.root.focus_force()
                except Exception:
                    pass
                self.root.after(100, lambda: self.root.attributes('-topmost', False))

                def flash_window():
                    original_bg = self.root.cget('bg')
                    self.root.configure(bg='darkred')
                    self.root.after(200, lambda: self.root.configure(bg=original_bg))
                flash_window()

                self.is_minimized = False
            except Exception as e:
                logging.error(f"彈出視窗失敗: {e}")

    def check_messages(self):
        """檢查並顯示新訊息（UI 線程中以 after 重覆排程）"""
        # 若已停止或視窗不存在，直接返回且不要再重排程
        if not self.running or (self.root is None):
            return
        try:
            has_new_messages = False
            while not self.message_queue.empty():
                message_data = self.message_queue.get_nowait()
                has_new_messages = True

                if isinstance(message_data, dict):
                    message = message_data.get('message', '')
                    is_comparison = message_data.get('is_comparison', False)
                    if is_comparison and self.popup_on_comparison:
                        self.popup_window()
                else:
                    message = str(message_data)

                # 顏色插入：按行判斷是否 formula/value 行
                if getattr(settings, 'CONSOLE_COLORIZE_TYPES', True):
                    try:
                        for line in (message + '\n').splitlines(True):
                            tag = None
                            if ' | formula | ' in line[:120]:
                                tag = 'formula_line'
                            elif ' | value | ' in line[:120]:
                                tag = 'value_line'
                            if tag:
                                self.text_widget.insert(tk.END, line, tag)
                            else:
                                self.text_widget.insert(tk.END, line)
                    except Exception:
                        self.text_widget.insert(tk.END, message + '\n')
                else:
                    self.text_widget.insert(tk.END, message + '\n')
                self.text_widget.see(tk.END)

            if has_new_messages and self.is_minimized:
                self.popup_window()
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"check_messages 錯誤: {e}")

        if self.running and self.root:
            self.root.after(100, self.check_messages)

    def add_message(self, message, is_comparison=False):
        """跨線程安全：只往佇列丟資料，UI 線程會自己取。若視窗已關閉/停止則忽略。"""
        try:
            if not self.running or (self.root is None):
                return
            message_data = {
                'message': str(message),
                'is_comparison': bool(is_comparison)
            }
            self.message_queue.put(message_data)
        except Exception:
            pass

    def toggle_topmost(self):
        """手動切換置頂狀態（UI 線程調用）"""
        if self.root and self.running:
            self.is_topmost = not self.is_topmost
            try:
                self.root.attributes('-topmost', self.is_topmost)
            except Exception:
                pass
            if not self.is_topmost and self.topmost_timer:
                try:
                    self.root.after_cancel(self.topmost_timer)
                except Exception:
                    pass
                self.topmost_timer = None

    def on_closing(self):
        """點右上角關閉時"""
        self.stop()

    def start(self):
        """在專用 UI 線程中啟動 Tk mainloop（所有 Tk 調用都在此線程）"""
        if self._ui_thread and self._ui_thread.is_alive():
            return

        def run_window():
            try:
                self.create_window()
                self.root.mainloop()
            except Exception as e:
                logging.error(f"Console UI 執行錯誤: {e}")
            finally:
                self.running = False
                self._cleanup_vars()

        self._ui_thread = threading.Thread(target=run_window, daemon=True, name="ConsoleUIThread")
        self._ui_thread.start()

        # 等待 UI 準備好（避免外部過早呼叫）
        self._ready_evt.wait(timeout=5.0)

    def _cleanup_vars(self):
        """清理 tkinter 變數"""
        try:
            # 清理所有追蹤的變數
            for var in self._tkinter_vars:
                try:
                    if hasattr(var, '_tk'):
                        var._tk = None
                except Exception:
                    pass
            self._tkinter_vars.clear()
        except Exception:
            pass

    def stop(self):
        """跨線程安全關閉 Tk 視窗與 mainloop"""
        # 先標記停止，阻止後續 add_message 與 check_messages 重排程
        self.running = False
        if not self.root:
            self._cleanup_vars()
            return

        def _shutdown():
            try:
                if self.topmost_timer:
                    try:
                        self.root.after_cancel(self.topmost_timer)
                    except Exception:
                        pass
                self._cleanup_vars()
                try:
                    self.root.quit()
                except Exception:
                    pass
                try:
                    self.root.destroy()
                except Exception:
                    pass
            except Exception:
                pass

        try:
            self.root.after(0, _shutdown)
        except Exception:
            self._cleanup_vars()
            self.root = None

# 全局 console 視窗實例
black_console = None

def init_console():
    """初始化控制台（在主線程呼叫，但 UI 自己用專用線程跑）"""
    global black_console
    if settings.ENABLE_BLACK_CONSOLE:
        black_console = BlackConsoleWindow()
        black_console.start()
    return black_console
