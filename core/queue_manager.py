"""
ShanuFx Downloader — Global download queue & scheduler.
Manages concurrent downloads with priority ordering.
"""

import logging
import time
import threading
from typing import Optional

from PyQt6.QtCore import QObject, QThreadPool, QMutex, QMutexLocker, pyqtSignal

from core.download_engine import DownloadWorker
from core.db import DatabaseManager

logger = logging.getLogger(__name__)


class DownloadItem:
    """Represents a queued download with its worker and metadata."""

    def __init__(
        self,
        download_id: int,
        url: str,
        save_dir: str,
        filename: str = "",
        source_type: str = "http",
        platform: str = "",
        segment_count: int = 16,
        speed_limit: int = 0,
        user_agent: str = "",
        proxy: Optional[dict] = None,
    ) -> None:
        self.download_id = download_id
        self.url = url
        self.save_dir = save_dir
        self.filename = filename
        self.source_type = source_type
        self.platform = platform
        self.segment_count = segment_count
        self.speed_limit = speed_limit
        self.user_agent = user_agent
        self.proxy = proxy
        self.worker: Optional[DownloadWorker] = None
        self.status: str = "queued"
        self.priority: int = 0


class QueueManager(QObject):
    """Manages the global download queue with concurrency limits."""

    queue_changed = pyqtSignal()
    download_started = pyqtSignal(int)  # download_id
    download_completed = pyqtSignal(int, str, int)  # download_id, filepath, size
    download_failed = pyqtSignal(int, str)  # download_id, error
    download_progress = pyqtSignal(int, int, int, float, float)  # id, downloaded, total, speed, eta
    download_status_changed = pyqtSignal(int, str)  # download_id, status
    download_filename_resolved = pyqtSignal(int, str, int)  # download_id, filename, size
    speed_update = pyqtSignal(int, float)  # download_id, speed_bps
    global_speed_update = pyqtSignal(float, float)  # total_down_speed, total_up_speed
    active_count_changed = pyqtSignal(int)  # count

    def __init__(self, db: DatabaseManager, max_concurrent: int = 5) -> None:
        super().__init__()
        self._db = db
        self._max_concurrent = max_concurrent
        self._mutex = QMutex()
        self._queue: list[DownloadItem] = []
        self._active: dict[int, DownloadItem] = {}
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(max_concurrent + 4)  # Extra threads for overhead
        self._paused_globally = False
        self._last_progress: dict[int, float] = {}

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        self._max_concurrent = max(1, min(value, 10))
        self._process_queue()

    def add_download(
        self,
        url: str,
        save_dir: str,
        filename: str = "",
        source_type: str = "http",
        platform: str = "",
        segment_count: int = 16,
        speed_limit: int = 0,
        user_agent: str = "",
        proxy: Optional[dict] = None,
        auto_start: bool = True,
    ) -> int:
        """Add a new download to the queue. Returns the download ID."""
        download_id = self._db.add_download(
            url=url,
            filename=filename or "Resolving...",
            filepath="",
            source_type=source_type,
            platform=platform,
            status="queued",
            segments=segment_count,
        )

        item = DownloadItem(
            download_id=download_id,
            url=url,
            save_dir=save_dir,
            filename=filename,
            source_type=source_type,
            platform=platform,
            segment_count=segment_count,
            speed_limit=speed_limit,
            user_agent=user_agent,
            proxy=proxy,
        )

        locker = QMutexLocker(self._mutex)
        self._queue.append(item)
        locker.unlock()

        logger.info("Download %d queued: %s", download_id, url)
        self.queue_changed.emit()

        if auto_start:
            self._process_queue()

        return download_id

    def apply_settings(
        self,
        max_concurrent: int = 5,
        global_speed_limit: int = 0,
    ) -> None:
        """Apply global queue and speed settings."""
        self.max_concurrent = max_concurrent
        # Speed limit is currently per-file in DownloadWorker, 
        # but could be implemented globally here if needed.
        # For now, we update max_concurrent which triggers queue processing.
        self._process_queue()

    def _process_queue(self) -> None:
        """Start downloads from the queue up to the concurrent limit."""
        if self._paused_globally:
            return

        locker = QMutexLocker(self._mutex)
        while len(self._active) < self._max_concurrent and self._queue:
            item = self._queue.pop(0)
            self._start_download(item)
        locker.unlock()
        self.active_count_changed.emit(len(self._active))

    def _start_download(self, item: DownloadItem) -> None:
        """Create and start a download worker for the given item."""
        worker = DownloadWorker(
            download_id=item.download_id,
            url=item.url,
            save_dir=item.save_dir,
            filename=item.filename,
            segment_count=item.segment_count,
            speed_limit=item.speed_limit,
            user_agent=item.user_agent or "",
            proxy=item.proxy,
        )

        worker.signals.progress.connect(self._on_progress)
        worker.signals.completed.connect(self._on_completed)
        worker.signals.failed.connect(self._on_failed)
        worker.signals.status_changed.connect(self._on_status_changed)
        worker.signals.filename_resolved.connect(self._on_filename_resolved)
        worker.signals.speed_update.connect(self._on_speed_update)

        item.worker = worker
        item.status = "downloading"
        self._active[item.download_id] = item

        self._db.update_download(item.download_id, status="downloading")
        self._thread_pool.start(worker)
        self.download_started.emit(item.download_id)
        logger.info("Download %d started", item.download_id)

    def _on_progress(self, download_id: int, downloaded: int, total: int, speed: float, eta: float) -> None:
        now = time.time()
        if now - self._last_progress.get(download_id, 0) < 0.1:  # 100ms throttle
            return
        self._last_progress[download_id] = now
        self.download_progress.emit(download_id, downloaded, total, speed, eta)

    def _on_completed(self, download_id: int, filepath: str, total_bytes: int) -> None:
        locker = QMutexLocker(self._mutex)
        item = self._active.pop(download_id, None)
        locker.unlock()

        if item:
            elapsed = 0
            avg_speed = total_bytes / max(elapsed, 1)
            self._db.complete_download(download_id, filepath, total_bytes, avg_speed)

        self.download_completed.emit(download_id, filepath, total_bytes)
        self.active_count_changed.emit(len(self._active))
        self._process_queue()
        logger.info("Download %d completed: %s", download_id, filepath)

    def _on_failed(self, download_id: int, error: str) -> None:
        locker = QMutexLocker(self._mutex)
        self._active.pop(download_id, None)
        locker.unlock()

        self._db.fail_download(download_id, error)
        self.download_failed.emit(download_id, error)
        self.active_count_changed.emit(len(self._active))
        self._process_queue()
        logger.error("Download %d failed: %s", download_id, error)

    def _on_status_changed(self, download_id: int, status: str) -> None:
        self.download_status_changed.emit(download_id, status)

    def _on_filename_resolved(self, download_id: int, filename: str, total_size: int) -> None:
        self._db.update_download(download_id, filename=filename, size_bytes=total_size)
        self.download_filename_resolved.emit(download_id, filename, total_size)

    def _on_speed_update(self, download_id: int, speed: float) -> None:
        self.speed_update.emit(download_id, speed)
        # Calculate global speed
        total_speed = sum(
            item.worker._calc_speed() if item.worker else 0
            for item in self._active.values()
        )
        self.global_speed_update.emit(total_speed, 0)

    def pause_download(self, download_id: int) -> None:
        """Pause a specific download."""
        locker = QMutexLocker(self._mutex)
        item = self._active.get(download_id)
        locker.unlock()

        if item and item.worker:
            item.worker.pause()
            item.status = "paused"
            self._db.update_download(download_id, status="paused")

    def resume_download(self, download_id: int) -> None:
        """Resume a specific download."""
        locker = QMutexLocker(self._mutex)
        item = self._active.get(download_id)
        locker.unlock()

        if item and item.worker:
            item.worker.resume()
            item.status = "downloading"
            self._db.update_download(download_id, status="downloading")

    def cancel_download(self, download_id: int) -> None:
        """Cancel a specific download."""
        locker = QMutexLocker(self._mutex)
        item = self._active.pop(download_id, None)

        if not item:
            self._queue = [q for q in self._queue if q.download_id != download_id]
            locker.unlock()
            self._db.update_download(download_id, status="cancelled")
            self.queue_changed.emit()
            return
        locker.unlock()

        if item.worker:
            item.worker.cancel()
        self._db.update_download(download_id, status="cancelled")
        self.active_count_changed.emit(len(self._active))
        self._process_queue()

    def pause_all(self) -> None:
        """Pause all active downloads."""
        self._paused_globally = True
        locker = QMutexLocker(self._mutex)
        for item in self._active.values():
            if item.worker:
                item.worker.pause()
                item.status = "paused"
        locker.unlock()

    def resume_all(self) -> None:
        """Resume all paused downloads."""
        self._paused_globally = False
        locker = QMutexLocker(self._mutex)
        for item in self._active.values():
            if item.worker and item.worker.is_paused:
                item.worker.resume()
                item.status = "downloading"
        locker.unlock()
        self._process_queue()

    def cancel_all(self) -> None:
        """Cancel all downloads."""
        locker = QMutexLocker(self._mutex)
        for item in list(self._active.values()):
            if item.worker:
                item.worker.cancel()
        self._active.clear()
        for item in self._queue:
            self._db.update_download(item.download_id, status="cancelled")
        self._queue.clear()
        locker.unlock()
        self.queue_changed.emit()
        self.active_count_changed.emit(0)

    def reorder_queue(self, download_ids: list[int]) -> None:
        """Reorder the queue based on a list of download IDs."""
        locker = QMutexLocker(self._mutex)
        id_to_item = {item.download_id: item for item in self._queue}
        new_queue = []
        for did in download_ids:
            if did in id_to_item:
                new_queue.append(id_to_item[did])
        for item in self._queue:
            if item.download_id not in download_ids:
                new_queue.append(item)
        self._queue = new_queue
        locker.unlock()
        self.queue_changed.emit()

    def get_queue_info(self) -> list[dict]:
        """Get info about queued items."""
        locker = QMutexLocker(self._mutex)
        result = [
            {"download_id": item.download_id, "url": item.url, "filename": item.filename, "status": item.status}
            for item in self._queue
        ]
        locker.unlock()
        return result

    def get_active_info(self) -> list[dict]:
        """Get info about active downloads."""
        locker = QMutexLocker(self._mutex)
        result = [
            {"download_id": item.download_id, "url": item.url, "filename": item.filename, "status": item.status}
            for item in self._active.values()
        ]
        locker.unlock()
        return result

    def get_active_count(self) -> int:
        return len(self._active)

    def get_queued_count(self) -> int:
        return len(self._queue)

    def shutdown(self) -> None:
        """Gracefully shut down: cancel all and wait for thread pool."""
        self.cancel_all()
        self._thread_pool.waitForDone(5000)
        logger.info("Queue manager shut down.")
