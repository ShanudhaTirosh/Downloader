"""
ShanuFx Downloader — Dashboard tab.
Active downloads, stat cards, speed graph, and floating add URL button.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QDialog,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QSizePolicy,
    QFileDialog,
)

from icons import get_icon, get_pixmap
import humanize

from ui.widgets.speed_graph import SpeedGraph
from ui.widgets.download_card import DownloadCard
from ui.widgets.empty_state import EmptyState


class StatCard(QFrame):
    """Glass stat card showing a value and label."""

    def __init__(self, label: str, value: str = "0", icon: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(get_pixmap(icon, 24))
            top_row.addWidget(icon_label)
        top_row.addStretch()
        layout.addLayout(top_row)
        
        layout.addStretch()

        self._value_label = QLabel(value)
        self._value_label.setObjectName("statValue")
        layout.addWidget(self._value_label)

        self._label = QLabel(label)
        self._label.setObjectName("statLabel")
        layout.addWidget(self._label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class AddUrlDialog(QDialog):
    """Dialog for adding a new download URL."""

    url_submitted = pyqtSignal(str, str, int)  # url, save_dir, segments

    def __init__(self, default_dir: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Download — ShanuFx Downloader")
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Add New Download")
        header.setObjectName("titleLargeLabel")
        layout.addWidget(header)

        # URL input
        url_label = QLabel("Download URL:")
        url_label.setObjectName("secondaryLabel")
        layout.addWidget(url_label)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com/file.zip")
        self._url_input.setMinimumHeight(40)
        self._url_input.setClearButtonEnabled(True)
        
        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.addWidget(self._url_input, 1)

        self._paste_btn = QPushButton(" Paste")
        self._paste_btn.setIcon(get_icon("link"))
        self._paste_btn.setMinimumHeight(40)
        self._paste_btn.clicked.connect(self._url_input.paste)
        url_row.addWidget(self._paste_btn)

        layout.addLayout(url_row)

        # Save directory
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Save to:")
        dir_label.setObjectName("secondaryLabel")
        dir_layout.addWidget(dir_label)

        self._dir_input = QLineEdit(default_dir)
        dir_layout.addWidget(self._dir_input, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(browse_btn)

        layout.addLayout(dir_layout)

        # Segments
        seg_layout = QHBoxLayout()
        seg_label = QLabel("Segments:")
        seg_label.setObjectName("secondaryLabel")
        seg_layout.addWidget(seg_label)

        self._seg_spin = QSpinBox()
        self._seg_spin.setRange(1, 32)
        self._seg_spin.setValue(16)
        self._seg_spin.setFixedWidth(80)
        seg_layout.addWidget(self._seg_spin)
        seg_layout.addStretch()

        layout.addLayout(seg_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        add_btn = QPushButton(" Add Download")
        add_btn.setIcon(get_icon("download"))
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._submit)
        btn_layout.addWidget(add_btn)

        layout.addLayout(btn_layout)

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose Download Folder", self._dir_input.text())
        if path:
            self._dir_input.setText(path)

    def _submit(self) -> None:
        url = self._url_input.text().strip()
        if url:
            self.url_submitted.emit(url, self._dir_input.text(), self._seg_spin.value())
            self.accept()


class DashboardTab(QWidget):
    """Main dashboard showing stats, speed graph, and active downloads."""

    add_url_requested = pyqtSignal(str, str, int)  # url, save_dir, segments
    pause_all_requested = pyqtSignal()
    resume_all_requested = pyqtSignal()

    def __init__(self, default_download_dir: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._default_dir = default_download_dir
        self._download_cards: dict[int, DownloadCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._stat_total = StatCard("Total Downloaded", "0 B", "chart")
        self._stat_active = StatCard("Active", "0", "download")
        self._stat_queued = StatCard("Queued", "0", "queue")
        self._stat_failed = StatCard("Failed", "0", "error")

        stats_row.addWidget(self._stat_total)
        stats_row.addWidget(self._stat_active)
        stats_row.addWidget(self._stat_queued)
        stats_row.addWidget(self._stat_failed)

        layout.addLayout(stats_row)

        # Speed graph
        self._speed_graph = SpeedGraph()
        layout.addWidget(self._speed_graph)

        # Downloads header
        dl_header = QHBoxLayout()
        dl_title = QLabel("Active Downloads")
        dl_title.setObjectName("headingLabel")
        dl_header.addWidget(dl_title)
        dl_header.addStretch()

        self._pause_all_btn = QPushButton(" Pause All")
        self._pause_all_btn.setIcon(get_icon("pause"))
        self._pause_all_btn.setObjectName("secondaryBtn")
        self._pause_all_btn.clicked.connect(self.pause_all_requested.emit)
        dl_header.addWidget(self._pause_all_btn)

        self._resume_all_btn = QPushButton(" Resume All")
        self._resume_all_btn.setIcon(get_icon("play"))
        self._resume_all_btn.setObjectName("secondaryBtn")
        self._resume_all_btn.clicked.connect(self.resume_all_requested.emit)
        dl_header.addWidget(self._resume_all_btn)

        layout.addLayout(dl_header)

        # Scrollable download cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        # Empty state
        self._empty_state = EmptyState(
            icon_name="download",
            title="No Active Downloads",
            description="Start a new download by clicking the + button or pasting a URL.",
            action_text="Add Download"
        )
        self._empty_state.set_action_callback(self._show_add_dialog)
        self._cards_layout.insertWidget(0, self._empty_state)

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, 1)

        # FAB button
        self._fab = QPushButton()
        self._fab.setIcon(get_icon("add"))
        self._fab.setIconSize(QSize(28, 28))
        self._fab.setObjectName("fabBtn")
        self._fab.setToolTip("Add new download")
        self._fab.clicked.connect(self._show_add_dialog)

    def resizeEvent(self, event: object) -> None:
        """Position the FAB at bottom-right."""
        super().resizeEvent(event)
        self._fab.setParent(self)
        self._fab.move(self.width() - 96, self.height() - 84)
        self._fab.raise_()
        self._fab.show()

    def _show_add_dialog(self) -> None:
        dialog = AddUrlDialog(self._default_dir, self)
        dialog.url_submitted.connect(self.add_url_requested.emit)
        dialog.exec()

    def add_download_card(
        self, download_id: int, filename: str = "Resolving...", url: str = "", total_size: int = 0, segments: int = 1
    ) -> DownloadCard:
        """Add a new download card widget."""
        card = DownloadCard(download_id, filename, url, total_size, segments)
        self._download_cards[download_id] = card

        idx = self._cards_layout.count() - 1
        self._cards_layout.insertWidget(idx, card)

        self._empty_state.setVisible(False)
        return card

    def get_card(self, download_id: int) -> Optional[DownloadCard]:
        return self._download_cards.get(download_id)

    def remove_card(self, download_id: int) -> None:
        card = self._download_cards.pop(download_id, None)
        if card:
            self._cards_layout.removeWidget(card)
            card.deleteLater()

        if not self._download_cards:
            self._empty_state.setVisible(True)

    def update_stats(self, total_bytes: int, active: int, queued: int, failed: int) -> None:
        """Update the stat cards."""
        self._stat_total.set_value(humanize.naturalsize(total_bytes, binary=True))
        self._stat_active.set_value(str(active))
        self._stat_queued.set_value(str(queued))
        self._stat_failed.set_value(str(failed))

    def update_speed(self, speed_bps: float) -> None:
        """Feed a speed value to the graph."""
        self._speed_graph.add_speed(speed_bps)
