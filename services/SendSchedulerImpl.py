# services/SendSchedulerImpl.py
"""发送调度器实现：创建并驱动 SendWorker，把进度信号转发出去。"""
from typing import List

from models.roster_item import RosterItem
from services.RosterServiceImpl import RosterServiceImpl
from services.SendScheduler import SendScheduler
from services.SendWorker import SendWorker


class SendSchedulerImpl(SendScheduler):
    def __init__(self, roster_service: RosterServiceImpl = None, parent=None) -> None:
        super().__init__(parent)
        self.roster_service = roster_service
        self._worker: SendWorker = None

    def start(
        self, items: List[RosterItem], rows: List[int], prefix: str = "", mode: str = "normal"
    ) -> bool:
        if self.is_running():
            return False
        if mode == "list":
            # 列表发送：不读姓名列表，固定循环次数，Alt+End 逐轮粘贴
            # （剪贴板内容由用户提前复制）
            from services.ListSendWorker import ListSendWorker

            self._worker = ListSendWorker(parent=self)
        else:
            self._worker = SendWorker(
                roster_service=self.roster_service,
                items=items,
                rows=rows,
                prefix=prefix,
                parent=self,
            )
        self._worker.row_started.connect(self.row_started)
        self._worker.row_finished.connect(self.row_finished)
        self._worker.finished_signal.connect(self._on_worker_finished)
        self._worker.tick.connect(self.tick)
        if mode == "list":
            self._worker.progress.connect(self.progress)
        self._worker.start()
        return True

    def stop(self):
        if self._worker:
            self._worker.stop()

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def wait(self, timeout: int = 3000) -> bool:
        if self._worker is None:
            return True
        return self._worker.wait(timeout)

    def _on_worker_finished(self, ok: bool, message: str) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.deleteLater()
        self.finished.emit(ok, message)
