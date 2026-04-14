"""
ShanuFx Downloader — About tab.
Displays developer info, tech stack, and social links.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QScrollArea,
)

from config import APP_VERSION, APP_NAME
from icons import get_pixmap, get_icon


class AboutTab(QWidget):
    """Informational tab about the application and its developer."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        # Scroll area for long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(24)

        # 1. Branding Header
        header_card = QFrame()
        header_card.setObjectName("glassCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setContentsMargins(32, 32, 32, 32)

        logo = QLabel()
        logo.setPixmap(get_pixmap("download", 80))
        header_layout.addWidget(logo)

        name_label = QLabel(APP_NAME)
        name_label.setObjectName("titleLargeLabel")
        name_label.setFont(QFont("Segoe UI Semibold", 24))
        header_layout.addWidget(name_label)

        ver_label = QLabel(f"Version {APP_VERSION}")
        ver_label.setObjectName("mutedLabel")
        header_layout.addWidget(ver_label)
        
        container_layout.addWidget(header_card)

        # 2. Body Grid
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)

        # Developer Section
        dev_card = QFrame()
        dev_card.setObjectName("glassCard")
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setSpacing(12)

        dev_title = QLabel("Meet the Developer")
        dev_title.setObjectName("headingLabel")
        dev_layout.addWidget(dev_title)

        dev_name = QLabel("ShanuFx")
        dev_name.setObjectName("accentLabel")
        dev_name.setFont(QFont("Segoe UI Semibold", 12))
        dev_layout.addWidget(dev_name)

        # I have updated this section in your about_tab.py:
        dev_bio = QLabel(
            "Hi, I’m Shanudha Tirosh, a passionate frontend developer and student from Sri Lanka 🇱🇰. "
            "I love building modern, user-friendly applications and exploring new technologies in the world of software development.\n\n"
            "💡 I enjoy:\n"
            "• Creating responsive and visually appealing UI/UX designs\n"
            "• Building real-world apps that solve everyday problems\n"
            "• Experimenting with AI integrations and smart systems\n"
            "• Working on IoT projects using ESP8266 and ESP32\n\n"
            "🎯 My goal is to become a professional software engineer and build innovative solutions that make life easier and smarter.\n\n"
            "📬 Connect with me:\n"
            "GitHub: https://github.com/ShanudhaTirosh\n"
            "Email: Tiroshbrot123@gmail.com"
        )

        dev_bio.setWordWrap(True)
        dev_bio.setObjectName("secondaryLabel")
        dev_layout.addWidget(dev_bio)
        
        dev_layout.addStretch()

        github_btn = QPushButton(" GitHub Profile")
        github_btn.setIcon(get_icon("link"))
        github_btn.setObjectName("primaryBtn")
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/ShanudhaTirosh")))
        dev_layout.addWidget(github_btn)

        grid_layout.addWidget(dev_card, 1)

        # Tech Stack Section
        tech_card = QFrame()
        tech_card.setObjectName("glassCard")
        tech_layout = QVBoxLayout(tech_card)
        tech_layout.setSpacing(12)

        tech_title = QLabel("Built With")
        tech_title.setObjectName("headingLabel")
        tech_layout.addWidget(tech_title)

        tech_items = [
            ("Python", "The core language"),
            ("PyQt6", "Modern UI Framework"),
            ("libtorrent", "High-performance torrent engine"),
            ("yt-dlp", "Universal media extractor"),
            ("SQLite", "Lightweight database engine"),
        ]

        for title, desc in tech_items:
            item_layout = QVBoxLayout()
            item_layout.setSpacing(2)
            
            t_label = QLabel(f"• {title}")
            t_label.setObjectName("accentLabel")
            t_label.setFont(QFont("Segoe UI Semibold", 10))
            item_layout.addWidget(t_label)
            
            d_label = QLabel(desc)
            d_label.setObjectName("mutedLabel")
            d_label.setContentsMargins(12, 0, 0, 0)
            item_layout.addWidget(d_label)
            
            tech_layout.addLayout(item_layout)

        grid_layout.addWidget(tech_card, 1)
        container_layout.addLayout(grid_layout)

        # 3. Footer
        footer = QLabel("Made with ❤️ for the community.")
        footer.setObjectName("mutedLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(footer)

        scroll.setWidget(container)
        layout.addWidget(scroll)
