# view/clipboard_util.py
"""剪贴板读取：识别「复制的文件」，其余按普通文本处理。"""
import os

from PySide6.QtWidgets import QApplication


def clipboard_local_file() -> str:
    """剪贴板里是本地文件时返回其归一化路径，否则返回空串。"""
    mime = QApplication.clipboard().mimeData()
    if mime is None or not mime.hasUrls():
        return ""
    for url in mime.urls():
        if not url.isLocalFile():
            continue
        path = url.toLocalFile()
        if os.path.isfile(path):
            return os.path.normpath(path)
    return ""


def clipboard_file_or_text() -> str:
    """剪贴板里是文件返回其路径，否则返回剪贴板文本。"""
    path = clipboard_local_file()
    if path:
        return path
    return QApplication.clipboard().text()


def clipboard_has_urls() -> bool:
    """剪贴板里是否为 URL/文件对象（复制的文件、链接等，非纯文本）。"""
    mime = QApplication.clipboard().mimeData()
    return mime is not None and mime.hasUrls()
