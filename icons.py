import os
import sys
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_icon(name: str) -> QIcon:
    """Load an SVG icon from the assets folder."""
    path = get_resource_path(os.path.join("assets", "icons", f"{name}.svg"))
    return QIcon(path)

def get_pixmap(name: str, size: int = 24) -> QPixmap:
    """Load an SVG icon as a scaled QPixmap for Labels."""
    return get_icon(name).pixmap(QSize(size, size))
