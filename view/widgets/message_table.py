# view/widgets/message_table.py
from view.models.sheet_model import SheetModel
from view.widgets.base_table_view import BaseTableView


class MessageTable(BaseTableView):
    """所有消息列所在的表格（卡片二）。"""

    def visible_columns(self):
        model = self.model()
        if model is None:
            return []
        return list(range(SheetModel.FIRST_MESSAGE_COLUMN, model.info_column))