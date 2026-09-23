# view/main_window.py
import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from view.constants import STATUS_TEXT
from view.enums.cell_status import CellStatus
from view.models.sheet_model import SheetModel
from view.widgets.card_frame import CardFrame
from view.widgets.info_table import InfoTable
from view.widgets.message_table import MessageTable
from view.widgets.prefix_name_table import PrefixNameTable
from view.widgets.scroll_synchronizer import ScrollSynchronizer

WINDOW_STYLE = """
QMainWindow, QWidget#CentralWidget {
    background-color: #F4F6F9;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #DCDFE6;
    border-radius: 8px;
    padding: 6px 14px;
    color: #303133;
}
QPushButton:hover {
    border-color: #409EFF;
    color: #409EFF;
}
QPushButton:pressed {
    background-color: #ECF5FF;
}
QPushButton#PrimaryButton {
    background-color: #409EFF;
    border-color: #409EFF;
    color: #FFFFFF;
}
QPushButton#PrimaryButton:hover {
    background-color: #66B1FF;
    border-color: #66B1FF;
    color: #FFFFFF;
}
QLabel#HintLabel {
    color: #909399;
    font-size: 12px;
}
"""


class MainWindow(QMainWindow):
    """群发脚本主窗口。"""

    PREFIX_CARD_WIDTH = 240
    INFO_CARD_WIDTH = 240

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("群发助手")
        self.resize(1280, 720)
        self.setStyleSheet(WINDOW_STYLE)

        self._model = SheetModel(message_column_count=2, parent=self)
        self._tables = []

        self._build_ui()
        self._connect_signals()
        self._load_demo_data()

    # ------------------------------------------------------------------
    # 构建界面
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("CentralWidget")
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(self._build_toolbar())
        root.addLayout(self._build_table_area(), 1)

        self.setCentralWidget(central)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._add_column_button = QPushButton("+ 消息列")
        self._remove_column_button = QPushButton("- 消息列")
        self._simulate_button = QPushButton("模拟发送")
        self._simulate_button.setObjectName("PrimaryButton")
        self._clear_button = QPushButton("清除状态")

        layout.addWidget(self._add_column_button)
        layout.addWidget(self._remove_column_button)
        layout.addWidget(self._simulate_button)
        layout.addWidget(self._clear_button)
        layout.addStretch(1)

        hint = QLabel("提示：选中一列后按 Ctrl+V 可批量粘贴，第一行可配置前缀与默认消息")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint)
        return bar

    def _build_table_area(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self._prefix_name_table = PrefixNameTable()
        self._message_table = MessageTable()
        self._info_table = InfoTable()

        for table in (self._prefix_name_table, self._message_table, self._info_table):
            table.setModel(self._model)
            self._tables.append(table)

        self._prefix_name_table.setMinimumWidth(0)
        self._info_table.setMinimumWidth(0)

        prefix_card = CardFrame()
        prefix_card.add_widget(self._prefix_name_table)
        prefix_card.setFixedWidth(self.PREFIX_CARD_WIDTH)

        message_card = CardFrame()
        message_card.add_widget(self._message_table)

        info_card = CardFrame()
        info_card.add_widget(self._info_table)
        info_card.setFixedWidth(self.INFO_CARD_WIDTH)

        layout.addWidget(prefix_card, 0)
        layout.addWidget(message_card, 1)
        layout.addWidget(info_card, 0)

        self._scroll_synchronizer = ScrollSynchronizer(self._tables, self)
        return layout

    # ------------------------------------------------------------------
    # 信号连接
    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        for table in self._tables:
            table.pasteRequested.connect(self._model.paste_text)

        self._model.columnsChanged.connect(self._refresh_columns)

        self._add_column_button.clicked.connect(self._model.add_message_column)
        self._remove_column_button.clicked.connect(self._on_remove_column)
        self._simulate_button.clicked.connect(self._on_simulate)
        self._clear_button.clicked.connect(self._model.clear_statuses)

    def _refresh_columns(self) -> None:
        for table in self._tables:
            table.sync_columns()

    def _on_remove_column(self) -> None:
        self._model.remove_message_column()

    # ------------------------------------------------------------------
    # 演示数据与模拟发送
    # ------------------------------------------------------------------
    def _load_demo_data(self) -> None:
        self._model.set_prefix("+86")
        names = ["张三", "李四", "王五"]
        self._model.paste_text(
            self._model.rowCount(),
            SheetModel.NAME_COLUMN,
            "\n".join(names),
        )

        self._model.paste_text(0, SheetModel.FIRST_MESSAGE_COLUMN, "您好，这是一条默认消息")

    def _on_simulate(self) -> None:
        candidates = [
            CellStatus.SUCCESS,
            CellStatus.FAILED,
            CellStatus.WARNING,
            CellStatus.SKIPPED,
            CellStatus.PENDING,
        ]
        for row in range(1, self._model.rowCount()):
            status = random.choice(candidates)
            self._model.set_row_status(row, status)
            self._model.set_row_info(row, STATUS_TEXT[status])