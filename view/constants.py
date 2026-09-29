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
    CellStatus.FAILED: "发送失败",
    CellStatus.WARNING: "发送异常：未收到回执",
    CellStatus.SKIPPED: "已跳过：备注包含关键字",
}

# 名单里消息全空的行：按新口径计入「失败」
FAILED_EMPTY_TEXT = "失败：内容为空"

# 顶部「姓名前缀」下拉列表的固定项（增删在「配置中心」里完成）
NO_PREFIX_LABEL = "（无前缀）"
