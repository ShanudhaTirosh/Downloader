"""
ShanuFx Downloader — Torrent peer list widget.
Shows connected peers with speed, client info, and country flags.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QWidget,
    QAbstractItemView,
)

import humanize


class TorrentPeerWidget(QFrame):
    """Expandable peer list panel for active torrents."""

    def __init__(self, info_hash: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.info_hash = info_hash
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()

        self._toggle_btn = QPushButton("▶ Peers (0)")
        self._toggle_btn.setObjectName("iconBtn")
        self._toggle_btn.setFont(QFont("Segoe UI Semibold", 9))
        self._toggle_btn.setStyleSheet("text-align: left; padding: 4px 8px; min-width: 120px; max-width: 200px;")
        self._toggle_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self._toggle_btn)

        header.addStretch()

        self._seed_label = QLabel("Seeds: 0/0")
        self._seed_label.setObjectName("secondaryLabel")
        header.addWidget(self._seed_label)

        self._peer_label = QLabel("Peers: 0/0")
        self._peer_label.setObjectName("secondaryLabel")
        header.addWidget(self._peer_label)

        layout.addLayout(header)

        # Peer table (hidden by default)
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["IP:Port", "Country", "Client", "↓ Speed", "↑ Speed", "Progress"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setMaximumHeight(200)
        self._table.setVisible(False)
        layout.addWidget(self._table)

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._table.setVisible(self._expanded)
        arrow = "▼" if self._expanded else "▶"
        count = self._table.rowCount()
        self._toggle_btn.setText(f"{arrow} Peers ({count})")

    def update_seeds_peers(
        self, seeds: int, seeds_total: int, peers: int, peers_total: int
    ) -> None:
        """Update seed/peer count labels."""
        self._seed_label.setText(f"Seeds: {seeds}/{seeds_total}")
        self._peer_label.setText(f"Peers: {peers}/{peers_total}")

    def update_peers(self, peers: list) -> None:
        """Update the peer table with fresh data."""
        self._table.setRowCount(len(peers))

        for i, peer in enumerate(peers):
            ip_port = f"{peer.ip}:{peer.port}"
            self._table.setItem(i, 0, QTableWidgetItem(ip_port))

            country = peer.country if hasattr(peer, "country") and peer.country else "🌍"
            self._table.setItem(i, 1, QTableWidgetItem(country))

            client = peer.client if hasattr(peer, "client") else "Unknown"
            self._table.setItem(i, 2, QTableWidgetItem(client[:30]))

            down = humanize.naturalsize(peer.down_speed, binary=True) + "/s" if peer.down_speed > 0 else "—"
            item_down = QTableWidgetItem(down)
            if peer.down_speed > 0:
                item_down.setForeground(QColor(0, 212, 255))
            self._table.setItem(i, 3, item_down)

            up = humanize.naturalsize(peer.up_speed, binary=True) + "/s" if peer.up_speed > 0 else "—"
            item_up = QTableWidgetItem(up)
            if peer.up_speed > 0:
                item_up.setForeground(QColor(124, 58, 237))
            self._table.setItem(i, 4, item_up)

            progress = f"{peer.progress:.1f}%" if hasattr(peer, "progress") else "—"
            self._table.setItem(i, 5, QTableWidgetItem(progress))

        peer_count = len(peers)
        arrow = "▼" if self._expanded else "▶"
        self._toggle_btn.setText(f"{arrow} Peers ({peer_count})")

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._toggle_btn.setText("▶ Peers (0)")
        self._seed_label.setText("Seeds: 0/0")
        self._peer_label.setText("Peers: 0/0")
