# services/SendWorker.py
"""发送线程：在后台跑企业微信自动化，逐行把进度回传给界面。"""
import time
from typing import List

from PySide6.QtCore import QThread, Signal

from models.roster_item import RosterItem


class SendWorker(QThread):
    # (行号) 开始处理某一行
    row_started = Signal(int)
    # (行号, 状态值, 信息文案) 某一行处理结束
    row_finished = Signal(int, str, str)
    # (是否正常结束, 结果说明) 整批任务结束；False 表示异常，需要提示
    finished_signal = Signal(bool, str)
    # (剩余秒数) 开始前的倒计时，界面用它刷新日志
    tick = Signal(int)

    # 开始前的等待秒数（期间按 F12 / 点击进度条可取消）
    COUNTDOWN_SECONDS = 5

    def __init__(
        self,
        roster_service,
        items: List[RosterItem],
        rows: List[int],
        prefix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.roster_service = roster_service
        self.items = items
        self.rows = rows
        self.prefix = prefix
        self.helper = None
        self._stop_requested = False

    def run(self):
        # 自动化依赖（pyautogui/keyboard/win32 等）只在真正发送时才需要，
        # 缺依赖时只影响发送，不影响界面启动。
        try:
            import pyautogui

            from services.BatchSendManager import BatchSendManager
            from services.SkipKeywordConfig import SkipKeywordConfig
            from services.WeWorkAutoServiceImpl import WeWorkAutoServiceImpl
        except ImportError as e:
            self.finished_signal.emit(False, f"缺少自动化依赖：{e}")
            return

        try:
            self.helper = WeWorkAutoServiceImpl(asset_path=None)
            self.helper.stop_event = self._stop_requested
            if self.helper.stop_event:
                raise InterruptedError("收到中断指令，任务已终止。")
            self.helper.start_hotkey_listener()
            # 倒计时留出切换到企业微信窗口的时间（期间按 F12 可取消）
            self._countdown(self.COUNTDOWN_SECONDS)

            manager = BatchSendManager(
                self.helper,
                self.roster_service,
                on_row_start=self.row_started.emit,
                on_row_result=self.row_finished.emit,
                # 每次发送都重读配置，弹窗里改的关键字立即生效
                skip_keywords=SkipKeywordConfig().load(),
            )
            manager.run_tasks(self._apply_prefix(), rows=self.rows)
            self.finished_signal.emit(True, "任务执行完毕")
        except InterruptedError as e:
            # stop_event 置位说明是按 F12 主动终止，属正常结束，不提示
            stopped = bool(self.helper and self.helper.stop_event)
            self.finished_signal.emit(stopped, str(e))
        except pyautogui.FailSafeException:
            # 鼠标停到屏幕安全角（左上角）= 预料中的急停：静默结束，不弹错误窗
            # （BatchSendManager 内部已把安全角转成 InterruptedError，这里兜底）
            if self.helper:
                self.helper.stop_event = True
            self.finished_signal.emit(True, "已触发鼠标安全角，任务自动停止")
        except Exception as e:
            self.finished_signal.emit(False, f"异常：{e}")
        finally:
            if self.helper:
                self.helper.stop_hotkey_listener()
            self.helper = None

    # ------------------------------------------------------------------
    # 倒计时与终止检查
    # ------------------------------------------------------------------
    def _interrupted(self) -> bool:
        return bool(self._stop_requested or (self.helper and self.helper.stop_event))

    def _countdown(self, seconds: int) -> None:
        """开始前倒计时：每秒发一次 tick，期间按 F12 / 点击进度条可取消。"""
        remaining = seconds
        while remaining > 0:
            if self._interrupted():
                raise InterruptedError("收到中断指令，任务已终止。")
            self.tick.emit(remaining)
            time.sleep(1)
            remaining -= 1

    def _apply_prefix(self) -> List[RosterItem]:
        if not self.prefix:
            return self.items
        return [
            RosterItem(user_id=self.prefix + item.user_id, payload=item.payload)
            for item in self.items
        ]

    def stop(self):
        """终止：置位标志，倒计时 / 自动化在下一个检查点立即中断。"""
        self._stop_requested = True
        if self.helper:
            self.helper.stop_event = True
