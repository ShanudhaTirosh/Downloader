import json
import logging
import os
import re
import zipfile
import yt_dlp
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from config import (
    YTDLP_PATH,
    FFMPEG_PATH,
    detect_platform,
    sanitize_filename,
    get_unique_filepath,
    VIDEO_FORMATS,
    AUDIO_FORMATS,
    TEMP_DIR,
)

logger = logging.getLogger(__name__)


class MediaInfo:
    """Parsed metadata from yt-dlp extraction."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.raw = data
        self.title: str = data.get("title", "Unknown")
        self.uploader: str = data.get("uploader", data.get("channel", "Unknown"))
        self.duration: int = int(data.get("duration", 0) or 0)
        self.view_count: int = int(data.get("view_count", 0) or 0)
        self.upload_date: str = data.get("upload_date", "")
        self.thumbnail: str = data.get("thumbnail", "")
        self.description: str = data.get("description", "")[:500]
        self.webpage_url: str = data.get("webpage_url", data.get("url", ""))
        self.extractor: str = data.get("extractor", "")
        self.ext: str = data.get("ext", "mp4")
        self.filesize: int = int(data.get("filesize", 0) or data.get("filesize_approx", 0) or 0)

        self.is_playlist: bool = "_type" in data and data["_type"] == "playlist"
        self.playlist_count: int = int(data.get("playlist_count", 0) or 0)
        self.playlist_title: str = data.get("playlist_title", "")
        self.playlist_entries: list[dict] = data.get("entries", []) or []

        self.formats: list[dict] = data.get("formats", []) or []
        self.subtitles: dict = data.get("subtitles", {}) or {}
        self.automatic_captions: dict = data.get("automatic_captions", {}) or {}

        self.is_tiktok_photos: bool = False
        self.photo_urls: list[str] = []
        self._detect_tiktok_photos(data)

    def _detect_tiktok_photos(self, data: dict) -> None:
        """Detect if TikTok URL is a photo slideshow."""
        extractor = data.get("extractor", "").lower()
        if "tiktok" in extractor:
            entries = data.get("entries", [])
            if entries:
                all_images = all(
                    e.get("ext", "") in ("jpg", "jpeg", "png", "webp")
                    or "image" in e.get("url", "")
                    for e in entries
                    if isinstance(e, dict)
                )
                if all_images and entries:
                    self.is_tiktok_photos = True
                    self.photo_urls = [e.get("url", "") for e in entries if isinstance(e, dict) and e.get("url")]

            if not self.is_tiktok_photos:
                images = data.get("thumbnails", [])
                if len(images) > 3 and not data.get("duration"):
                    self.is_tiktok_photos = True
                    self.photo_urls = [img.get("url", "") for img in images if img.get("url")]

    @property
    def duration_str(self) -> str:
        if self.duration <= 0:
            return "N/A"
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def formatted_date(self) -> str:
        if not self.upload_date or len(self.upload_date) < 8:
            return "Unknown"
        try:
            return f"{self.upload_date[:4]}-{self.upload_date[4:6]}-{self.upload_date[6:8]}"
        except (IndexError, ValueError):
            return self.upload_date

    def get_available_qualities(self) -> list[dict[str, str]]:
        """Get available video qualities from format list."""
        available = []
        heights_seen: set[int] = set()

        for fmt in self.formats:
            height = fmt.get("height")
            if height and height not in heights_seen and fmt.get("vcodec", "none") != "none":
                heights_seen.add(height)
                available.append({
                    "height": height,
                    "format_id": fmt.get("format_id", ""),
                    "ext": fmt.get("ext", "mp4"),
                    "filesize": fmt.get("filesize", 0) or 0,
                    "fps": fmt.get("fps", 0) or 0,
                })

        available.sort(key=lambda x: x["height"], reverse=True)
        return available


class ExtractorWorker(QThread):
    """Worker thread for yt-dlp metadata extraction."""

    extraction_complete = pyqtSignal(object)  # MediaInfo
    extraction_failed = pyqtSignal(str)  # error message
    extraction_progress = pyqtSignal(str)  # status text

    def __init__(self, url: str, ytdlp_path: str = "", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.url = url
        self.ytdlp_path = ytdlp_path or YTDLP_PATH or "yt-dlp"
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        """Extract metadata using the yt_dlp library."""
        try:
            self.extraction_progress.emit("Extracting metadata...")

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',  # Don't resolve all items in a playlist immediately
                'nocheckcertificate': True,
                'logger': logger,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We use download=False to just get the metadata
                data = ydl.extract_info(self.url, download=False)
                
                if self._cancelled:
                    return

                if not data:
                    self.extraction_failed.emit("No metadata returned from yt-dlp")
                    return

                # If it's a playlist, ensure we have the entries
                if data.get("_type") == "playlist" and not data.get("entries"):
                     self.extraction_failed.emit("Playlist has no entries")
                     return

                info = MediaInfo(data)
                self.extraction_complete.emit(info)

        except yt_dlp.utils.DownloadError as e:
            clean_msg = self._parse_error(str(e))
            self.extraction_failed.emit(clean_msg)
        except Exception as e:
            self.extraction_failed.emit(f"Extraction error: {e}")

    def _parse_error(self, error_text: str) -> str:
        """Parse yt-dlp stderr for a human-readable message."""
        lines = error_text.split("\n")
        for line in lines:
            line = line.strip()
            if "ERROR" in line:
                msg = re.sub(r"^.*ERROR:\s*", "", line)
                return msg
        return error_text[:300] if error_text else "Unknown extraction error"


class SocialDownloadWorker(QThread):
    """Worker thread for downloading social media content via yt-dlp."""

    download_progress = pyqtSignal(int, float, str)  # download_id, percentage, status
    download_complete = pyqtSignal(int, str, int)  # download_id, filepath, size
    download_failed = pyqtSignal(int, str)  # download_id, error
    status_update = pyqtSignal(int, str)  # download_id, status_text

    def __init__(
        self,
        download_id: int,
        url: str,
        save_dir: str,
        format_spec: str = "best",
        postprocessor: str = "",
        audio_quality: str = "",
        embed_thumbnail: bool = False,
        subtitle_langs: str = "",
        ytdlp_path: str = "",
        ffmpeg_path: str = "",
        filename_template: str = "%(title)s.%(ext)s",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.download_id = download_id
        self.url = url
        self.save_dir = save_dir
        self.format_spec = format_spec
        self.postprocessor = postprocessor
        self.audio_quality = audio_quality
        self.embed_thumbnail = embed_thumbnail
        self.subtitle_langs = subtitle_langs
        self.ytdlp_path = ytdlp_path or YTDLP_PATH or "yt-dlp"
        self.ffmpeg_path = ffmpeg_path or FFMPEG_PATH or ""
        self.filename_template = filename_template
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        """Download content using the yt_dlp library."""
        try:
            output_template = os.path.join(self.save_dir, self.filename_template)

            ydl_opts = {
                'format': self.format_spec,
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'progress_hooks': [self._progress_hook],
                'logger': logger,
                'merge_output_format': 'mp4',
            }

            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            if self.postprocessor:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.postprocessor,
                    'preferredquality': self.audio_quality or '192',
                }]

            if self.embed_thumbnail:
                 if 'postprocessors' not in ydl_opts:
                     ydl_opts['postprocessors'] = []
                 ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
                 ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata'})

            if self.subtitle_langs:
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = self.subtitle_langs.split(',')

            self.status_update.emit(self.download_id, "Starting download...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # This will start the actual extraction and download
                # extract_info with download=True is correct here
                final_info = ydl.extract_info(self.url, download=True)
                
                if self._cancelled:
                    return

                # Find the actual output file from final_info
                # yt-dlp usually provides 'requested_downloads' or '_filename'
                output_file = final_info.get('_filename', "")
                if not output_file and 'requested_downloads' in final_info:
                    output_file = final_info['requested_downloads'][0].get('filepath', "")

                if output_file and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                else:
                    found = self._find_downloaded_file()
                    if found:
                        output_file = found
                        file_size = os.path.getsize(found)
                    else:
                        output_file = self.save_dir
                        file_size = 0

                self.download_complete.emit(self.download_id, output_file, file_size)

        except Exception as e:
            self.download_failed.emit(self.download_id, str(e))

    def _progress_hook(self, d: dict[str, Any]) -> None:
        """Internal callback for yt-dlp progress updates."""
        if self._cancelled:
            # Raising an exception inside the hook will stop yt-dlp
            raise Exception("Download cancelled by user")

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                percentage = (downloaded / total) * 100
                speed_str = d.get('_speed_str', "N/A")
                eta_str = d.get('_eta_str', "N/A")
                status = f"Downloading: {percentage:.1f}% ({speed_str}, ETA: {eta_str})"
                self.download_progress.emit(self.download_id, percentage, status)
            else:
                self.download_progress.emit(self.download_id, 0.0, "Downloading...")

        elif d['status'] == 'finished':
            self.status_update.emit(self.download_id, "Download finished. Processing...")

    def _find_downloaded_file(self) -> str:
        """Try to find the most recently created file in save_dir."""
        try:
            save_path = Path(self.save_dir)
            files = list(save_path.iterdir())
            if not files:
                return ""
            newest = max(files, key=lambda f: f.stat().st_mtime)
            return str(newest)
        except OSError:
            return ""


class TikTokPhotoDownloader(QThread):
    """Downloads TikTok photo slideshows as ZIP archives."""

    progress = pyqtSignal(int, float, str)  # download_id, percentage, status
    complete = pyqtSignal(int, str, int)  # download_id, filepath, size
    failed = pyqtSignal(int, str)  # download_id, error

    def __init__(
        self,
        download_id: int,
        photo_urls: list[str],
        save_dir: str,
        username: str = "unknown",
        post_id: str = "0",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.download_id = download_id
        self.photo_urls = photo_urls
        self.save_dir = save_dir
        self.username = sanitize_filename(username)
        self.post_id = post_id
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        """Download all photos and create a ZIP archive."""
        import requests as req

        try:
            zip_name = f"TikTok_Photos_{self.username}_{self.post_id}.zip"
            zip_path = get_unique_filepath(Path(self.save_dir), zip_name)

            temp_dir = TEMP_DIR / f"tiktok_{self.download_id}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            total = len(self.photo_urls)
            downloaded_files: list[Path] = []

            for i, url in enumerate(self.photo_urls):
                if self._cancelled:
                    return

                pct = (i / total) * 100
                self.progress.emit(self.download_id, pct, f"Downloading photo {i + 1}/{total}")

                try:
                    resp = req.get(url, timeout=30)
                    resp.raise_for_status()

                    ext = ".jpg"
                    ct = resp.headers.get("Content-Type", "")
                    if "png" in ct:
                        ext = ".png"
                    elif "webp" in ct:
                        ext = ".webp"

                    photo_path = temp_dir / f"photo_{i + 1:03d}{ext}"
                    with open(photo_path, "wb") as f:
                        f.write(resp.content)
                    downloaded_files.append(photo_path)

                except req.RequestException as e:
                    logger.warning("Failed to download photo %d: %s", i + 1, e)

            if not downloaded_files:
                self.failed.emit(self.download_id, "No photos could be downloaded")
                return

            self.progress.emit(self.download_id, 95, "Creating ZIP archive...")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for photo in downloaded_files:
                    zf.write(photo, photo.name)

            for photo in downloaded_files:
                photo.unlink(missing_ok=True)
            try:
                temp_dir.rmdir()
            except OSError:
                pass

            file_size = zip_path.stat().st_size
            self.complete.emit(self.download_id, str(zip_path), file_size)

        except Exception as e:
            self.failed.emit(self.download_id, str(e))


class SocialExtractor(QObject):
    """High-level social media extraction manager."""

    info_ready = pyqtSignal(object)  # MediaInfo
    info_failed = pyqtSignal(str)  # error
    download_progress = pyqtSignal(int, float, str)  # id, pct, status
    download_complete = pyqtSignal(int, str, int)  # id, path, size
    download_failed = pyqtSignal(int, str)  # id, error

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._extractor: Optional[ExtractorWorker] = None
        self._downloaders: dict[int, QThread] = {}

    def extract_info(self, url: str) -> None:
        """Start metadata extraction for a URL."""
        if self._extractor and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor.wait(2000)

        self._extractor = ExtractorWorker(url)
        self._extractor.extraction_complete.connect(self.info_ready.emit)
        self._extractor.extraction_failed.connect(self.info_failed.emit)
        self._extractor.start()

    def download(
        self,
        download_id: int,
        url: str,
        save_dir: str,
        format_spec: str = "best",
        postprocessor: str = "",
        audio_quality: str = "",
        embed_thumbnail: bool = False,
        subtitle_langs: str = "",
        media_info: Optional[MediaInfo] = None,
    ) -> None:
        """Start downloading social media content."""
        if media_info and media_info.is_tiktok_photos:
            worker = TikTokPhotoDownloader(
                download_id=download_id,
                photo_urls=media_info.photo_urls,
                save_dir=save_dir,
                username=media_info.uploader,
                post_id=str(hash(url))[-8:],
            )
            worker.progress.connect(self.download_progress.emit)
            worker.complete.connect(self._on_download_complete)
            worker.failed.connect(self.download_failed.emit)
        else:
            worker = SocialDownloadWorker(
                download_id=download_id,
                url=url,
                save_dir=save_dir,
                format_spec=format_spec,
                postprocessor=postprocessor,
                audio_quality=audio_quality,
                embed_thumbnail=embed_thumbnail,
                subtitle_langs=subtitle_langs,
            )
            worker.download_progress.connect(self.download_progress.emit)
            worker.download_complete.connect(self._on_download_complete)
            worker.download_failed.connect(self.download_failed.emit)

        self._downloaders[download_id] = worker
        worker.start()

    def _on_download_complete(self, download_id: int, filepath: str, size: int) -> None:
        self._downloaders.pop(download_id, None)
        self.download_complete.emit(download_id, filepath, size)

    def cancel_download(self, download_id: int) -> None:
        worker = self._downloaders.get(download_id)
        if worker:
            if hasattr(worker, "cancel"):
                worker.cancel()
            self._downloaders.pop(download_id, None)

    def shutdown(self) -> None:
        if self._extractor and self._extractor.isRunning():
            self._extractor.cancel()
            self._extractor.wait(2000)
        for worker in list(self._downloaders.values()):
            if hasattr(worker, "cancel"):
                worker.cancel()
            worker.wait(2000)
        self._downloaders.clear()
