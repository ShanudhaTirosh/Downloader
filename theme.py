"""
ShanuFx Downloader — Full QSS glassmorphism dark stylesheet.
"""

# ── Color Constants ───────────────────────────────────────────────────────────
BG_BASE = "#0a0a0f"
BG_SURFACE = "rgba(255, 255, 255, 0.04)"
BG_SURFACE_HOVER = "rgba(255, 255, 255, 0.07)"
BG_SURFACE_PRESSED = "rgba(255, 255, 255, 0.10)"
BG_SIDEBAR = "rgba(255, 255, 255, 0.03)"
BORDER_SUBTLE = "rgba(255, 255, 255, 0.09)"
BORDER_ACCENT = "rgba(0, 212, 255, 0.3)"

ACCENT_PRIMARY = "#00d4ff"
ACCENT_SECONDARY = "#7c3aed"
ACCENT_SUCCESS = "#10b981"
ACCENT_WARNING = "#f59e0b"
ACCENT_DANGER = "#ef4444"

TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#475569"

FONT_FAMILY = "Segoe UI"
FONT_SIZE_BASE = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_HEADING = 12
FONT_SIZE_TITLE = 14


def get_stylesheet() -> str:
    """Return the complete QSS stylesheet string."""
    return f"""
    /* ── Global ───────────────────────────────────────────────── */
    * {{
        font-family: "{FONT_FAMILY}";
        font-size: {FONT_SIZE_BASE}pt;
        color: {TEXT_PRIMARY};
        outline: none;
    }}

    QMainWindow, QDialog {{
        background-color: {BG_BASE};
    }}

    QWidget {{
        background-color: transparent;
    }}

    QWidget#centralWidget {{
        background-color: {BG_BASE};
    }}

    /* ── Title Bar ────────────────────────────────────────────── */
    QWidget#titleBar {{
        background-color: rgba(10, 10, 15, 0.95);
        border-bottom: 1px solid {BORDER_SUBTLE};
        min-height: 40px;
        max-height: 40px;
    }}

    QLabel#titleLabel {{
        font-family: "{FONT_FAMILY} Semibold";
        font-size: {FONT_SIZE_HEADING}pt;
        color: {ACCENT_PRIMARY};
        padding-left: 12px;
    }}

    QPushButton#titleBtn {{
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        font-size: 14pt;
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
        border-radius: 0px;
    }}

    QPushButton#titleBtn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        color: {TEXT_PRIMARY};
    }}

    QPushButton#titleBtnClose {{
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        font-size: 14pt;
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
        border-radius: 0px;
    }}

    QPushButton#titleBtnClose:hover {{
        background-color: {ACCENT_DANGER};
        color: white;
    }}

    /* ── Sidebar ──────────────────────────────────────────────── */
    QWidget#sidebar {{
        background-color: rgba(255, 255, 255, 0.03);
        border-right: 1px solid {BORDER_SUBTLE};
    }}

    QPushButton#sidebarBtn {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {TEXT_SECONDARY};
        text-align: left;
        padding: 10px 12px;
        margin: 2px 8px;
        font-size: {FONT_SIZE_BASE}pt;
    }}

    QPushButton#sidebarBtn:hover {{
        background-color: rgba(255, 255, 255, 0.06);
        color: {TEXT_PRIMARY};
    }}

    QPushButton#sidebarBtnActive {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(0, 212, 255, 0.15), stop:1 rgba(124, 58, 237, 0.08));
        border: none;
        border-radius: 8px;
        border-left: 3px solid {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY};
        text-align: left;
        padding: 10px 12px;
        margin: 2px 8px;
        font-size: {FONT_SIZE_BASE}pt;
        font-weight: 600;
    }}

    QLabel#sidebarVersion {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL}pt;
        padding: 8px;
    }}

    /* ── Glass Card ───────────────────────────────────────────── */
    QFrame#glassCard {{
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 12px;
        padding: 16px;
    }}

    QFrame#glassCard:hover {{
        background-color: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }}

    QFrame#statCard {{
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 12px;
        padding: 16px;
    }}

    /* ── Buttons ──────────────────────────────────────────────── */
    QPushButton {{
        background-color: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        padding: 8px 16px;
        font-size: {FONT_SIZE_BASE}pt;
        min-height: 20px;
    }}

    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }}

    QPushButton:pressed {{
        background-color: rgba(255, 255, 255, 0.14);
    }}

    QPushButton:disabled {{
        background-color: rgba(255, 255, 255, 0.02);
        color: {TEXT_MUTED};
        border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    QPushButton#primaryBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
        border: none;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 24px;
    }}

    QPushButton#primaryBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #33ddff, stop:1 #9555ff);
    }}

    QPushButton#primaryBtn:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #00bbdd, stop:1 #6a2ec8);
    }}

    QPushButton#dangerBtn {{
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: {ACCENT_DANGER};
    }}

    QPushButton#dangerBtn:hover {{
        background-color: rgba(239, 68, 68, 0.25);
    }}

    QPushButton#iconBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 6px;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }}

    QPushButton#iconBtn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}

    QPushButton#fabBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
        border: none;
        border-radius: 24px;
        min-width: 48px;
        max-width: 48px;
        min-height: 48px;
        max-height: 48px;
        font-size: 18pt;
        color: white;
    }}

    QPushButton#fabBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #33ddff, stop:1 #9555ff);
    }}

    /* ── Line Edits ───────────────────────────────────────────── */
    QLineEdit {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        padding: 8px 12px;
        font-size: {FONT_SIZE_BASE}pt;
        selection-background-color: rgba(0, 212, 255, 0.3);
    }}

    QLineEdit:focus {{
        border: 1px solid {ACCENT_PRIMARY};
        background-color: rgba(255, 255, 255, 0.07);
    }}

    QLineEdit:disabled {{
        background-color: rgba(255, 255, 255, 0.02);
        color: {TEXT_MUTED};
    }}

    QLineEdit::placeholder {{
        color: {TEXT_MUTED};
    }}

    /* ── Text Edit ────────────────────────────────────────────── */
    QTextEdit, QPlainTextEdit {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        padding: 8px;
        selection-background-color: rgba(0, 212, 255, 0.3);
    }}

    QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {ACCENT_PRIMARY};
    }}

    /* ── Combo Box ────────────────────────────────────────────── */
    QComboBox {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        padding: 8px 12px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}

    QComboBox:focus {{
        border: 1px solid {ACCENT_PRIMARY};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}

    QComboBox::down-arrow {{
        image: url(assets/icons/arrow_down.svg);
        width: 16px;
        height: 16px;
        margin-right: 10px;
    }}

    QComboBox QAbstractItemView {{
        background-color: #1a1a24;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        selection-background-color: rgba(0, 212, 255, 0.2);
        selection-color: {ACCENT_PRIMARY};
        padding: 4px;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 6px 12px;
        border-radius: 4px;
        min-height: 24px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}

    /* ── Spin Box ─────────────────────────────────────────────── */
    QSpinBox, QDoubleSpinBox {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        padding: 6px 10px;
        min-height: 20px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {ACCENT_PRIMARY};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        border-top-right-radius: 8px;
        background: transparent;
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 22px;
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom-right-radius: 8px;
        background: transparent;
    }}

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url(assets/icons/arrow_up.svg);
        width: 14px;
        height: 14px;
    }}

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url(assets/icons/arrow_down.svg);
        width: 14px;
        height: 14px;
    }}

    /* ── Check Box ────────────────────────────────────────────── */
    QCheckBox {{
        spacing: 8px;
        color: {TEXT_PRIMARY};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        background-color: rgba(255, 255, 255, 0.05);
    }}

    QCheckBox::indicator:hover {{
        border-color: {ACCENT_PRIMARY};
        background-color: rgba(0, 212, 255, 0.08);
    }}

    QCheckBox::indicator:checked {{
        background-color: {ACCENT_PRIMARY};
        border-color: {ACCENT_PRIMARY};
        image: none;
    }}

    /* ── Slider ───────────────────────────────────────────────── */
    QSlider::groove:horizontal {{
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: {ACCENT_PRIMARY};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}

    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
        border-radius: 3px;
    }}

    /* ── Progress Bar ─────────────────────────────────────────── */
    QProgressBar {{
        background-color: rgba(255, 255, 255, 0.06);
        border: none;
        border-radius: 4px;
        text-align: center;
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL}pt;
        min-height: 8px;
        max-height: 8px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
        border-radius: 4px;
    }}

    /* ── Table Widget ─────────────────────────────────────────── */
    QTableWidget {{
        background-color: transparent;
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        gridline-color: rgba(255, 255, 255, 0.06);
        selection-background-color: rgba(0, 212, 255, 0.12);
        selection-color: {TEXT_PRIMARY};
    }}

    QTableWidget::item {{
        padding: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }}

    QTableWidget::item:hover {{
        background-color: rgba(255, 255, 255, 0.04);
    }}

    QTableWidget::item:selected {{
        background-color: rgba(0, 212, 255, 0.12);
    }}

    QHeaderView::section {{
        background-color: rgba(255, 255, 255, 0.04);
        color: {TEXT_SECONDARY};
        padding: 8px;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.09);
        font-weight: 600;
        font-size: {FONT_SIZE_SMALL}pt;
    }}

    QHeaderView::section:hover {{
        background-color: rgba(255, 255, 255, 0.07);
        color: {TEXT_PRIMARY};
    }}

    /* ── Scroll Area ──────────────────────────────────────────── */
    QScrollArea {{
        background: transparent;
        border: none;
    }}

    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    /* ── Scroll Bars ──────────────────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.12);
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.2);
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: rgba(255, 255, 255, 0.12);
        border-radius: 4px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: rgba(255, 255, 255, 0.2);
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* ── Tab Widget ───────────────────────────────────────────── */
    QTabWidget::pane {{
        background: transparent;
        border: none;
    }}

    QTabBar::tab {{
        background: transparent;
        color: {TEXT_SECONDARY};
        padding: 10px 20px;
        border-bottom: 2px solid transparent;
        font-size: {FONT_SIZE_BASE}pt;
    }}

    QTabBar::tab:hover {{
        color: {TEXT_PRIMARY};
        background: rgba(255, 255, 255, 0.04);
    }}

    QTabBar::tab:selected {{
        color: {ACCENT_PRIMARY};
        border-bottom: 2px solid {ACCENT_PRIMARY};
        font-weight: 600;
    }}

    /* ── Group Box ────────────────────────────────────────────── */
    QGroupBox {{
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        margin-top: 16px;
        padding-top: 20px;
        font-size: {FONT_SIZE_BASE}pt;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        padding: 0 8px;
        color: {ACCENT_PRIMARY};
    }}

    /* ── Labels ───────────────────────────────────────────────── */
    QLabel {{
        color: {TEXT_PRIMARY};
        background: transparent;
    }}

    QLabel#headingLabel {{
        font-family: "{FONT_FAMILY} Semibold";
        font-size: {FONT_SIZE_HEADING}pt;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}

    QLabel#titleLargeLabel {{
        font-family: "{FONT_FAMILY} Semibold";
        font-size: {FONT_SIZE_TITLE}pt;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}

    QLabel#secondaryLabel {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL}pt;
    }}

    QLabel#mutedLabel {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL}pt;
    }}

    QLabel#accentLabel {{
        color: {ACCENT_PRIMARY};
        font-weight: 600;
    }}

    QLabel#statValue {{
        font-size: 18pt;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}

    QLabel#statLabel {{
        font-size: {FONT_SIZE_SMALL}pt;
        color: {TEXT_SECONDARY};
    }}

    QLabel#badgeLabel {{
        background-color: rgba(0, 212, 255, 0.15);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_PRIMARY};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: 600;
    }}

    QLabel#successBadge {{
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_SUCCESS};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: 600;
    }}

    QLabel#warningBadge {{
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_WARNING};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: 600;
    }}

    QLabel#dangerBadge {{
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_DANGER};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: 600;
    }}

    /* ── Status Bar ───────────────────────────────────────────── */
    QWidget#statusBar {{
        background-color: rgba(10, 10, 15, 0.95);
        border-top: 1px solid {BORDER_SUBTLE};
        min-height: 32px;
        max-height: 32px;
    }}

    QLabel#statusLabel {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL}pt;
        padding: 0 8px;
    }}

    /* ── Menu ─────────────────────────────────────────────────── */
    QMenu {{
        background-color: #1a1a24;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 8px 24px 8px 16px;
        border-radius: 4px;
        color: {TEXT_PRIMARY};
    }}

    QMenu::item:selected {{
        background-color: rgba(0, 212, 255, 0.15);
        color: {ACCENT_PRIMARY};
    }}

    QMenu::separator {{
        height: 1px;
        background: rgba(255, 255, 255, 0.08);
        margin: 4px 8px;
    }}

    /* ── Tooltips ─────────────────────────────────────────────── */
    QToolTip {{
        background-color: #1e1e2e;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        color: {TEXT_PRIMARY};
        padding: 6px 10px;
        font-size: {FONT_SIZE_SMALL}pt;
    }}

    /* ── Splitter ─────────────────────────────────────────────── */
    QSplitter::handle {{
        background: rgba(255, 255, 255, 0.06);
        width: 2px;
    }}

    QSplitter::handle:hover {{
        background: {ACCENT_PRIMARY};
    }}

    /* ── Dialog ───────────────────────────────────────────────── */
    QDialog {{
        background-color: {BG_BASE};
    }}

    /* ── Tree Widget ──────────────────────────────────────────── */
    QTreeWidget {{
        background-color: transparent;
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        selection-background-color: rgba(0, 212, 255, 0.12);
        outline: none;
    }}

    QTreeWidget::item {{
        padding: 4px;
        border-radius: 4px;
    }}

    QTreeWidget::item:hover {{
        background-color: rgba(255, 255, 255, 0.04);
    }}

    QTreeWidget::item:selected {{
        background-color: rgba(0, 212, 255, 0.12);
    }}

    QTreeWidget::branch {{
        background: transparent;
    }}

    /* ── Toast Notification ───────────────────────────────────── */
    QFrame#toast {{
        background-color: rgba(30, 30, 46, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 12px 16px;
    }}

    /* ── Drag & Drop Zone ─────────────────────────────────────── */
    QFrame#dropZone {{
        background-color: rgba(255, 255, 255, 0.02);
        border: 2px dashed rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        min-height: 120px;
    }}

    QFrame#dropZone:hover {{
        border-color: {ACCENT_PRIMARY};
        background-color: rgba(0, 212, 255, 0.04);
    }}

    /* ── Download Status Badges ───────────────────────────────── */
    QLabel#statusDownloading {{
        background-color: rgba(0, 212, 255, 0.15);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_PRIMARY};
        font-size: 8pt;
        font-weight: 600;
    }}

    QLabel#statusPaused {{
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_WARNING};
        font-size: 8pt;
        font-weight: 600;
    }}

    QLabel#statusQueued {{
        background-color: rgba(148, 163, 184, 0.15);
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {TEXT_SECONDARY};
        font-size: 8pt;
        font-weight: 600;
    }}

    QLabel#statusComplete {{
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_SUCCESS};
        font-size: 8pt;
        font-weight: 600;
    }}

    QLabel#statusFailed {{
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_DANGER};
        font-size: 8pt;
        font-weight: 600;
    }}

    QLabel#statusMerging {{
        background-color: rgba(124, 58, 237, 0.15);
        border: 1px solid rgba(124, 58, 237, 0.3);
        border-radius: 10px;
        padding: 2px 10px;
        color: {ACCENT_SECONDARY};
        font-size: 8pt;
        font-weight: 600;
    }}
    """
