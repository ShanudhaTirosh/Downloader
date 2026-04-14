"""
ShanuFx Downloader — FFmpeg post-processing & audio conversion.
Uses QProcess for non-blocking execution.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from config import FFMPEG_PATH, detect_executable

logger = logging.getLogger(__name__)

try:
    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, ID3NoHeaderError
    from mutagen.mp3 import MP3

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("mutagen not installed — audio tagging disabled")


class ConversionWorker(QObject):
    """Non-blocking FFmpeg process wrapper."""

    progress = pyqtSignal(int, float)  # task_id, percentage
    completed = pyqtSignal(int, str)  # task_id, output_path
    failed = pyqtSignal(int, str)  # task_id, error
    status_update = pyqtSignal(int, str)  # task_id, status_text

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._processes: dict[int, QProcess] = {}
        self._task_data: dict[int, dict] = {}
        self._next_id: int = 0
        self._ffmpeg_path: str = FFMPEG_PATH or detect_executable("ffmpeg")

    @property
    def ffmpeg_available(self) -> bool:
        return bool(self._ffmpeg_path)

    def set_ffmpeg_path(self, path: str) -> None:
        self._ffmpeg_path = path

    def merge_video_audio(
        self, video_path: str, audio_path: str, output_path: str, duration: float = 0
    ) -> int:
        """Merge separate video and audio streams into a single file."""
        task_id = self._next_id
        self._next_id += 1

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            "-y",
            output_path,
        ]

        self._task_data[task_id] = {
            "type": "merge",
            "output": output_path,
            "duration": duration,
            "video_path": video_path,
            "audio_path": audio_path,
        }

        self._start_process(task_id, args)
        return task_id

    def convert_audio(
        self,
        input_path: str,
        output_path: str,
        codec: str = "mp3",
        bitrate: str = "320k",
        duration: float = 0,
    ) -> int:
        """Convert audio to specified format."""
        task_id = self._next_id
        self._next_id += 1

        codec_map = {
            "mp3": ("-c:a", "libmp3lame"),
            "aac": ("-c:a", "aac"),
            "flac": ("-c:a", "flac"),
            "wav": ("-c:a", "pcm_s16le"),
            "ogg": ("-c:a", "libvorbis"),
            "vorbis": ("-c:a", "libvorbis"),
            "opus": ("-c:a", "libopus"),
        }

        codec_flag, codec_value = codec_map.get(codec, ("-c:a", "libmp3lame"))

        args = [
            "-i", input_path,
            codec_flag, codec_value,
        ]

        if codec not in ("flac", "wav"):
            args.extend(["-b:a", bitrate])

        args.extend(["-y", output_path])

        self._task_data[task_id] = {
            "type": "convert",
            "output": output_path,
            "duration": duration,
            "input_path": input_path,
        }

        self._start_process(task_id, args)
        return task_id

    def extract_audio(self, video_path: str, output_path: str, duration: float = 0) -> int:
        """Extract audio from a video file."""
        task_id = self._next_id
        self._next_id += 1

        args = [
            "-i", video_path,
            "-vn",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        self._task_data[task_id] = {
            "type": "extract_audio",
            "output": output_path,
            "duration": duration,
        }

        self._start_process(task_id, args)
        return task_id

    def _start_process(self, task_id: int, args: list[str]) -> None:
        """Start an FFmpeg QProcess."""
        if not self._ffmpeg_path:
            self.failed.emit(task_id, "FFmpeg not found. Please install FFmpeg or set the path in Settings.")
            return

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        process.readyReadStandardOutput.connect(lambda: self._on_output(task_id))
        process.finished.connect(lambda code, status: self._on_finished(task_id, code, status))
        process.errorOccurred.connect(lambda err: self._on_error(task_id, err))

        self._processes[task_id] = process
        self.status_update.emit(task_id, "Processing...")

        full_args = ["-progress", "pipe:1", "-nostats"] + args
        process.start(self._ffmpeg_path, full_args)
        logger.info("FFmpeg task %d started: %s", task_id, " ".join(args[:6]))

    def _on_output(self, task_id: int) -> None:
        """Parse FFmpeg progress output."""
        process = self._processes.get(task_id)
        if not process:
            return

        data = process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        task = self._task_data.get(task_id, {})
        duration = task.get("duration", 0)

        time_match = re.search(r"out_time_us=(\d+)", data)
        if time_match and duration > 0:
            current_us = int(time_match.group(1))
            current_s = current_us / 1_000_000
            pct = min((current_s / duration) * 100, 99.0)
            self.progress.emit(task_id, pct)

    def _on_finished(self, task_id: int, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle FFmpeg process completion."""
        self._processes.pop(task_id, None)
        task = self._task_data.pop(task_id, {})
        output_path = task.get("output", "")

        if exit_code == 0 and os.path.exists(output_path):
            self.progress.emit(task_id, 100.0)
            self.completed.emit(task_id, output_path)
            logger.info("FFmpeg task %d completed: %s", task_id, output_path)

            if task.get("type") == "merge":
                for key in ("video_path", "audio_path"):
                    temp = task.get(key, "")
                    if temp and os.path.exists(temp) and temp != output_path:
                        try:
                            os.remove(temp)
                        except OSError:
                            pass
        else:
            self.failed.emit(task_id, f"FFmpeg exited with code {exit_code}")

    def _on_error(self, task_id: int, error: QProcess.ProcessError) -> None:
        """Handle FFmpeg process errors."""
        error_messages = {
            QProcess.ProcessError.FailedToStart: "FFmpeg failed to start",
            QProcess.ProcessError.Crashed: "FFmpeg crashed",
            QProcess.ProcessError.Timedout: "FFmpeg timed out",
            QProcess.ProcessError.WriteError: "Write error to FFmpeg",
            QProcess.ProcessError.ReadError: "Read error from FFmpeg",
            QProcess.ProcessError.UnknownError: "Unknown FFmpeg error",
        }
        msg = error_messages.get(error, "Unknown error")
        self._processes.pop(task_id, None)
        self._task_data.pop(task_id, None)
        self.failed.emit(task_id, msg)
        logger.error("FFmpeg task %d error: %s", task_id, msg)

    def cancel_task(self, task_id: int) -> None:
        process = self._processes.get(task_id)
        if process and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()
            self._processes.pop(task_id, None)
            self._task_data.pop(task_id, None)

    def shutdown(self) -> None:
        for task_id, process in list(self._processes.items()):
            if process.state() != QProcess.ProcessState.NotRunning:
                process.kill()
                process.waitForFinished(2000)
        self._processes.clear()
        self._task_data.clear()


