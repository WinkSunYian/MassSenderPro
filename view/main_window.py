# view/main_window.py
import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from view.constants import DEFAULT_ROW_FONT, STATUS_TEXT
from view.enums.cell_status import CellStatus
from view.models.sheet_model import SheetModel
from view.theme import build_stylesheet, theme_manager
from view.widgets.card_frame import CardFrame
from view.widgets.info_table import InfoTable
from view.widgets.message_table import MessageTable
from view.widgets.prefix_name_table import PrefixNameTable
from view.widgets.scroll_synchronizer import ScrollSynchronizer


class MainWindow(QMainWindow):
    """群发脚本主窗口。"""

    PREFIX_CARD_WIDTH = 240
    INFO_CARD_WIDTH = 240

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("群发助手")
        self.resize(1280, 720)
        self.setStyleSheet(build_stylesheet(theme_manager().palette))

        self._model = SheetModel(message_column_count=2, parent=self)
        self._tables = []

        # 先灌演示数据：顶部配置卡片的输入框在构建时从模型读取初值
        self._load_demo_data()
        self._build_ui()
        self._connect_signals()

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
        root.addLayout(self._build_config_area())
        root.addLayout(self._build_table_area(), 1)
        root.addLayout(self._build_bottom_bar())

        self.setCentralWidget(central)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("群发助手")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self._config_button = QPushButton("配置")
        self._config_button.setToolTip("配置（暂未接入）")
        layout.addWidget(self._config_button)
        return bar

    def _build_bottom_bar(self) -> QHBoxLayout:
        """底部操作栏：左侧模拟发送 / 清除状态，右下角发送。"""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._simulate_button = QPushButton("模拟发送")
        self._simulate_button.setObjectName("PrimaryButton")
        self._clear_button = QPushButton("清除状态")
        self._send_button = QPushButton("发送")
        self._send_button.setObjectName("PrimaryButton")
        self._send_button.setToolTip("开始发送（暂未接入发送逻辑）")

        layout.addWidget(self._simulate_button)
        layout.addWidget(self._clear_button)
        layout.addStretch(1)
        layout.addWidget(self._send_button)
        return layout

    def _build_config_area(self) -> QHBoxLayout:
        """顶部配置区：姓名前缀 + 默认消息，与下方卡片同宽、左右对齐。"""
        layout = QHBoxLayout()
        layout.setSpacing(12)  # 与表格区一致，保证上下两行卡片对齐

        # 卡片一：姓名前缀（与下方「姓名」卡片同宽）
        self._prefix_card = CardFrame("姓名前缀")
        self._prefix_input = QLineEdit(self._model.prefix)
        self._prefix_input.setObjectName("ConfigInput")
        self._prefix_input.setFont(DEFAULT_ROW_FONT)
        self._prefix_input.setPlaceholderText("如 +86")
        self._prefix_input.textChanged.connect(self._model.set_prefix)
        self._prefix_card.add_widget(self._prefix_input)
        self._prefix_card.setFixedWidth(self.PREFIX_CARD_WIDTH)

        # 卡片二：默认消息（与下方「消息」卡片同宽，内部与消息列一一对应）
        self._default_message_card = CardFrame("默认消息")
        # 卡片右上角：增删消息列的 +/− 小按钮
        self._add_column_button = QPushButton("+")
        self._add_column_button.setObjectName("StepButton")
        self._add_column_button.setToolTip("增加消息列")
        self._remove_column_button = QPushButton("−")
        self._remove_column_button.setObjectName("StepButton")
        self._remove_column_button.setToolTip("减少消息列")
        self._default_message_card.add_header_widget(self._add_column_button)
        self._default_message_card.add_header_widget(self._remove_column_button)

        self._default_message_inputs = []
        container = QWidget()
        self._default_message_inputs_layout = QHBoxLayout(container)
        self._default_message_inputs_layout.setContentsMargins(0, 0, 0, 0)
        self._default_message_inputs_layout.setSpacing(6)
        self._default_message_card.add_widget(container)

        # 右侧：状态统计（与下方「信息」卡片对齐，统计发送结果）
        self._stats_card = self._build_stats_card()
        self._stats_card.setFixedWidth(self.INFO_CARD_WIDTH)

        layout.addWidget(self._prefix_card, 0)
        layout.addWidget(self._default_message_card, 1)
        layout.addWidget(self._stats_card, 0)

        self._rebuild_default_message_inputs()
        return layout

    def _build_stats_card(self) -> CardFrame:
        """状态统计卡：标题行右侧总计，卡身 2×2（成功/失败/待发/跳过）。"""
        card = CardFrame("状态统计")

        self._stats_total = QLabel("0")
        self._stats_total.setObjectName("StatsTotal")
        card.add_header_widget(self._stats_total)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        # (标签, 归并类别, 颜色取自的状态, 行, 列)
        specs = [
            ("成功", "success", CellStatus.SUCCESS, 0, 0),
            ("失败", "failed", CellStatus.FAILED, 0, 1),
            ("待发", "pending", CellStatus.PENDING, 1, 0),
            ("跳过", "skipped", CellStatus.SKIPPED, 1, 1),
        ]
        self._stats_values = {}
        for text, key, color_status, row, column in specs:
            cell = QWidget()
            row_layout = QHBoxLayout(cell)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            label = QLabel(text)
            label.setObjectName("StatsLabel")
            value = QLabel("0")
            value.setObjectName("StatsValue")
            row_layout.addWidget(label)
            row_layout.addStretch(1)
            row_layout.addWidget(value)
            grid.addWidget(cell, row, column)
            self._stats_values[key] = (value, color_status)

        container = QWidget()
        container.setLayout(grid)
        card.add_widget(container)
        self._refresh_stats()
        return card

    def _refresh_stats(self, *args) -> None:
        """按行归并统计发送状态（四项之和恒等于总计）。"""
        counts = {status: 0 for status in CellStatus}
        model = self._model
        for row in range(model.rowCount()):
            counts[model.row_status(row)] += 1

        total = model.rowCount()
        grouped = {
            "success": counts[CellStatus.SUCCESS],
            "failed": counts[CellStatus.FAILED] + counts[CellStatus.WARNING],
            "skipped": counts[CellStatus.SKIPPED],
        }
        grouped["pending"] = total - grouped["success"] - grouped["failed"] - grouped["skipped"]

        palette = theme_manager().palette
        self._stats_total.setText(str(total))
        for key, (label, color_status) in self._stats_values.items():
            label.setText(str(grouped[key]))
            fg = palette.status_fg.get(color_status)
            label.setStyleSheet(f"color: {fg.name() if fg else palette.hint_text.name()}")

    def _rebuild_default_message_inputs(self) -> None:
        """按消息列数量重建默认消息输入框（与消息列一一对应）。"""
        while self._default_message_inputs_layout.count():
            item = self._default_message_inputs_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._default_message_inputs.clear()

        for column in range(self._model.message_column_count):
            edit = QLineEdit(self._model.default_message(column))
            edit.setObjectName("ConfigInput")
            edit.setFont(DEFAULT_ROW_FONT)
            edit.setPlaceholderText(f"消息{column + 1} 默认值")
            edit.textChanged.connect(
                lambda text, index=column: self._model.set_default_message(index, text)
            )
            self._default_message_inputs_layout.addWidget(edit, 1)
            self._default_message_inputs.append(edit)

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

        self._name_card = CardFrame()
        self._name_card.add_widget(self._prefix_name_table)
        self._name_card.setFixedWidth(self.PREFIX_CARD_WIDTH)

        self._message_card = CardFrame()
        self._message_card.add_widget(self._message_table)

        self._info_card = CardFrame()
        self._info_card.add_widget(self._info_table)
        self._info_card.setFixedWidth(self.INFO_CARD_WIDTH)

        layout.addWidget(self._name_card, 0)
        layout.addWidget(self._message_card, 1)
        layout.addWidget(self._info_card, 0)

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
        # 发送按钮暂未接入发送逻辑（原型阶段无发送通道）

        # 状态统计：任何单元格变化 / 行增删都刷新
        self._model.dataChanged.connect(self._refresh_stats)
        self._model.rowsInserted.connect(self._refresh_stats)
        self._model.rowsRemoved.connect(self._refresh_stats)

    def _refresh_columns(self) -> None:
        for table in self._tables:
            table.sync_columns()
        # 默认消息输入框与消息列保持一一对应
        self._rebuild_default_message_inputs()

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
        self._model.set_default_message(0, "您好，这是一条默认消息")

    def _on_simulate(self) -> None:
        candidates = [
            CellStatus.SUCCESS,
            CellStatus.FAILED,
            CellStatus.WARNING,
            CellStatus.SKIPPED,
            CellStatus.PENDING,
        ]
        for row in range(self._model.rowCount()):
            status = random.choice(candidates)
            self._model.set_row_status(row, status)
            self._model.set_row_info(row, STATUS_TEXT[status])