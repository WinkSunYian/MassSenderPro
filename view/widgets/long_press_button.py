# view/widgets/long_press_button.py
"""带长按进度动画的按钮：右键按住时从左到右填充，松手回缩、到点撑满。"""
from PySide6.QtCore import QPointF, QRectF, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton


class LongPressButton(QPushButton):
    """QPushButton + 长按填充动画（配合「右键长按切换发送模式」）。

    - startHold(ms)：右键按下起，填充 0→100%，到点刚好撑满；
    - cancelHold()：中途松手，按当前进度快速回缩归零
      （进度太小直接归零，普通右键点一下不闪）；
    - finishHold()：长按到点，先撑满给完成反馈再回缩复位。

    填充层 = 白色半透明色块 + 前沿亮线，圆角与 QSS（8px）一致，
    叠在按钮底色/文字之上，蓝 / 青按钮、明暗主题都看得清。
    """

    # 白色半透明填充与前沿亮线（对蓝、青两种底色都有对比）
    FILL_COLOR = QColor(255, 255, 255, 64)
    EDGE_COLOR = QColor(255, 255, 255, 150)

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._hold_value = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_hold_value)

    # ------------------------------------------------------------------
    # 长按生命周期
    # ------------------------------------------------------------------
    def startHold(self, duration_ms: int) -> None:
        """右键按下：填充从 0 重新长到 100%，时长与长按阈值一致。

        每次按下都强制清零——上一次的回缩 / 收尾可能还没走完，
        不能让它从残留进度接着长。
        """
        self._anim.stop()
        self._set_hold_value(0.0)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(100.0)
        self._anim.start()

    def cancelHold(self) -> None:
        """中途松手：按当前进度快速回缩；几乎没进度（普通点击）直接归零不闪。"""
        self._anim.stop()
        if self._hold_value < 8.0:
            self._set_hold_value(0.0)
            return
        self._anim.setDuration(max(90, int(180 * self._hold_value / 100.0)))
        self._anim.setStartValue(self._hold_value)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def finishHold(self) -> None:
        """长按到点：瞬间撑满给完成反馈，再回缩复位（切页隐藏时也无害）。"""
        self._anim.stop()
        self._set_hold_value(100.0)
        self._anim.setDuration(200)
        self._anim.setStartValue(100.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def holdValue(self) -> float:
        """当前填充进度（0-100，测试用）。"""
        return self._hold_value

    # ------------------------------------------------------------------
    def _set_hold_value(self, value: float) -> None:
        self._hold_value = float(value)
        self.update()

    def _on_hold_value(self, value) -> None:
        self._set_hold_value(float(value))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._hold_value <= 0.0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 圆角与 QSS 的 border-radius: 8px 一致，填充不越界
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 8.0, 8.0)
        painter.setClipPath(clip)

        fill_width = self.width() * self._hold_value / 100.0
        painter.fillRect(QRectF(0, 0, fill_width, self.height()), self.FILL_COLOR)
        if fill_width >= 1.0:
            # 前沿亮线：让「进度走到哪了」一眼可见
            painter.setPen(QPen(self.EDGE_COLOR, 2.0))
            painter.drawLine(
                QPointF(fill_width, 1.0),
                QPointF(fill_width, self.height() - 1.0),
            )
        painter.end()
