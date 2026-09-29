# services/ListSendWorker.py
"""列表发送线程：与姓名表格完全无关的另一种发送逻辑。

固定循环 DEFAULT_LOOP_COUNT 次（原 FromBottomToTop 脚本为 range(200)），
每轮 Alt+End 跳到会话列表最底部 → 粘贴剪贴板 → 回车发送。

- 不读姓名列表：items / rows 一概不用，表格行状态、统计卡都不动；
- 进度通过 progress(已完成, 总数) 信号单独上报，驱动界面进度条；
- 倒计时 / F12 终止 / 切窗保护沿用 SendWorker 的设施。

约定：剪贴板内容由用户提前复制好（文本或文件），本线程只读检测、不改写剪贴板。
"""
from PySide6.QtCore import Signal

from services.SendWorker import SendWorker


class ListSendWorker(SendWorker):
    """继承 SendWorker：复用倒计时 / 中断检查 / stop / tick 信号。"""

    # 默认循环次数（原脚本 range(200)）；构造时传 count 可覆盖
    DEFAULT_LOOP_COUNT = 200
    # 单轮节奏（秒）：调这三个常量即可调速（pyautogui.PAUSE 已归零）
    DELAY_AFTER_MOVE = 0.6    # Alt+End 切会话后，等输入框就绪再粘贴
    DELAY_AFTER_PASTE = 0.4   # 粘贴渲染完再回车
    DELAY_AFTER_SEND = 0.5   # 回车发送后，等会话列表重排再切下一条

    # (已完成轮数, 总轮数) 逐轮进度，驱动界面进度条（与表格行信号无关）
    progress = Signal(int, int)

    def __init__(self, count: int = None, parent=None) -> None:
        super().__init__(
            roster_service=None, items=[], rows=[], prefix="", parent=parent
        )
        self._count = self.DEFAULT_LOOP_COUNT if count is None else count

    def run(self) -> None:
        # 自动化依赖只在真正发送时才导入，缺依赖只影响发送、不影响界面
        try:
            import pyautogui
            from services.WeWorkAutoServiceImpl import WeWorkAutoServiceImpl
        except ImportError as e:
            self.finished_signal.emit(False, f"缺少自动化依赖：{e}")
            return

        try:
            if not self._clipboard_has_content():
                self.finished_signal.emit(
                    False, "剪贴板里没有内容，请先复制要发送的内容（文本或文件）"
                )
                return

            self.helper = WeWorkAutoServiceImpl(asset_path=None)
            self.helper.stop_event = self._stop_requested
            if self.helper.stop_event:
                raise InterruptedError("收到中断指令，任务已终止。")
            self.helper.start_hotkey_listener()
            # 倒计时留出把聊天窗口切到前台的时间（期间按 F12 可取消）
            self._countdown(self.COUNTDOWN_SECONDS)

            # 记录前台窗口类名：中途切走窗口立刻终止，防止键鼠注入到别的程序
            target_class = self._foreground_class()
            pyautogui.PAUSE = 0  # 注入零停顿，节奏完全由上面的 DELAY 常量控制

            for index in range(1, self._count + 1):
                self._check_injection(target_class)
                pyautogui.hotkey("alt", "end")  # 跳到会话列表最底部一条
                self.helper.sleep(self.DELAY_AFTER_MOVE)
                pyautogui.hotkey("ctrl", "v")
                self.helper.sleep(self.DELAY_AFTER_PASTE)
                pyautogui.press("enter")

                self.progress.emit(index, self._count)
                print(f"[列表发送] {index}/{self._count}")
                self.helper.sleep(self.DELAY_AFTER_SEND)

            self.finished_signal.emit(True, "任务执行完毕")
        except InterruptedError as e:
            # stop_event 置位 = 按 F12 / 点击终止（正常结束，不弹窗）
            stopped = bool(self.helper and self.helper.stop_event)
            self.finished_signal.emit(stopped, str(e))
        except pyautogui.FailSafeException:
            # 鼠标停到屏幕安全角（左上角）= 预料中的急停：静默停止，不弹错误窗
            self.finished_signal.emit(True, "已触发鼠标安全角，列表发送自动停止")
        except Exception as e:
            self.finished_signal.emit(False, f"异常：{e}")
        finally:
            if self.helper:
                self.helper.stop_hotkey_listener()
            self.helper = None

    # ------------------------------------------------------------------
    # 中断与校验
    # ------------------------------------------------------------------
    def _check_injection(self, target_class: str) -> None:
        """每轮注入前：F12/点击终止 → 中断；前台窗口类名变了 → 已切走，终止。"""
        if self._interrupted():
            raise InterruptedError("收到中断指令，任务已终止。")
        current = self._foreground_class()
        if target_class and current != target_class:
            raise InterruptedError(
                f"已切离聊天窗口（当前: {current or '无'}），任务终止。"
            )

    # ------------------------------------------------------------------
    # 环境检测
    # ------------------------------------------------------------------
    @staticmethod
    def _foreground_class() -> str:
        try:
            import win32gui

            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetClassName(hwnd) if hwnd else ""
        except Exception:
            return ""

    @staticmethod
    def _clipboard_has_content() -> bool:
        """剪贴板里要有文本或文件；检测不了时放行（不破坏原脚本行为）。"""
        try:
            import win32clipboard
            import win32con

            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        try:
            import pyperclip

            return bool(pyperclip.paste().strip())
        except Exception:
            return True
