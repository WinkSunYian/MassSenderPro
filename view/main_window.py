# view/main_window.py
import os

import app_paths
from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.roster_item import RosterItem
from services.ListSendWorker import ListSendWorker
from services.PrefixConfig import PrefixConfig
from services.RosterServiceImpl import RosterServiceImpl
from services.SendSchedulerImpl import SendSchedulerImpl
from services.SkipKeywordConfig import SkipKeywordConfig
from view.config_dialog import ConfigDialog
from view.constants import (
    DEFAULT_ROW_FONT,
    FAILED_EMPTY_TEXT,
    NO_PREFIX_LABEL,
    STATUS_TEXT,
)
from view.enums.cell_status import CellStatus
from view.models.default_message_model import DefaultMessageModel
from view.models.sheet_model import SheetModel
from view.theme import build_stylesheet, theme_manager
from view.widgets.card_frame import CardFrame
from view.widgets.clickable_progress_bar import ClickableProgressBar
from view.widgets.default_message_table import DefaultMessageTable
from view.widgets.info_table import InfoTable
from view.widgets.long_press_button import LongPressButton
from view.widgets.message_table import MessageTable
from view.widgets.prefix_name_table import PrefixNameTable
from view.widgets.scroll_synchronizer import ScrollSynchronizer
from view.widgets.send_mode_mask import SendModeMask


