"""
ShanuFx Downloader — Multi-threaded HTTP download engine.
Supports multi-segment downloads, resume, auto-retry, and progress signals.
"""

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, QMutex

from config import (
    DEFAULT_SEGMENT_COUNT,
    MAX_RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
    SPEED_UPDATE_INTERVAL_MS,
    USER_AGENT,
    TEMP_DIR,
    sanitize_filename,
    get_unique_filepath,
)

logger = logging.getLogger(__name__)


class DownloadSignals(QObject):
    """Signals emitted by download workers."""

    progress = pyqtSignal(int, int, int, float, float)  # download_id, downloaded, total, speed_bps, eta_seconds
    segment_progress = pyqtSignal(int, int, int, int)  # download_id, segment_id, downloaded, total
    status_changed = pyqtSignal(int, str)  # download_id, status
    completed = pyqtSignal(int, str, int)  # download_id, filepath, total_bytes
    failed = pyqtSignal(int, str)  # download_id, error_message
    filename_resolved = pyqtSignal(int, str, int)  # download_id, filename, total_size
    speed_update = pyqtSignal(int, float)  # download_id, speed_bps


class SegmentInfo:
    """Tracks the state of a single download segment."""

    def __init__(self, segment_id: int, start_byte: int, end_byte: int) -> None:
        self.segment_id = segment_id
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.downloaded: int = 0
        self.total: int = end_byte - start_byte + 1
        self.completed: bool = False
        self.temp_path: str = ""


class DownloadMetadata:
    """Persisted metadata for resume support (.shfx file)."""

    def __init__(self, url: str, filepath: str, total_size: int, segments: list[SegmentInfo]) -> None:
        self.url = url
        self.filepath = filepath
        self.total_size = total_size
        self.segments = segments

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "filepath": self.filepath,
            "total_size": self.total_size,
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "start_byte": s.start_byte,
                    "end_byte": s.end_byte,
                    "downloaded": s.downloaded,
                    "completed": s.completed,
                    "temp_path": s.temp_path,
                }
                for s in self.segments
            ],
        }

    def save(self, meta_path: Path) -> None:
        """Save metadata to .shfx file."""
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except OSError as e:
            logger.error("Failed to save metadata: %s", e)

    @staticmethod
    def load(meta_path: Path) -> Optional["DownloadMetadata"]:
        """Load metadata from .shfx file."""
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            segments = [
                SegmentInfo(s["segment_id"], s["start_byte"], s["end_byte"])
                for s in data["segments"]
            ]
            for seg_data, seg_obj in zip(data["segments"], segments):
                seg_obj.downloaded = seg_data["downloaded"]
                seg_obj.completed = seg_data["completed"]
                seg_obj.temp_path = seg_data["temp_path"]
            return DownloadMetadata(data["url"], data["filepath"], data["total_size"], segments)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load metadata: %s", e)
            return None


