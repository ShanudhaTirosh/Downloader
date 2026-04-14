"""
ShanuFx Downloader — Media preview panel widget.
Shows thumbnail, metadata, platform badge, and format selector for social media content.
"""

import os
from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QPixmap, QFont, QImage, QColor, QPainter, QLinearGradient
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QWidget,
    QSizePolicy,
    QGridLayout,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from config import (
    get_platform_icon,
    VIDEO_FORMATS,
    AUDIO_FORMATS,
)


class ThumbnailLoader(QThread):
    """Background thread to download thumbnail images."""

    loaded = pyqtSignal(QPixmap)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            import requests

            resp = requests.get(self.url, timeout=15, stream=True)
            resp.raise_for_status()
            data = resp.content

            image = QImage()
            if image.loadFromData(data):
                pixmap = QPixmap.fromImage(image)
                self.loaded.emit(pixmap)
            else:
                self.failed.emit("Invalid image data")

        except Exception as e:
            self.failed.emit(str(e))


class MediaPreview(QFrame):
    """Thumbnail + metadata preview panel for social media content."""

    format_selected = pyqtSignal(str, str, str)  # format_spec, postprocessor, quality

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")
        self._thumbnail_loader: Optional[ThumbnailLoader] = None
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top section: thumbnail + info
        top_section = QHBoxLayout()
        top_section.setSpacing(16)

        # Thumbnail
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(180, 100)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet(
            "background: rgba(255,255,255,0.04); border-radius: 8px; color: #475569;"
        )
        self._thumb_label.setText("🖼️")
        self._thumb_label.setFont(QFont("Segoe UI", 24))
        top_section.addWidget(self._thumb_label)

        # Metadata column
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(4)

        # Platform badge row
        badge_row = QHBoxLayout()
        self._platform_badge = QLabel()
        self._platform_badge.setObjectName("badgeLabel")
        self._platform_badge.setVisible(False)
        badge_row.addWidget(self._platform_badge)

        self._photo_badge = QLabel("📸 Photos")
        self._photo_badge.setObjectName("warningBadge")
        self._photo_badge.setVisible(False)
        badge_row.addWidget(self._photo_badge)

        badge_row.addStretch()
        meta_layout.addLayout(badge_row)

        # Title
        self._title_label = QLabel("No content loaded")
        self._title_label.setObjectName("headingLabel")
        self._title_label.setWordWrap(True)
        self._title_label.setMaximumHeight(40)
        meta_layout.addWidget(self._title_label)

        # Info row
        info_grid = QGridLayout()
        info_grid.setSpacing(8)

        self._uploader_label = QLabel("—")
        self._uploader_label.setObjectName("secondaryLabel")
        info_grid.addWidget(QLabel("Uploader:"), 0, 0)
        info_grid.addWidget(self._uploader_label, 0, 1)

        self._duration_label = QLabel("—")
        self._duration_label.setObjectName("secondaryLabel")
        info_grid.addWidget(QLabel("Duration:"), 0, 2)
        info_grid.addWidget(self._duration_label, 0, 3)

        self._views_label = QLabel("—")
        self._views_label.setObjectName("secondaryLabel")
        info_grid.addWidget(QLabel("Views:"), 1, 0)
        info_grid.addWidget(self._views_label, 1, 1)

        self._date_label = QLabel("—")
        self._date_label.setObjectName("secondaryLabel")
        info_grid.addWidget(QLabel("Date:"), 1, 2)
        info_grid.addWidget(self._date_label, 1, 3)

        for lbl in (info_grid.itemAtPosition(0, 0), info_grid.itemAtPosition(0, 2),
                    info_grid.itemAtPosition(1, 0), info_grid.itemAtPosition(1, 2)):
            if lbl and lbl.widget():
                lbl.widget().setObjectName("mutedLabel")

        meta_layout.addLayout(info_grid)
        meta_layout.addStretch()
        top_section.addLayout(meta_layout, 1)
        layout.addLayout(top_section)

        # Photo grid preview (for TikTok photo posts)
        self._photo_grid = QWidget()
        self._photo_grid_layout = QHBoxLayout(self._photo_grid)
        self._photo_grid_layout.setSpacing(4)
        self._photo_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._photo_grid.setVisible(False)
        layout.addWidget(self._photo_grid)

        # Playlist info
        self._playlist_info = QLabel()
        self._playlist_info.setObjectName("secondaryLabel")
        self._playlist_info.setVisible(False)
        layout.addWidget(self._playlist_info)

        # Format selector section
        format_section = QHBoxLayout()
        format_section.setSpacing(12)

        format_label = QLabel("Format:")
        format_label.setObjectName("secondaryLabel")
        format_section.addWidget(format_label)

        self._format_combo = QComboBox()
        self._format_combo.setMinimumWidth(300)
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)
        format_section.addWidget(self._format_combo, 1)

        self._subtitle_check = QCheckBox("Download subtitles")
        format_section.addWidget(self._subtitle_check)

        layout.addLayout(format_section)

    def set_media_info(self, info: object) -> None:
        """Populate the preview with extracted media info."""
        self.show()

        self._title_label.setText(info.title)
        self._uploader_label.setText(info.uploader)
        self._duration_label.setText(info.duration_str)
        self._date_label.setText(info.formatted_date)

        if info.view_count > 0:
            import humanize
            self._views_label.setText(humanize.intcomma(info.view_count))
        else:
            self._views_label.setText("—")

        # Platform badge
        platform = info.extractor or "Unknown"
        icon = get_platform_icon(platform)
        self._platform_badge.setText(f"{icon} {platform}")
        self._platform_badge.setVisible(True)

        # TikTok photos
        if info.is_tiktok_photos:
            self._photo_badge.setVisible(True)
            self._photo_badge.setText(f"📸 {len(info.photo_urls)} Photos")
            self._setup_photo_format()
        else:
            self._photo_badge.setVisible(False)
            self._populate_formats(info)

        # Playlist
        if info.is_playlist:
            self._playlist_info.setText(
                f"📋 Playlist: {info.playlist_title} — {info.playlist_count} items"
            )
            self._playlist_info.setVisible(True)
        else:
            self._playlist_info.setVisible(False)

        # Thumbnail
        if info.thumbnail:
            self._load_thumbnail(info.thumbnail)

        # Subtitles available?
        has_subs = bool(info.subtitles or info.automatic_captions)
        self._subtitle_check.setEnabled(has_subs)
        if not has_subs:
            self._subtitle_check.setChecked(False)

    def _load_thumbnail(self, url: str) -> None:
        """Load thumbnail from URL in background thread."""
        if self._thumbnail_loader and self._thumbnail_loader.isRunning():
            self._thumbnail_loader.terminate()

        self._thumbnail_loader = ThumbnailLoader(url)
        self._thumbnail_loader.loaded.connect(self._on_thumbnail_loaded)
        self._thumbnail_loader.failed.connect(
            lambda err: self._thumb_label.setText("🖼️")
        )
        self._thumbnail_loader.start()

    def _on_thumbnail_loaded(self, pixmap: QPixmap) -> None:
        """Apply loaded thumbnail image."""
        scaled = pixmap.scaled(
            180, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self._thumb_label.setPixmap(scaled)

    def _populate_formats(self, info: object) -> None:
        """Populate format dropdown from video/audio options."""
        self._format_combo.clear()

        # Video formats header
        self._format_combo.addItem("── VIDEO FORMATS ──", None)

        for vf in VIDEO_FORMATS:
            self._format_combo.addItem(
                f"  🎬 {vf['label']}",
                {"type": "video", "format": vf["ytdlp_format"], "post": "", "quality": ""},
            )

        # Audio formats header
        self._format_combo.addItem("── AUDIO ONLY ──", None)

        for af in AUDIO_FORMATS:
            self._format_combo.addItem(
                f"  🎵 {af['label']}",
                {"type": "audio", "format": af["ytdlp_format"], "post": af.get("postprocessor", ""), "quality": af.get("quality", "")},
            )

        # Default to 1080p
        for i in range(self._format_combo.count()):
            data = self._format_combo.itemData(i)
            if data and isinstance(data, dict) and "1080" in self._format_combo.itemText(i):
                self._format_combo.setCurrentIndex(i)
                break

    def _setup_photo_format(self) -> None:
        """Set format for TikTok photo posts."""
        self._format_combo.clear()
        self._format_combo.addItem(
            "📸 Download as ZIP (all photos)",
            {"type": "photos", "format": "photos", "post": "", "quality": ""},
        )
        self._subtitle_check.setEnabled(False)

    def _on_format_changed(self, index: int) -> None:
        """Emit signal when format selection changes."""
        data = self._format_combo.currentData()
        if data and isinstance(data, dict):
            self.format_selected.emit(
                data.get("format", "best"),
                data.get("post", ""),
                data.get("quality", ""),
            )

    def get_selected_format(self) -> dict:
        """Return the currently selected format info."""
        data = self._format_combo.currentData()
        if data and isinstance(data, dict):
            return {
                "format_spec": data.get("format", "best"),
                "postprocessor": data.get("post", ""),
                "quality": data.get("quality", ""),
                "subtitles": self._subtitle_check.isChecked(),
            }
        return {"format_spec": "best", "postprocessor": "", "quality": "", "subtitles": False}

    def clear(self) -> None:
        """Reset the preview panel."""
        self._title_label.setText("No content loaded")
        self._uploader_label.setText("—")
        self._duration_label.setText("—")
        self._views_label.setText("—")
        self._date_label.setText("—")
        self._thumb_label.setPixmap(QPixmap())
        self._thumb_label.setText("🖼️")
        self._platform_badge.setVisible(False)
        self._photo_badge.setVisible(False)
        self._playlist_info.setVisible(False)
        self._format_combo.clear()
        self.hide()