class MainWindow(QMainWindow):
    """群发脚本主窗口。"""

    PREFIX_CARD_WIDTH = 240
    INFO_CARD_WIDTH = 240

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("群发助手")
        self.resize(1280, 720)
        self.setStyleSheet(build_stylesheet(theme_manager().palette))

        self._model = SheetModel(message_column_count=1, parent=self)
        self._tables = []
        # 发送进度状态：发送按钮在「按钮 ↔ 进度条」间切换，进度条点击即终止
        self._sending = False
        self._send_done = 0
        self._send_total = 0
        # 发送模式："normal" 搜索发送 / "list" 列表发送（右键长按发送按钮切换）
        self._send_mode = "normal"
        self._mode_locked = False
        # 长按计时：右键按住超过阈值才切换模式，普通右键点一下不切
        self._right_held = False
        self._mode_press_timer = QTimer(self)
        self._mode_press_timer.setSingleShot(True)
        self._mode_press_timer.timeout.connect(self._on_send_mode_long_press)

        # 发送链路：名册落盘服务 + 发送调度器（内部驱动 SendWorker 线程）
        # 失败名册写 %APPDATA%\MassSenderPro\logs（打包后安装目录不可写）
        self._roster_service = RosterServiceImpl(logs_dir=app_paths.logs_dir())
        self._scheduler = SendSchedulerImpl(self._roster_service, self)
        # 跳过关键字配置（配置弹窗读写同一份 configs/skip_keywords.txt）
        self._skip_config = SkipKeywordConfig()
        # 姓名前缀列表配置（configs/prefixes.txt，顶部下拉读写）
        self._prefix_config = PrefixConfig()

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
        # 发送按钮与进度条同高（挂进带样式表的窗口后 sizeHint 才准确）
        height = self._send_button.sizeHint().height()
        self._send_stack.setFixedHeight(height)
        self._list_send_button.setFixedHeight(height)
        self._progress_bar.setFixedHeight(height)

        # 列表发送模式遮罩：铺满主区域，仅放行右下角发送区
        self._mode_mask = SendModeMask(central)
        self._mode_mask.hide()
        central.installEventFilter(self)  # 跟随窗口尺寸变化重排遮罩
        self._update_mask_geometry()

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
        self._config_button.setToolTip("配置中心：姓名前缀 / 跳过关键字")
        layout.addWidget(self._config_button)
        return bar

    def _build_bottom_bar(self) -> QHBoxLayout:
        """底部操作栏：左侧清除状态 / 移除成功发送，右下角发送（发送中变进度条）。"""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._clear_button = QPushButton("清除状态")
        self._remove_success_button = QPushButton("移除成功发送")
        self._remove_success_button.setToolTip("删除已发送成功的行")

        self._send_button = LongPressButton("发送")
        self._send_button.setObjectName("PrimaryButton")
        self._send_button.setToolTip(
            "开始发送（运行中按 F12 紧急终止；右键长按切换发送模式）"
        )
        # 列表发送模式按钮（青色）：右键长按「发送」按钮切换到这一档
        self._list_send_button = LongPressButton("列表发送")
        self._list_send_button.setObjectName("ListSendButton")
        self._list_send_button.setToolTip(
            "列表发送：Alt+End 跳到列表底部 → 粘贴 → 回车"
            "（先复制好内容到剪贴板；运行中按 F12 终止；右键长按切回正常模式）"
        )

        # 发送中：按钮切换成进度条，点击进度条 = 终止（与按 F12 相同）
        self._progress_bar = ClickableProgressBar()
        self._progress_bar.setObjectName("SendProgress")
        self._progress_bar.setFixedWidth(self.INFO_CARD_WIDTH)
        self._progress_bar.setFormat("点击或按F12终止")
        self._progress_bar.setToolTip("点击或按 F12 终止")
        self._progress_bar.clicked.connect(self._on_send)

        # 与信息卡片同宽：发送按钮 / 列表发送 / 进度条叠放在定宽容器里切换
        self._send_stack = QStackedWidget()
        self._send_stack.setFixedWidth(self.INFO_CARD_WIDTH)
        self._send_stack.addWidget(self._send_button)  # 0：正常发送
        self._send_stack.addWidget(self._list_send_button)  # 1：列表发送
        self._send_stack.addWidget(self._progress_bar)  # 2：发送中（点击即终止）

        layout.addWidget(self._clear_button)
        layout.addWidget(self._remove_success_button)

        # 中间空白区：单行提示（倒计时 / 正在发送谁 / 终止原因）
        self._log_label = QLabel("")
        self._log_label.setObjectName("LogBar")
        self._log_label.setWordWrap(False)
        self._log_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._log_label, 1)

        layout.addWidget(self._send_stack)
        return layout

    def _build_config_area(self) -> QHBoxLayout:
        """顶部配置区：姓名前缀 + 默认消息，与下方卡片同宽、左右对齐。"""
        layout = QHBoxLayout()
        layout.setSpacing(12)  # 与表格区一致，保证上下两行卡片对齐

        # 卡片一：姓名前缀（纯下拉，增删在「配置中心」里完成）
        self._prefix_card = CardFrame("姓名前缀")
        self._prefix_combo = QComboBox()
        self._prefix_combo.setObjectName("ConfigInput")
        self._prefix_combo.setFont(DEFAULT_ROW_FONT)
        self._prefix_combo.setMinimumHeight(30)
        self._prefix_combo.setToolTip("选择姓名前缀（增删在「配置」里）")
        # activated 只在用户手动选择时触发，程序重建列表不会误触
        self._prefix_combo.activated.connect(self._on_prefix_activated)
        self._prefix_card.add_widget(self._prefix_combo)
        self._prefix_card.setFixedWidth(self.PREFIX_CARD_WIDTH)
        self._rebuild_prefix_combo(self._model.prefix)

        # 卡片二：默认消息（与下方「消息」卡片同宽，内部与消息列一一对应）
        self._default_message_card = CardFrame("默认消息")
        # 卡片右上角：消息列 −/+ 小按钮（减少在左、增加在右）
        self._remove_column_button = QPushButton("−")
        self._remove_column_button.setObjectName("StepButton")
        self._remove_column_button.setToolTip("减少消息列")
        self._add_column_button = QPushButton("+")
        self._add_column_button.setObjectName("StepButton")
        self._add_column_button.setToolTip("增加消息列")
        # 头排按钮垂直策略改 Preferred：卡片被拉高时标题行能和「姓名前缀」
        # 卡一样从 28px 撑到 33px，两个输入框才会在同一水平线上
        self._remove_column_button.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Preferred
        )
        self._add_column_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self._default_message_card.add_header_widget(self._remove_column_button)
        self._default_message_card.add_header_widget(self._add_column_button)
        # 至少保留一个消息列：只剩一列时禁用「−」
        self._remove_column_button.setEnabled(self._model.message_column_count > 1)

        # 卡片二内容：与下方「消息」表格同款的默认消息表格（1 行 × N 消息列，
        # 图片显示小缩略图、文字显示原文，绘制/编辑/粘贴与消息列完全一致）
        self._default_message_model = DefaultMessageModel(self._model, self)
        self._default_message_table = DefaultMessageTable()
        self._default_message_table.setModel(self._default_message_model)
        self._default_message_card.add_widget(self._default_message_table)

        # 右侧：状态统计（与下方「信息」卡片对齐，统计发送结果）
        self._stats_card = self._build_stats_card()
        self._stats_card.setFixedWidth(self.INFO_CARD_WIDTH)

        layout.addWidget(self._prefix_card, 0)
        layout.addWidget(self._default_message_card, 1)
        layout.addWidget(self._stats_card, 0)
        return layout

    def _rebuild_prefix_combo(self, select: str = None) -> None:
        """重建前缀下拉：（无前缀）+ configs 里的前缀，并选中 select。"""
        current = self._model.prefix if select is None else select

        self._prefix_combo.clear()
        self._prefix_combo.addItem(NO_PREFIX_LABEL, "")
        for prefix in self._prefix_config.load():
            self._prefix_combo.addItem(prefix, prefix)

        target = -1
        for index in range(self._prefix_combo.count()):
            if self._prefix_combo.itemData(index) == current:
                target = index
                break
        if target < 0:
            # 当前前缀已不在配置里（例如在配置中心删掉了）：回落「（无前缀）」
            target = 0
            self._model.set_prefix("")
        self._prefix_combo.setCurrentIndex(target)

    def _on_prefix_activated(self, index: int) -> None:
        """下拉选中：把前缀写进模型。"""
        self._model.set_prefix(self._prefix_combo.itemData(index) or "")

    def _sync_prefix_from_config(self) -> None:
        """配置中心保存后同步下拉；当前前缀被删掉则回落「（无前缀）」。"""
        if self._model.prefix and self._model.prefix not in self._prefix_config.load():
            self._model.set_prefix("")
        self._rebuild_prefix_combo(self._model.prefix)

    def _build_stats_card(self) -> CardFrame:
        """状态统计卡：成功 / 失败 / 待发 / 跳过 2×2（口径见 _refresh_stats）。"""
        card = CardFrame("状态统计")

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

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
        """按行归并统计发送状态（四项之和恒等于总计）。

        - 成功：发送成功
        - 失败：姓名与备注不符 / 未定位到聊天窗口 / 内容为空 / 发送异常
        - 跳过：备注包含关键字
        - 待发：尚未处理
        """
        counts = {status: 0 for status in CellStatus}
        model = self._model
        total = 0
        for row in range(model.rowCount()):
            if not model.user_name(row).strip():
                # 空姓名输入行不参与发送，也不计入统计
                continue
            counts[model.row_status(row)] += 1
            total += 1
        grouped = {
            "success": counts[CellStatus.SUCCESS],
            "failed": counts[CellStatus.FAILED] + counts[CellStatus.WARNING],
            "skipped": counts[CellStatus.SKIPPED],
        }
        grouped["pending"] = total - grouped["success"] - grouped["failed"] - grouped["skipped"]

        palette = theme_manager().palette
        for key, (label, color_status) in self._stats_values.items():
            label.setText(str(grouped[key]))
            fg = palette.status_fg.get(color_status)
            label.setStyleSheet(f"color: {fg.name() if fg else palette.hint_text.name()}")

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
            table.selectionModel().selectionChanged.connect(
                lambda selected, deselected, source=table: self._on_table_selection_changed(
                    source
                )
            )

        # 顶部默认消息表也参与四表互斥选中（粘贴单独连接，见下）
        self._default_message_table.selectionModel().selectionChanged.connect(
            lambda selected, deselected, source=self._default_message_table: (
                self._on_table_selection_changed(source)
            )
        )

        self._model.columnsChanged.connect(self._refresh_columns)

        # 底部单行提示：手动输入重名被拒 / 姓名粘贴导入统计
        self._model.duplicateName.connect(self._on_duplicate_name)
        self._model.namesPasted.connect(self._on_names_pasted)

        # 默认消息表格：单元格粘贴（文件路径 / 文本）写入对应列默认值
        self._default_message_table.pasteRequested.connect(
            self._on_paste_default_message
        )

        self._add_column_button.clicked.connect(self._model.add_message_column)
        self._remove_column_button.clicked.connect(self._on_remove_column)
        self._config_button.clicked.connect(self._on_open_config)
        self._clear_button.clicked.connect(self._model.clear_statuses)
        self._remove_success_button.clicked.connect(self._on_remove_success)
        self._send_button.clicked.connect(self._on_send)
        self._list_send_button.clicked.connect(self._on_send)
        # 右键（含长按）发送按钮切换发送模式，并吞掉右键菜单
        for button in (self._send_button, self._list_send_button):
            button.installEventFilter(self)
        # 遮罩放行区：左键开始/终止发送，右键按下/松开交给长按计时
        self._mode_mask.send_clicked.connect(self._on_send)
        self._mode_mask.mode_pressed.connect(self._start_send_mode_long_press)
        self._mode_mask.mode_released.connect(self._cancel_send_mode_long_press)

        # 发送进度：逐行刷新状态与信息列，并让表格跟随发送行
        self._scheduler.row_started.connect(self._on_row_started)
        self._scheduler.row_finished.connect(self._on_row_finished)
        self._scheduler.finished.connect(self._on_send_finished)
        # 列表发送逐轮进度（不走行信号）
        self._scheduler.progress.connect(self._on_list_progress)
        # 开始前 / 恢复后的倒计时刷新日志栏
        self._scheduler.tick.connect(self._on_countdown_tick)

        # 状态统计：任何单元格变化 / 行增删都刷新
        self._model.dataChanged.connect(self._refresh_stats)
        self._model.rowsInserted.connect(self._refresh_stats)
        self._model.rowsRemoved.connect(self._refresh_stats)

    def _refresh_columns(self) -> None:
        for table in self._tables:
            table.sync_columns()
        # 默认消息表格与消息列保持一一对应
        self._default_message_model.sync_columns()
        self._default_message_table.sync_columns()
        # 至少保留一个消息列：只剩一列时禁用「−」（锁定期间不动，解锁时统一还原）
        if not self._mode_locked:
            self._remove_column_button.setEnabled(
                self._model.message_column_count > 1
            )

    def _on_table_selection_changed(self, source) -> None:
        """四张表格互斥选中：任一表格产生选中时清掉另外三张的选中
        （下方姓名/消息/信息三表 + 顶部默认消息表）。"""
        selection = source.selectionModel()
        if selection is None or not selection.hasSelection():
            return
        for table in self._all_tables():
            if table is source:
                continue
            other = table.selectionModel()
            if other is not None and other.hasSelection():
                other.clearSelection()

    def _all_tables(self):
        # 互斥选中的全部表格：下方三表 + 顶部默认消息表
        return (*self._tables, self._default_message_table)

    def _on_remove_column(self) -> None:
        self._model.remove_message_column()

    def _on_paste_default_message(self, row: int, column: int, text: str) -> None:
        """默认消息表格粘贴：写入对应消息列的默认值并刷新该格显示。"""
        self._model.set_default_message(column, text)
        index = self._default_message_model.index(0, column)
        self._default_message_model.dataChanged.emit(
            index, index, [Qt.DisplayRole, Qt.EditRole]
        )

    def _on_open_config(self) -> None:
        """打开配置中心：各页改动即时写入 configs，关闭时兜底同步下拉。"""
        dialog = ConfigDialog(self._prefix_config, self._skip_config, parent=self)
        dialog.changed.connect(self._on_config_changed)
        dialog.exec()
        self._sync_prefix_from_config()

    def _on_config_changed(self, key: str) -> None:
        """配置中心某页即时变更：前缀变化立刻反映到顶部下拉。"""
        if key == "prefixes":
            self._sync_prefix_from_config()

    # ------------------------------------------------------------------
    # 发送模式（正常 / 列表）与遮罩
    # ------------------------------------------------------------------
    # 发送栈页签：0 正常发送 / 1 列表发送 / 2 发送中进度条
    SEND_STACK_NORMAL = 0
    SEND_STACK_LIST = 1
    SEND_STACK_PROGRESS = 2
    # 右键长按多久才切换发送模式（普通右键点一下不切）
    SEND_MODE_LONG_PRESS_MS = 500

    def eventFilter(self, obj, event) -> bool:
        # 发送按钮：右键长按才切换模式，不弹右键菜单
        if obj is self._send_button or obj is self._list_send_button:
            if event.type() == QEvent.ContextMenu:
                return True
            if (
                event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.RightButton
            ):
                self._start_send_mode_long_press()
                return True
            if (
                event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.RightButton
            ):
                self._cancel_send_mode_long_press()
                return True
        elif obj is self.centralWidget() and event.type() == QEvent.Resize:
            # 布局下一拍才跑完：延后一帧取发送栈的准确位置
            QTimer.singleShot(0, self._update_mask_geometry)
        return super().eventFilter(obj, event)

    def _hold_button(self):
        """当前发送区里能画长按动画的按钮（发送中是进度条则没有）。"""
        widget = self._send_stack.currentWidget()
        return widget if isinstance(widget, LongPressButton) else None

    def _start_send_mode_long_press(self) -> None:
        """右键按下：开始长按计时 + 按钮填充动画，到时才切换模式。"""
        self._right_held = True
        self._mode_press_timer.start(self.SEND_MODE_LONG_PRESS_MS)
        button = self._hold_button()
        if button is not None:
            button.startHold(self.SEND_MODE_LONG_PRESS_MS)

    def _cancel_send_mode_long_press(self) -> None:
        """右键松开：没满长按就取消，点一下不切换（填充回缩归零）。"""
        self._right_held = False
        self._mode_press_timer.stop()
        button = self._hold_button()
        if button is not None:
            button.cancelHold()

    def _on_send_mode_long_press(self) -> None:
        """长按到时：仍按着右键才切换（松开走取消，不会重复切）。"""
        if self._right_held:
            button = self._hold_button()
            if button is not None:
                button.finishHold()  # 撑满 → 复位；切换本身就是完成动效
            self._toggle_send_mode()

    def _toggle_send_mode(self) -> None:
        """右键长按发送按钮：正常发送 ↔ 列表发送（发送中不允许切换）。"""
        if self._sending or self._scheduler.is_running():
            return
        self._send_mode = "normal" if self._send_mode == "list" else "list"
        self._apply_send_mode()

    def _apply_send_mode(self) -> None:
        """模式落地：发送区显示对应按钮、遮罩显隐、其它控件锁定。"""
        is_list = self._send_mode == "list"
        self._mode_locked = is_list
        self._refresh_send_stack()
        if is_list:
            self._mode_mask.show()
            self._set_controls_locked(True)
            self._set_log("列表发送模式：其它控件已锁定，请先复制内容到剪贴板")
        else:
            self._mode_mask.hide()
            self._set_controls_locked(False)
            self._set_log("已切换回正常发送模式")
        self._update_mask_geometry()

    def _set_controls_locked(self, locked: bool) -> None:
        """列表发送模式：除右下角发送区外的交互控件全部禁用。"""
        for widget in (
            self._config_button,
            self._prefix_combo,
            self._add_column_button,
            self._remove_column_button,
            self._clear_button,
            self._remove_success_button,
            *self._all_tables(),
        ):
            widget.setEnabled(not locked)
        if not locked:
            # 解锁时按各自规则还原（消息列至少 1；发送中「移除成功」保持禁用）
            self._remove_column_button.setEnabled(
                self._model.message_column_count > 1
            )
            self._remove_success_button.setEnabled(not self._sending)

    def _refresh_send_stack(self) -> None:
        """发送区页签：发送中 → 进度条；否则按模式显示对应按钮。"""
        if self._sending:
            index = self.SEND_STACK_PROGRESS
        elif self._send_mode == "list":
            index = self.SEND_STACK_LIST
        else:
            index = self.SEND_STACK_NORMAL
        self._send_stack.setCurrentIndex(index)
        self._update_mask_geometry()

    def _update_mask_geometry(self) -> None:
        """遮罩铺满主区域；放行区 = 发送栈，底部提示行保持明亮。"""
        mask = getattr(self, "_mode_mask", None)
        central = self.centralWidget()
        if mask is None or central is None:
            return
        mask.setGeometry(central.rect())
        origin = self._send_stack.mapTo(central, QPoint(0, 0))
        log_origin = self._log_label.mapTo(central, QPoint(0, 0))
        mask.set_regions(
            QRect(origin, self._send_stack.size()),
            [QRect(log_origin, self._log_label.size())],
        )
        if mask.isVisible():
            mask.raise_()

    # ------------------------------------------------------------------
    # 发送链路
    # ------------------------------------------------------------------
    def _on_send(self) -> None:
        """开始发送；发送中（按钮或进度条）再次点击则直接终止。"""
        if self._sending:
            self._scheduler.stop()
            self._progress_bar.setFormat("正在终止…")
            return
        if self._scheduler.is_running():
            return

        if self._send_mode == "list":
            # 列表发送是另一种逻辑：固定循环次数，完全不读姓名列表
            items, rows = [], []
            total = ListSendWorker.DEFAULT_LOOP_COUNT
        else:
            items, rows, empty_rows = self._collect_tasks()
            for row in empty_rows:
                # 消息全空的行按新口径计入「失败」
                self._model.set_row_status(row, CellStatus.FAILED)
                self._model.set_row_info(row, FAILED_EMPTY_TEXT)
            if not items:
                if not empty_rows:
                    # 名单本来就空 / 有行但都已有结果（成功、失败、跳过）
                    has_contact = any(
                        self._model.user_name(row).strip()
                        for row in range(self._model.rowCount())
                    )
                    if has_contact:
                        QMessageBox.information(self, "提示", "没有待发送的联系人")
                    else:
                        QMessageBox.information(self, "提示", "名单为空，请先粘贴联系人")
                return
            # 队列里的行（未发送的）置为「等待发送」；已有结果的行保留原状态不发
            for row in rows:
                self._model.set_row_status(row, CellStatus.PENDING)
                self._model.set_row_info(row, STATUS_TEXT[CellStatus.PENDING])
            total = len(rows)

        if not self._scheduler.start(
            items, rows, self._model.prefix, mode=self._send_mode
        ):
            return
        # 切到进度条：点击进度条或按 F12 终止
        self._sending = True
        self._send_done = 0
        self._send_total = total
        self._progress_bar.setRange(0, self._send_total)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("点击或按F12终止")
        self._refresh_send_stack()
        self._remove_success_button.setEnabled(False)
        if self._send_mode == "list":
            self._set_log("准备列表发送…")
        else:
            self._set_log("准备开始发送…")

    def _collect_tasks(self):
        """按行收集 (任务列表, 对应行号, 内容为空的行号)；已有结果的行不入队。

        仅用于正常发送；列表发送不读姓名列表，不走这里。
        """
        model = self._model
        items, rows, empty_rows = [], [], []
        for row in range(model.rowCount()):
            name = model.user_name(row).strip()
            if not name:
                continue
            # 只发「待发 / 无状态」的行：成功、失败(含警告)、跳过的保留状态、不再发
            if model.row_status(row) in (
                CellStatus.SUCCESS,
                CellStatus.FAILED,
                CellStatus.WARNING,
                CellStatus.SKIPPED,
            ):
                continue
            payload = self._build_payload(model.outgoing_messages(row))
            if not payload:
                empty_rows.append(row)
                continue
            items.append(RosterItem(user_id=name, payload=payload))
            rows.append(row)
        return items, rows, empty_rows

    @staticmethod
    def _build_payload(messages) -> list:
        """消息文本转负载：路径存在则按文件发送，否则按文本发送。"""
        payload = []
        for text in messages:
            if os.path.exists(text):
                payload.append({"type": "file", "data": os.path.abspath(text)})
            else:
                payload.append({"type": "text", "data": text})
        return payload

    def _on_row_started(self, row: int) -> None:
        self._model.set_row_status(row, CellStatus.SENDING)
        self._model.set_row_info(row, STATUS_TEXT[CellStatus.SENDING])
        self._scroll_row_into_view(row)
        position = min(self._send_done + 1, max(self._send_total, 1))
        self._set_log(
            f"正在发送 [{position}/{self._send_total}] {self._send_target(row)}"
        )

    def _on_row_finished(self, row: int, status: str, info: str) -> None:
        try:
            cell_status = CellStatus(status)
        except ValueError:
            cell_status = CellStatus.FAILED
        self._model.set_row_status(row, cell_status)
        self._model.set_row_info(row, info)

        self._send_done += 1
        self._progress_bar.setValue(self._send_done)
        self._set_log(
            f"[{self._send_done}/{self._send_total}] {self._send_target(row)}"
            f"：{self._result_short(cell_status)}"
        )

    def _on_list_progress(self, done: int, total: int) -> None:
        """列表发送逐轮进度：只动进度条和日志，不碰表格行状态与统计卡。"""
        if self._progress_bar.maximum() != total:
            self._progress_bar.setRange(0, total)
        self._send_done = done
        self._send_total = total
        self._progress_bar.setValue(done)
        self._set_log(f"列表发送进度：{done}/{total}")

    def _on_send_finished(self, ok: bool, message: str) -> None:
        self._sending = False
        self._progress_bar.setFormat("点击或按F12终止")
        self._refresh_send_stack()
        # 列表模式下「移除成功发送」保持锁定
        self._remove_success_button.setEnabled(not self._mode_locked)
        # 正常完毕 / 中止原因（含 F12、点击终止与异常终止）都留在日志栏
        self._set_log(message)
        if not ok:
            QMessageBox.warning(self, "发送终止", message)

    # ------------------------------------------------------------------
    # 进度与日志
    # ------------------------------------------------------------------
    def _on_countdown_tick(self, remaining: int) -> None:
        self._set_log(f"{remaining} 秒后开始…")

    def _on_remove_success(self) -> None:
        """删除所有发送成功的行。"""
        removed = self._model.remove_successful_rows()
        if removed:
            self._set_log(f"已移除 {removed} 条发送成功的记录")

    def _on_duplicate_name(self, name: str) -> None:
        """手动输入 / 改名撞上已有联系人：写入被拒绝，提示一下。"""
        self._set_log(f"重名：{name} 已存在")

    def _on_names_pasted(self, imported: int, duplicated: int) -> None:
        """姓名粘贴结果：导入多少条、其中重复跳过多少条。"""
        self._set_log(f"粘贴 {imported} 个姓名，重复 {duplicated} 个")

    def _send_target(self, row: int) -> str:
        """日志里显示的目标：姓名带上当前前缀。"""
        return f"{self._model.prefix}{self._model.user_name(row)}"

    @staticmethod
    def _result_short(status: CellStatus) -> str:
        """日志里的简短结果文案。"""
        if status == CellStatus.SUCCESS:
            return "成功"
        if status in (CellStatus.FAILED, CellStatus.WARNING):
            return "失败"
        if status == CellStatus.SKIPPED:
            return "跳过"
        if status == CellStatus.PENDING:
            return "已中止"
        return STATUS_TEXT.get(status, "")

    def _set_log(self, text: str) -> None:
        self._log_label.setText(text)
        self._log_label.setToolTip(text)

    def _scroll_row_into_view(self, row: int) -> None:
        """三张卡片的表格各自把当前发送行滚到视野中间（跟随发送进度）。"""
        if not (0 <= row < self._model.rowCount()):
            return
        for table in self._tables:
            columns = table.visible_columns()
            if not columns:
                continue
            index = self._model.index(row, columns[0])
            if table.viewport().rect().contains(table.visualRect(index)):
                continue
            table.scrollTo(index, QAbstractItemView.PositionAtCenter)

    def closeEvent(self, event) -> None:
        """关窗前先停掉发送线程，避免自动化还在后台操作窗口。"""
        if self._scheduler.is_running():
            self._scheduler.stop()
            self._scheduler.wait(3000)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # 演示数据
    # ------------------------------------------------------------------
    def _load_demo_data(self) -> None:
        """默认数据：前缀与默认消息；首行就是那个空姓名输入行（不放演示姓名）。"""
        self._model.set_prefix("PY111")
        self._model.set_default_message(0, "您好，这是一条默认消息")