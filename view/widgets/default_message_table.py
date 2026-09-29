# view/widgets/default_message_table.py
"""顶部「默认消息」表格：与「姓名前缀」输入框同款外观的单元格显示与编辑。"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLineEdit

from view.clipboard_util import clipboard_file_or_text
from view.constants import DEFAULT_ROW_FONT
from view.content_kind import ContentKind, classify_content
from view.widgets.base_table_view import BaseTableView
from view.widgets.message_delegate import MessageDelegate


class DefaultMessageDelegate(MessageDelegate):
    """默认消息格绘制：图片 / 文件同消息列；空格就是空（本表无幽灵）。"""

    def _visual(self, index):
        text = (index.data(Qt.DisplayRole) or "").strip()
        if not text:
            return ContentKind.TEXT, "", False
        return classify_content(text), text, False

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        # 编辑框与「姓名前缀」完全一致：ConfigInput 样式（圆角浅底 / 15px）
        # + 斜体（字号由 QSS 给出，setFont 只带斜体）
        if isinstance(editor, QLineEdit):
            editor.setObjectName("ConfigInput")
            editor.setFont(DEFAULT_ROW_FONT)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        # 铺满整个单元格（option.rect 被 ::item 的 padding 缩进过）：
        # 编辑框高度 = 行高 31px = 前缀输入框，文字内边距交给编辑框自己的
        # ConfigInput 样式（4px 8px），与前缀完全一致
        view = option.widget
        rect = view.visualRect(index) if view is not None else option.rect
        # visualRect 被网格线吃掉 1px（宽高各少 1）：补足到整格
        if view is not None:
            rect.setHeight(view.rowHeight(index.row()))
            rect.setWidth(view.columnWidth(index.column()))
        editor.setGeometry(rect)


class DefaultMessageTable(BaseTableView):
    """1 行 × N 消息列的默认消息表格（高度 / 字体 / 底色与前缀输入框一致）。"""

    SHOW_VERTICAL_HEADER = False
    # 与「姓名前缀」QComboBox#ConfigInput 实测高度一致（31px）
    ROW_HEIGHT = 31

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DefaultMessageTable")
        self.setMinimumWidth(0)
        # 三态显示与消息列同一绘制层：图片小图 / 文件图标 / 文字原文
        self.setItemDelegate(DefaultMessageDelegate())
        # 本表只要表格内容：隐藏「消息1/消息2…」列标题（卡片头已有「默认消息」）
        self.horizontalHeader().setVisible(False)
        # 卡片内容恒为一行：固定高度，编辑框恰好等于前缀输入框高度
        self.setFixedHeight(self._content_height())

    def sizeHint(self):
        # QTableView.sizeHint() 是与行数无关的常数(192)，会把顶行卡片撑高、
        # 压扁下方消息表格；本表恒为 1 行，自然高度 = 一行 + 边框
        # （列标题已隐藏，不再占高度）
        base = super().sizeHint()
        return QSize(base.width(), self._content_height())

    def minimumSizeHint(self):
        # QTableView.minimumSizeHint() 把（已隐藏的）列标题也算进来（58），
        # 使卡片最小高度=8+28+58+8=102，把顶部三卡整体撑高、行下方留空。
        # 本表只有一行：最小高度 = 一行 + 边框。
        base = super().minimumSizeHint()
        return QSize(base.width(), self._content_height())

    def _content_height(self) -> int:
        header = self.horizontalHeader()
        header_height = header.height() if header.isVisible() else 0
        return header_height + self.ROW_HEIGHT + 2 * self.frameWidth()

    def visible_columns(self):
        model = self.model()
        if model is None:
            return []
        return list(range(model.columnCount()))

    def _paste_text_for(self, column: int) -> str:
        # 整表都是消息列：文件 / 链接允许粘贴（不受姓名列限制）
        return clipboard_file_or_text()
