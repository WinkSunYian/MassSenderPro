# view/theme.py
"""明暗主题：调色板定义、应用样式表生成与切换信号。

- Palette：一套完整的主题颜色（QSS + 单元格角色色）。
- build_stylesheet：把调色板渲染成整窗 QSS（窗口/按钮/卡片/表格/表头/滚动条）。
- ThemeManager：持有当前模式，切换时发出 changed 信号。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication

from view.enums.cell_status import CellStatus


class ThemeMode(Enum):
    """主题模式。"""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Palette:
    """一套完整的主题颜色。"""
    # 窗口 / 卡片
    window_bg: QColor
    card_bg: QColor
    card_border: QColor
    # 按钮
    btn_bg: QColor
    btn_border: QColor
    btn_text: QColor
    btn_hover_border: QColor
    btn_hover_text: QColor
    btn_pressed_bg: QColor
    primary_bg: QColor
    primary_hover_bg: QColor
    primary_text: QColor
    # 列表发送模式按钮（青色，与蓝色「发送」区分）
    list_send_bg: QColor
    list_send_hover_bg: QColor
    hint_text: QColor
    # 表格
    table_text: QColor
    gridline: QColor
    sel_bg: QColor
    sel_fg: QColor
    header_bg: QColor
    header_text: QColor
    # 卡片标题（姓名前缀 / 默认消息 / 状态统计）：比表头文字更醒目
    card_title_text: QColor
    header_border_b: QColor
    header_border_r: QColor
    scroll_handle: QColor
    scroll_hover: QColor
    # 顶部配置卡片的输入框
    config_bg: QColor
    # 发送状态单元格（NORMAL 为透明）
    # 五色规范：成功=绿、失败=红、待发=橙、跳过=灰、发送中(当前)=蓝
    status_bg: Dict[CellStatus, Optional[QColor]]
    status_fg: Dict[CellStatus, Optional[QColor]]


LIGHT_PALETTE = Palette(
    window_bg=QColor("#F4F6F9"),
    card_bg=QColor("#FFFFFF"),
    card_border=QColor("#E5E7EB"),
    btn_bg=QColor("#FFFFFF"),
    btn_border=QColor("#DCDFE6"),
    btn_text=QColor("#303133"),
    btn_hover_border=QColor("#409EFF"),
    btn_hover_text=QColor("#409EFF"),
    btn_pressed_bg=QColor("#ECF5FF"),
    primary_bg=QColor("#409EFF"),
    primary_hover_bg=QColor("#66B1FF"),
    primary_text=QColor("#FFFFFF"),
    list_send_bg=QColor("#00B8A9"),
    list_send_hover_bg=QColor("#26C6BA"),
    hint_text=QColor("#909399"),
    table_text=QColor("#303133"),
    gridline=QColor("#F0F1F3"),
    sel_bg=QColor("#D9E9FF"),
    sel_fg=QColor("#1F2D3D"),
    header_bg=QColor("#F7F8FA"),
    header_text=QColor("#606266"),
    # 浅色主题卡片标题：比表头文字更深、更醒目（不是真"白"）
    card_title_text=QColor("#26292E"),
    header_border_b=QColor("#EBEEF5"),
    header_border_r=QColor("#F2F3F5"),
    scroll_handle=QColor("#D9DDE3"),
    scroll_hover=QColor("#BFC5CD"),
    config_bg=QColor("#F5F7FA"),
    status_bg={
        CellStatus.NORMAL: None,
        CellStatus.PENDING: QColor("#FFF2E8"),
        CellStatus.SENDING: QColor("#E9F2FF"),
        CellStatus.SUCCESS: QColor("#E9F9F0"),
        CellStatus.FAILED: QColor("#FDECEC"),
        CellStatus.WARNING: QColor("#FDECEC"),
        CellStatus.SKIPPED: QColor("#F4F4F5"),
    },
    status_fg={
        CellStatus.NORMAL: None,
        CellStatus.PENDING: QColor("#D46B08"),
        CellStatus.SENDING: QColor("#0958D9"),
        CellStatus.SUCCESS: QColor("#237804"),
        CellStatus.FAILED: QColor("#CF1322"),
        CellStatus.WARNING: QColor("#CF1322"),
        CellStatus.SKIPPED: QColor("#8C8C8C"),
    },
)

DARK_PALETTE = Palette(
    window_bg=QColor("#17191D"),
    card_bg=QColor("#1F2228"),
    card_border=QColor("#30343B"),
    btn_bg=QColor("#24272D"),
    btn_border=QColor("#3A3E46"),
    btn_text=QColor("#E4E6EA"),
    btn_hover_border=QColor("#409EFF"),
    btn_hover_text=QColor("#409EFF"),
    btn_pressed_bg=QColor("#22345C"),
    primary_bg=QColor("#409EFF"),
    primary_hover_bg=QColor("#66B1FF"),
    primary_text=QColor("#FFFFFF"),
    list_send_bg=QColor("#00B8A9"),
    list_send_hover_bg=QColor("#26C6BA"),
    hint_text=QColor("#8B9099"),
    table_text=QColor("#E4E6EA"),
    gridline=QColor("#2A2E34"),
    sel_bg=QColor("#2B4670"),
    sel_fg=QColor("#FFFFFF"),
    header_bg=QColor("#24272D"),
    header_text=QColor("#A8ADB5"),
    # 深色主题卡片标题：从灰 (#A8ADB5) 提亮到接近白，卡片标题更醒目
    card_title_text=QColor("#F2F4F7"),
    header_border_b=QColor("#30343B"),
    header_border_r=QColor("#2A2E34"),
    scroll_handle=QColor("#3C4048"),
    scroll_hover=QColor("#4E535C"),
    config_bg=QColor("#24272D"),
    status_bg={
        CellStatus.NORMAL: None,
        CellStatus.PENDING: QColor("#3A2A18"),
        CellStatus.SENDING: QColor("#17273F"),
        CellStatus.SUCCESS: QColor("#153524"),
        CellStatus.FAILED: QColor("#3A1B1E"),
        CellStatus.WARNING: QColor("#3A1B1E"),
        CellStatus.SKIPPED: QColor("#2A2D33"),
    },
    status_fg={
        CellStatus.NORMAL: None,
        CellStatus.PENDING: QColor("#F0A33B"),
        CellStatus.SENDING: QColor("#6BA4F7"),
        CellStatus.SUCCESS: QColor("#57D08A"),
        CellStatus.FAILED: QColor("#F97066"),
        CellStatus.WARNING: QColor("#F97066"),
        CellStatus.SKIPPED: QColor("#9AA0A8"),
    },
)

_PALETTES = {
    ThemeMode.LIGHT: LIGHT_PALETTE,
    ThemeMode.DARK: DARK_PALETTE,
}


def build_stylesheet(palette: Palette) -> str:
    """把调色板渲染成整窗样式表（对所有子控件级联生效）。"""
    def n(color: QColor) -> str:
        return color.name()

    return f"""
