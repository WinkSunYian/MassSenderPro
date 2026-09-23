# view/widgets/scroll_synchronizer.py
from PySide6.QtCore import QObject


class ScrollSynchronizer(QObject):
    """让多个表格视图的垂直滚动条保持同步。"""

    def __init__(self, views, parent=None) -> None:
        super().__init__(parent)
        self._views = list(views)
        self._updating = False

        for view in self._views:
            view.verticalScrollBar().valueChanged.connect(
                lambda value, source=view: self._on_value_changed(source, value)
            )

    def _on_value_changed(self, source, value: int) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            for view in self._views:
                if view is source:
                    continue
                bar = view.verticalScrollBar()
                if bar.value() != value:
                    bar.setValue(value)
        finally:
            self._updating = False