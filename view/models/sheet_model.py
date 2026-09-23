# view/models/sheet_model.py
"""表格数据模型。

列结构： [姓名] [消息1] [消息2] ... [信息]
行结构： 第 0 行为「前缀 / 默认消息配置行」，第 1..N 行为用户数据行。
        所有联系人共用同一个前缀，存放在模型级的 prefix 属性中，
        在视图里显示为第 0 行姓名列的单元格。
"""
from typing import List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal

from view.constants import (
    DEFAULT_ROW_BACKGROUND,
    DEFAULT_ROW_FOREGROUND,
    STATUS_BACKGROUND,
    STATUS_FOREGROUND,
)
from view.enums.cell_status import CellStatus


class SheetModel(QAbstractTableModel):
    """群发表格数据模型。"""

    NAME_COLUMN = 0
    FIRST_MESSAGE_COLUMN = 1

    columnsChanged = Signal()

    def __init__(self, message_column_count: int = 2, parent=None) -> None:
        super().__init__(parent)
        self._message_column_count = max(1, int(message_column_count))
        self._prefix = ""
        self._default_messages: List[str] = ["" for _ in range(self._message_column_count)]

        self._names: List[str] = []
        self._messages: List[List[str]] = []
        self._infos: List[str] = []
        self._statuses: List[List[CellStatus]] = []

    # ------------------------------------------------------------------
    # 结构信息
    # ------------------------------------------------------------------
    @property
    def message_column_count(self) -> int:
        return self._message_column_count

    @property
    def info_column(self) -> int:
        return self.FIRST_MESSAGE_COLUMN + self._message_column_count

    @property
    def user_row_count(self) -> int:
        return len(self._names)

    @property
    def prefix(self) -> str:
        """所有联系人共用的前缀。"""
        return self._prefix

    def set_prefix(self, text: str) -> None:
        """设置共用前缀（对应第 0 行姓名列的单元格）。"""
        self._prefix = "" if text is None else str(text)
        index = self.index(0, self.NAME_COLUMN)
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])

    # ------------------------------------------------------------------
    # QAbstractTableModel 接口
    # ------------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return 1 + self.user_row_count

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.FIRST_MESSAGE_COLUMN + self._message_column_count + 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, column = index.row(), index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._text_at(row, column)
        if role == Qt.BackgroundRole:
            return self._background_at(row, column)
        if role == Qt.ForegroundRole:
            return self._foreground_at(row, column)
        if role == Qt.TextAlignmentRole:
            if column == self.NAME_COLUMN:
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.ToolTipRole:
            return self._text_at(row, column) or None
        return None

    def setData(self, index, value, role=Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        row, column = index.row(), index.column()
        text = "" if value is None else str(value)

        if column == self.NAME_COLUMN:
            if row == 0:
                self._prefix = text
            else:
                self._names[row - 1] = text
        elif column == self.info_column:
            return False
        else:
            message_index = column - self.FIRST_MESSAGE_COLUMN
            if row == 0:
                self._default_messages[message_index] = text
            else:
                self._messages[row - 1][message_index] = text

        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        row, column = index.row(), index.column()

        if column == self.info_column:
            return base
        return base | Qt.ItemIsEditable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            if section == self.NAME_COLUMN:
                return "姓名"
            if section == self.info_column:
                return "信息"
            return f"消息{section - self.NAME_COLUMN}"
        # 垂直表头：配置行不计行号
        if section == 0:
            return "前缀"
        return str(section)

    # ------------------------------------------------------------------
    # 列的动态增删
    # ------------------------------------------------------------------
    def add_message_column(self) -> None:
        position = self.info_column
        self.beginInsertColumns(QModelIndex(), position, position)
        self._message_column_count += 1
        self._default_messages.append("")
        for row in self._messages:
            row.append("")
        for row in self._statuses:
            row.append(CellStatus.NORMAL)
        self.endInsertColumns()
        self.columnsChanged.emit()

    def remove_message_column(self, index: int = None) -> bool:
        if self._message_column_count <= 1:
            return False
        if index is None:
            index = self._message_column_count - 1
        if not 0 <= index < self._message_column_count:
            return False

        position = self.FIRST_MESSAGE_COLUMN + index
        self.beginRemoveColumns(QModelIndex(), position, position)
        del self._default_messages[index]
        for row in self._messages:
            del row[index]
        for row in self._statuses:
            del row[index]
        self._message_column_count -= 1
        self.endRemoveColumns()
        self.columnsChanged.emit()
        return True

    # ------------------------------------------------------------------
    # Excel 风格粘贴
    # ------------------------------------------------------------------
    def paste_text(self, start_row: int, start_column: int, text: str) -> None:
        matrix = self._parse_clipboard(text)
        if not matrix:
            return

        needed = start_row + len(matrix)
        if needed > self.rowCount():
            self._append_rows(needed - self.rowCount())

        column_limit = self.columnCount()
        last_row, last_column = start_row, start_column

        for row_offset, row_values in enumerate(matrix):
            for column_offset, value in enumerate(row_values):
                row = start_row + row_offset
                column = start_column + column_offset
                if column >= column_limit:
                    continue
                if self.setData(self.index(row, column), value, Qt.EditRole):
                    last_row = max(last_row, row)
                    last_column = max(last_column, column)

        if last_row >= start_row and last_column >= start_column:
            self.dataChanged.emit(
                self.index(start_row, start_column),
                self.index(last_row, last_column),
                [Qt.DisplayRole, Qt.EditRole],
            )

    # ------------------------------------------------------------------
    # 状态与信息
    # ------------------------------------------------------------------
    def set_cell_status(self, row: int, column: int, status: CellStatus) -> None:
        if row <= 0 or column < self.FIRST_MESSAGE_COLUMN or column >= self.info_column:
            return
        self._statuses[row - 1][column - self.FIRST_MESSAGE_COLUMN] = status
        index = self.index(row, column)
        self.dataChanged.emit(index, index, [Qt.BackgroundRole, Qt.ForegroundRole])

    def set_row_status(self, row: int, status: CellStatus) -> None:
        if row <= 0:
            return
        for offset in range(self._message_column_count):
            self._statuses[row - 1][offset] = status
        left = self.index(row, self.FIRST_MESSAGE_COLUMN)
        right = self.index(row, self.info_column - 1)
        self.dataChanged.emit(left, right, [Qt.BackgroundRole, Qt.ForegroundRole])

    def set_row_info(self, row: int, text: str) -> None:
        if row <= 0:
            return
        self._infos[row - 1] = text
        index = self.index(row, self.info_column)
        self.dataChanged.emit(index, index, [Qt.DisplayRole])

    def clear_statuses(self) -> None:
        for statuses in self._statuses:
            for offset in range(len(statuses)):
                statuses[offset] = CellStatus.NORMAL
        for offset in range(len(self._infos)):
            self._infos[offset] = ""

        if self.rowCount() > 1:
            top = self.index(1, self.FIRST_MESSAGE_COLUMN)
            bottom = self.index(self.rowCount() - 1, self.info_column)
            self.dataChanged.emit(
                top, bottom, [Qt.BackgroundRole, Qt.ForegroundRole, Qt.DisplayRole]
            )

    def user_name(self, row: int) -> str:
        return self._names[row - 1] if row > 0 else ""

    def user_prefix(self, row: int) -> str:
        return self._prefix

    def user_messages(self, row: int) -> List[str]:
        if row <= 0:
            return list(self._default_messages)
        return list(self._messages[row - 1])

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _text_at(self, row: int, column: int) -> str:
        if column == self.NAME_COLUMN:
            if row == 0:
                return self._prefix
            return self._names[row - 1]
        if column == self.info_column:
            return "" if row == 0 else self._infos[row - 1]
        message_index = column - self.FIRST_MESSAGE_COLUMN
        if row == 0:
            return self._default_messages[message_index]
        return self._messages[row - 1][message_index]

    def _background_at(self, row: int, column: int):
        if row == 0:
            return DEFAULT_ROW_BACKGROUND
        if column < self.FIRST_MESSAGE_COLUMN or column >= self.info_column:
            return None
        status = self._statuses[row - 1][column - self.FIRST_MESSAGE_COLUMN]
        return STATUS_BACKGROUND.get(status)

    def _foreground_at(self, row: int, column: int):
        if row == 0:
            return DEFAULT_ROW_FOREGROUND
        if column < self.FIRST_MESSAGE_COLUMN or column >= self.info_column:
            return None
        status = self._statuses[row - 1][column - self.FIRST_MESSAGE_COLUMN]
        return STATUS_FOREGROUND.get(status)

    def _append_rows(self, count: int) -> None:
        if count <= 0:
            return
        first = self.rowCount()
        self.beginInsertRows(QModelIndex(), first, first + count - 1)
        for _ in range(count):
            self._names.append("")
            self._messages.append(["" for _ in range(self._message_column_count)])
            self._infos.append("")
            self._statuses.append([CellStatus.NORMAL for _ in range(self._message_column_count)])
        self.endInsertRows()

    @staticmethod
    def _parse_clipboard(text: str) -> List[List[str]]:
        if not text:
            return []
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        return [line.split("\t") for line in lines]