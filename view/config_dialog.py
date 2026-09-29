# view/config_dialog.py
"""配置中心：每个配置一页、各自独立 UI，改动即时写入 configs 并生效。

没有取消 / 保存按钮：添加或删除的瞬间就写文件，
主窗口通过 changed 信号实时感知（例如前缀变化刷新顶部下拉）。
未来新增配置 = 新建一个 XxxConfigPage + addTab 一行。

外观遵循「简约 + 卡片」：
- 窗口底色 = 主窗口同款 window_bg；页签交给 Qt 原生绘制、只接管文字色，
  页签容器（pane）显式铺同款底色并去边框——原生窗格会画系统底色，很丑；
- 每页一张 CardFrame 卡片承载内容，与主窗口卡片同款样式；
- 两页结构统一：说明 → 列表 → 添加行（输入框 +「添加」）→ 删除行，
  添加行统一在列表下方；
- 不做「共几条」统计（无意义）；按钮保持原生样式，只做启用联动：
  内容为空 / 重复不能加、无选中不能删；
- 列表圆角描边 + 悬停淡染，空列表中央一行提示。
"""
from typing import List

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.LineListConfig import LineListConfig
from view.theme import build_stylesheet, theme_manager


def _mix(base: QColor, over: QColor, t: float) -> QColor:
    """把 over 色按 t 比例混进 base 得到不透明实色（QSS 写不了混色，列表悬停淡染用它）。"""
    return QColor(
        round(base.red() + (over.red() - base.red()) * t),
        round(base.green() + (over.green() - base.green()) * t),
        round(base.blue() + (over.blue() - base.blue()) * t),
    )


