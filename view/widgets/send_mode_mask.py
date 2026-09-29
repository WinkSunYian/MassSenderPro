# view/widgets/send_mode_mask.py
"""列表发送模式遮罩：盖住主区域锁定其它控件，右下角发送区放行。"""
from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QRegion
from PySide6.QtWidgets import QLabel, QWidget


class SendModeMask(QWidget):
    """半透明遮罩（自绘压暗，QWidget 子类的 QSS 背景不生效）。

    - 铺满主区域：压暗其它控件、吞掉它们的鼠标事件（键盘侧另有禁用兜底）。
    - 「放行区」（右下角发送栈）内的事件转发出去：
        左键按下           → send_clicked（开始 / 终止发送）
        右键按下 / 松开    → mode_pressed / mode_released
                             （由主窗口做长按计时：普通右键点一下不切换，
                              按住超过阈值才切换模式）
    - 右键按住拖出放行区 → 补发一次 mode_released 取消长按。
    - 放行区与底部提示区保持明亮（活的信息 / 活的控件不压暗）。
    - 悬停放行区时光标变手型，提示这里仍然可点。
    """

    send_clicked = Signal()
    mode_pressed = Signal()
    mode_released = Signal()

    # 压暗色：全窗统一叠一层半透明深色（明暗主题通用）
    DIM_COLOR = QColor(14, 16, 20, 115)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SendModeMask")
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setMouseTracking(True)
        self._pass_rect = QRect()
        self._bright_rects = []

        self._hint = QLabel(self)
        self._hint.setObjectName("MaskHint")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setWordWrap(True)
        # 提示标签也开鼠标跟踪：掠过它时事件会冒泡上来，光标才能复原成箭头
        self._hint.setMouseTracking(True)
        self._hint.setText(
            "列表发送模式 · 其它控件已锁定\n"
            "先把要发送的内容复制到剪贴板，点右下角按钮开始（F12 终止）\n"
            "右键长按右下角按钮可切回正常发送模式"
        )

    # ------------------------------------------------------------------
    def set_regions(self, pass_rect: QRect, bright_rects=()) -> None:
        """放行区（可点击）+ 额外保持明亮的区域（仅不压暗，点击仍被挡住）。

        额外明亮区用于底部提示行：倒计时 / 进程日志要保持清晰可读。
        """
        self._pass_rect = QRect(pass_rect)
        self._bright_rects = [QRect(pass_rect)] + [QRect(r) for r in bright_rects]
        self.update()

    def _in_pass(self, pos) -> bool:
        return self._pass_rect.contains(pos)

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        region = QRegion(self.rect())
        for rect in self._bright_rects:
            region = region.subtracted(QRegion(rect))
        with QPainter(self) as painter:
            painter.setClipRegion(region)
            painter.fillRect(self.rect(), self.DIM_COLOR)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # 提示文字水平居中、垂直居中偏上，给底部发送区留出空间
        self._hint.setGeometry(
            24,
            24,
            max(self.width() - 48, 0),
            max(self.height() - 48 - 70, 0),
        )

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        if not self._in_pass(pos):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.send_clicked.emit()
        elif event.button() == Qt.RightButton:
            self.mode_pressed.emit()  # 只报「按下」，长按判定交给主窗口计时
        else:
            event.ignore()
            return
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.RightButton and self._in_pass(
            event.position().toPoint()
        ):
            self.mode_released.emit()  # 没到长按阈值就松开 → 主窗口取消
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event) -> None:
        # 右键按住拖出放行区：取消长按（没按在放行区也发，发了只是空操作）
        if event.buttons() & Qt.RightButton and not self._in_pass(
            event.position().toPoint()
        ):
            self.mode_released.emit()
        cursor = (
            Qt.PointingHandCursor
            if self._in_pass(event.position().toPoint())
            else Qt.ArrowCursor
        )
        self.setCursor(cursor)
        event.accept()
