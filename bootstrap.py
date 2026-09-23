# bootstrap.py
"""应用启动引导：负责创建 QApplication、主窗口并进入事件循环。"""
import sys
from typing import List, Optional

from PySide6.QtWidgets import QApplication

from view import MainWindow


class AppRunner:
    """应用运行器：封装 QApplication 的创建与事件循环的执行。"""

    def __init__(self, argv: Optional[List[str]] = None) -> None:
        self._argv = list(sys.argv if argv is None else argv)
        self._app: Optional[QApplication] = None
        self._window: Optional[MainWindow] = None

    @property
    def app(self) -> Optional[QApplication]:
        return self._app

    @property
    def window(self) -> Optional[MainWindow]:
        return self._window

    def run(self) -> int:
        """启动应用并返回事件循环的退出码。"""
        self._app = QApplication(self._argv)
        self._window = MainWindow()
        self._window.show()
        return self._app.exec()
