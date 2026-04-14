"""
ShanuFx Downloader — Settings tab.
Full preferences panel with sections for General, Network, Social, Torrent, Advanced.
"""

import os
import logging
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
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QFileDialog,
    QScrollArea,
    QFrame,
    QMessageBox,
    QSizePolicy,
)

from config import LOG_FILE, get_default_settings
from icons import get_icon

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """Application preferences panel with persistent storage."""

    settings_changed = pyqtSignal(str, object)  # key, value
    settings_reset = pyqtSignal()

    def __init__(self, db: object, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._widgets: dict[str, QWidget] = {}
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("Settings")
        header.setObjectName("titleLargeLabel")
        layout.addWidget(header)

        # ── General ──────────────────────────────────────────
        general = QGroupBox("General")
        gen_layout = QVBoxLayout(general)

        self._add_path_setting(gen_layout, "download_dir", "Default Download Folder")
        self._add_spin_setting(gen_layout, "max_simultaneous", "Max Simultaneous Downloads", 1, 10)
        self._add_toggle_setting(gen_layout, "ask_location", "Ask for download location each time")
        self._add_toggle_setting(gen_layout, "auto_start", "Auto-start downloads when added")
        self._add_toggle_setting(gen_layout, "minimize_to_tray", "Minimize to system tray on close")

        layout.addWidget(general)

        # ── Network ──────────────────────────────────────────
        network = QGroupBox("Network")
        net_layout = QVBoxLayout(network)

        self._add_spin_setting(net_layout, "max_speed_per_file", "Max Speed Per File (KB/s, 0=unlimited)", 0, 1000000)
        self._add_spin_setting(net_layout, "max_total_speed", "Max Total Speed (KB/s, 0=unlimited)", 0, 1000000)

        # Proxy section
        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel("Proxy:"))
        proxy_type = QComboBox()
        proxy_type.addItems(["None", "HTTP", "SOCKS5"])
        self._widgets["proxy_type"] = proxy_type
        proxy_type.currentTextChanged.connect(lambda v: self._save("proxy_type", v.lower()))
        proxy_row.addWidget(proxy_type)

        proxy_host = QLineEdit()
        proxy_host.setPlaceholderText("Host")
        self._widgets["proxy_host"] = proxy_host
        proxy_host.editingFinished.connect(lambda: self._save("proxy_host", proxy_host.text()))
        proxy_row.addWidget(proxy_host)

        proxy_port = QSpinBox()
        proxy_port.setRange(0, 65535)
        proxy_port.setFixedWidth(80)
        self._widgets["proxy_port"] = proxy_port
        proxy_port.valueChanged.connect(lambda v: self._save("proxy_port", v))
        proxy_row.addWidget(proxy_port)

        net_layout.addLayout(proxy_row)

        self._add_text_setting(net_layout, "user_agent", "User-Agent String")

        layout.addWidget(network)

        # ── Social Media ─────────────────────────────────────
        social = QGroupBox("Social Media")
        soc_layout = QVBoxLayout(social)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Default Video Quality:"))
        quality_combo = QComboBox()
        quality_combo.addItems(["2160p", "1440p", "1080p", "720p", "480p", "360p", "best", "worst"])
        self._widgets["default_video_quality"] = quality_combo
        quality_combo.currentTextChanged.connect(lambda v: self._save("default_video_quality", v))
        quality_row.addWidget(quality_combo)
        quality_row.addStretch()
        soc_layout.addLayout(quality_row)

        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("Default Audio Format:"))
        audio_combo = QComboBox()
        audio_combo.addItems(["mp3_320", "mp3_192", "mp3_128", "aac_256", "ogg", "flac", "wav"])
        self._widgets["default_audio_format"] = audio_combo
        audio_combo.currentTextChanged.connect(lambda v: self._save("default_audio_format", v))
        audio_row.addWidget(audio_combo)
        audio_row.addStretch()
        soc_layout.addLayout(audio_row)

        self._add_toggle_setting(soc_layout, "auto_embed_thumbnail", "Auto-embed thumbnail in audio files")
        self._add_text_setting(soc_layout, "subtitle_languages", "Subtitle Languages (e.g., en,si)")
        self._add_path_setting(soc_layout, "ffmpeg_path", "FFmpeg Executable Path", is_file=True)
        self._add_toggle_setting(soc_layout, "ytdlp_auto_update", "Auto-update yt-dlp on launch")

        layout.addWidget(social)

        # ── Torrent ──────────────────────────────────────────
        torrent = QGroupBox("Torrent")
        tor_layout = QVBoxLayout(torrent)

        self._add_path_setting(tor_layout, "torrent_save_path", "Default Torrent Save Path")
        self._add_spin_setting(tor_layout, "torrent_max_download_speed", "Max Download Speed (KB/s, 0=unlimited)", 0, 1000000)
        self._add_spin_setting(tor_layout, "torrent_max_upload_speed", "Max Upload Speed (KB/s, 0=unlimited)", 0, 1000000)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port Range:"))
        port_start = QSpinBox()
        port_start.setRange(1024, 65535)
        self._widgets["torrent_port_start"] = port_start
        port_start.valueChanged.connect(lambda v: self._save("torrent_port_start", v))
        port_row.addWidget(port_start)
        port_row.addWidget(QLabel("to"))
        port_end = QSpinBox()
        port_end.setRange(1024, 65535)
        self._widgets["torrent_port_end"] = port_end
        port_end.valueChanged.connect(lambda v: self._save("torrent_port_end", v))
        port_row.addWidget(port_end)
        port_row.addStretch()
        tor_layout.addLayout(port_row)

        self._add_toggle_setting(tor_layout, "torrent_dht", "Enable DHT")
        self._add_toggle_setting(tor_layout, "torrent_pex", "Enable Peer Exchange (PEX)")
        self._add_toggle_setting(tor_layout, "torrent_lsd", "Enable Local Service Discovery (LSD)")

        enc_row = QHBoxLayout()
        enc_row.addWidget(QLabel("Encryption:"))
        enc_combo = QComboBox()
        enc_combo.addItems(["enabled", "forced", "disabled"])
        self._widgets["torrent_encryption"] = enc_combo
        enc_combo.currentTextChanged.connect(lambda v: self._save("torrent_encryption", v))
        enc_row.addWidget(enc_combo)
        enc_row.addStretch()
        tor_layout.addLayout(enc_row)

        self._add_spin_setting(tor_layout, "torrent_seed_ratio", "Seed Ratio Limit (0=forever)", 0, 100, is_double=True)
        self._add_toggle_setting(tor_layout, "torrent_move_completed", "Move completed torrents to folder")
        self._add_path_setting(tor_layout, "torrent_move_path", "Completed Torrents Folder")

        layout.addWidget(torrent)

        # ── Advanced ─────────────────────────────────────────
        advanced = QGroupBox("Advanced")
        adv_layout = QVBoxLayout(advanced)

        seg_row = QHBoxLayout()
        seg_row.addWidget(QLabel("Segment Count for HTTP:"))
        seg_combo = QComboBox()
        seg_combo.addItems(["4", "8", "16", "32"])
        self._widgets["segment_count"] = seg_combo
        seg_combo.currentTextChanged.connect(lambda v: self._save("segment_count", int(v)))
        seg_row.addWidget(seg_combo)
        seg_row.addStretch()
        adv_layout.addLayout(seg_row)

        self._add_spin_setting(adv_layout, "retry_attempts", "Retry Attempts", 1, 10)
        self._add_spin_setting(adv_layout, "retry_delay", "Retry Delay (seconds)", 1, 60, is_double=True)

        log_row = QHBoxLayout()
        log_row.addWidget(QLabel("Log Level:"))
        log_combo = QComboBox()
        log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._widgets["log_level"] = log_combo
        log_combo.currentTextChanged.connect(lambda v: self._save("log_level", v))
        log_row.addWidget(log_combo)

        open_log_btn = QPushButton(" Open Log File")
        open_log_btn.setIcon(get_icon("folder"))
        open_log_btn.clicked.connect(self._open_log)
        log_row.addWidget(open_log_btn)
        log_row.addStretch()
        adv_layout.addLayout(log_row)

        layout.addWidget(advanced)

        # ── Actions ──────────────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.addStretch()

        reset_btn = QPushButton(" Reset All Settings to Defaults")
        reset_btn.setIcon(get_icon("refresh"))
        reset_btn.setObjectName("dangerBtn")
        reset_btn.clicked.connect(self._reset_settings)
        actions_row.addWidget(reset_btn)

        layout.addLayout(actions_row)

        # About
        about = QFrame()
        about.setObjectName("glassCard")
        about_layout = QVBoxLayout(about)
        about_label = QLabel("ShanuFx Downloader v2.0.0\nBuilt by Shanudha Tirosh · ShanuFx")
        about_label.setObjectName("mutedLabel")
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(about_label)
        layout.addWidget(about)

        layout.addStretch()
        scroll.setWidget(container)

    def _add_toggle_setting(self, layout: QVBoxLayout, key: str, label: str) -> None:
        cb = QCheckBox(label)
        self._widgets[key] = cb
        cb.toggled.connect(lambda v: self._save(key, v))
        layout.addWidget(cb)

    def _add_spin_setting(
        self, layout: QVBoxLayout, key: str, label: str,
        min_val: int = 0, max_val: int = 100, is_double: bool = False
    ) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        if is_double:
            spin = QDoubleSpinBox()
            spin.setRange(float(min_val), float(max_val))
            spin.setDecimals(1)
        else:
            spin = QSpinBox()
            spin.setRange(min_val, max_val)
        spin.setFixedWidth(100)
        self._widgets[key] = spin
        spin.valueChanged.connect(lambda v: self._save(key, v))
        row.addWidget(spin)
        row.addStretch()
        layout.addLayout(row)

    def _add_text_setting(self, layout: QVBoxLayout, key: str, label: str) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        self._widgets[key] = edit
        edit.editingFinished.connect(lambda: self._save(key, edit.text()))
        row.addWidget(edit, 1)
        layout.addLayout(row)

    def _add_path_setting(self, layout: QVBoxLayout, key: str, label: str, is_file: bool = False) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        self._widgets[key] = edit
        edit.editingFinished.connect(lambda: self._save(key, edit.text()))
        row.addWidget(edit, 1)
        browse = QPushButton("Browse")
        if is_file:
            browse.clicked.connect(lambda: self._browse_file(edit))
        else:
            browse.clicked.connect(lambda: self._browse_dir(edit))
        row.addWidget(browse)
        layout.addLayout(row)

    def _browse_dir(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder", edit.text())
        if path:
            edit.setText(path)
            key = [k for k, w in self._widgets.items() if w is edit]
            if key:
                self._save(key[0], path)

    def _browse_file(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File", edit.text())
        if path:
            edit.setText(path)
            key = [k for k, w in self._widgets.items() if w is edit]
            if key:
                self._save(key[0], path)

    def _load_settings(self) -> None:
        """Load all settings from database into widgets."""
        settings = self._db.get_all_settings()
        defaults = get_default_settings()

        for key, widget in self._widgets.items():
            value = settings.get(key, defaults.get(key))
            if value is None:
                continue

            try:
                if isinstance(widget, QCheckBox):
                    widget.blockSignals(True)
                    widget.setChecked(bool(value))
                    widget.blockSignals(False)
                elif isinstance(widget, QSpinBox):
                    widget.blockSignals(True)
                    widget.setValue(int(value))
                    widget.blockSignals(False)
                elif isinstance(widget, QDoubleSpinBox):
                    widget.blockSignals(True)
                    widget.setValue(float(value))
                    widget.blockSignals(False)
                elif isinstance(widget, QLineEdit):
                    widget.blockSignals(True)
                    widget.setText(str(value))
                    widget.blockSignals(False)
                elif isinstance(widget, QComboBox):
                    widget.blockSignals(True)
                    idx = widget.findText(str(value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                    widget.blockSignals(False)
            except (ValueError, TypeError):
                pass

    def _save(self, key: str, value: object) -> None:
        """Save a setting to database."""
        self._db.set_setting(key, value)
        self.settings_changed.emit(key, value)

    def _open_log(self) -> None:
        log_path = str(LOG_FILE)
        if os.path.exists(log_path):
            if os.name == "nt":
                os.startfile(log_path)
            else:
                import subprocess
                subprocess.run(["xdg-open", log_path])
        else:
            QMessageBox.information(self, "Log File", "No log file found yet.")

    def _reset_settings(self) -> None:
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.reset_settings()
            self._load_settings()
            self.settings_reset.emit()
