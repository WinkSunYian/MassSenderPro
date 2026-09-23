# view/widgets/card_frame.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout

from view.constants import CARD_STYLE


class CardFrame(QFrame):
    """圆角卡片容器，内部通过 add_widget 挂载内容。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(CARD_STYLE)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(0)

    def add_widget(self, widget) -> None:
        self._layout.addWidget(widget)