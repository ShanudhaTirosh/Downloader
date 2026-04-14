"""
ShanuFx Downloader — Reusable empty state widget.
Displays a beautiful SVG-style icon and message when no data is available.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QFont
from icons import get_pixmap


class EmptyState(QWidget):
    """Visual placeholder for empty lists or tabs."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        description: str,
        action_text: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setPixmap(get_pixmap(icon_name, 80))
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("opacity: 0.5; margin-bottom: 10px;")
        layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setObjectName("headingLabel")
        self._title_label.setFont(QFont("Segoe UI Semibold", 14))
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel(description)
        self._desc_label.setObjectName("secondaryLabel")
        self._desc_label.setWordWrap(True)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setMaximumWidth(400)
        layout.addWidget(self._desc_label)

        # Optional Action
        if action_text:
            layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
            self._action_button = QPushButton(action_text)
            self._action_button.setObjectName("primaryBtn")
            self._action_button.setFixedWidth(200)
            self._action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(self._action_button, 0, Qt.AlignmentFlag.AlignCenter)

    def set_action_callback(self, callback) -> None:
        if hasattr(self, "_action_button"):
            self._action_button.clicked.connect(callback)
