"""
ShanuFx Downloader — Custom QStackedWidget with sliding transitions.
Provides a smooth, modern navigation experience.
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup, pyqtProperty
from PyQt6.QtWidgets import QStackedWidget, QWidget


class SlidingStackedWidget(QStackedWidget):
    """StackedWidget with animated slide transitions."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._animation_duration = 350
        self._animation_easing = QEasingCurve.Type.OutCubic
        self._active_animation = False
        self._current_index = 0
        self._next_index = 0
        self._wrap = False

    def set_duration(self, duration: int) -> None:
        self._animation_duration = duration

    def set_easing(self, easing: QEasingCurve.Type) -> None:
        self._animation_easing = easing

    def slide_to_index(self, index: int) -> None:
        if self._active_animation or index == self.currentIndex():
            return

        self._current_index = self.currentIndex()
        self._next_index = index

        w = self.width()
        h = self.height()

        # Determine direction
        if self._next_index > self._current_index:
            p_out_start = QPoint(0, 0)
            p_out_end = QPoint(-w, 0)
            p_in_start = QPoint(w, 0)
            p_in_end = QPoint(0, 0)
        else:
            p_out_start = QPoint(0, 0)
            p_out_end = QPoint(w, 0)
            p_in_start = QPoint(-w, 0)
            p_in_end = QPoint(0, 0)

        # Prepare next widget
        next_widget = self.widget(self._next_index)
        current_widget = self.widget(self._current_index)

        next_widget.setGeometry(p_in_start.x(), p_in_start.y(), w, h)
        next_widget.show()
        next_widget.raise_()

        # Create animations
        anim_out = QPropertyAnimation(current_widget, b"pos")
        anim_out.setDuration(self._animation_duration)
        anim_out.setEasingCurve(self._animation_easing)
        anim_out.setStartValue(p_out_start)
        anim_out.setEndValue(p_out_end)

        anim_in = QPropertyAnimation(next_widget, b"pos")
        anim_in.setDuration(self._animation_duration)
        anim_in.setEasingCurve(self._animation_easing)
        anim_in.setStartValue(p_in_start)
        anim_in.setEndValue(p_in_end)

        self._group = QParallelAnimationGroup()
        self._group.addAnimation(anim_out)
        self._group.addAnimation(anim_in)
        self._group.finished.connect(self._on_animation_finished)

        self._active_animation = True
        self._group.start()

    def _on_animation_finished(self) -> None:
        if not self._active_animation:
            return
            
        super().setCurrentIndex(self._next_index)
        self._active_animation = False
        
        # Reset positions and ensure only target is visible
        for i in range(self.count()):
            w = self.widget(i)
            w.move(0, 0)
            w.show() if i == self._next_index else w.hide()

    def setCurrentIndex(self, index: int) -> None:
        # Override to use animation if visible and not already there
        if self.isVisible() and index != self.currentIndex() and not self._active_animation:
            self.slide_to_index(index)
        elif not self._active_animation:
            super().setCurrentIndex(index)