class DownloadWorker(QRunnable):
    """Multi-segment HTTP download worker running in QThreadPool."""

    def __init__(
        self,
        download_id: int,
        url: str,
        save_dir: str,
        filename: str = "",
        segment_count: int = DEFAULT_SEGMENT_COUNT,
        max_retries: int = MAX_RETRY_ATTEMPTS,
        speed_limit: int = 0,
        user_agent: str = USER_AGENT,
        proxy: Optional[dict] = None,
    ) -> None:
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_dir = Path(save_dir)
        self.filename = filename
        self.segment_count = segment_count
        self.max_retries = max_retries
        self.speed_limit = speed_limit  # KB/s, 0 = unlimited
        self.user_agent = user_agent
        self.proxy = proxy
        self.signals = DownloadSignals()
        self.setAutoDelete(True)

        self._paused = threading.Event()
        self._paused.set()  # Not paused initially
        self._cancelled = False
        self._mutex = QMutex()
        self._total_downloaded: int = 0
        self._total_size: int = 0
        self._start_time: float = 0
        self._speed_bytes: list[tuple[float, int]] = []

    def pause(self) -> None:
        """Pause the download."""
        self._paused.clear()
        self.signals.status_changed.emit(self.download_id, "paused")

    def resume(self) -> None:
        """Resume the download."""
        self._paused.set()
        self.signals.status_changed.emit(self.download_id, "downloading")

    def cancel(self) -> None:
        """Cancel the download."""
        self._cancelled = True
        self._paused.set()  # Unblock if paused
        self.signals.status_changed.emit(self.download_id, "cancelled")

    @property
    def is_paused(self) -> bool:
        return not self._paused.is_set()

    def _get_session(self) -> requests.Session:
        """Create a configured requests session."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        if self.proxy:
            session.proxies = self.proxy
        return session

    def _resolve_filename_and_size(self, session: requests.Session) -> tuple[str, int, bool]:
        """HEAD request to resolve filename, total size, and range support."""
        try:
            resp = session.head(self.url, allow_redirects=True, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            resp = session.get(self.url, stream=True, allow_redirects=True, timeout=15)
            resp.raise_for_status()

        total_size = int(resp.headers.get("Content-Length", 0))
        accept_ranges = resp.headers.get("Accept-Ranges", "").lower() == "bytes"

        if not self.filename:
            cd = resp.headers.get("Content-Disposition", "")
            match = re.search(r'filename[*]?=["\']?(?:UTF-8\'\')?([^"\';]+)', cd, re.IGNORECASE)
            if match:
                self.filename = sanitize_filename(unquote(match.group(1).strip()))
            else:
                parsed = urlparse(str(resp.url))
                path_name = Path(parsed.path).name
                self.filename = sanitize_filename(unquote(path_name)) if path_name else "download"

        if not Path(self.filename).suffix:
            content_type = resp.headers.get("Content-Type", "")
            ext_map = {
                "application/zip": ".zip",
                "application/pdf": ".pdf",
                "video/mp4": ".mp4",
                "audio/mpeg": ".mp3",
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "application/octet-stream": ".bin",
            }
            for ct, ext in ext_map.items():
                if ct in content_type:
                    self.filename += ext
                    break

        return self.filename, total_size, accept_ranges

    def _create_segments(self, total_size: int, supports_range: bool) -> list[SegmentInfo]:
        """Split the download into segments."""
        if total_size <= 0 or not supports_range or self.segment_count <= 1:
            seg = SegmentInfo(0, 0, max(total_size - 1, 0))
            seg.temp_path = str(TEMP_DIR / f"{self.download_id}_seg_0.tmp")
            return [seg]

        segment_size = total_size // self.segment_count
        segments: list[SegmentInfo] = []

        for i in range(self.segment_count):
            start = i * segment_size
            end = (i + 1) * segment_size - 1 if i < self.segment_count - 1 else total_size - 1
            seg = SegmentInfo(i, start, end)
            seg.temp_path = str(TEMP_DIR / f"{self.download_id}_seg_{i}.tmp")
            segments.append(seg)

        return segments

    def _download_segment(
        self, session: requests.Session, segment: SegmentInfo, metadata: DownloadMetadata, meta_path: Path
    ) -> bool:
        """Download a single segment with resume and retry support."""
        if segment.completed:
            return True

        for attempt in range(self.max_retries):
            if self._cancelled:
                return False

            try:
                start_byte = segment.start_byte + segment.downloaded
                headers = {"Range": f"bytes={start_byte}-{segment.end_byte}"}

                resp = session.get(self.url, headers=headers, stream=True, timeout=30)
                if resp.status_code not in (200, 206):
                    raise requests.RequestException(f"HTTP {resp.status_code}")

                mode = "ab" if segment.downloaded > 0 else "wb"
                with open(segment.temp_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if self._cancelled:
                            return False

                        self._paused.wait()

                        if chunk:
                            f.write(chunk)
                            chunk_len = len(chunk)
                            segment.downloaded += chunk_len

                            self._mutex.lock()
                            self._total_downloaded += chunk_len
                            now = time.time()
                            self._speed_bytes.append((now, chunk_len))
                            # Keep only last 2 seconds of data for speed calc
                            cutoff = now - 2.0
                            self._speed_bytes = [(t, b) for t, b in self._speed_bytes if t > cutoff]
                            self._mutex.unlock()

                            self.signals.segment_progress.emit(
                                self.download_id, segment.segment_id, segment.downloaded, segment.total
                            )

                            # Speed limiting
                            if self.speed_limit > 0:
                                expected_time = chunk_len / (self.speed_limit * 1024)
                                elapsed = time.time() - now
                                if elapsed < expected_time:
                                    time.sleep(expected_time - elapsed)

                segment.completed = True
                metadata.save(meta_path)
                return True

            except requests.RequestException as e:
                logger.warning(
                    "Segment %d attempt %d failed: %s", segment.segment_id, attempt + 1, e
                )
                if attempt < self.max_retries - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info("Retrying in %.1fs...", delay)
                    time.sleep(delay)
                else:
                    return False

        return False

    def _merge_segments(self, segments: list[SegmentInfo], output_path: Path) -> bool:
        """Merge all segment temp files into the final output file."""
        self.signals.status_changed.emit(self.download_id, "merging")
        try:
            with open(output_path, "wb") as out:
                for seg in sorted(segments, key=lambda s: s.segment_id):
                    if os.path.exists(seg.temp_path):
                        with open(seg.temp_path, "rb") as inp:
                            while True:
                                chunk = inp.read(65536)
                                if not chunk:
                                    break
                                out.write(chunk)
            return True
        except OSError as e:
            logger.error("Merge failed: %s", e)
            return False

    def _cleanup_temp(self, segments: list[SegmentInfo], meta_path: Path) -> None:
        """Remove temporary segment files and metadata."""
        for seg in segments:
            try:
                if os.path.exists(seg.temp_path):
                    os.remove(seg.temp_path)
            except OSError:
                pass
        try:
            if meta_path.exists():
                meta_path.unlink()
        except OSError:
            pass

    def _calc_speed(self) -> float:
        """Calculate current download speed in bytes per second."""
        self._mutex.lock()
        try:
            now = time.time()
            cutoff = now - 2.0
            recent = [(t, b) for t, b in self._speed_bytes if t > cutoff]
            if not recent:
                return 0.0
            total_bytes = sum(b for _, b in recent)
            time_span = now - recent[0][0]
            if time_span <= 0:
                return 0.0
            return total_bytes / time_span
        finally:
            self._mutex.unlock()

    @pyqtSlot()
    def run(self) -> None:
        """Main download execution."""
        self.signals.status_changed.emit(self.download_id, "downloading")
        self._start_time = time.time()

        session = self._get_session()
        meta_path = TEMP_DIR / f"{self.download_id}.shfx"

        try:
            # Check for existing metadata (resume)
            existing_meta = DownloadMetadata.load(meta_path) if meta_path.exists() else None

            if existing_meta and existing_meta.url == self.url:
                logger.info("Resuming download %d from metadata", self.download_id)
                filename = Path(existing_meta.filepath).name
                total_size = existing_meta.total_size
                segments = existing_meta.segments
                self._total_downloaded = sum(s.downloaded for s in segments)
                output_path = Path(existing_meta.filepath)
            else:
                # Fresh download — resolve everything
                filename, total_size, supports_range = self._resolve_filename_and_size(session)
                output_path = get_unique_filepath(self.save_dir, filename)
                segments = self._create_segments(total_size, supports_range)

                existing_meta = DownloadMetadata(self.url, str(output_path), total_size, segments)
                existing_meta.save(meta_path)

            self._total_size = total_size
            self.signals.filename_resolved.emit(self.download_id, filename, total_size)

            if self._cancelled:
                return

            # Start progress reporting timer thread
            stop_progress = threading.Event()

            def report_progress() -> None:
                while not stop_progress.is_set():
                    speed = self._calc_speed()
                    remaining = self._total_size - self._total_downloaded
                    eta = remaining / speed if speed > 0 else 0
                    self.signals.progress.emit(
                        self.download_id, self._total_downloaded, self._total_size, speed, eta
                    )
                    self.signals.speed_update.emit(self.download_id, speed)
                    stop_progress.wait(SPEED_UPDATE_INTERVAL_MS / 1000.0)

            progress_thread = threading.Thread(target=report_progress, daemon=True)
            progress_thread.start()

            # Download all segments using threads
            if len(segments) == 1 or total_size <= 0:
                # Single segment — download directly
                success = self._download_segment(session, segments[0], existing_meta, meta_path)
                if not success and not self._cancelled:
                    raise Exception("Download failed after all retries")
            else:
                # Multi-segment — download concurrently
                errors: list[str] = []
                threads: list[threading.Thread] = []

                def seg_worker(seg: SegmentInfo) -> None:
                    seg_session = self._get_session()
                    try:
                        if not self._download_segment(seg_session, seg, existing_meta, meta_path):
                            if not self._cancelled:
                                errors.append(f"Segment {seg.segment_id} failed")
                    finally:
                        seg_session.close()

                for seg in segments:
                    if not seg.completed:
                        t = threading.Thread(target=seg_worker, args=(seg,), daemon=True)
                        threads.append(t)
                        t.start()

                for t in threads:
                    t.join()

                if errors and not self._cancelled:
                    raise Exception("; ".join(errors))

            stop_progress.set()
            progress_thread.join(timeout=2)

            if self._cancelled:
                self._cleanup_temp(segments, meta_path)
                return

            # Merge segments
            if len(segments) > 1:
                if not self._merge_segments(segments, output_path):
                    raise Exception("Failed to merge segments")
            else:
                # Single segment — just rename
                seg_path = Path(segments[0].temp_path)
                if seg_path.exists():
                    seg_path.rename(output_path)

            # Final size
            final_size = output_path.stat().st_size if output_path.exists() else self._total_downloaded
            elapsed = time.time() - self._start_time
            avg_speed = final_size / elapsed if elapsed > 0 else 0

            self._cleanup_temp(segments, meta_path)
            self.signals.progress.emit(self.download_id, final_size, final_size, 0, 0)
            self.signals.completed.emit(self.download_id, str(output_path), final_size)
            self.signals.status_changed.emit(self.download_id, "complete")
            logger.info("Download %d complete: %s (%.2f MB)", self.download_id, output_path.name, final_size / 1048576)

        except Exception as e:
            error_msg = str(e)
            logger.error("Download %d failed: %s", self.download_id, error_msg)
            self.signals.failed.emit(self.download_id, error_msg)
            self.signals.status_changed.emit(self.download_id, "failed")
        finally:
            session.close()
