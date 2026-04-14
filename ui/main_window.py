"""
ShanuFx Downloader — Main window with frameless title bar, animated sidebar, tab router,
status bar, and system tray integration.
"""

import logging
import os
import subprocess
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)

from PyQt6.QtCore import (
    Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QFont, QIcon, QAction, QColor, QMouseEvent, QResizeEvent, QCloseEvent,
)

from icons import get_icon, get_pixmap, get_resource_path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy, QSystemTrayIcon, QMenu, QApplication,
    QGraphicsOpacityEffect, QMessageBox, QGraphicsDropShadowEffect,
)

from ui.widgets.sliding_stack import SlidingStackedWidget

import humanize
import psutil

from config import (
    WINDOW_TITLE, APP_VERSION, DEFAULT_DOWNLOAD_DIR,
    SIDEBAR_COLLAPSED_WIDTH, SIDEBAR_EXPANDED_WIDTH, SIDEBAR_ANIMATION_DURATION,
)


class TitleBar(QWidget):
    """Custom frameless title bar with drag, minimize, maximize, close."""

    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self._drag_pos: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        # App icon / branding
        icon_label = QLabel()
        icon_label.setPixmap(get_pixmap("download", 24))
        icon_label.setStyleSheet("border-radius: 4px; padding: 4px;")
        layout.addWidget(icon_label)

        title = QLabel(WINDOW_TITLE)
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addStretch()

        # Window controls
        min_btn = QPushButton("─")
        min_btn.setObjectName("titleBtn")
        min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(min_btn)

        max_btn = QPushButton("□")
        max_btn.setObjectName("titleBtn")
        max_btn.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(max_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("titleBtnClose")
        close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(close_btn)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.maximize_clicked.emit()


class Sidebar(QWidget):
    """Animated sidebar with icon/text navigation buttons."""

    tab_changed = pyqtSignal(int)
    exit_requested = pyqtSignal()

    TAB_ITEMS = [
        ("download", "Downloads"),
        ("play", "Social Media"),
        ("bolt", "Torrents"),
        ("clock", "History"),
        ("settings", "Settings"),
        ("info", "About"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)
        self._expanded = False
        self._current_index = 0

        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(SIDEBAR_ANIMATION_DURATION)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._anim2 = QPropertyAnimation(self, b"maximumWidth")
        self._anim2.setDuration(SIDEBAR_ANIMATION_DURATION)
        self._anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        self._buttons: list[QPushButton] = []
        for i, (icon_name, text) in enumerate(self.TAB_ITEMS):
            btn = QPushButton(f"  {text}")
            btn.setIcon(get_icon(icon_name))
            btn.setIconSize(QSize(18, 18))
            btn.setObjectName("sidebarBtnActive" if i == 0 else "sidebarBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_click(idx))
            
            # Button animations
            btn.setGraphicsEffect(None) # Clear inherited effects
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        
        # Add shadow to sidebar
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setColor(QColor(0, 0, 0, 80))
        self._shadow.setOffset(2, 0)
        self.setGraphicsEffect(self._shadow)

        # Version label
        self._ver_label = QLabel(f"ShanuFx v{APP_VERSION}")
        self._ver_label.setObjectName("sidebarVersion")
        self._ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ver_label)

        layout.addSpacing(4)

        self._exit_btn = QPushButton("  Exit")
        self._exit_btn.setIcon(get_icon("power"))
        self._exit_btn.setIconSize(QSize(18, 18))
        self._exit_btn.setObjectName("sidebarBtn")
        self._exit_btn.setStyleSheet("color: #ef4444; margin-bottom: 8px;")
        self._exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._exit_btn.clicked.connect(self.exit_requested.emit)
        layout.addWidget(self._exit_btn)

    def enterEvent(self, event: object) -> None:
        self._expand()

    def leaveEvent(self, event: object) -> None:
        self._collapse()

    def _expand(self) -> None:
        if self._expanded:
            return
        self._expanded = True
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(SIDEBAR_EXPANDED_WIDTH)
        self._anim2.setStartValue(self.width())
        self._anim2.setEndValue(SIDEBAR_EXPANDED_WIDTH)
        self._anim.start()
        self._anim2.start()

    def _collapse(self) -> None:
        if not self._expanded:
            return
        self._expanded = False
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(SIDEBAR_COLLAPSED_WIDTH)
        self._anim2.setStartValue(self.width())
        self._anim2.setEndValue(SIDEBAR_COLLAPSED_WIDTH)
        self._anim.start()
        self._anim2.start()

    def _on_tab_click(self, index: int) -> None:
        if index == self._current_index:
            return
        for i, btn in enumerate(self._buttons):
            btn.setObjectName("sidebarBtnActive" if i == index else "sidebarBtn")
            btn.setStyle(btn.style())
        self._current_index = index
        self.tab_changed.emit(index)


class StatusBar(QWidget):
    """Bottom status bar showing global speeds, active count, and CPU."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self._down_icon = QLabel()
        self._down_icon.setPixmap(get_pixmap("arrow_down", 16))
        layout.addWidget(self._down_icon)
        self._down_label = QLabel("0 B/s")
        self._down_label.setObjectName("statusLabel")
        self._down_label.setStyleSheet("color: #00d4ff; font-family: 'Segoe UI';")
        layout.addWidget(self._down_label)

        self._up_icon = QLabel()
        self._up_icon.setPixmap(get_pixmap("arrow_up", 16))
        layout.addWidget(self._up_icon)
        self._up_label = QLabel("0 B/s")
        self._up_label.setObjectName("statusLabel")
        self._up_label.setStyleSheet("color: #7c3aed; font-family: 'Segoe UI';")
        layout.addWidget(self._up_label)

        sep1 = QLabel("|")
        sep1.setObjectName("statusLabel")
        layout.addWidget(sep1)

        self._active_label = QLabel("0 active")
        self._active_label.setObjectName("statusLabel")
        layout.addWidget(self._active_label)

        layout.addStretch()

        self._cpu_label = QLabel("CPU: 0%")
        self._cpu_label.setObjectName("statusLabel")
        layout.addWidget(self._cpu_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_cpu)
        self._timer.start(2000)

    def update_speeds(self, down: float, up: float) -> None:
        self._down_label.setText(f"{humanize.naturalsize(down, binary=True)}/s")
        self._up_label.setText(f"{humanize.naturalsize(up, binary=True)}/s")

    def update_active_count(self, count: int) -> None:
        self._active_label.setText(f"{count} active")

    def _update_cpu(self) -> None:
        try:
            cpu = psutil.cpu_percent(interval=0)
            self._cpu_label.setText(f"CPU: {cpu:.0f}%")
        except Exception:
            pass


class ToastNotification(QFrame):
    """Slide-in toast notification from bottom-right."""

    def __init__(self, message: str, duration_ms: int = 4000, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFixedWidth(320)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)

        # Slide-in animation
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(300)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._opacity_anim = QPropertyAnimation(self._opacity, b"opacity")
        self._opacity_anim.setDuration(300)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)

        QTimer.singleShot(duration_ms, self._dismiss)

    def show_at(self, x: int, y: int) -> None:
        """Show the toast sliding in from an offset position."""
        self._pos_anim.setStartValue(QPoint(x, y + 30))
        self._pos_anim.setEndValue(QPoint(x, y))
        self.show()
        self._pos_anim.start()
        self._opacity_anim.start()

    def _dismiss(self) -> None:
        fade = QPropertyAnimation(self._opacity, b"opacity")
        fade.setDuration(200)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.finished.connect(self.deleteLater)
        fade.start()
        self._fade_anim = fade  # prevent gc


class MainWindow(QMainWindow):
    """Main application window with frameless design, sidebar, tabs, and tray."""

    def __init__(self, db: object, queue_manager: object, social_extractor: object, torrent_engine: object) -> None:
        super().__init__()
        self._db = db
        self._queue = queue_manager
        self._social = social_extractor
        self._torrent = torrent_engine
        self._toast_offset = 0

        self.setWindowTitle(WINDOW_TITLE)
        
        # Use high-res .ico for taskbar/titlebar
        icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(get_icon("download"))
        self.setMinimumSize(960, 640)
        self.resize(1200, 780)
        
        # Enable Native Windows Dark Mode Title Bar
        try:
            import ctypes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = int(self.winId())
            value = ctypes.c_int(2)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Body: sidebar + content
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.tab_changed.connect(self._switch_tab)
        body.addWidget(self._sidebar)

        # Content stack (Animated)
        self._stack = SlidingStackedWidget()

        settings = self._db.get_all_settings()
        dl_dir = settings.get("download_dir", str(DEFAULT_DOWNLOAD_DIR))
        torrent_dir = settings.get("torrent_save_path", str(DEFAULT_DOWNLOAD_DIR / "Torrents"))

        from ui.dashboard_tab import DashboardTab
        from ui.social_tab import SocialTab
        from ui.torrent_tab import TorrentTab
        from ui.history_tab import HistoryTab
        from ui.settings_tab import SettingsTab
        from ui.about_tab import AboutTab

        self._dashboard = DashboardTab(dl_dir)
        self._social_tab = SocialTab()
        self._torrent_tab = TorrentTab(torrent_dir)
        self._history_tab = HistoryTab(self._db)
        self._settings_tab = SettingsTab(self._db)
        self._settings_tab.settings_changed.connect(self._on_setting_updated)
        self._about_tab = AboutTab()

        self._stack.addWidget(self._dashboard)
        self._stack.addWidget(self._social_tab)
        self._stack.addWidget(self._torrent_tab)
        self._stack.addWidget(self._history_tab)
        self._stack.addWidget(self._settings_tab)
        self._stack.addWidget(self._about_tab)

        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        # Status bar
        self._status_bar = StatusBar()
        root.addWidget(self._status_bar)

    def _setup_tray(self) -> None:
        """Setup system tray icon and menu."""
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip(WINDOW_TITLE)

        tray_menu = QMenu()
        tray_menu.addAction("Show Window", self._tray_show)
        tray_menu.addAction("Open Download Folder", self._open_download_folder)
        tray_menu.addSeparator()
        tray_menu.addAction("Pause All", self._queue.pause_all)
        tray_menu.addAction("Resume All", self._queue.resume_all)
        tray_menu.addSeparator()
        tray_menu.addAction("Quit", self._quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        # Dashboard
        self._dashboard.add_url_requested.connect(self._on_add_url)
        self._dashboard.pause_all_requested.connect(self._queue.pause_all)
        self._dashboard.resume_all_requested.connect(self._queue.resume_all)

        # Sidebar exit
        self._sidebar.exit_requested.connect(self.close)

        # Queue manager signals
        self._queue.download_started.connect(self._on_download_started)
        self._queue.download_completed.connect(self._on_download_completed)
        self._queue.download_failed.connect(self._on_download_failed)
        self._queue.download_progress.connect(self._on_download_progress)
        self._queue.download_status_changed.connect(self._on_download_status_changed)
        self._queue.download_filename_resolved.connect(self._on_filename_resolved)
        self._queue.global_speed_update.connect(self._status_bar.update_speeds)
        self._queue.global_speed_update.connect(lambda down, up: self._dashboard.update_speed(down))
        self._queue.active_count_changed.connect(self._status_bar.update_active_count)

        # Social tab
        self._social_tab.download_requested.connect(self._on_social_download)

        # Social extractor
        self._social.download_complete.connect(self._on_social_complete)
        self._social.download_failed.connect(self._on_social_failed)
        self._social.download_progress.connect(self._on_social_progress)

        # Torrent tab
        self._torrent_tab.add_torrent_file.connect(self._on_add_torrent_file)
        self._torrent_tab.add_magnet.connect(self._on_add_magnet)

        # Torrent engine
        self._torrent.torrent_added.connect(self._on_torrent_added)
        self._torrent.torrent_status_update.connect(self._on_torrent_status)
        self._torrent.torrent_complete.connect(self._on_torrent_complete)
        self._torrent.torrent_removed.connect(self._torrent_tab.remove_card)
        self._torrent.peers_updated.connect(self._on_peers_updated)

        # Settings
        self._settings_tab.settings_changed.connect(self._on_setting_updated)

        # Dashboard card signals
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(3000)

    def _switch_tab(self, index: int) -> None:
        """Switch to the tab at the given index with animation."""
        self._stack.setCurrentIndex(index)
        if index == 3:
            self._history_tab.refresh()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_close_clicked(self) -> None:
        minimize_to_tray = self._db.get_setting("minimize_to_tray", True)
        if minimize_to_tray:
            self.hide()
            self._show_toast("ShanuFx minimized to system tray")
        else:
            self._quit()

    def _tray_show(self) -> None:
        self.show()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_show()

    def _open_download_folder(self) -> None:
        dl_dir = self._db.get_setting("download_dir", str(DEFAULT_DOWNLOAD_DIR))
        if sys.platform == "win32":
            os.startfile(dl_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", dl_dir])
        else:
            subprocess.run(["xdg-open", dl_dir])

    def _quit(self) -> None:
        self._queue.shutdown()
        self._torrent.shutdown()
        self._social.shutdown()
        self._db.shutdown()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        minimize_to_tray = self._db.get_setting("minimize_to_tray", True)
        if minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            self._quit()
            event.accept()

    # ── Download Handlers ─────────────────────────────────────────────────────

    def _on_add_url(self, url: str, save_dir: str, segments: int) -> None:
        """Handle new URL download request from dashboard."""
        settings = self._db.get_all_settings()
        
        # Resolve proxy
        proxy = None
        ptype = settings.get("proxy_type", "none")
        if ptype != "none":
            host = settings.get("proxy_host", "")
            port = settings.get("proxy_port", 0)
            if host and port:
                url_proxy = f"{ptype}://{host}:{port}"
                proxy = {"http": url_proxy, "https": url_proxy}

        self._queue.add_download(
            url=url,
            save_dir=save_dir or settings.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)),
            segment_count=segments,
            speed_limit=settings.get("max_speed_per_file", 0),
            user_agent=settings.get("user_agent", ""),
            proxy=proxy,
            auto_start=settings.get("auto_start", True),
        )

    def _on_download_started(self, download_id: int) -> None:
        dl = self._db.get_download(download_id)
        filename = dl.get("filename", "Resolving...") if dl else "Resolving..."
        url = dl.get("url", "") if dl else ""
        card = self._dashboard.add_download_card(download_id, filename, url)
        card.pause_clicked.connect(self._queue.pause_download)
        card.resume_clicked.connect(self._queue.resume_download)
        card.cancel_clicked.connect(self._queue.cancel_download)

    def _on_download_progress(self, download_id: int, downloaded: int, total: int, speed: float, eta: float) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.update_progress(downloaded, total, speed, eta)

    def _on_download_completed(self, download_id: int, filepath: str, size: int) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_status("complete")
        self._show_toast(f"Download complete: {os.path.basename(filepath)}")
        self._refresh_stats()

    def _on_download_failed(self, download_id: int, error: str) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_status("failed")
        self._show_toast(f"Download failed: {error[:60]}")

    def _on_download_status_changed(self, download_id: int, status: str) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_status(status)

    def _on_filename_resolved(self, download_id: int, filename: str, total_size: int) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_filename(filename)

    # ── Social Download Handlers ──────────────────────────────────────────────

    def _on_social_download(self, url: str, format_info: dict, media_info: object) -> None:
        """Handle social media download request."""
        settings = self._db.get_all_settings()
        save_dir = settings.get("download_dir", str(DEFAULT_DOWNLOAD_DIR))

        download_id = self._db.add_download(
            url=url,
            filename=media_info.title if media_info else "Social Download",
            source_type="social",
            platform=media_info.extractor if media_info else "",
            status="downloading",
        )

        card = self._dashboard.add_download_card(
            download_id,
            media_info.title if media_info else "Downloading...",
            url,
        )
        card.set_status("downloading")

        self._social.download(
            download_id=download_id,
            url=url,
            save_dir=save_dir,
            format_spec=format_info.get("format_spec", "best"),
            postprocessor=format_info.get("postprocessor", ""),
            audio_quality=format_info.get("quality", ""),
            embed_thumbnail=settings.get("auto_embed_thumbnail", True),
            subtitle_langs=settings.get("subtitle_languages", "") if format_info.get("subtitles") else "",
            ytdlp_path=settings.get("ytdlp_path", ""),
            ffmpeg_path=settings.get("ffmpeg_path", ""),
            media_info=media_info,
        )

        self._switch_tab(0)
        self._sidebar._on_tab_click(0)

    def _on_social_complete(self, download_id: int, filepath: str, size: int) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_status("complete")
            card.update_progress(size, size, 0, 0)
        self._db.complete_download(download_id, filepath, size, 0)
        self._show_toast(f"Download complete: {os.path.basename(filepath)}")

    def _on_social_failed(self, download_id: int, error: str) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            card.set_status("failed")
        self._db.fail_download(download_id, error)
        self._show_toast(f"Social download failed: {error[:60]}")

    def _on_social_progress(self, download_id: int, percentage: float, status: str) -> None:
        card = self._dashboard.get_card(download_id)
        if card:
            total_est = 100
            downloaded = int(percentage)
            card.update_progress(downloaded, total_est, 0, 0)

    # ── Torrent Handlers ──────────────────────────────────────────────────────

    def _on_add_torrent_file(self, path: str, save_dir: str, priorities: list) -> None:
        self._torrent.add_torrent_file(path, save_dir, priorities)

    def _on_add_magnet(self, magnet: str, save_dir: str) -> None:
        self._torrent.add_magnet(magnet, save_dir)

    def _on_torrent_added(self, info_hash: str, name: str) -> None:
        card = self._torrent_tab.add_torrent_card(info_hash, name)
        card.pause_clicked.connect(self._torrent.pause_torrent)
        card.resume_clicked.connect(self._torrent.resume_torrent)
        card.remove_clicked.connect(self._torrent.remove_torrent)
        card.recheck_clicked.connect(self._torrent.force_recheck)
        card.reannounce_clicked.connect(self._torrent.force_reannounce)
        card.sequential_toggled.connect(self._torrent.set_sequential)
        card.copy_magnet_clicked.connect(
            lambda ih: QApplication.clipboard().setText(self._torrent.get_magnet_uri(ih))
        )
        card.open_folder_clicked.connect(self._on_open_torrent_folder)
        self._show_toast(f"Torrent added: {name}")

    def _on_open_torrent_folder(self, info_hash: str) -> None:
        """Open the specific save folder for a torrent."""
        status = self._torrent.get_status(info_hash)
        if status and status.save_path:
            path = status.save_path
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            self._open_download_folder()

    def _on_torrent_status(self, status: object) -> None:
        card = self._torrent_tab.get_card(status.info_hash)
        if card:
            card.update_status(status)

    def _on_torrent_complete(self, info_hash: str, name: str) -> None:
        self._show_toast(f"Torrent complete: {name}")

    def _on_peers_updated(self, info_hash: str, peers: list) -> None:
        card = self._torrent_tab.get_card(info_hash)
        if card:
            card.update_peers(peers)

    # ── Settings Handler ──────────────────────────────────────────────────────

    def _on_setting_updated(self, key: str, value: Any) -> None:
        """Dispatch real-time setting updates to engines."""
        logger.info("Setting updated: %s = %s", key, value)
        settings = self._db.get_all_settings()

        # 1. Queue Settings
        if key in ("max_simultaneous", "max_total_speed"):
            self._queue.apply_settings(
                max_concurrent=settings.get("max_simultaneous", 5),
                global_speed_limit=settings.get("max_total_speed", 0)
            )

        # 2. Torrent Settings
        if key.startswith("torrent_"):
            if self._torrent.is_available:
                self._torrent.apply_settings(
                    max_download_speed=settings.get("torrent_max_download_speed", 0),
                    max_upload_speed=settings.get("torrent_max_upload_speed", 0),
                    dht_enabled=settings.get("torrent_dht", True),
                    pex_enabled=settings.get("torrent_pex", True),
                    lsd_enabled=settings.get("torrent_lsd", True),
                    port_start=settings.get("torrent_port_start", 6881),
                    port_end=settings.get("torrent_port_end", 6889),
                    encryption=settings.get("torrent_encryption", "enabled"),
                )

        # 3. Logging Settings
        if key == "log_level":
            logging.getLogger().setLevel(value)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        stats = self._db.get_download_stats()
        self._dashboard.update_stats(
            stats["total_bytes"],
            stats["active_count"],
            stats["queued_count"],
            stats["failed_count"],
        )

    # ── Toast ─────────────────────────────────────────────────────────────────

    def _show_toast(self, message: str) -> None:
        toast = ToastNotification(message, 4000, self)
        x = self.width() - 340
        y = self.height() - 80 - self._toast_offset
        toast.show_at(x, y)
        self._toast_offset = (self._toast_offset + 60) % 180