def embed_thumbnail_in_mp3(mp3_path: str, image_path: str) -> bool:
    """Embed a thumbnail image into an MP3 file's ID3 tags."""
    if not MUTAGEN_AVAILABLE:
        logger.warning("mutagen not available, cannot embed thumbnail")
        return False

    try:
        try:
            audio = ID3(mp3_path)
        except ID3NoHeaderError:
            audio = ID3()

        with open(image_path, "rb") as img_f:
            image_data = img_f.read()

        mime = "image/jpeg"
        if image_path.lower().endswith(".png"):
            mime = "image/png"
        elif image_path.lower().endswith(".webp"):
            mime = "image/webp"

        audio.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image_data))
        audio.save(mp3_path)
        logger.info("Thumbnail embedded in %s", mp3_path)
        return True

    except Exception as e:
        logger.error("Failed to embed thumbnail: %s", e)
        return False


def tag_audio_metadata(
    mp3_path: str,
    title: str = "",
    artist: str = "",
    album: str = "",
    year: str = "",
) -> bool:
    """Write ID3 metadata tags to an MP3 file."""
    if not MUTAGEN_AVAILABLE:
        return False

    try:
        try:
            audio = ID3(mp3_path)
        except ID3NoHeaderError:
            audio = ID3()

        if title:
            audio.add(TIT2(encoding=3, text=title))
        if artist:
            audio.add(TPE1(encoding=3, text=artist))
        if album:
            audio.add(TALB(encoding=3, text=album))
        if year:
            audio.add(TDRC(encoding=3, text=year))

        audio.save(mp3_path)
        logger.info("Audio metadata tagged: %s", mp3_path)
        return True

    except Exception as e:
        logger.error("Failed to tag metadata: %s", e)
        return False
