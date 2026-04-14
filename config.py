"""
ShanuFx Downloader — App-wide constants & user settings.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Any

# ── Branding ──────────────────────────────────────────────────────────────────
APP_NAME: str = "ShanuFx Downloader"
APP_VERSION: str = "2.0.0"
APP_ID: str = "com.shanufx.downloader"
APP_AUTHOR: str = "Shanudha Tirosh"
WINDOW_TITLE: str = f"ShanuFx Downloader v{APP_VERSION}"

# ── Paths ─────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    APP_DATA_DIR: Path = Path(os.environ.get("APPDATA", Path.home())) / "ShanuFxDownloader"
else:
    APP_DATA_DIR: Path = Path.home() / ".shanufx_downloader"

DB_PATH: Path = APP_DATA_DIR / "shanufx.db"
LOG_DIR: Path = APP_DATA_DIR / "logs"
LOG_FILE: Path = LOG_DIR / "shanu_fx.log"
TEMP_DIR: Path = APP_DATA_DIR / "temp"
DEFAULT_DOWNLOAD_DIR: Path = Path.home() / "Downloads" / "ShanuFx"

# Ensure directories exist
for _dir in (APP_DATA_DIR, LOG_DIR, TEMP_DIR, DEFAULT_DOWNLOAD_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ── External Tool Detection ──────────────────────────────────────────────────
def detect_executable(name: str) -> str:
    """Auto-detect an executable from PATH. Returns path or empty string."""
    path = shutil.which(name)
    return path if path else ""


FFMPEG_PATH: str = detect_executable("ffmpeg")
FFPROBE_PATH: str = detect_executable("ffprobe")
YTDLP_PATH: str = detect_executable("yt-dlp")

# ── Download Engine Defaults ─────────────────────────────────────────────────
MAX_SIMULTANEOUS_DOWNLOADS: int = 5
DEFAULT_SEGMENT_COUNT: int = 16
MAX_RETRY_ATTEMPTS: int = 3
RETRY_BASE_DELAY: float = 2.0  # seconds, exponential backoff base
SPEED_UPDATE_INTERVAL_MS: int = 500
PROGRESS_SIGNAL_INTERVAL_MS: int = 500

# ── Torrent Defaults ─────────────────────────────────────────────────────────
TORRENT_PORT_START: int = 6881
TORRENT_PORT_END: int = 6889
TORRENT_MAX_CONNECTIONS: int = 200
TORRENT_DHT_ENABLED: bool = True
TORRENT_PEX_ENABLED: bool = True
TORRENT_LSD_ENABLED: bool = True
TORRENT_ENCRYPTION_MODE: str = "enabled"  # enabled / forced / disabled

# ── Social Media Defaults ────────────────────────────────────────────────────
DEFAULT_VIDEO_QUALITY: str = "1080p"
DEFAULT_AUDIO_FORMAT: str = "mp3_320"
AUTO_EMBED_THUMBNAIL: bool = True
SUBTITLE_LANGUAGES: str = "en"
YTDLP_AUTO_UPDATE: bool = False

# ── Network Defaults ─────────────────────────────────────────────────────────
MAX_SPEED_PER_FILE: int = 0  # 0 = unlimited, KB/s
MAX_TOTAL_SPEED: int = 0  # 0 = unlimited, KB/s
PROXY_TYPE: str = "none"  # none / http / socks5
PROXY_HOST: str = ""
PROXY_PORT: int = 0
PROXY_USER: str = ""
PROXY_PASS: str = ""
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── Logging Defaults ─────────────────────────────────────────────────────────
LOG_LEVEL: str = "INFO"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 3

# ── UI Constants ──────────────────────────────────────────────────────────────
SIDEBAR_COLLAPSED_WIDTH: int = 64
SIDEBAR_EXPANDED_WIDTH: int = 200
SIDEBAR_ANIMATION_DURATION: int = 200
TAB_ANIMATION_DURATION: int = 150
TOAST_DISPLAY_DURATION: int = 4000
SPEED_GRAPH_WINDOW_SECONDS: int = 60


# ── File Type Icons ───────────────────────────────────────────────────────────
FILE_TYPE_ICONS: dict[str, str] = {
    "video":      "video",
    "audio":      "audio",
    "image":      "image",
    "archive":    "archive",
    "document":   "document",
    "executable": "executable",
    "torrent":    "bolt",
    "other":      "folder",
}
FILE_TYPE_EXTENSIONS: dict[str, list[str]] = {
    "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
    "audio": [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".opus"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx"],
    "executable": [".exe", ".msi", ".dmg", ".appimage", ".deb", ".rpm"],
}

# ── Platform Detection Patterns ──────────────────────────────────────────────
PLATFORM_DOMAINS: dict[str, list[str]] = {
    "YouTube": ["youtube.com", "youtu.be", "youtube-nocookie.com"],
    "Instagram": ["instagram.com", "instagr.am"],
    "TikTok": ["tiktok.com", "vm.tiktok.com"],
    "Facebook": ["facebook.com", "fb.watch", "fb.com"],
    "Twitter": ["twitter.com", "x.com", "t.co"],
    "Snapchat": ["snapchat.com"],
    "Pinterest": ["pinterest.com", "pin.it"],
    "Reddit": ["reddit.com", "redd.it"],
    "Vimeo": ["vimeo.com"],
    "Dailymotion": ["dailymotion.com", "dai.ly"],
    "SoundCloud": ["soundcloud.com"],
    "Twitch": ["twitch.tv", "clips.twitch.tv"],
    "LinkedIn": ["linkedin.com"],
    "Bilibili": ["bilibili.com", "b23.tv"],
}

# ── Platform Icons ────────────────────────────────────────────────────────────
PLATFORM_ICONS: dict[str, str] = {
    "YouTube":     "play",
    "Instagram":   "image",
    "TikTok":      "play",
    "Facebook":    "globe",
    "Twitter":     "globe",
    "Unknown":     "globe",
}
# ── Format Definitions ───────────────────────────────────────────────────────
VIDEO_FORMATS: list[dict[str, str]] = [
    {"id": "2160p", "label": "2160p (4K) MP4", "ytdlp_format": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]"},
    {"id": "1440p", "label": "1440p MP4", "ytdlp_format": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]"},
    {"id": "1080p", "label": "1080p MP4", "ytdlp_format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"},
    {"id": "720p", "label": "720p MP4", "ytdlp_format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"},
    {"id": "480p", "label": "480p MP4", "ytdlp_format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]"},
    {"id": "360p", "label": "360p MP4", "ytdlp_format": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]"},
    {"id": "best", "label": "Best quality (auto)", "ytdlp_format": "bestvideo+bestaudio/best"},
    {"id": "worst", "label": "Worst quality (smallest)", "ytdlp_format": "worstvideo+worstaudio/worst"},
]

AUDIO_FORMATS: list[dict[str, str]] = [
    {"id": "mp3_320", "label": "MP3 320kbps", "ytdlp_format": "bestaudio/best", "postprocessor": "mp3", "quality": "320"},
    {"id": "mp3_192", "label": "MP3 192kbps", "ytdlp_format": "bestaudio/best", "postprocessor": "mp3", "quality": "192"},
    {"id": "mp3_128", "label": "MP3 128kbps", "ytdlp_format": "bestaudio/best", "postprocessor": "mp3", "quality": "128"},
    {"id": "aac_256", "label": "AAC 256kbps", "ytdlp_format": "bestaudio/best", "postprocessor": "aac", "quality": "256"},
    {"id": "ogg", "label": "OGG Vorbis", "ytdlp_format": "bestaudio/best", "postprocessor": "vorbis", "quality": "5"},
    {"id": "flac", "label": "FLAC (lossless)", "ytdlp_format": "bestaudio/best", "postprocessor": "flac", "quality": "0"},
    {"id": "wav", "label": "WAV", "ytdlp_format": "bestaudio/best", "postprocessor": "wav", "quality": "0"},
]


def get_file_type(filename: str) -> str:
    """Determine file type from extension."""
    ext = Path(filename).suffix.lower()
    for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return "other"


def get_file_icon(filename: str) -> str:
    """Get the icon emoji for a file type."""
    return FILE_TYPE_ICONS.get(get_file_type(filename), "📁")


def detect_platform(url: str) -> str:
    """Detect social media platform from URL. Returns platform name or 'Unknown'."""
    url_lower = url.lower()
    for platform, domains in PLATFORM_DOMAINS.items():
        for domain in domains:
            if domain in url_lower:
                return platform
    return "Unknown"


def get_platform_icon(platform: str) -> str:
    """Get the icon emoji for a platform."""
    return PLATFORM_ICONS.get(platform, "🌐")


def sanitize_filename(filename: str) -> str:
    """Remove illegal characters from a filename."""
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, "_")
    filename = filename.strip(". ")
    if not filename:
        filename = "download"
    return filename


def get_unique_filepath(directory: Path, filename: str) -> Path:
    """Generate a unique file path, appending (1), (2), etc. if file exists."""
    filepath = directory / filename
    if not filepath.exists():
        return filepath

    stem = filepath.stem
    suffix = filepath.suffix
    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = directory / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def get_default_settings() -> dict[str, Any]:
    """Return a dictionary of all default settings."""
    return {
        "download_dir": str(DEFAULT_DOWNLOAD_DIR),
        "max_simultaneous": MAX_SIMULTANEOUS_DOWNLOADS,
        "ask_location": False,
        "auto_start": True,
        "max_speed_per_file": MAX_SPEED_PER_FILE,
        "max_total_speed": MAX_TOTAL_SPEED,
        "proxy_type": PROXY_TYPE,
        "proxy_host": PROXY_HOST,
        "proxy_port": PROXY_PORT,
        "proxy_user": PROXY_USER,
        "proxy_pass": PROXY_PASS,
        "user_agent": USER_AGENT,
        "default_video_quality": DEFAULT_VIDEO_QUALITY,
        "default_audio_format": DEFAULT_AUDIO_FORMAT,
        "auto_embed_thumbnail": AUTO_EMBED_THUMBNAIL,
        "subtitle_languages": SUBTITLE_LANGUAGES,
        "ffmpeg_path": FFMPEG_PATH,
        "ytdlp_auto_update": YTDLP_AUTO_UPDATE,
        "torrent_save_path": str(DEFAULT_DOWNLOAD_DIR / "Torrents"),
        "torrent_max_upload_speed": 0,
        "torrent_max_download_speed": 0,
        "torrent_port_start": TORRENT_PORT_START,
        "torrent_port_end": TORRENT_PORT_END,
        "torrent_dht": TORRENT_DHT_ENABLED,
        "torrent_pex": TORRENT_PEX_ENABLED,
        "torrent_lsd": TORRENT_LSD_ENABLED,
        "torrent_encryption": TORRENT_ENCRYPTION_MODE,
        "torrent_seed_ratio": 0.0,
        "torrent_move_completed": False,
        "torrent_move_path": "",
        "segment_count": DEFAULT_SEGMENT_COUNT,
        "retry_attempts": MAX_RETRY_ATTEMPTS,
        "retry_delay": RETRY_BASE_DELAY,
        "log_level": LOG_LEVEL,
        "minimize_to_tray": True,
    }
