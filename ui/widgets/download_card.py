"""
ShanuFx Downloader — Per-download progress card widget.
Glass-styled card with segmented progress, speed, ETA, and hover controls.
"""

import time
from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QLinearGradient,
    QPen,
    QFont,
    QBrush,
    QPainterPath,
)
from PyQt6.QtCore import pyqtProperty
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)

import humanize

from config import get_file_icon, get_file_type
from icons import get_icon, get_pixmap


class SegmentedProgressBar(QWidget):
    """Custom progress bar showing per-segment progress with gradient shading."""

    def __init__(self, segment_count: int = 1, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(6)
        self.setMaximumHeight(6)
        self._segment_count = max(segment_count, 1)
        self._segment_progress: list[float] = [0.0] * self._segment_count
        self._overall_progress: float = 0.0

    def set_segment_count(self, count: int) -> None:
        self._segment_count = max(count, 1)
        self._segment_progress = [0.0] * self._segment_count
        self.update()

    def set_segment_progress(self, segment_id: int, progress: float) -> None:
        if 0 <= segment_id < self._segment_count:
            self._segment_progress[segment_id] = min(progress, 1.0)
            self._overall_progress = sum(self._segment_progress) / self._segment_count
            self.update()

    @pyqtProperty(float)
    def progress(self) -> float:
        return self._overall_progress

    @progress.setter
    def progress(self, value: float) -> None:
        self._overall_progress = value
        self.update()

    def set_overall_progress(self, progress: float, animate: bool = True) -> None:
        target = min(progress, 1.0)
        if not animate or abs(target - self._overall_progress) < 0.01:
            self.progress = target
            self._segment_progress = [target] * self._segment_count
        else:
            if hasattr(self, "_anim"):
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"progress")
            self._anim.setDuration(400)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.setStartValue(self._overall_progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self._segment_progress = [target] * self._segment_count

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 15))
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        if self._overall_progress <= 0:
            painter.end()
            return

        # Filled portion with gradient
        fill_w = int(w * self._overall_progress)
        if fill_w < 1:
            painter.end()
            return

        gradient = QLinearGradient(0, 0, w, 0)
        gradient.setColorAt(0, QColor(0, 212, 255))
        gradient.setColorAt(1, QColor(124, 58, 237))

        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, fill_w, h, radius, radius)

        # Segment separators
        if self._segment_count > 1:
            seg_w = w / self._segment_count
            painter.setPen(QPen(QColor(10, 10, 15, 80), 1))
            for i in range(1, self._segment_count):
                x = int(i * seg_w)
                if x < fill_w:
                    painter.drawLine(x, 0, x, h)

        painter.end()


