# view/models/sheet_model.py
"""表格数据模型。

列结构： [姓名] [消息1] [消息2] ... [信息]
行结构： 全部为用户数据行（第 0..N-1 行），没有配置行。
        末行恒为「空姓名输入行」：恰好一个空姓名单元格、且只在最后一行；
        在输入行里填上名字会自动补一个新的空行，空姓名不参与发送。
共用前缀与默认消息不在表格内，由顶部「姓名前缀」「默认消息」卡片编辑。
"""
from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal

from view.content_kind import content_tooltip, ghost_tooltip
from view.enums.cell_status import CellStatus
from view.theme import theme_manager


class SheetModel(QAbstractTableModel):
    """群发表格数据模型。"""

    NAME_COLUMN = 0
    FIRST_MESSAGE_COLUMN = 1

    columnsChanged = Signal()
    # 手动输入 / 改名撞上已有联系人：写入被拒绝，带出名字供底部提示
    duplicateName = Signal(str)
    # 姓名列粘贴结果：(导入条数, 跳过的重复条数)
    namesPasted = Signal(int, int)

    def __init__(self, message_column_count: int = 2, parent=None) -> None:
        super().__init__(parent)
        self._message_column_count = max(1, int(message_column_count))
        self._prefix = ""
        self._default_messages: List[str] = ["" for _ in range(self._message_column_count)]

        self._names: List[str] = []
        self._messages: List[List[str]] = []
        self._infos: List[str] = []
        self._statuses: List[List[CellStatus]] = []

        # 起始就带着唯一的空姓名输入行（末行）
        self._append_rows(1)

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
        """所有联系人共用的前缀（顶部「姓名前缀」卡片编辑）。"""
        return self._prefix

    def set_prefix(self, text: str) -> None:
        self._prefix = "" if text is None else str(text)

    def default_message(self, index: int) -> str:
        """指定消息列的默认消息（顶部「默认消息」卡片编辑）。"""
        if 0 <= index < len(self._default_messages):
            return self._default_messages[index]
        return ""

    def set_default_message(self, index: int, text: str) -> None:
        if 0 <= index < len(self._default_messages):
            self._default_messages[index] = "" if text is None else str(text)

    # ------------------------------------------------------------------
    # QAbstractTableModel 接口
    # ------------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.user_row_count

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
            return self._tooltip_at(row, column)
        return None

    def setData(self, index, value, role=Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        row, column = index.row(), index.column()
        text = "" if value is None else str(value)

        if column == self.NAME_COLUMN:
            if not text.strip():
                if self._names[row].strip():
                    # 具名行被清空姓名：直接删除该行（三张卡片共用本模型，行会同步消失）
                    self._remove_user_row(row)
                # 输入行自己被清空：保持不动——它就是必须存在的那个空单元格
                self._normalize_name_rows()
                return True
            # 重名过滤：手动输入 / 改名与已有联系人撞名 → 拒绝写入并提示
            # （输入行保持空、原行保持原名，表格结构不被破坏）
            name = text.strip()
            for i, existing in enumerate(self._names):
                if i != row and existing.strip() == name:
                    self.duplicateName.emit(name)
                    return False
            self._names[row] = text
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            # 在末行输入行里填了名字 → 自动补一个新的空输入行
            self._normalize_name_rows()
            return True

        if column == self.info_column:
            return False

        message_index = column - self.FIRST_MESSAGE_COLUMN
        self._messages[row][message_index] = text
        roles = [Qt.DisplayRole, Qt.EditRole]
        if not text.strip() and self._statuses[row][message_index] != CellStatus.NORMAL:
            # 内容被清空（Delete / 剪切 / 粘贴空值）：状态色回到等待
            self._statuses[row][message_index] = CellStatus.NORMAL
            roles.extend([Qt.BackgroundRole, Qt.ForegroundRole])
        self.dataChanged.emit(index, index, roles)
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
        # 垂直表头：用户行从 1 开始编号
        return str(section + 1)

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

        if start_column == self.NAME_COLUMN:
            # 姓名列粘贴 = 去重导入（不看起始行、不覆盖现有行）
            self._import_name_rows(matrix)
            return

        # 消息/信息列粘贴：只写现有行，超出姓名行数的尾部剔除（不能造无名行）
        needed = start_row + len(matrix)
        if needed > self.rowCount():
            remaining = self.rowCount() - start_row
            if remaining <= 0:
                return
            matrix = matrix[:remaining]

        column_limit = self.columnCount()
        last_row, last_column = start_row, start_column
        for row_offset, row_values in enumerate(matrix):
            row = start_row + row_offset
            for column_offset, value in enumerate(row_values):
                column = start_column + column_offset
                if column >= column_limit:
                    continue
                if self.setData(self.index(row, column), value, Qt.EditRole):
                    last_row = max(last_row, row)
                    last_column = max(last_column, column)

        if (
            last_row >= start_row
            and last_column >= start_column
            and last_row < self.rowCount()
            and last_column < self.columnCount()
        ):
            self.dataChanged.emit(
                self.index(start_row, start_column),
                self.index(last_row, last_column),
                [Qt.DisplayRole, Qt.EditRole],
            )

    def _import_name_rows(self, matrix: List[List[str]]) -> None:
        """姓名列粘贴：去重导入，并回报「导入多少 / 重复多少」。

        已存在的名字整行忽略，不存在的插到空输入行之前（绝不覆盖现有行，
        也不把输入行挤到中间）；粘贴内容自身重复的只导入一次，空名字跳过。
        """
        known = {name.strip() for name in self._names if name.strip()}
        new_rows: List[List[str]] = []
        duplicated = 0
        for row_values in matrix:
            name = str(row_values[0]).strip() if row_values else ""
            if not name:
                continue
            if name in known:
                duplicated += 1
                continue
            known.add(name)
            new_rows.append(row_values)

        if new_rows:
            # 插到输入行前面；没有输入行（异常态）就补到末尾
            position = (
                self.rowCount() - 1
                if self._names and not self._names[-1].strip()
                else self.rowCount()
            )
            self._insert_rows(position, len(new_rows))
            for offset, row_values in enumerate(new_rows):
                row = position + offset
                for column, value in enumerate(row_values):
                    if column >= self.info_column or not str(value):
                        continue
                    if column == self.NAME_COLUMN:
                        self._names[row] = str(value)
                    else:
                        self._messages[row][column - self.FIRST_MESSAGE_COLUMN] = str(
                            value
                        )
            self.dataChanged.emit(
                self.index(position, 0),
                self.index(position + len(new_rows) - 1, self.columnCount() - 1),
                [Qt.DisplayRole, Qt.EditRole],
            )

        # 收敛空姓名行：有输入行就留它，没有就补一个
        self._normalize_name_rows()

        # 回报粘贴结果（连空行都没有时什么都不提，避免刷提示）
        if new_rows or duplicated:
            self.namesPasted.emit(len(new_rows), duplicated)

    # ------------------------------------------------------------------
    # 状态与信息
    # ------------------------------------------------------------------
    def set_cell_status(self, row: int, column: int, status: CellStatus) -> None:
        if row < 0 or row >= self.user_row_count:
            return
        if column < self.FIRST_MESSAGE_COLUMN or column >= self.info_column:
            return
        self._statuses[row][column - self.FIRST_MESSAGE_COLUMN] = status
        index = self.index(row, column)
        self.dataChanged.emit(index, index, [Qt.BackgroundRole, Qt.ForegroundRole])

    def row_status(self, row: int) -> CellStatus:
        """整行的发送状态（取第一个消息格状态）。"""
        if 0 <= row < len(self._statuses) and self._statuses[row]:
            return self._statuses[row][0]
        return CellStatus.NORMAL

    def set_row_status(self, row: int, status: CellStatus) -> None:
        if row < 0 or row >= self.user_row_count:
            return
        for offset in range(self._message_column_count):
            self._statuses[row][offset] = status
        # 起点取姓名列：姓名格也随整行状态着色
        left = self.index(row, self.NAME_COLUMN)
        right = self.index(row, self.info_column - 1)
        self.dataChanged.emit(left, right, [Qt.BackgroundRole, Qt.ForegroundRole])

    def set_row_info(self, row: int, text: str) -> None:
        if row < 0 or row >= self.user_row_count:
            return
        self._infos[row] = text
        index = self.index(row, self.info_column)
        self.dataChanged.emit(index, index, [Qt.DisplayRole])

    def clear_statuses(self) -> None:
        for statuses in self._statuses:
            for offset in range(len(statuses)):
                statuses[offset] = CellStatus.NORMAL
        for offset in range(len(self._infos)):
            self._infos[offset] = ""

        if self.rowCount() > 0:
            # 起点取姓名列：姓名格的状态色一并清掉
            top = self.index(0, self.NAME_COLUMN)
            bottom = self.index(self.rowCount() - 1, self.info_column)
            self.dataChanged.emit(
                top, bottom, [Qt.BackgroundRole, Qt.ForegroundRole, Qt.DisplayRole]
            )

    def remove_successful_rows(self) -> int:
        """删除所有「发送成功」的行，返回删除的行数（空姓名输入行不删）。"""
        rows = [
            row
            for row in range(self.user_row_count)
            if self.row_status(row) == CellStatus.SUCCESS and self._names[row].strip()
        ]
        for row in reversed(rows):
            self._remove_user_row(row)
        self._normalize_name_rows()
        return len(rows)

    def refresh_all(self) -> None:
        """让全部单元格重新取显示角色（主题切换后调用）。"""
        if self.rowCount() == 0 or self.columnCount() == 0:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [
                Qt.DisplayRole,
                Qt.EditRole,
                Qt.BackgroundRole,
                Qt.ForegroundRole,
                Qt.FontRole,
                Qt.ToolTipRole,
            ],
        )

    def user_name(self, row: int) -> str:
        if 0 <= row < len(self._names):
            return self._names[row]
        return ""

    def user_prefix(self, row: int) -> str:
        return self._prefix

    def user_messages(self, row: int) -> List[str]:
        if 0 <= row < len(self._messages):
            return list(self._messages[row])
        return list(self._default_messages)

    def outgoing_messages(self, row: int) -> List[str]:
        """本行实际要发送的消息：单元格为空时回落到该列的默认消息，空串剔除。"""
        if not (0 <= row < len(self._messages)):
            return []
        outgoing = []
        for column, text in enumerate(self._messages[row]):
            value = (text or "").strip() or self.default_message(column).strip()
            if value:
                outgoing.append(value)
        return outgoing

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _text_at(self, row: int, column: int) -> str:
        if column == self.NAME_COLUMN:
            return self._names[row]
        if column == self.info_column:
            return self._infos[row]
        return self._messages[row][column - self.FIRST_MESSAGE_COLUMN]

    def _tooltip_at(self, row: int, column: int) -> Optional[str]:
        """悬停文案：图片给文件名 + 大图，其余给完整原文；空消息格提示回落默认消息。"""
        text = (self._text_at(row, column) or "").strip()
        if text:
            return content_tooltip(text) or None
        if self.FIRST_MESSAGE_COLUMN <= column < self.info_column:
            # 空格子（幽灵显示）：提示将发送默认消息
            return ghost_tooltip(self.default_message(column - self.FIRST_MESSAGE_COLUMN)) or None
        return None

    def _background_at(self, row: int, column: int):
        status = self._status_for(row, column)
        if status is None:
            return None
        return theme_manager().palette.status_bg.get(status)

    def _foreground_at(self, row: int, column: int):
        status = self._status_for(row, column)
        if status is None:
            return None
        return theme_manager().palette.status_fg.get(status)

    def _status_for(self, row: int, column: int):
        """着色用的状态：姓名列随整行状态，消息列各自状态，信息列不着色。"""
        if column == self.NAME_COLUMN:
            return self.row_status(row)
        if self.FIRST_MESSAGE_COLUMN <= column < self.info_column:
            return self._statuses[row][column - self.FIRST_MESSAGE_COLUMN]
        return None

    def _normalize_name_rows(self) -> None:
        """姓名列不变式：有且只有一个空姓名单元格，且必须在最后一行。

        多余的空姓名行整行删除；一个不剩就补一个新的空输入行。
        """
        empties = [row for row, name in enumerate(self._names) if not name.strip()]
        if empties == [len(self._names) - 1]:
            return
        for row in reversed(empties):
            self._remove_user_row(row)
        self._append_rows(1)

    def _insert_rows(self, position: int, count: int) -> None:
        """在 position 处插入 count 个空白行。"""
        if count <= 0:
            return
        self.beginInsertRows(QModelIndex(), position, position + count - 1)
        for offset in range(count):
            at = position + offset
            self._names.insert(at, "")
            self._messages.insert(at, ["" for _ in range(self._message_column_count)])
            self._infos.insert(at, "")
            self._statuses.insert(
                at, [CellStatus.NORMAL for _ in range(self._message_column_count)]
            )
        self.endInsertRows()

    def _append_rows(self, count: int) -> None:
        self._insert_rows(self.rowCount(), count)

    def _remove_user_row(self, row: int) -> None:
        """删除一个用户行（姓名、消息、状态与信息一并移除）。"""
        if row < 0 or row >= self.user_row_count:
            return
        index = row
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._names[index]
        del self._messages[index]
        del self._infos[index]
        del self._statuses[index]
        self.endRemoveRows()

    @staticmethod
    def _parse_clipboard(text: str) -> List[List[str]]:
        if not text:
            return []
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        return [line.split("\t") for line in lines]