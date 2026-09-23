# view/enums/cell_status.py
from enum import Enum


class CellStatus(Enum):
    """消息单元格的状态枚举。"""
    NORMAL = "normal"
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"