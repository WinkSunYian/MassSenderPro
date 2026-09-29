# view/widgets/message_delegate.py
"""消息列单元格绘制：图片=小缩略图、文件=图标、空格=默认消息幽灵。

只改绘制层：模型里的真实值（DisplayRole / EditRole）原样保留，
编辑器、复制、发送负载都不受影响；文字格走 Qt 默认绘制，
空格子的默认文本消息用 hint 色画成占位提示（不进真实值）。
"""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate

from view.content_kind import ContentKind, classify_content, file_icon, load_thumbnail
from view.models.sheet_model import SheetModel
from view.theme import theme_manager


class MessageDelegate(QStyledItemDelegate):
    """消息列专用委托：三态显示 + 淡色幽灵（文本幽灵走 hint 占位色）。"""

    # 行高 34：小图 24 留出上下边距
    THUMB_SIZE = 24
    GHOST_OPACITY = 0.38
    # 文本幽灵的内边距：对齐 QSS `QTableView::item { padding: 2px 6px; }`，
    # 让占位提示与真实文字起笔位置一致
    GHOST_PAD_X = 6
    GHOST_PAD_Y = 2

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        # 图片 / 文件格不绘制原始路径文本（真实值仍在模型里，编辑器照常读取）
        if self._should_hide_text(index):
            option.text = ""

    def paint(self, painter: QPainter, option, index) -> None:
        kind, text, ghost = self._visual(index)
        # 先画背景 / 选中 / 焦点 / （可能残留的）文本
        super().paint(painter, option, index)
        if not text:
            return
        if kind is ContentKind.TEXT:
            if ghost:
                # 默认文本消息 → hint 色占位提示（真实值仍是空）
                self._paint_ghost_text(painter, option, text)
            return
        painter.save()
        try:
            if ghost:
                painter.setOpacity(self.GHOST_OPACITY)
            rect = option.rect
            if kind is ContentKind.IMAGE:
                pixmap = load_thumbnail(text)
                if pixmap.isNull():
                    return  # 读不出图：initStyleOption 已保留路径文本
                scaled = pixmap.scaled(
                    self.THUMB_SIZE, self.THUMB_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                x = rect.center().x() - scaled.width() // 2
                y = rect.center().y() - scaled.height() // 2
                painter.drawPixmap(x, y, scaled)
            else:  # FILE
                half = self.THUMB_SIZE // 2
                icon_rect = QRect(
                    rect.center().x() - half,
                    rect.center().y() - half,
                    self.THUMB_SIZE,
                    self.THUMB_SIZE,
                )
                file_icon(text).paint(painter, icon_rect, Qt.AlignCenter)
        finally:
            painter.restore()

    # ------------------------------------------------------------------
    def _paint_ghost_text(self, painter: QPainter, option, text: str) -> None:
        """空格子的默认文本消息：hint 色占位提示（只在绘制层，不进真实值）。"""
        rect = option.rect.adjusted(
            self.GHOST_PAD_X,
            self.GHOST_PAD_Y,
            -self.GHOST_PAD_X,
            -self.GHOST_PAD_Y,
        )
        if rect.width() <= 0 or rect.height() <= 0:
            return
        painter.save()
        try:
            painter.setFont(option.font)
            painter.setPen(QPen(theme_manager().palette.hint_text))
            elided = painter.fontMetrics().elidedText(text, Qt.ElideRight, rect.width())
            painter.drawText(
                rect,
                int(option.displayAlignment) | int(Qt.TextSingleLine),
                elided,
            )
        finally:
            painter.restore()

    def _visual(self, index):
        """返回 (类型, 显示文本, 是否幽灵)；姓名 / 信息列不当作内容格。"""
        model = index.model()
        column = index.column()
        if model is None or column < SheetModel.FIRST_MESSAGE_COLUMN or column >= model.info_column:
            return ContentKind.TEXT, "", False
        text = (index.data(Qt.DisplayRole) or "").strip()
        if text:
            return classify_content(text), text, False
        # 空格子 → 幽灵显示该列默认消息
        default = (model.default_message(column - SheetModel.FIRST_MESSAGE_COLUMN) or "").strip()
        if not default:
            return ContentKind.TEXT, "", False
        return classify_content(default), default, True

    def _should_hide_text(self, index) -> bool:
        kind, text, _ = self._visual(index)
        if kind is ContentKind.FILE:
            return True
        if kind is ContentKind.IMAGE:
            # 图能加载出来才隐藏路径；读不出图时回落画文本
            return not load_thumbnail(text).isNull()
        return False
