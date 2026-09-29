# view/widgets/clickable_progress_bar.py
"""可点击的进度条：发送中显示进度，点击发出暂停 / 继续信号。"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QProgressBar


class ClickableProgressBar(QProgressBar):
    """左键点击发出 clicked 信号的进度条。"""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
