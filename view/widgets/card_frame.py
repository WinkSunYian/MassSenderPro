# view/widgets/card_frame.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class CardFrame(QFrame):
    """圆角卡片容器，可带标题，内部通过 add_widget 挂载内容。

    标题行布局为 [标题][拉伸][控件...]，可用 add_header_widget
    往右上角挂控件。样式（背景/边框/圆角/标题）来自根窗口的
    统一 QSS（view/theme.py）。
    """

    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(0)

        # 标题行：标题居左 + 拉伸，右侧留给 add_header_widget 的控件
        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(6)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            self._header_layout.addWidget(label)
        self._header_layout.addStretch(1)
        self._layout.addLayout(self._header_layout)

    def add_widget(self, widget) -> None:
        self._layout.addWidget(widget)

    def add_header_widget(self, widget) -> None:
        """在标题行右侧（卡片右上角）添加控件。"""
        self._header_layout.addWidget(widget)
