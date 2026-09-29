# view/content_kind.py
"""单元格内容三态识别与缩略图（与发送负载同源）。

判定规则跟 _build_payload 同源：路径存在 → 文件，否则就是普通文本；
文件再按「图片扩展名白名单 + QImageReader 可读」细分为图片，
PDF 等即便 Qt 能读也一律按普通文件（图标占位）。
同时提供缩略图 / 文件图标缓存与悬停大图的 tooltip 文案。
"""
import html
import os
from enum import Enum
from typing import Tuple

from PySide6.QtCore import QFileInfo, QUrl
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import QFileIconProvider

# 悬停大图的最长边（宽、高都不超过，避免竖图撑满屏幕）
TOOLTIP_MAX = 320

# 图片扩展名白名单：即便 Qt 带 pdfium 之类的插件能把 PDF/其它东西当图读，
# 「图片格」只认常见图片格式，PDF 等一律走文件图标占位。
IMAGE_EXTS = {
    ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png",
    ".svg", ".svgz", ".tga", ".tif", ".tiff", ".webp", ".xpm",
}


class ContentKind(Enum):
    """单元格内容三态。"""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


_kind_cache = {}
_thumbnail_cache = {}
_icon_cache = {}
_file_icon_provider = QFileIconProvider()


def classify_content(text) -> ContentKind:
    """把单元格真实值分类为 文本 / 图片 / 普通文件。

    与发送侧同源：os.path.exists 才当文件；图片还需在白名单扩展名内
    且 QImageReader 能读，否则按普通文件（图标占位）。
    只缓存「确实存在」的结果；不存在的路径不缓存（文件可能稍后才创建）。
    """
    value = (text or "").strip()
    if not value:
        return ContentKind.TEXT
    cached = _kind_cache.get(value)
    if cached is not None:
        return cached
    if os.path.exists(value):
        ext = os.path.splitext(value)[1].lower()
        if ext in IMAGE_EXTS and QImageReader(value).canRead():
            kind = ContentKind.IMAGE
        else:
            kind = ContentKind.FILE
        _kind_cache[value] = kind
        return kind
    return ContentKind.TEXT


def is_image_path(text) -> bool:
    """是否是「存在的图片路径」（默认消息输入框预览用）。"""
    return classify_content(text) is ContentKind.IMAGE


def load_thumbnail(text) -> QPixmap:
    """图片的原图缓存（绘制时再按需缩放）。调用方须先确认是图片。"""
    value = (text or "").strip()
    pixmap = _thumbnail_cache.get(value)
    if pixmap is None:
        pixmap = QPixmap(value)
        _thumbnail_cache[value] = pixmap
    return pixmap


def file_icon(text) -> QIcon:
    """普通文件的占位图标（按扩展名 / 系统关联）。"""
    value = (text or "").strip()
    icon = _icon_cache.get(value)
    if icon is None:
        icon = _file_icon_provider.icon(QFileInfo(value))
        _icon_cache[value] = icon
    return icon


def tooltip_size(text) -> Tuple[int, int]:
    """悬停大图的显示尺寸：最长边压到 TOOLTIP_MAX 并保持比例。"""
    value = (text or "").strip()
    size = QImageReader(value).size()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        return TOOLTIP_MAX, TOOLTIP_MAX
    scale = min(1.0, TOOLTIP_MAX / max(size.width(), size.height()))
    return max(1, round(size.width() * scale)), max(1, round(size.height() * scale))


def _image_html(value: str) -> str:
    width, height = tooltip_size(value)
    name = html.escape(os.path.basename(value))
    src = QUrl.fromLocalFile(os.path.abspath(value)).toString()
    return f'<b>{name}</b><br><img src="{src}" width="{width}" height="{height}">'


def content_tooltip(text) -> str:
    """悬停文案：图片 → 文件名 + 大图；其余 → 完整原文。"""
    value = (text or "").strip()
    if not value:
        return ""
    if classify_content(value) is ContentKind.IMAGE:
        return _image_html(value)
    return html.escape(value)


def ghost_tooltip(text, label: str = "将发送默认消息") -> str:
    """空格子回落默认消息时的悬停文案：标题 + 内容（图片给大图）。"""
    value = (text or "").strip()
    if not value:
        return ""
    if classify_content(value) is ContentKind.IMAGE:
        return f"{label}：{_image_html(value)}"
    return f"{label}：{html.escape(value)}"
