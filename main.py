"""
ShanuFx Downloader — Entry point & app bootstrap.
Initializes logging, database, engines, and launches the main window.
"""

import sys
import os
import logging
import traceback
import ctypes
from logging.handlers import RotatingFileHandler
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from config import (
    APP_NAME,
    APP_VERSION,
    WINDOW_TITLE,
    LOG_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOG_LEVEL,
)
from theme import get_stylesheet
from icons import get_resource_path


def setup_logging() -> None:
    """Configure rotating log file and console logging."""
    log_dir = LOG_FILE.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    file_handler = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)


class CrashDialog(QDialog):
    """Crash dialog shown on unhandled exceptions."""

    def __init__(self, error_text: str, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Crash Report")
        self.setMinimumSize(500, 350)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel(f"💥 {APP_NAME} encountered an error")
        header.setFont(QFont("Segoe UI Semibold", 14))
        header.setStyleSheet("color: #ef4444;")
        layout.addWidget(header)

        desc = QLabel("An unexpected error occurred. Please copy the details below if reporting the issue.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._error_text = QTextEdit()
        self._error_text.setPlainText(error_text)
        self._error_text.setReadOnly(True)
        self._error_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self._error_text, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        copy_btn = QPushButton("📋 Copy Error")
        copy_btn.clicked.connect(self._copy)
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _copy(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._error_text.toPlainText())


def global_exception_handler(exc_type: type, exc_value: BaseException, exc_tb: object) -> None:
    """Global exception handler — logs error and shows crash dialog."""
    error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger = logging.getLogger(__name__)
    logger.critical("Unhandled exception:\n%s", error_text)

    try:
        app = QApplication.instance()
        if app:
            dialog = CrashDialog(error_text)
            dialog.exec()
    except Exception:
        pass


def main() -> None:
    """Application entry point."""
    # Fix taskbar icon on Windows - must match the AppID used in the installer
    if sys.platform == "win32":
        myappid = 'ShanuFx.Downloader.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)

    sys.excepthook = global_exception_handler

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("ShanuFx")
    app.setOrganizationDomain("shanufx.com")

    # Apply theme
    app.setStyleSheet(get_stylesheet())

    # Set application icon globally
    icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Initialize database
    from core.db import DatabaseManager

    db = DatabaseManager()
    logger.info("Database initialized")

    # Initialize engines
    from core.queue_manager import QueueManager
    from core.social_extractor import SocialExtractor
    from core.torrent_engine import TorrentEngine

    settings = db.get_all_settings()

    queue_manager = QueueManager(db, max_concurrent=settings.get("max_simultaneous", 5))
    social_extractor = SocialExtractor()
    torrent_engine = TorrentEngine(db)

    # Apply torrent settings
    if torrent_engine.is_available:
        torrent_engine.apply_settings(
            max_download_speed=settings.get("torrent_max_download_speed", 0),
            max_upload_speed=settings.get("torrent_max_upload_speed", 0),
            dht_enabled=settings.get("torrent_dht", True),
            port_start=settings.get("torrent_port_start", 6881),
            port_end=settings.get("torrent_port_end", 6889),
            encryption=settings.get("torrent_encryption", "enabled"),
        )

    logger.info("Engines initialized")

    # Create and show main window
    from ui.main_window import MainWindow

    window = MainWindow(db, queue_manager, social_extractor, torrent_engine)
    window.show()

    logger.info("Main window displayed")

    exit_code = app.exec()

    # Graceful shutdown
    queue_manager.shutdown()
    torrent_engine.shutdown()
    social_extractor.shutdown()
    db.shutdown()

    logger.info("Shutdown complete (exit code %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
