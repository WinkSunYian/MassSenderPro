# view/constants.py
"""全局样式常量：颜色、尺寸等。这里只有模块级常量，不定义任何类。"""
from PySide6.QtGui import QColor

from view.enums.cell_status import CellStatus

# ---------- 背景 ----------
DEFAULT_ROW_BACKGROUND = QColor("#FFF9E8")
DEFAULT_ROW_FOREGROUND = QColor("#B07C1F")

# ---------- 状态配色（预设多组颜色） ----------
STATUS_BACKGROUND = {
    CellStatus.NORMAL: None,
    CellStatus.PENDING: QColor("#FFF7E6"),
    CellStatus.SENDING: QColor("#E9F2FF"),
    CellStatus.SUCCESS: QColor("#E9F9F0"),
    CellStatus.FAILED: QColor("#FDECEC"),
    CellStatus.WARNING: QColor("#FFF3E0"),
    CellStatus.SKIPPED: QColor("#F4F4F5"),
}

STATUS_FOREGROUND = {
    CellStatus.NORMAL: None,
    CellStatus.PENDING: QColor("#AD6800"),
    CellStatus.SENDING: QColor("#0958D9"),
    CellStatus.SUCCESS: QColor("#237804"),
    CellStatus.FAILED: QColor("#CF1322"),
    CellStatus.WARNING: QColor("#D46B08"),
    CellStatus.SKIPPED: QColor("#8C8C8C"),
}

STATUS_TEXT = {
    CellStatus.NORMAL: "",
    CellStatus.PENDING: "等待发送",
    CellStatus.SENDING: "发送中…",
    CellStatus.SUCCESS: "发送成功",
    CellStatus.FAILED: "发送失败：网络超时",
    CellStatus.WARNING: "发送异常：未收到回执",
    CellStatus.SKIPPED: "已跳过：内容为空",
}

# ---------- 卡片 & 表格样式表 ----------
CARD_STYLE = """
QFrame#CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
"""

TABLE_STYLE = """
QTableView {
    background-color: transparent;
    border: none;
    gridline-color: #F0F1F3;
    selection-background-color: #D9E9FF;
    selection-color: #1F2D3D;
    color: #303133;
    outline: none;
}
QTableView::item {
    padding: 2px 6px;
}
QHeaderView {
    background-color: transparent;
}
QHeaderView::section {
    background-color: #F7F8FA;
    color: #606266;
    border: none;
    border-bottom: 1px solid #EBEEF5;
    border-right: 1px solid #F2F3F5;
    padding: 6px 8px;
    font-weight: 600;
}
QHeaderView::section:first {
    border-top-left-radius: 8px;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #D9DDE3;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #BFC5CD;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""