QMainWindow, QWidget#CentralWidget {{
    background-color: {n(palette.window_bg)};
}}
QPushButton {{
    background-color: {n(palette.btn_bg)};
    border: 1px solid {n(palette.btn_border)};
    border-radius: 8px;
    padding: 6px 14px;
    color: {n(palette.btn_text)};
}}
QPushButton:hover {{
    border-color: {n(palette.btn_hover_border)};
    color: {n(palette.btn_hover_text)};
}}
QPushButton:pressed {{
    background-color: {n(palette.btn_pressed_bg)};
}}
QPushButton#PrimaryButton {{
    background-color: {n(palette.primary_bg)};
    border-color: {n(palette.primary_bg)};
    color: {n(palette.primary_text)};
}}
QPushButton#PrimaryButton:hover {{
    background-color: {n(palette.primary_hover_bg)};
    border-color: {n(palette.primary_hover_bg)};
    color: {n(palette.primary_text)};
}}
QPushButton#ListSendButton {{
    background-color: {n(palette.list_send_bg)};
    border-color: {n(palette.list_send_bg)};
    color: {n(palette.primary_text)};
}}
QPushButton#ListSendButton:hover {{
    background-color: {n(palette.list_send_hover_bg)};
    border-color: {n(palette.list_send_hover_bg)};
    color: {n(palette.primary_text)};
}}
QPushButton#StepButton {{
    padding: 0px;
    min-width: 26px;
    min-height: 26px;  /* 与 min-width 等值 → ± 按钮宽高一致（含 1px 边框） */
    font-weight: 700;
    text-align: center;
}}
QPushButton#StepButton:disabled {{
    color: {n(palette.hint_text)};
    background-color: {n(palette.header_bg)};
    border-color: {n(palette.gridline)};
}}
QProgressBar#SendProgress {{
    background-color: {n(palette.btn_bg)};
    border: 1px solid {n(palette.btn_border)};
    border-radius: 6px;
    text-align: center;
    color: {n(palette.btn_text)};
    font-weight: 600;
}}
QProgressBar#SendProgress::chunk {{
    background-color: {n(palette.primary_bg)};
}}
QLabel#LogBar {{
    color: {n(palette.hint_text)};
    font-size: 13px;
    padding: 2px 4px;
}}
/* 列表发送模式遮罩：压暗在控件内自绘（QWidget 子类 QSS 背景不生效），
   这里只管遮罩里的提示文字 */
