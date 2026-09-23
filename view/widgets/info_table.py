# view/widgets/info_table.py
from view.widgets.base_table_view import BaseTableView


class InfoTable(BaseTableView):
    """最右侧的信息列（卡片三）。"""

    def visible_columns(self):
        model = self.model()
        if model is None:
            return []
        return [model.info_column]