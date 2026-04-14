"""
ShanuFx Downloader — Download history & file manager tab.
Searchable/filterable table with stats panel and context menu.
"""

import os
import subprocess
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen, QAction
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QFrame,
    QMessageBox,
    QApplication,
    QSizePolicy,
)

import humanize
from datetime import datetime

from icons import get_icon
from ui.widgets.empty_state import EmptyState


class DailyStatsChart(QWidget):
    """30-day download bar chart painted with QPainter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
        self._data: list[dict] = []

    def set_data(self, daily_stats: list[dict]) -> None:
        self._data = daily_stats[-30:] if len(daily_stats) > 30 else daily_stats
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 8

        painter.fillRect(0, 0, w, h, QColor(10, 10, 15))

        if not self._data:
            painter.setPen(QColor(71, 85, 105))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "No download history")
            painter.end()
            return

        max_count = max((d.get("count", 0) for d in self._data), default=1) or 1
        bar_count = len(self._data)
        bar_width = max((w - margin * 2) / max(bar_count, 1) - 2, 4)

        for i, day in enumerate(self._data):
            count = day.get("count", 0)
            bar_h = int((count / max_count) * (h - margin * 3))
            x = margin + i * ((w - margin * 2) / bar_count)
            y = h - margin - bar_h

            gradient = QLinearGradient(x, y, x, y + bar_h)
            gradient.setColorAt(0, QColor(0, 212, 255))
            gradient.setColorAt(1, QColor(124, 58, 237))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_h), 2, 2)

        painter.end()


class HistoryTab(QWidget):
    """Download history with search, filters, context menu, and stats."""

    def __init__(self, db: object, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._setup_ui()
        QTimer.singleShot(100, self.refresh)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        title = QLabel("Download History")
        title.setObjectName("titleLargeLabel")
        layout.addWidget(title)

        # Stats panel
        stats_frame = QFrame()
        stats_frame.setObjectName("glassCard")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(24)

        self._total_label = QLabel("Total: 0 B")
        self._total_label.setObjectName("accentLabel")
        stats_layout.addWidget(self._total_label)

        self._count_label = QLabel("Downloads: 0")
        self._count_label.setObjectName("secondaryLabel")
        stats_layout.addWidget(self._count_label)

        self._avg_speed_label = QLabel("Avg Speed: —")
        self._avg_speed_label.setObjectName("secondaryLabel")
        stats_layout.addWidget(self._avg_speed_label)

        stats_layout.addStretch()

        self._chart = DailyStatsChart()
        self._chart.setFixedWidth(300)
        stats_layout.addWidget(self._chart)

        layout.addWidget(stats_frame)

        # Filters row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search downloads...")
        self._search_input.setMinimumHeight(34)
        self._search_input.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_input, 1)

        self._type_filter = QComboBox()
        self._type_filter.addItems(["All Types", "HTTP", "Social", "Torrent"])
        self._type_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._type_filter)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["All Status", "Complete", "Failed", "Cancelled"])
        self._status_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._status_filter)

        refresh_btn = QPushButton(" Refresh")
        refresh_btn.setIcon(get_icon("refresh"))
        refresh_btn.clicked.connect(self.refresh)
        filter_row.addWidget(refresh_btn)

        clear_btn = QPushButton(" Clear History")
        clear_btn.setIcon(get_icon("trash"))
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self._clear_history)
        filter_row.addWidget(clear_btn)

        layout.addLayout(filter_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Filename", "Size", "Source", "Platform", "Status", "Format", "Date", "Speed",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.setAlternatingRowColors(False)

        layout.addWidget(self._table, 1)

        # Empty state
        self._empty_state = EmptyState(
            icon_name="clock",
            title="No History Found",
            description="Your download history will appear here once you complete some downloads.",
        )
        layout.addWidget(self._empty_state, 1)
        self._empty_state.setVisible(False)

    def refresh(self) -> None:
        """Reload data from database."""
        search = self._search_input.text().strip() or None
        type_idx = self._type_filter.currentIndex()
        status_idx = self._status_filter.currentIndex()

        source_type = [None, "http", "social", "torrent"][type_idx] if type_idx < 4 else None
        status = [None, "complete", "failed", "cancelled"][status_idx] if status_idx < 4 else None

        downloads = self._db.get_downloads(
            status=status, source_type=source_type, search=search, limit=500
        )

        self._populate_table(downloads)
        self._update_stats()

        has_data = len(downloads) > 0
        self._table.setVisible(has_data)
        self._empty_state.setVisible(not has_data)
        if not has_data:
            search = self._search_input.text().strip()
            if search:
                self._empty_state._title_label.setText("No Matches Found")
                self._empty_state._desc_label.setText(f"No results found for '{search}'. Try a different search term.")
            else:
                self._empty_state._title_label.setText("History Empty")
                self._empty_state._desc_label.setText("Your completed downloads and torrents will be listed here.")

    def _populate_table(self, downloads: list[dict]) -> None:
        self._table.setRowCount(len(downloads))

        for i, dl in enumerate(downloads):
            self._table.setItem(i, 0, QTableWidgetItem(dl.get("filename", "?")))
            self._table.setItem(i, 1, QTableWidgetItem(
                humanize.naturalsize(dl.get("size_bytes", 0), binary=True) if dl.get("size_bytes") else "—"
            ))
            self._table.setItem(i, 2, QTableWidgetItem(dl.get("source_type", "—")))
            self._table.setItem(i, 3, QTableWidgetItem(dl.get("platform", "—")))

            status = dl.get("status", "—")
            status_item = QTableWidgetItem(status.upper())
            color_map = {
                "complete": QColor(16, 185, 129),
                "failed": QColor(239, 68, 68),
                "cancelled": QColor(245, 158, 11),
                "queued": QColor(148, 163, 184),
            }
            status_item.setForeground(color_map.get(status, QColor(241, 245, 249)))
            self._table.setItem(i, 4, status_item)

            self._table.setItem(i, 5, QTableWidgetItem(dl.get("format", "—")))

            date_str = dl.get("created_at", "")
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            self._table.setItem(i, 6, QTableWidgetItem(date_str))

            speed = dl.get("speed_avg", 0)
            speed_str = humanize.naturalsize(speed, binary=True) + "/s" if speed else "—"
            self._table.setItem(i, 7, QTableWidgetItem(speed_str))

            # Store download id in first column
            self._table.item(i, 0).setData(Qt.ItemDataRole.UserRole, dl.get("id"))

    def _update_stats(self) -> None:
        stats = self._db.get_download_stats()
        self._total_label.setText(f"Total: {humanize.naturalsize(stats['total_bytes'], binary=True)}")
        self._count_label.setText(f"Downloads: {stats['total_count']}")

        avg = stats.get("avg_speed", 0)
        if avg > 0:
            self._avg_speed_label.setText(f"Avg Speed: {humanize.naturalsize(avg, binary=True)}/s")
        else:
            self._avg_speed_label.setText("Avg Speed: —")

        self._chart.set_data(stats.get("daily_stats", []))

    def _on_filter_changed(self) -> None:
        self.refresh()

    def _show_context_menu(self, pos: object) -> None:
        row = self._table.currentRow()
        if row < 0:
            return

        item = self._table.item(row, 0)
        if not item:
            return

        download_id = item.data(Qt.ItemDataRole.UserRole)
        dl = self._db.get_download(download_id) if download_id else None
        if not dl:
            return

        menu = QMenu(self)

        if dl.get("filepath") and os.path.exists(dl["filepath"]):
            menu.addAction(get_icon("play"), "Open File", lambda: self._open_file(dl["filepath"]))
            menu.addAction(get_icon("folder"), "Open Folder", lambda: self._open_folder(dl["filepath"]))

        menu.addAction(get_icon("link"), "Copy URL", lambda: self._copy_text(dl.get("url", "")))
        menu.addAction(get_icon("folder"), "Copy Path", lambda: self._copy_text(dl.get("filepath", "")))
        menu.addSeparator()
        menu.addAction(get_icon("trash"), "Delete Record", lambda: self._delete_record(download_id))

        if dl.get("filepath") and os.path.exists(dl["filepath"]):
            menu.addAction(get_icon("close"), "Delete File + Record", lambda: self._delete_file_and_record(download_id, dl["filepath"]))

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _open_file(self, filepath: str) -> None:
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])

    def _open_folder(self, filepath: str) -> None:
        folder = os.path.dirname(filepath)
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", filepath])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", filepath])
        else:
            subprocess.run(["xdg-open", folder])

    def _copy_text(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

    def _delete_record(self, download_id: int) -> None:
        self._db.delete_download(download_id)
        self.refresh()

    def _delete_file_and_record(self, download_id: int, filepath: str) -> None:
        reply = QMessageBox.question(
            self, "Delete File",
            f"Are you sure you want to delete the file and its record?\n{filepath}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError:
                pass
            self._db.delete_download(download_id)
            self.refresh()

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to delete all download history records?\nFiles will not be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.clear_history()
            self.refresh()
