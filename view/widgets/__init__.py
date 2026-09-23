# view/widgets/__init__.py
from view.widgets.base_table_view import BaseTableView
from view.widgets.card_frame import CardFrame
from view.widgets.info_table import InfoTable
from view.widgets.message_table import MessageTable
from view.widgets.prefix_name_table import PrefixNameTable
from view.widgets.scroll_synchronizer import ScrollSynchronizer

__all__ = [
    "BaseTableView",
    "CardFrame",
    "InfoTable",
    "MessageTable",
    "PrefixNameTable",
    "ScrollSynchronizer",
]