# view/models/default_message_model.py
"""顶部「默认消息」表格模型：1 行 × N 个消息列，值透写 SheetModel。"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from view.content_kind import content_tooltip


class DefaultMessageModel(QAbstractTableModel):
    """与下方消息列一一对应的默认消息（显示/编辑语义与消息格一致）。

    - DisplayRole / EditRole 原样保存路径或文字（图片不在模型层隐藏，
      由 MessageDelegate 在绘制层画缩略图，与消息列同一套机制）；
    - 数据真身在 SheetModel.default_message / set_default_message，
      发送负载、空格幽灵等既有读取路径完全不变。
    """

    def __init__(self, sheet, parent=None) -> None:
        super().__init__(parent)
        self._sheet = sheet

    # ------------------------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else 1

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else self._sheet.message_column_count

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._sheet.default_message(index.column())
        if role in (Qt.DisplayRole, Qt.EditRole):
            return value
        if role == Qt.ToolTipRole:
            text = (value or "").strip()
            if not text:
                return None
            return content_tooltip(text) or None
        if role == Qt.TextAlignmentRole:
            # 与消息格一致：文字左对齐垂直居中（缩略图由委托居中绘制）
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        self._sheet.set_default_message(index.column(), value)
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return f"消息{section + 1}"
        return str(section + 1)

    # ------------------------------------------------------------------
    def sync_columns(self) -> None:
        """消息列数变化后重置（+/− 按钮经 SheetModel.columnsChanged 触达）。"""
        self.beginResetModel()
        self.endResetModel()
