from typing import List

from PySide6.QtCore import QObject, Signal

from models.roster_item import RosterItem


class SendScheduler(QObject):
    """发送调度器基类：持有进度信号，子类负责驱动发送线程。"""

    # (行号) 开始处理某一行
    row_started = Signal(int)
    # (行号, 状态值, 信息文案) 某一行处理结束，状态值取 CellStatus.value
    row_finished = Signal(int, str, str)
    # (是否正常结束, 结果说明) 整批任务结束；False 表示异常终止，需要提示
    finished = Signal(bool, str)
    # (剩余秒数) 开始前 / 恢复后的倒计时（界面日志栏用）
    tick = Signal(int)
    # (已完成轮数, 总轮数) 列表发送逐轮进度（正常发送不用）
    progress = Signal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def start(
        self, items: List[RosterItem], rows: List[int], prefix: str = "", mode: str = "normal"
    ) -> bool:
        """启动发送；mode="normal" 搜索发送，mode="list" 列表发送（Alt+End）。"""
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError

    def wait(self, timeout: int = 3000) -> bool:
        """等待发送线程退出（关闭窗口前调用）。"""
        return True
