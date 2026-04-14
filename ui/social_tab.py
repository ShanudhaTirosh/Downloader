"""
ShanuFx Downloader — Social media downloader tab.
URL input, platform auto-detect, media preview, format selection, and download.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QSizePolicy,
    QMessageBox,
)

from config import detect_platform, get_platform_icon, PLATFORM_ICONS
from icons import get_icon, get_pixmap
from ui.widgets.media_preview import MediaPreview
from ui.widgets.empty_state import EmptyState


class SocialTab(QWidget):
    """Social media content downloader tab."""

    download_requested = pyqtSignal(str, dict, object)  # url, format_info, media_info

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_info = None  # type: ignore
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("Social Media Downloader")
        header.setObjectName("titleLargeLabel")
        layout.addWidget(header)

        desc = QLabel("Paste a URL from YouTube, Instagram, TikTok, Twitter, and 1000+ sites")
        desc.setObjectName("secondaryLabel")
        layout.addWidget(desc)

        # URL input bar
        url_frame = QFrame()
        url_frame.setObjectName("glassCard")
        url_layout = QHBoxLayout(url_frame)
        url_layout.setContentsMargins(12, 8, 12, 8)
        url_layout.setSpacing(8)

        self._platform_icon = QLabel()
        self._platform_icon.setPixmap(get_pixmap("globe", 24))
        self._platform_icon.setFixedWidth(32)
        url_layout.addWidget(self._platform_icon)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Paste URL here (e.g., https://youtube.com/watch?v=...)")
        self._url_input.setMinimumHeight(36)
        self._url_input.setClearButtonEnabled(True)
        self._url_input.textChanged.connect(self._on_url_changed)
        self._url_input.returnPressed.connect(self._on_extract)
        url_layout.addWidget(self._url_input, 1)

        self._paste_btn = QPushButton(" Paste")
        self._paste_btn.setIcon(get_icon("link"))
        self._paste_btn.setMinimumHeight(36)
        self._paste_btn.clicked.connect(self._url_input.paste)
        url_layout.addWidget(self._paste_btn)

        self._platform_badge = QLabel("")
        self._platform_badge.setObjectName("badgeLabel")
        self._platform_badge.setVisible(False)
        url_layout.addWidget(self._platform_badge)

        self._extract_btn = QPushButton(" Extract")
        self._extract_btn.setIcon(get_icon("search"))
        self._extract_btn.setObjectName("primaryBtn")
        self._extract_btn.setFixedWidth(100)
        self._extract_btn.clicked.connect(self._on_extract)
        url_layout.addWidget(self._extract_btn)

        layout.addWidget(url_frame)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("secondaryLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Media preview panel
        self._media_preview = MediaPreview()
        layout.addWidget(self._media_preview)

        # Download button
        self._download_btn = QPushButton(" Download")
        self._download_btn.setIcon(get_icon("download"))
        self._download_btn.setObjectName("primaryBtn")
        self._download_btn.setMinimumHeight(44)
        self._download_btn.setFont(QFont("Segoe UI Semibold", 11))
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setVisible(False)
        layout.addWidget(self._download_btn)

        # Empty state (shown initially)
        self._empty_state = EmptyState(
            icon_name="play",
            title="Ready to Extract",
            description="Paste a URL from YouTube, Instagram, or TikTok above to see media details.",
            action_text="Paste from Clipboard"
        )
        self._empty_state.set_action_callback(self._url_input.paste)
        layout.addWidget(self._empty_state, 1)

        layout.addStretch()

    def _on_url_changed(self, text: str) -> None:
        """Auto-detect platform from URL as user types."""
        text = text.strip()
        if not text:
            self._platform_icon.setPixmap(get_pixmap("globe", 24))
            self._platform_badge.setVisible(False)
            return

        platform = detect_platform(text)
        if platform != "Unknown":
            # Correctly display platform icons using pixmaps
            icon_name = PLATFORM_ICONS.get(platform, "globe")
            self._platform_icon.setPixmap(get_pixmap(icon_name, 24))
            self._platform_badge.setText(platform)
            self._platform_badge.setVisible(True)
        else:
            self._platform_icon.setPixmap(get_pixmap("globe", 24))
            self._platform_badge.setVisible(False)

    def _on_extract(self) -> None:
        """Start metadata extraction."""
        url = self._url_input.text().strip()
        if not url:
            return

        self._extract_btn.setEnabled(False)
        self._extract_btn.setText("Loading...")
        self._status_label.setText("Extracting metadata... this may take a moment")
        self._download_btn.setVisible(False)
        self._media_preview.setVisible(False)
        self._empty_state.setVisible(False)
        self._media_preview.clear()

        from core.social_extractor import ExtractorWorker

        self._extractor = ExtractorWorker(url)
        self._extractor.extraction_complete.connect(self._on_extraction_complete)
        self._extractor.extraction_failed.connect(self._on_extraction_failed)
        self._extractor.start()

    def _on_extraction_complete(self, info: object) -> None:
        """Handle successful extraction."""
        self._current_info = info
        self._extract_btn.setEnabled(True)
        self._extract_btn.setText("Extract")
        self._status_label.setText("")

        self._media_preview.set_media_info(info)
        self._media_preview.setVisible(True)
        self._download_btn.setVisible(True)
        self._empty_state.setVisible(False)

        if info.is_tiktok_photos:
            self._download_btn.setText(f"Download {len(info.photo_urls)} Photos as ZIP")
        elif info.is_playlist:
            self._download_btn.setText(f"Download Playlist ({info.playlist_count} items)")
        else:
            self._download_btn.setText("Download")

    def _on_extraction_failed(self, error: str) -> None:
        """Handle extraction failure."""
        self._extract_btn.setEnabled(True)
        self._extract_btn.setText("Extract")
        self._status_label.setText(f"Error: {error}")
        self._status_label.setStyleSheet("color: #ef4444;")
        self._download_btn.setVisible(False)
        self._media_preview.setVisible(False)
        self._empty_state.setVisible(True)

    def _on_download(self) -> None:
        """Emit download request with selected format."""
        if not self._current_info:
            return

        url = self._url_input.text().strip()
        format_info = self._media_preview.get_selected_format()

        self.download_requested.emit(url, format_info, self._current_info)
        self._status_label.setText("Download added to queue")
        self._status_label.setStyleSheet("color: #10b981;")
