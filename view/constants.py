# view/constants.py
"""与主题无关的全局常量（状态文案、配置行字体）。

颜色与样式表统一由 view/theme.py 管理，随明暗主题切换。
"""
from PySide6.QtGui import QFont

from view.enums.cell_status import CellStatus

# 顶部配置卡片（姓名前缀 / 默认消息）的输入框使用斜体强调
DEFAULT_ROW_FONT = QFont()
DEFAULT_ROW_FONT.setItalic(True)

STATUS_TEXT = {
    CellStatus.NORMAL: "",
    CellStatus.PENDING: "等待发送",
    CellStatus.SENDING: "发送中…",
    CellStatus.SUCCESS: "发送成功",
    CellStatus.FAILED: "发送失败：网络超时",
    CellStatus.WARNING: "发送异常：未收到回执",
    CellStatus.SKIPPED: "已跳过：内容为空",
}
