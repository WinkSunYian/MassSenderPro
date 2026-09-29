import os
import sys
import time
import keyboard
import pyautogui
import pyperclip
import win32clipboard
import win32con
import win32gui

from services.WeWorkAutoService import WeWorkAutoService


class WeWorkAutoServiceImpl(WeWorkAutoService):
    def __init__(self, asset_path=None):
        self.asset_path = asset_path
        self.stop_event = False
        self.target_classes = {"WeWorkWindow", "WwStandaloneConversationWnd"}

    def check_active_window(self):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            raise InterruptedError("无法获取当前活动窗口，任务已终止。")
        class_name = win32gui.GetClassName(hwnd)
        if class_name not in self.target_classes:
            title = win32gui.GetWindowText(hwnd)
            raise InterruptedError(
                f"当前活动窗口不是企业微信（标题: '{title}', 类名: '{class_name}'），任务终止。"
            )

    def check_interrupted(self):
        if self.stop_event:
            raise InterruptedError("收到中断指令，任务已终止。")
        self.check_active_window()

    def sleep(self, seconds: float):
        step = 0.1
        elapsed = 0.0
        while elapsed < seconds:
            if self.stop_event:
                raise InterruptedError("收到中断指令，任务已终止。")
            time.sleep(min(step, seconds - elapsed))
            elapsed += step
        if self.stop_event:
            raise InterruptedError("收到中断指令，任务已终止。")

    def start_hotkey_listener(self, hotkey: str = "f12"):
        self.stop_event = False

        def on_triggered():
            print(f"\n\n[热键] 捕获到 {hotkey.upper()} 按键，正在停止程序...")
            self.stop_event = True

        keyboard.add_hotkey(hotkey, on_triggered)
        print(f"提示：程序运行过程中，随时按下 [{hotkey.upper()}] 键即可紧急终止。")

    def stop_hotkey_listener(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

    @staticmethod
    def _enum_windows_callback(hwnd, result):
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
        if cls == "WwStandaloneConversationWnd" and title:
            result.append({"hwnd": hwnd, "title": title, "class_name": cls})

    def get_standalone_chat_title(self, timeout=3.0, sleep_interval=0.2):
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.check_interrupted()
            win_list = []
            win32gui.EnumWindows(self._enum_windows_callback, win_list)
            if win_list:
                return win_list[0]["title"]
            time.sleep(sleep_interval)
        return None

    def close_standalone_window(self, sleep_time=0.3):
        self.sleep(sleep_time)
        pyautogui.press("esc")

    def _find_image(self, img_path, confidence=0.8):
        self.check_interrupted()
        if not self.asset_path:
            raise ValueError("未配置 asset_path 路径")
        full_path = os.path.join(self.asset_path, img_path)
        try:
            pos = pyautogui.locateCenterOnScreen(full_path, confidence=confidence)
            return pos
        except pyautogui.ImageNotFoundException:
            print(f"[异常] 没有找到图片: {full_path}")
            return None

    def _click(self, pos, clicks=1, sleep_time=0.5):
        self.sleep(sleep_time)
        if pos:
            pyautogui.click(pos, clicks=clicks)
            return True
        return False

    def _copy_text(self, text):
        pyperclip.copy(text)

    def _copy_file(self, file_path):
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"文件不存在: {abs_path}")
        buffer = abs_path.encode("utf-16le") + b"\x00\x00\x00\x00"
        drop_files = (
            b"\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"
            + buffer
        )
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, drop_files)
        finally:
            win32clipboard.CloseClipboard()

    def search_and_open_user(self, user_id: str) -> bool:
        self.sleep(0.5)
        pyautogui.hotkey("ctrl", "f")
        self.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        self.sleep(0.2)
        self.send_text(user_id)
        self.sleep(0.5)
        pyautogui.hotkey("ctrl", "o")
        self.sleep(0.3)
        return True

    def send_text(self, text: str):
        self._copy_text(text)
        self.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        self.sleep(0.3)
        pyautogui.press("enter")

    def send_file(self, file_path: str):
        self._copy_file(file_path)
        self.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        self.sleep(0.3)
        pyautogui.press("enter")

    def close_chat(self):
        self.sleep(0.3)
        pyautogui.press("esc")

    def search_and_open_standalone_user(self, user_id, sleep_time=0.5):
        return self.search_and_open_user(user_id)

    def close_standalone_window(self, sleep_time=0.3, max_retries=3):
        for _ in range(max_retries):
            self.sleep(sleep_time)
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                continue
            class_name = win32gui.GetClassName(hwnd)
            if class_name == "WwStandaloneConversationWnd":
                pyautogui.press("esc")
                return True
            if class_name == "WeWorkWindow":
                print("[提示] 当前活动窗口为主界面，重新搜索用户...")
                return False
        pyautogui.press("esc")
        return True