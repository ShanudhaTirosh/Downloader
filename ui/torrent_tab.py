"""
ShanuFx Downloader — Torrent manager tab.
Add torrents via magnet/file/drag-drop, view progress, peers, and controls.
"""

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QScrollArea,
    QFileDialog,
    QDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QProgressBar,
    QCheckBox,
    QMessageBox,
    QSizePolicy,
    QMenu,
)

import humanize

from core.torrent_engine import LIBTORRENT_AVAILABLE, TorrentInfo, TorrentStatus
from icons import get_icon, get_pixmap
from ui.widgets.torrent_peer import TorrentPeerWidget
from ui.widgets.empty_state import EmptyState


class TorrentInfoDialog(QDialog):
    """Dialog shown before starting a torrent download — file tree and save path."""

    confirmed = pyqtSignal(str, str, list)  # torrent_source, save_path, file_priorities

    def __init__(self, info: TorrentInfo, default_save_path: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Add Torrent — {info.name}")
        self.setMinimumSize(600, 450)
        self._info = info

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel(f"  {info.name}")
        header.setObjectName("titleLargeLabel")
        header.setWordWrap(True)
        layout.addWidget(header)

        # Info row
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Size: {humanize.naturalsize(info.total_size, binary=True)}"))
        info_row.addWidget(QLabel(f"Files: {info.file_count}"))
        info_row.addWidget(QLabel(f"Hash: {info.info_hash[:16]}..."))
        info_row.addStretch()
        layout.addLayout(info_row)

        # File tree
        tree_label = QLabel("Select files to download:")
        tree_label.setObjectName("secondaryLabel")
        layout.addWidget(tree_label)

        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderLabels(["File", "Size"])
        self._file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        for f in info.files:
            item = QTreeWidgetItem([f["name"], humanize.naturalsize(f["size"], binary=True)])
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setData(0, Qt.ItemDataRole.UserRole, f["index"])
            self._file_tree.addTopLevelItem(item)

        layout.addWidget(self._file_tree, 1)

        # Save path
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Save to:"))
        self._save_input = QLineEdit(default_save_path)
        save_layout.addWidget(self._save_input, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        save_layout.addWidget(browse_btn)
        layout.addLayout(save_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        confirm_btn = QPushButton("Start Download")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Save Torrent Files", self._save_input.text())
        if path:
            self._save_input.setText(path)

    def _confirm(self) -> None:
        priorities = []
        for i in range(self._file_tree.topLevelItemCount()):
            item = self._file_tree.topLevelItem(i)
            priority = 4 if item.checkState(0) == Qt.CheckState.Checked else 0
            priorities.append(priority)
        self.confirmed.emit(self._info.info_hash, self._save_input.text(), priorities)
        self.accept()


class TorrentCard(QFrame):
    """Active torrent progress card."""

    pause_clicked = pyqtSignal(str)
    resume_clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(str, bool)  # info_hash, delete_files
    recheck_clicked = pyqtSignal(str)
    reannounce_clicked = pyqtSignal(str)
    sequential_toggled = pyqtSignal(str, bool)
    open_folder_clicked = pyqtSignal(str)
    copy_magnet_clicked = pyqtSignal(str)

    def __init__(self, info_hash: str, name: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.info_hash = info_hash
        self._name = name
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row
        top_row = QHBoxLayout()
        self._icon = QLabel()
        self._icon.setPixmap(get_pixmap("bolt", 24))
        top_row.addWidget(self._icon)

        self._name_label = QLabel(self._name or self.info_hash[:16])
        self._name_label.setObjectName("headingLabel")
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row.addWidget(self._name_label, 1)

        self._state_badge = QLabel("—")
        self._state_badge.setObjectName("statusQueued")
        top_row.addWidget(self._state_badge)

        layout.addLayout(top_row)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(8)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self._size_label = QLabel("0 B / 0 B")
        self._size_label.setObjectName("secondaryLabel")
        stats_row.addWidget(self._size_label)

        self._down_speed = QLabel("↓ 0 B/s")
        self._down_speed.setObjectName("secondaryLabel")
        self._down_speed.setStyleSheet("color: #00d4ff;")
        stats_row.addWidget(self._down_speed)

        self._up_speed = QLabel("↑ 0 B/s")
        self._up_speed.setObjectName("secondaryLabel")
        self._up_speed.setStyleSheet("color: #7c3aed;")
        stats_row.addWidget(self._up_speed)

        self._seeds_label = QLabel("Seeds: 0")
        self._seeds_label.setObjectName("secondaryLabel")
        stats_row.addWidget(self._seeds_label)

        self._eta_label = QLabel("ETA: —")
        self._eta_label.setObjectName("secondaryLabel")
        stats_row.addWidget(self._eta_label)

        self._ratio_label = QLabel("Ratio: 0.00")
        self._ratio_label.setObjectName("mutedLabel")
        stats_row.addWidget(self._ratio_label)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Control buttons
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(4)

        self._pause_btn = QPushButton(" Pause")
        self._pause_btn.setIcon(get_icon("pause"))
        self._pause_btn.setObjectName("iconBtn")
        self._pause_btn.setStyleSheet("min-width: 80px;")
        self._pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.info_hash))
        ctrl_row.addWidget(self._pause_btn)

        self._resume_btn = QPushButton(" Resume")
        self._resume_btn.setIcon(get_icon("play"))
        self._resume_btn.setObjectName("iconBtn")
        self._resume_btn.setStyleSheet("min-width: 80px;")
        self._resume_btn.clicked.connect(lambda: self.resume_clicked.emit(self.info_hash))
        self._resume_btn.setVisible(False)
        ctrl_row.addWidget(self._resume_btn)

        more_btn = QPushButton()
        more_btn.setIcon(get_icon("more"))
        more_btn.setObjectName("iconBtn")
        more_btn.clicked.connect(self._show_context_menu)
        ctrl_row.addWidget(more_btn)

        ctrl_row.addStretch()

        self._sequential_check = QCheckBox("Sequential")
        self._sequential_check.setToolTip("Download sequentially for streaming")
        self._sequential_check.toggled.connect(lambda v: self.sequential_toggled.emit(self.info_hash, v))
        ctrl_row.addWidget(self._sequential_check)

        layout.addLayout(ctrl_row)

        # Peer widget
        self._peer_widget = TorrentPeerWidget(self.info_hash)
        layout.addWidget(self._peer_widget)

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction(get_icon("folder"), "Open Folder", lambda: self.open_folder_clicked.emit(self.info_hash))
        menu.addAction(get_icon("link"), "Copy Magnet", lambda: self.copy_magnet_clicked.emit(self.info_hash))
        menu.addSeparator()
        menu.addAction(get_icon("refresh"), "Force Recheck", lambda: self.recheck_clicked.emit(self.info_hash))
        menu.addAction(get_icon("refresh"), "Force Reannounce", lambda: self.reannounce_clicked.emit(self.info_hash))
        menu.addSeparator()
        menu.addAction(get_icon("trash"), "Remove (keep files)", lambda: self.remove_clicked.emit(self.info_hash, False))
        menu.addAction(get_icon("close"), "Remove (delete files)", lambda: self.remove_clicked.emit(self.info_hash, True))
        menu.exec(self.mapToGlobal(self.sender().pos()) if self.sender() else menu.pos())

    def update_status(self, status: TorrentStatus) -> None:
        """Update card from a TorrentStatus snapshot."""
        self._name_label.setText(status.name)
        self._progress_bar.setValue(int(status.progress))

        done = humanize.naturalsize(status.total_downloaded, binary=True)
        total = humanize.naturalsize(status.total_size, binary=True)
        self._size_label.setText(f"{done} / {total}")

        self._down_speed.setText(f"↓ {humanize.naturalsize(status.download_rate, binary=True)}/s")
        self._up_speed.setText(f"↑ {humanize.naturalsize(status.upload_rate, binary=True)}/s")
        self._seeds_label.setText(f"Seeds: {status.num_seeds}")
        self._ratio_label.setText(f"Ratio: {status.share_ratio:.2f}")

        if status.eta_seconds > 0:
            eta = int(status.eta_seconds)
            if eta >= 3600:
                self._eta_label.setText(f"ETA: {eta // 3600}h {(eta % 3600) // 60}m")
            elif eta >= 60:
                self._eta_label.setText(f"ETA: {eta // 60}m {eta % 60}s")
            else:
                self._eta_label.setText(f"ETA: {eta}s")
        else:
            self._eta_label.setText("ETA: —")

        state = status.state
        state_map = {
            "downloading": ("statusDownloading", "DOWNLOADING"),
            "seeding": ("statusComplete", "SEEDING"),
            "finished": ("statusComplete", "COMPLETE"),
            "checking_files": ("statusMerging", "CHECKING"),
            "downloading_metadata": ("statusPaused", "METADATA"),
            "queued": ("statusQueued", "QUEUED"),
            "allocating": ("statusMerging", "ALLOCATING"),
        }
        style, label = state_map.get(state, ("statusQueued", state.upper()))
        self._state_badge.setObjectName(style)
        self._state_badge.setText(label)
        self._state_badge.setStyle(self._state_badge.style())

        is_active = state in ("downloading", "downloading_metadata")
        self._pause_btn.setVisible(is_active)
        self._resume_btn.setVisible(not is_active and state != "seeding" and state != "finished")

        self._peer_widget.update_seeds_peers(
            status.num_seeds, status.num_seeds_total,
            status.num_peers, status.num_peers_total,
        )

    def update_peers(self, peers: list) -> None:
        self._peer_widget.update_peers(peers)


class TorrentTab(QWidget):
    """Torrent manager tab with add/manage/monitor functionality."""

    add_torrent_file = pyqtSignal(str, str, list)  # path, save_dir, priorities
    add_magnet = pyqtSignal(str, str)  # magnet_uri, save_dir

    def __init__(self, default_save_path: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._default_save = default_save_path
        self._torrent_cards: dict[str, TorrentCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Torrent Manager")
        title.setObjectName("titleLargeLabel")
        header_row.addWidget(title)
        header_row.addStretch()

        if not LIBTORRENT_AVAILABLE:
            warning = QLabel("libtorrent not installed")
            warning.setObjectName("warningBadge")
            header_row.addWidget(warning)

        layout.addLayout(header_row)

        if not LIBTORRENT_AVAILABLE:
            content = QWidget()
            err_layout = QVBoxLayout(content)
            err_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.setSpacing(24)

            # Warning icon
            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_pixmap("error", 64))
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(icon_lbl)

            # Main text
            title = QLabel("Torrent Engine Unavailable")
            title.setObjectName("titleLargeLabel")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(title)

            # Description
            desc = QLabel(
                "The python-libtorrent bindings are currently missing or unsupported on your Python version.\n"
                "Due to complex C++ dependencies, libtorrent may not cleanly install on Windows with Python 3.12+.\n\n"
                "If you would like to enable Torrent support, please install Python 3.11 and run:\n"
                "pip install libtorrent"
            )
            desc.setObjectName("secondaryLabel")
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(desc)

            layout.addStretch()
            layout.addWidget(content)
            layout.addStretch()
            return

        # Add torrent section
        add_frame = QFrame()
        add_frame.setObjectName("glassCard")
        add_layout = QVBoxLayout(add_frame)
        add_layout.setSpacing(8)

        # Magnet input
        magnet_row = QHBoxLayout()
        self._magnet_input = QLineEdit()
        self._magnet_input.setPlaceholderText("Paste magnet:?xt=urn:btih:... link here")
        self._magnet_input.setMinimumHeight(36)
        magnet_row.addWidget(self._magnet_input, 1)

        magnet_btn = QPushButton(" Add Magnet")
        magnet_btn.setIcon(get_icon("link"))
        magnet_btn.setObjectName("primaryBtn")
        magnet_btn.clicked.connect(self._on_add_magnet)
        magnet_row.addWidget(magnet_btn)

        add_layout.addLayout(magnet_row)

        # File button
        file_row = QHBoxLayout()
        file_btn = QPushButton(" Open .torrent File")
        file_btn.setIcon(get_icon("folder"))
        file_btn.clicked.connect(self._on_open_file)
        file_row.addWidget(file_btn)
        file_row.addStretch()

        drop_label = QLabel("or drag & drop .torrent files here")
        drop_label.setObjectName("mutedLabel")
        file_row.addWidget(drop_label)

        add_layout.addLayout(file_row)
        layout.addWidget(add_frame)

        # Active torrents scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        self._empty_state = EmptyState(
            icon_name="bolt",
            title="No Active Torrents",
            description="Add a magnet link or open a .torrent file above to start downloading.",
            action_text="Add Magnet"
        )
        self._empty_state.set_action_callback(self._on_add_magnet)
        self._cards_layout.insertWidget(0, self._empty_state)

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, 1)

    def _on_add_magnet(self) -> None:
        magnet = self._magnet_input.text().strip()
        if magnet and magnet.startswith("magnet:"):
            self.add_magnet.emit(magnet, self._default_save)
            self._magnet_input.clear()

    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Torrent", "", "Torrent Files (*.torrent)")
        if path:
            self._handle_torrent_file(path)

    def _handle_torrent_file(self, path: str) -> None:
        """Show torrent info dialog before adding."""
        from core.torrent_engine import TorrentEngine

        engine = TorrentEngine()
        info = engine.get_torrent_info(path)
        if not info:
            QMessageBox.warning(self, "Error", "Failed to parse torrent file")
            return

        dialog = TorrentInfoDialog(info, self._default_save, self)
        dialog.confirmed.connect(lambda ih, sp, prio: self.add_torrent_file.emit(path, sp, prio))
        dialog.exec()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".torrent"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.endswith(".torrent"):
                    self._handle_torrent_file(path)

    def add_torrent_card(self, info_hash: str, name: str) -> TorrentCard:
        """Add a new torrent card."""
        card = TorrentCard(info_hash, name)
        self._torrent_cards[info_hash] = card
        idx = self._cards_layout.count() - 1
        self._cards_layout.insertWidget(idx, card)
        self._empty_state.setVisible(False)
        return card

    def get_card(self, info_hash: str) -> Optional[TorrentCard]:
        return self._torrent_cards.get(info_hash)

    def remove_card(self, info_hash: str) -> None:
        card = self._torrent_cards.pop(info_hash, None)
        if card:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        if not self._torrent_cards:
            self._empty_state.setVisible(True)
