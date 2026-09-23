# view/widgets/info_table.py
from view.widgets.base_table_view import BaseTableView


class InfoTable(BaseTableView):
    """最右侧的信息列（卡片三）。隐藏行号与「前缀」表头。"""

    SHOW_VERTICAL_HEADER = False

    def visible_columns(self):
        model = self.model()
        if model is None:
            return []
        return [model.info_column]