class PrefixConfigPage(QWidget):
    """姓名前缀页：说明 → 列表 → 添加行（输入在列表下方）→ 删除行。

    添加 / 删除立即写入 configs/prefixes.txt，并发出 changed("prefixes")。
    """

    changed = Signal(str)
    KEY = "prefixes"

    def __init__(self, config: LineListConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._items: List[str] = list(config.load())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        hint = QLabel("发送时拼在联系人姓名前。")
        hint.setObjectName("PageHint")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        card_layout.addWidget(self._list, 1)
        self._empty = self._make_empty_hint("还没有前缀，输入后回车添加")

        # 添加行统一在列表下方（与跳过关键字页一致）
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setObjectName("ConfigInput")
        self._input.setPlaceholderText("输入前缀后回车添加，如 PY111")
        self._add_button = QPushButton("添加")
        self._add_button.setEnabled(False)
        add_row.addWidget(self._input, 1)
        add_row.addWidget(self._add_button)
        card_layout.addLayout(add_row)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self._delete_button = QPushButton("删除选中")
        self._delete_button.setEnabled(False)
        foot.addWidget(self._delete_button)
        foot.addStretch(1)
        card_layout.addLayout(foot)

        root.addWidget(card, 1)

        self._input.returnPressed.connect(self._on_add)
        self._input.textChanged.connect(self._refresh_actions)
        self._add_button.clicked.connect(self._on_add)
        self._delete_button.clicked.connect(self._on_delete)
        self._list.itemSelectionChanged.connect(self._refresh_actions)
        self._list.installEventFilter(self)

        self._reload()
        self._refresh_actions()

    def items(self) -> List[str]:
        return list(self._items)

    # ------------------------------------------------------------------
    def _make_empty_hint(self, text: str) -> QLabel:
        """空态提示：浮在列表正中，透明过鼠标（点击落到底下的列表）。"""
        label = QLabel(text, self._list)
        label.setObjectName("EmptyHint")
        label.setAlignment(Qt.AlignCenter)
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        label.hide()
        return label

    def eventFilter(self, obj, event):
        if obj is self._list and event.type() in (QEvent.Resize, QEvent.Show):
            self._empty.setGeometry(self._list.rect())
            self._empty.raise_()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        # 列表获得焦点时 Delete / Backspace 直接删选中行
        if (
            event.key() in (Qt.Key_Delete, Qt.Key_Backspace)
            and self._list.hasFocus()
            and self._list.selectedItems()
        ):
            self._on_delete()
            return
        super().keyPressEvent(event)

    def _reload(self) -> None:
        self._list.clear()
        for item in self._items:
            self._list.addItem(QListWidgetItem(item))
        self._refresh_empty()

    def _refresh_empty(self) -> None:
        self._empty.setVisible(self._list.count() == 0)

    def _refresh_actions(self) -> None:
        """「添加」= 有内容且不重复；「删除选中」= 列表里有选中，才可点。"""
        text = self._input.text().strip()
        self._add_button.setEnabled(bool(text) and text not in self._items)
        self._delete_button.setEnabled(bool(self._list.selectedItems()))

    def _persist(self) -> None:
        self._config.save(self._items)
        self.changed.emit(self.KEY)

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if text and text not in self._items:
            self._items.append(text)
            self._list.addItem(QListWidgetItem(text))
            self._list.setCurrentRow(self._list.count() - 1)
            self._persist()
            self._refresh_empty()
        self._input.clear()
        self._input.setFocus()

    def _on_delete(self) -> None:
        rows = sorted(
            {index.row() for index in self._list.selectedIndexes()}, reverse=True
        )
        if not rows:
            return
        for row in rows:
            self._items.pop(row)
            self._list.takeItem(row)
        self._persist()
        self._refresh_empty()
        self._refresh_actions()


class KeywordConfigPage(QWidget):
    """跳过关键字页：说明 → 列表 → 添加行（输入在列表下方）→ 删除行。

    备注命中关键字的联系人会被跳过。添加 / 删除立即写入
    configs/skip_keywords.txt，并发出 changed("keywords")。
    发送流程每次发送都重读该文件，所以改完下一次发送即生效。
    """

    changed = Signal(str)
    KEY = "keywords"

    def __init__(self, config: LineListConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._items: List[str] = list(config.load())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        hint = QLabel("好友备注包含任意关键字时，该联系人会被跳过、不发送。")
        hint.setObjectName("PageHint")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        card_layout.addWidget(self._list, 1)
        self._empty = self._make_empty_hint("还没有关键字，输入后回车添加")

        # 添加行统一在列表下方（与姓名前缀页一致）
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setObjectName("ConfigInput")
        self._input.setPlaceholderText("输入关键字后回车添加")
        self._add_button = QPushButton("添加")
        self._add_button.setEnabled(False)
        add_row.addWidget(self._input, 1)
        add_row.addWidget(self._add_button)
        card_layout.addLayout(add_row)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self._delete_button = QPushButton("删除选中")
        self._delete_button.setEnabled(False)
        foot.addWidget(self._delete_button)
        foot.addStretch(1)
        card_layout.addLayout(foot)

        root.addWidget(card, 1)

        self._input.returnPressed.connect(self._on_add)
        self._input.textChanged.connect(self._refresh_actions)
        self._add_button.clicked.connect(self._on_add)
        self._delete_button.clicked.connect(self._on_delete)
        self._list.itemSelectionChanged.connect(self._refresh_actions)
        self._list.installEventFilter(self)

        self._reload()
        self._refresh_actions()

    def items(self) -> List[str]:
        return list(self._items)

    # ------------------------------------------------------------------
    def _make_empty_hint(self, text: str) -> QLabel:
        """空态提示：浮在列表正中，透明过鼠标（点击落到底下的列表）。"""
        label = QLabel(text, self._list)
        label.setObjectName("EmptyHint")
        label.setAlignment(Qt.AlignCenter)
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        label.hide()
        return label

    def eventFilter(self, obj, event):
        if obj is self._list and event.type() in (QEvent.Resize, QEvent.Show):
            self._empty.setGeometry(self._list.rect())
            self._empty.raise_()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        # 列表获得焦点时 Delete / Backspace 直接删选中行
        if (
            event.key() in (Qt.Key_Delete, Qt.Key_Backspace)
            and self._list.hasFocus()
            and self._list.selectedItems()
        ):
            self._on_delete()
            return
        super().keyPressEvent(event)

    def _reload(self) -> None:
        self._list.clear()
        for item in self._items:
            self._list.addItem(QListWidgetItem(item))
        self._refresh_empty()

    def _refresh_empty(self) -> None:
        self._empty.setVisible(self._list.count() == 0)

    def _refresh_actions(self) -> None:
        """「添加」= 有内容且不重复；「删除选中」= 列表里有选中，才可点。"""
        text = self._input.text().strip()
        self._add_button.setEnabled(bool(text) and text not in self._items)
        self._delete_button.setEnabled(bool(self._list.selectedItems()))

    def _persist(self) -> None:
        self._config.save(self._items)
        self.changed.emit(self.KEY)

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if text and text not in self._items:
            self._items.append(text)
            self._list.addItem(QListWidgetItem(text))
            self._list.setCurrentRow(self._list.count() - 1)
            self._persist()
            self._refresh_empty()
        self._input.clear()
        self._input.setFocus()

    def _on_delete(self) -> None:
        rows = sorted(
            {index.row() for index in self._list.selectedIndexes()}, reverse=True
        )
        if not rows:
            return
        for row in rows:
            self._items.pop(row)
            self._list.takeItem(row)
        self._persist()
        self._refresh_empty()
        self._refresh_actions()


class ConfigDialog(QDialog):
    """配置中心：选项卡承载各配置页，改动即时生效，关闭即完成。"""

    changed = Signal(str)

    MIN_WIDTH = 460
    MIN_HEIGHT = 470

    def __init__(
        self,
        prefix_config: LineListConfig,
        keyword_config: LineListConfig,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("配置中心")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.setStyleSheet(self._build_stylesheet())
        self._build_ui(prefix_config, keyword_config)

    # ------------------------------------------------------------------
    def _build_ui(
        self, prefix_config: LineListConfig, keyword_config: LineListConfig
    ) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self._tabs = QTabWidget()
        self._prefix_page = PrefixConfigPage(prefix_config)
        self._keyword_page = KeywordConfigPage(keyword_config)
        self._prefix_page.changed.connect(self.changed)
        self._keyword_page.changed.connect(self.changed)
        self._tabs.addTab(self._prefix_page, "姓名前缀")
        self._tabs.addTab(self._keyword_page, "跳过关键字")
        root.addWidget(self._tabs, 1)

    # ------------------------------------------------------------------
    def _build_stylesheet(self) -> str:
        p = theme_manager().palette
        hover = _mix(p.card_bg, p.table_text, 0.05)  # 列表行悬停淡染
        return (
            build_stylesheet(p)
            + f"""
QDialog {{
    background-color: {p.window_bg.name()};
}}
/* 页签容器：显式铺窗口底色、去掉原生窗格的边框与系统底色（就是那个丑底色） */
QTabWidget::pane {{
    background-color: {p.window_bg.name()};
    border: none;
}}
/* 页签交给 Qt 原生绘制，只接管文字色与字号以便跟随主题 */
QTabBar::tab {{
    color: {p.table_text.name()};
    font-size: 14px;
}}
QLabel {{
    color: {p.header_text.name()};
    font-size: 13px;
}}
QLabel#PageHint {{
    /* 页内说明：弱化的小号提示文字 */
    color: {p.hint_text.name()};
    font-size: 12px;
}}
QLabel#EmptyHint {{
    color: {p.hint_text.name()};
    font-size: 13px;
    background: transparent;
}}
QListWidget {{
    background-color: {p.card_bg.name()};
    color: {p.table_text.name()};
    border: 1px solid {p.card_border.name()};
    border-radius: 8px;
    font-size: 14px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border: none;
}}
QListWidget::item:hover {{
    background-color: {hover.name()};
}}
QListWidget::item:selected {{
    background-color: {p.sel_bg.name()};
    color: {p.sel_fg.name()};
    border: none;
}}
"""
        )
