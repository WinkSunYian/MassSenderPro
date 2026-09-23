# view/widgets/prefix_name_table.py
from view.models.sheet_model import SheetModel
from view.widgets.base_table_view import BaseTableView


class PrefixNameTable(BaseTableView):
    """卡片一：第 0 行显示共用前缀，其余行为姓名列。"""

    def visible_columns(self):
        return [SheetModel.NAME_COLUMN]
