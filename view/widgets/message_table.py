# view/widgets/message_table.py
from view.models.sheet_model import SheetModel
from view.widgets.base_table_view import BaseTableView
from view.widgets.message_delegate import MessageDelegate


class MessageTable(BaseTableView):
    """所有消息列所在的表格（卡片二）。隐藏行号与「前缀」表头。"""

    SHOW_VERTICAL_HEADER = False

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # 消息列三态显示：图片小图 / 文件图标 / 默认消息幽灵（只改绘制层）
        self.setItemDelegate(MessageDelegate())

    def visible_columns(self):
        model = self.model()
        if model is None:
            return []
        return list(range(SheetModel.FIRST_MESSAGE_COLUMN, model.info_column))