QLabel#MaskHint {{
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 600;
    background-color: transparent;
}}
QLabel#AppTitle {{
    color: {n(palette.table_text)};
    font-size: 17px;
    font-weight: 700;
    padding: 2px 4px;
}}
QFrame#CardFrame {{
    background-color: {n(palette.card_bg)};
    border: 1px solid {n(palette.card_border)};
    border-radius: 12px;
}}
QTableView {{
    background-color: transparent;
    border: none;
    gridline-color: {n(palette.gridline)};
    selection-background-color: {n(palette.sel_bg)};
    selection-color: {n(palette.sel_fg)};
    color: {n(palette.table_text)};
    outline: none;
    font-size: 14px;  /* 表格内容：比列标题(15px)小、比原默认大 */
}}
QTableView::item {{
    padding: 2px 6px;
}}
/* 顶部「默认消息」表：外观与「姓名前缀」输入框完全一致
   （圆角浅底 / 15px 斜体 / 文字左右 8px 内边距） */
QTableView#DefaultMessageTable {{
    background-color: {n(palette.config_bg)};
    border-radius: 6px;
    font-size: 15px;
    font-style: italic;
}}
QTableView#DefaultMessageTable::item {{
    padding: 0px 8px;
}}
QLineEdit {{
    background-color: {n(palette.card_bg)};
    color: {n(palette.table_text)};
    border: none;
    selection-background-color: {n(palette.sel_bg)};
    selection-color: {n(palette.sel_fg)};
}}
QLineEdit#ConfigInput {{
    background-color: {n(palette.config_bg)};
    color: {n(palette.table_text)};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 15px;
}}
QLineEdit#ConfigInput:focus {{
    border-color: {n(palette.primary_bg)};
}}
QComboBox#ConfigInput {{
    background-color: {n(palette.config_bg)};
    color: {n(palette.table_text)};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 15px;
}}
QComboBox#ConfigInput:focus {{
    border-color: {n(palette.primary_bg)};
}}
QComboBox#ConfigInput::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox#ConfigInput::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {n(palette.hint_text)};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {n(palette.card_bg)};
    color: {n(palette.table_text)};
    border: 1px solid {n(palette.card_border)};
    selection-background-color: {n(palette.sel_bg)};
    selection-color: {n(palette.sel_fg)};
    outline: none;
    font-size: 14px;
}}
QLabel#CardTitle {{
    color: {n(palette.card_title_text)};
    font-size: 16px;
    font-weight: 700;
    padding: 2px 6px 6px 6px;
}}
QLabel#StatsLabel {{
    color: {n(palette.header_text)};
    font-size: 12px;
}}
QLabel#StatsValue {{
    font-size: 13px;
    font-weight: 700;
}}
QToolTip {{
    color: {n(palette.table_text)};
    background-color: {n(palette.card_bg)};
    border: 1px solid {n(palette.card_border)};
    padding: 4px 6px;
}}
QHeaderView {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: {n(palette.header_bg)};
    color: {n(palette.header_text)};
    border: none;
    border-bottom: 1px solid {n(palette.header_border_b)};
    border-right: 1px solid {n(palette.header_border_r)};
    padding: 6px 8px;
    font-weight: 600;
}}
QHeaderView::section:first {{
    border-top-left-radius: 8px;
}}
QHeaderView::section:horizontal {{
    /* 列标题：比表格内容大、加粗、用正文色更显眼 */
    font-size: 15px;
    font-weight: 700;
    color: {n(palette.table_text)};
}}
QTableCornerButton::section {{
    /* 行列表头交叉的拐角块：与表头同色同线，弱化存在感 */
    background-color: {n(palette.header_bg)};
    border: none;
    border-bottom: 1px solid {n(palette.header_border_b)};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {n(palette.scroll_handle)};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {n(palette.scroll_hover)};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""


def system_theme_mode() -> ThemeMode:
    """读取系统当前的明暗偏好（无 QGuiApplication 时退回浅色）。"""
    if QGuiApplication.instance() is None:
        return ThemeMode.LIGHT
    try:
        if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
            return ThemeMode.DARK
    except (AttributeError, RuntimeError):
        pass
    return ThemeMode.LIGHT


class ThemeManager(QObject):
    """主题切换器：持有当前模式与调色板，切换时发出 changed 信号。"""

    changed = Signal(ThemeMode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = system_theme_mode()

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def palette(self) -> Palette:
        return _PALETTES[self._mode]

    @property
    def toggle_label(self) -> str:
        """切换按钮应显示的目标模式名称。"""
        if self._mode == ThemeMode.DARK:
            return "浅色模式"
        return "深色模式"

    def set_mode(self, mode: ThemeMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self.changed.emit(mode)

    def toggle(self) -> None:
        if self._mode == ThemeMode.LIGHT:
            self.set_mode(ThemeMode.DARK)
        else:
            self.set_mode(ThemeMode.LIGHT)


_manager: Optional[ThemeManager] = None


def theme_manager() -> ThemeManager:
    """全局主题管理器（惰性单例，首次调用时跟随系统模式）。"""
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager
