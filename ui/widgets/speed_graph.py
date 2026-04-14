"""
ShanuFx Downloader — Real-time speed graph widget.
Custom QPainter widget with 60-second rolling window and smooth bezier curves.
"""

import time
from collections import deque
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QLinearGradient,
    QPen,
    QFont,
    QBrush,
)
from PyQt6.QtWidgets import QWidget

import humanize


class SpeedGraph(QWidget):
    """Animated real-time download speed graph with smooth cubic bezier curves."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMaximumHeight(200)

        self._window_seconds: int = 60
        self._data_points: deque[tuple[float, float]] = deque(maxlen=120)
        self._max_speed: float = 1024  # Minimum 1 KB/s for Y-axis
        self._current_speed: float = 0.0

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._tick)
        self._update_timer.start(500)

        self._bg_color = QColor(10, 10, 15)
        self._grid_color = QColor(255, 255, 255, 12)
        self._text_color = QColor(148, 163, 184)
        self._line_color_start = QColor(0, 212, 255)
        self._line_color_end = QColor(124, 58, 237)
        self._fill_color_start = QColor(0, 212, 255, 40)
        self._fill_color_end = QColor(124, 58, 237, 10)

    def add_speed(self, speed_bps: float) -> None:
        """Add a speed data point (in bytes per second)."""
        self._current_speed = speed_bps
        self._data_points.append((time.time(), speed_bps))
        if speed_bps > self._max_speed:
            self._max_speed = speed_bps * 1.2

    def _tick(self) -> None:
        """Periodic update: prune old data and request repaint."""
        now = time.time()
        cutoff = now - self._window_seconds
        while self._data_points and self._data_points[0][0] < cutoff:
            self._data_points.popleft()

        if self._data_points:
            recent_max = max(s for _, s in self._data_points)
            self._max_speed = max(recent_max * 1.2, 1024)
        else:
            self._max_speed = 1024

        self.update()

    def paintEvent(self, event: object) -> None:
        """Custom paint the speed graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_left = 60
        margin_right = 12
        margin_top = 12
        margin_bottom = 28
        graph_w = w - margin_left - margin_right
        graph_h = h - margin_top - margin_bottom

        # Background
        painter.fillRect(0, 0, w, h, self._bg_color)

        # Grid lines (4 horizontal)
        painter.setPen(QPen(self._grid_color, 1))
        for i in range(5):
            y = margin_top + (graph_h * i / 4)
            painter.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))

        # Y-axis labels
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QPen(self._text_color, 1))
        for i in range(5):
            y = margin_top + (graph_h * i / 4)
            speed_val = self._max_speed * (1 - i / 4)
            label = self._format_speed(speed_val)
            painter.drawText(QRectF(0, y - 8, margin_left - 8, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # X-axis time labels
        for i in range(5):
            x = margin_left + (graph_w * i / 4)
            secs_ago = int(self._window_seconds * (1 - i / 4))
            label = f"-{secs_ago}s" if secs_ago > 0 else "now"
            painter.drawText(QRectF(x - 20, h - margin_bottom + 4, 40, 20), Qt.AlignmentFlag.AlignCenter, label)

        if len(self._data_points) < 2:
            # No data label
            painter.setPen(QPen(QColor(71, 85, 105), 1))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(margin_left, margin_top, graph_w, graph_h), Qt.AlignmentFlag.AlignCenter, "No activity")
            painter.end()
            return

        # Build path from data points
        now = time.time()
        points: list[QPointF] = []

        for t, speed in self._data_points:
            age = now - t
            x = margin_left + graph_w * (1 - age / self._window_seconds)
            y = margin_top + graph_h * (1 - speed / self._max_speed)
            x = max(margin_left, min(x, margin_left + graph_w))
            y = max(margin_top, min(y, margin_top + graph_h))
            points.append(QPointF(x, y))

        if not points:
            painter.end()
            return

        # Smooth cubic bezier path
        path = QPainterPath()
        path.moveTo(points[0])

        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]
            dx = (curr.x() - prev.x()) / 3
            cp1 = QPointF(prev.x() + dx, prev.y())
            cp2 = QPointF(curr.x() - dx, curr.y())
            path.cubicTo(cp1, cp2, curr)

        # Fill gradient under curve
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1].x(), margin_top + graph_h)
        fill_path.lineTo(points[0].x(), margin_top + graph_h)
        fill_path.closeSubpath()

        fill_gradient = QLinearGradient(0, margin_top, 0, margin_top + graph_h)
        fill_gradient.setColorAt(0, self._fill_color_start)
        fill_gradient.setColorAt(1, self._fill_color_end)
        painter.fillPath(fill_path, QBrush(fill_gradient))

        # Line gradient
        line_gradient = QLinearGradient(margin_left, 0, margin_left + graph_w, 0)
        line_gradient.setColorAt(0, self._line_color_start)
        line_gradient.setColorAt(1, self._line_color_end)

        pen = QPen(QBrush(line_gradient), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        # Glow dot at latest point
        if points:
            last = points[-1]
            glow_gradient = QLinearGradient(last.x() - 4, last.y() - 4, last.x() + 4, last.y() + 4)
            glow_gradient.setColorAt(0, self._line_color_start)
            glow_gradient.setColorAt(1, self._line_color_end)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 212, 255, 50))
            painter.drawEllipse(last, 8, 8)
            painter.setBrush(QBrush(glow_gradient))
            painter.drawEllipse(last, 4, 4)

        # Current speed label
        painter.setPen(QPen(self._line_color_start, 1))
        painter.setFont(QFont("Segoe UI Semibold", 10))
        speed_text = f"↓ {self._format_speed(self._current_speed)}/s"
        painter.drawText(QRectF(margin_left + 8, margin_top + 4, 200, 20), Qt.AlignmentFlag.AlignLeft, speed_text)

        painter.end()

    def _format_speed(self, bps: float) -> str:
        """Format bytes per second to human-readable."""
        if bps <= 0:
            return "0 B"
        if bps < 1024:
            return f"{bps:.0f} B"
        if bps < 1024 * 1024:
            return f"{bps / 1024:.1f} KB"
        if bps < 1024 * 1024 * 1024:
            return f"{bps / (1024 * 1024):.2f} MB"
        return f"{bps / (1024 * 1024 * 1024):.2f} GB"
