# view/widgets/base_table_view.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHeaderView,
    QTableView,
)

from view.constants import TABLE_STYLE


class BaseTableView(QTableView):
    """带 Excel 风格粘贴能力的表格视图基类。"""

    pasteRequested = Signal(int, int, str)

    ROW_HEIGHT = 34
    HEADER_HEIGHT = 36

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._configure_base()

    # ------------------------------------------------------------------
    # 子类需要实现
    # ------------------------------------------------------------------
    def visible_columns(self):
        """返回本视图需要显示的模型列索引列表。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    def setModel(self, model) -> None:
        super().setModel(model)
        self.sync_columns()

    def sync_columns(self) -> None:
        model = self.model()
        if model is None:
            return
        visible = set(self.visible_columns())
        for column in range(model.columnCount()):
            self.setColumnHidden(column, column not in visible)

    # ------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.Paste):
            self._handle_paste()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    def _configure_base(self) -> None:
        self.setStyleSheet(TABLE_STYLE)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setShowGrid(True)
        self.setWordWrap(False)
        self.setAlternatingRowColors(False)

        horizontal = self.horizontalHeader()
        horizontal.setHighlightSections(False)
        horizontal.setFixedHeight(self.HEADER_HEIGHT)
        horizontal.setSectionResizeMode(QHeaderView.Stretch)

        vertical = self.verticalHeader()
        vertical.setDefaultSectionSize(self.ROW_HEIGHT)
        vertical.setSectionResizeMode(QHeaderView.Fixed)
        vertical.setHighlightSections(False)

    def _handle_paste(self) -> None:
        text = QApplication.clipboard().text()
        if not text:
            return

        selection = self.selectionModel()
        model = self.model()
        if selection is None or model is None:
            return

        indexes = selection.selectedIndexes()
        if not indexes:
            return

        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        start_row, start_column = rows[0], columns[0]

        # 整列粘贴时跳过第 0 行（前缀 / 默认消息配置行），从第一个用户行开始写入
        if start_row == 0 and len(rows) == model.rowCount():
            start_row = 1

        self.pasteRequested.emit(start_row, start_column, text)