class DownloadCard(QFrame):
    """Per-download progress card with glassmorphism styling."""

    pause_clicked = pyqtSignal(int)  # download_id
    resume_clicked = pyqtSignal(int)
    cancel_clicked = pyqtSignal(int)
    open_folder_clicked = pyqtSignal(int)

    STATUS_STYLES = {
        "downloading": "statusDownloading",
        "paused": "statusPaused",
        "queued": "statusQueued",
        "complete": "statusComplete",
        "failed": "statusFailed",
        "merging": "statusMerging",
        "cancelled": "statusFailed",
    }

    STATUS_LABELS = {
        "downloading": "DOWNLOADING",
        "paused": "PAUSED",
        "queued": "QUEUED",
        "complete": "COMPLETE",
        "failed": "FAILED",
        "merging": "MERGING",
        "cancelled": "CANCELLED",
    }

    def __init__(
        self,
        download_id: int,
        filename: str = "Resolving...",
        url: str = "",
        total_size: int = 0,
        segment_count: int = 1,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.download_id = download_id
        self._filename = filename
        self._url = url
        self._total_size = total_size
        self._status = "queued"
        self._speed: float = 0
        self._eta: float = 0
        self._downloaded: int = 0
        self._start_time = time.time()

        self.setObjectName("glassCard")
        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Pulse animation for status badge
        self._pulse_anim = None

        self._setup_ui(segment_count)
        self._update_display()

    def _setup_ui(self, segment_count: int) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # File type icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setPixmap(get_pixmap(get_file_icon(self._filename), 32))
        main_layout.addWidget(self._icon_label)

        # Info column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Top row: filename + status badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._name_label = QLabel(self._filename)
        self._name_label.setObjectName("headingLabel")
        self._name_label.setFont(QFont("Segoe UI Semibold", 10))
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row.addWidget(self._name_label)

        self._status_badge = QLabel("QUEUED")
        self._status_badge.setObjectName("statusQueued")
        self._status_badge.setFixedHeight(20)
        top_row.addWidget(self._status_badge)

        info_layout.addLayout(top_row)

        # Progress bar
        self._progress_bar = SegmentedProgressBar(segment_count)
        info_layout.addWidget(self._progress_bar)

        # Bottom row: size, speed, eta, source
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        self._size_label = QLabel("0 B / 0 B")
        self._size_label.setObjectName("secondaryLabel")
        bottom_row.addWidget(self._size_label)

        self._speed_label = QLabel("—")
        self._speed_label.setObjectName("secondaryLabel")
        bottom_row.addWidget(self._speed_label)

        self._eta_label = QLabel("—")
        self._eta_label.setObjectName("secondaryLabel")
        bottom_row.addWidget(self._eta_label)

        bottom_row.addStretch()

        # Source domain
        self._source_label = QLabel("")
        self._source_label.setObjectName("mutedLabel")
        bottom_row.addWidget(self._source_label)

        info_layout.addLayout(bottom_row)
        main_layout.addLayout(info_layout, 1)

        # Action buttons (shown on hover)
        self._actions_widget = QWidget()
        actions_layout = QVBoxLayout(self._actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)

        self._pause_btn = QPushButton()
        self._pause_btn.setIcon(get_icon("pause"))
        self._pause_btn.setObjectName("iconBtn")
        self._pause_btn.setToolTip("Pause")
        self._pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.download_id))

        self._resume_btn = QPushButton()
        self._resume_btn.setIcon(get_icon("play"))
        self._resume_btn.setObjectName("iconBtn")
        self._resume_btn.setToolTip("Resume")
        self._resume_btn.clicked.connect(lambda: self.resume_clicked.emit(self.download_id))
        self._resume_btn.setVisible(False)

        self._cancel_btn = QPushButton()
        self._cancel_btn.setIcon(get_icon("close"))
        self._cancel_btn.setObjectName("iconBtn")
        self._cancel_btn.setToolTip("Cancel")
        self._cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(self.download_id))

        actions_layout.addWidget(self._pause_btn)
        actions_layout.addWidget(self._resume_btn)
        actions_layout.addWidget(self._cancel_btn)
        actions_layout.addStretch()

        self._actions_widget.setVisible(False)
        main_layout.addWidget(self._actions_widget)

        # Hover shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(15)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self._shadow.setOffset(0, 4)
        self.setGraphicsEffect(self._shadow)

        if self._url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(self._url).netloc
                if domain.startswith("www."):
                    domain = domain[4:]
                self._source_label.setText(domain)
            except Exception:
                pass

    def enterEvent(self, event: object) -> None:
        self._actions_widget.setVisible(True)
        self._shadow.setColor(QColor(0, 0, 0, 100))
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:
        self._actions_widget.setVisible(False)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        super().leaveEvent(event)

    def update_progress(self, downloaded: int, total: int, speed: float, eta: float) -> None:
        """Update download progress."""
        self._downloaded = downloaded
        self._total_size = total if total > 0 else self._total_size
        self._speed = speed
        self._eta = eta

        if self._total_size > 0:
            progress = downloaded / self._total_size
            self._progress_bar.set_overall_progress(progress)

        self._update_display()

    def update_segment_progress(self, segment_id: int, downloaded: int, total: int) -> None:
        """Update a specific segment's progress."""
        if total > 0:
            self._progress_bar.set_segment_progress(segment_id, downloaded / total)

    def set_status(self, status: str) -> None:
        """Update the download status."""
        self._status = status
        style = self.STATUS_STYLES.get(status, "statusQueued")
        label_text = self.STATUS_LABELS.get(status, status.upper())
        self._status_badge.setObjectName(style)
        self._status_badge.setText(label_text)
        self._status_badge.setStyle(self._status_badge.style())

        self._pause_btn.setVisible(status == "downloading")
        self._resume_btn.setVisible(status == "paused")
        self._cancel_btn.setVisible(status in ("downloading", "paused", "queued"))

        self._update_pulse(status == "downloading")
        self._update_display()

    def _update_pulse(self, active: bool) -> None:
        if active:
            if not self._pulse_anim:
                eff = QGraphicsOpacityEffect(self._status_badge)
                self._status_badge.setGraphicsEffect(eff)
                self._pulse_anim = QPropertyAnimation(eff, b"opacity")
                self._pulse_anim.setDuration(1000)
                self._pulse_anim.setStartValue(1.0)
                self._pulse_anim.setEndValue(0.4)
                self._pulse_anim.setLoopCount(-1)
                self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            self._pulse_anim.start()
        else:
            if self._pulse_anim:
                self._pulse_anim.stop()
                self._status_badge.graphicsEffect().setOpacity(1.0)

    def set_filename(self, filename: str) -> None:
        self._filename = filename
        self._name_label.setText(filename)
        self._icon_label.setPixmap(get_pixmap(get_file_icon(self._filename), 32))

    def _update_display(self) -> None:
        """Refresh all display labels."""
        # Size
        if self._total_size > 0:
            dl = humanize.naturalsize(self._downloaded, binary=True)
            total = humanize.naturalsize(self._total_size, binary=True)
            self._size_label.setText(f"{dl} / {total}")
        else:
            if self._downloaded > 0:
                self._size_label.setText(humanize.naturalsize(self._downloaded, binary=True))
            else:
                self._size_label.setText("—")

        # Speed
        if self._status == "downloading" and self._speed > 0:
            speed_str = humanize.naturalsize(self._speed, binary=True)
            self._speed_label.setText(f"↓ {speed_str}/s")
        elif self._status == "complete":
            self._speed_label.setText("✓ Done")
        else:
            self._speed_label.setText("—")

        # ETA
        if self._status == "downloading" and self._eta > 0:
            eta_int = int(self._eta)
            if eta_int >= 3600:
                h = eta_int // 3600
                m = (eta_int % 3600) // 60
                self._eta_label.setText(f"ETA {h}h {m}m")
            elif eta_int >= 60:
                m = eta_int // 60
                s = eta_int % 60
                self._eta_label.setText(f"ETA {m}m {s}s")
            else:
                self._eta_label.setText(f"ETA {eta_int}s")
        elif self._status == "complete":
            elapsed = int(time.time() - self._start_time)
            self._eta_label.setText(f"in {elapsed}s")
        else:
            self._eta_label.setText("—")
