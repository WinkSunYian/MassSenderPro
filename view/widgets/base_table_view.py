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

from view.clipboard_util import clipboard_file_or_text, clipboard_has_urls
from view.models.sheet_model import SheetModel


class BaseTableView(QTableView):
    """带 Excel 风格粘贴能力的表格视图基类。"""

    pasteRequested = Signal(int, int, str)

    ROW_HEIGHT = 34
    HEADER_HEIGHT = 36
    SHOW_VERTICAL_HEADER = True

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
        # 删列后 Qt 的 Stretch 表头不会自动重分发宽度（会残留旧列宽+死区，
        # 甚至残留已删列的旧像素，看起来像列没减少），这里强制重排并刷新视口，
        # 保证剩余消息列始终铺满卡片宽度
        self.horizontalHeader().resizeSections()
        self.viewport().update()

    # ------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.Copy):
            self._handle_copy()
            event.accept()
            return
        if event.matches(QKeySequence.Cut):
            self._handle_cut()
            event.accept()
            return
        if event.matches(QKeySequence.Delete):
            self._handle_clear()
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            self._handle_paste()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    def _configure_base(self) -> None:
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # 两个方向的滚动条都不显示（滚轮/方向键仍可滚动，行不会丢失可达性）
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        vertical.setVisible(self.SHOW_VERTICAL_HEADER)

    def _handle_copy(self) -> None:
        """Ctrl+C：有选中 → 整块写入剪贴板（多选一起复制，不清空单元格）；
        无选中 → 回落复制当前格。"""
        found = self._selected_matrix()
        if found is None:
            current = self.currentIndex()
            text = current.data() if current.isValid() else ""
            if text:
                QApplication.clipboard().setText(text)
            return
        text = self._matrix_text(found[2])
        if text:
            QApplication.clipboard().setText(text)

    def _handle_cut(self) -> None:
        """剪切：选区文本写入剪贴板并清空单元格（清空姓名会删除整行）。"""
        found = self._selected_matrix()
        if found is None:
            return
        rows, columns, matrix = found

        # 1) 先把选区写成剪贴板矩阵（tab 分列、换行分行，与粘贴格式互通）
        QApplication.clipboard().setText(self._matrix_text(matrix))

        # 2) 再清空选区
        self._clear_cells(rows, columns)

    def _selected_matrix(self):
        """选区读成 (行号升序, 列号升序, 矩阵)；无模型/无选区 → None。"""
        selection = self.selectionModel()
        model = self.model()
        if selection is None or model is None:
            return None

        indexes = selection.selectedIndexes()
        if not indexes:
            return None

        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        row_at = {row: pos for pos, row in enumerate(rows)}
        column_at = {column: pos for pos, column in enumerate(columns)}

        matrix = [["" for _ in columns] for _ in rows]
        for index in indexes:
            matrix[row_at[index.row()]][column_at[index.column()]] = index.data() or ""
        return rows, columns, matrix

    @staticmethod
    def _matrix_text(matrix) -> str:
        """矩阵 → 剪贴板文本：tab 分列、换行分行，与粘贴解析互通。"""
        return "\n".join("\t".join(row_values) for row_values in matrix)

    def _handle_clear(self) -> None:
        """Delete：清空选中单元格内容（清空具名行会删除整行，空输入行保持）。"""
        selection = self.selectionModel()
        model = self.model()
        if selection is None or model is None:
            return

        indexes = selection.selectedIndexes()
        if not indexes:
            return

        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        self._clear_cells(rows, columns)

    def _clear_cells(self, rows, columns) -> None:
        """清空指定行列的单元格。

        清空姓名会删除整行、令后续行号上移，用 shift 补偿；
        某行删除后，该行剩余单元格随之消失，跳过即可。
        空姓名输入行清空时保持不动（它就是必须存在的空单元格）。
        """
        model = self.model()
        shift = 0
        for row in rows:
            target = row - shift
            if target >= model.rowCount():
                break
            row_deleted = False
            for column in columns:
                before = model.rowCount()
                model.setData(model.index(target, column), "", Qt.EditRole)
                if model.rowCount() < before:
                    row_deleted = True
                    break
            if row_deleted:
                shift += 1

    def _handle_paste(self) -> None:
        selection = self.selectionModel()
        model = self.model()
        if selection is None or model is None:
            return

        indexes = selection.selectedIndexes()
        if not indexes:
            # 表格被清空后没有任何可选单元格，允许直接粘贴到姓名列起点
            if model.rowCount() == 0:
                text = self._paste_text_for(SheetModel.NAME_COLUMN)
                if text:
                    self.pasteRequested.emit(0, 0, text)
            return

        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        text = self._paste_text_for(columns[0])
        if not text:
            return
        self.pasteRequested.emit(rows[0], columns[0], text)

    def _paste_text_for(self, column: int) -> str:
        """取粘贴文本：姓名列禁止粘贴文件/链接，只认纯文本。"""
        if column == SheetModel.NAME_COLUMN:
            if clipboard_has_urls():
                return ""
            return QApplication.clipboard().text()
        return clipboard_file_or_text()