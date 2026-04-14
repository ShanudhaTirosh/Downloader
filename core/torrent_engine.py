"""
ShanuFx Downloader — libtorrent wrapper for torrent downloads.
Gracefully handles missing libtorrent with a fallback flag.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

if TYPE_CHECKING:
    from core.db import DatabaseManager

logger = logging.getLogger(__name__)

try:
    import libtorrent as lt

    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
    lt = None  # type: ignore
    logger.warning("libtorrent not installed — torrent features disabled")


class TorrentInfo:
    """Parsed torrent metadata for display."""

    def __init__(self) -> None:
        self.name: str = ""
        self.info_hash: str = ""
        self.total_size: int = 0
        self.file_count: int = 0
        self.files: list[dict[str, Any]] = []
        self.comment: str = ""
        self.creator: str = ""
        self.creation_date: str = ""
        self.is_magnet: bool = False


class TorrentStatus:
    """Live status snapshot of an active torrent."""

    def __init__(self) -> None:
        self.info_hash: str = ""
        self.name: str = ""
        self.progress: float = 0.0
        self.download_rate: float = 0.0
        self.upload_rate: float = 0.0
        self.total_downloaded: int = 0
        self.total_uploaded: int = 0
        self.total_size: int = 0
        self.num_seeds: int = 0
        self.num_seeds_total: int = 0
        self.num_peers: int = 0
        self.num_peers_total: int = 0
        self.eta_seconds: float = 0
        self.elapsed_seconds: float = 0
        self.share_ratio: float = 0.0
        self.state: str = "unknown"
        self.pieces_have: int = 0
        self.pieces_total: int = 0
        self.sequential: bool = False
        self.save_path: str = ""

    @staticmethod
    def state_to_string(state_val: int) -> str:
        """Convert libtorrent state enum to string."""
        states = {
            0: "queued",
            1: "checking_files",
            2: "downloading_metadata",
            3: "downloading",
            4: "finished",
            5: "seeding",
            6: "allocating",
            7: "checking_resume",
        }
        return states.get(state_val, "unknown")


class PeerInfo:
    """Info about a single peer."""

    def __init__(self) -> None:
        self.ip: str = ""
        self.port: int = 0
        self.client: str = ""
        self.down_speed: float = 0.0
        self.up_speed: float = 0.0
        self.country: str = ""
        self.progress: float = 0.0
        self.flags: str = ""


class TorrentEngine(QObject):
    """Manages libtorrent session and active torrents."""

    torrent_added = pyqtSignal(str, str)  # info_hash, name
    torrent_removed = pyqtSignal(str)  # info_hash
    torrent_status_update = pyqtSignal(object)  # TorrentStatus
    torrent_complete = pyqtSignal(str, str)  # info_hash, name
    torrent_error = pyqtSignal(str, str)  # info_hash, error
    torrent_metadata_received = pyqtSignal(str, object)  # info_hash, TorrentInfo
    peers_updated = pyqtSignal(str, list)  # info_hash, list[PeerInfo]
    all_status_update = pyqtSignal(list)  # list[TorrentStatus]

    def __init__(self, db: Optional["DatabaseManager"] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._session: Any = None
        self._handles: dict[str, Any] = {}
        self._start_times: dict[str, float] = {}
        self._poll_timer: Optional[QTimer] = None
        self._initialized = False

        if LIBTORRENT_AVAILABLE:
            self._init_session()
            if self._db:
                QTimer.singleShot(500, self.load_from_db)

    def _init_session(self) -> None:
        """Initialize the libtorrent session with default settings."""
        if not LIBTORRENT_AVAILABLE:
            return

        settings = {
            "user_agent": "ShanuFxDownloader/2.0",
            "listen_interfaces": "0.0.0.0:6881,[::]:6881",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "alert_mask": (
                lt.alert.category_t.status_notification
                | lt.alert.category_t.error_notification
                | lt.alert.category_t.storage_notification
                | lt.alert.category_t.peer_notification
            ),
        }

        self._session = lt.session(settings)
        self._initialized = True

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_alerts)
        self._poll_timer.start(100)

        logger.info("libtorrent session initialized (v%s)", lt.version)

    def load_from_db(self) -> None:
        """Restore torrents from database."""
        if not self._session or not self._db:
            return

        states = self._db.get_torrent_states()
        for state in states:
            info_hash = state["info_hash"]
            if info_hash in self._handles:
                continue

            try:
                params = {}
                if state["resume_data"]:
                    params = lt.read_resume_data(state["resume_data"])
                
                params["save_path"] = state["save_path"]
                
                # If we don't have a .torrent file, we'll need to metadata from DHT/Peers
                # libtorrent handles this if we add via magnet or with info_hash
                if not state["resume_data"]:
                    # Fallback to magnet-like add if no resume data
                    params["info_hash"] = lt.sha1_hash(bytes.fromhex(info_hash))
                
                handle = self._session.add_torrent(params)
                self._handles[info_hash] = handle
                self._start_times[info_hash] = time.time()
                
                if state["file_priorities"]:
                    import json
                    try:
                        priorities = json.loads(state["file_priorities"])
                        if priorities:
                            handle.prioritize_files(priorities)
                    except Exception:
                        pass
                
                if state["status"] == "paused":
                    handle.pause()
                
                self.torrent_added.emit(info_hash, state["name"])
                logger.info("Restored torrent from DB: %s (%s)", state["name"], info_hash)

            except Exception as e:
                logger.error("Failed to restore torrent %s: %s", info_hash, e)

    @property
    def is_available(self) -> bool:
        return LIBTORRENT_AVAILABLE and self._initialized

    def apply_settings(
        self,
        max_download_speed: int = 0,
        max_upload_speed: int = 0,
        max_connections: int = 200,
        dht_enabled: bool = True,
        pex_enabled: bool = True,
        lsd_enabled: bool = True,
        port_start: int = 6881,
        port_end: int = 6889,
        encryption: str = "enabled",
    ) -> None:
        """Apply torrent settings to the session."""
        if not self._session:
            return

        s = self._session.get_settings()
        s["download_rate_limit"] = max_download_speed * 1024 if max_download_speed > 0 else 0
        s["upload_rate_limit"] = max_upload_speed * 1024 if max_upload_speed > 0 else 0
        s["connections_limit"] = max_connections
        s["enable_dht"] = dht_enabled
        s["enable_lsd"] = lsd_enabled
        
        # PEX is set on the handle generally, but session-level exists in some plugins
        # In modern lt, we use set_alert_mask and other features for fine control.
        
        s["listen_interfaces"] = f"0.0.0.0:{port_start},[::]{port_start}"

        enc_map = {
            "enabled": (lt.enc_policy.pe_enabled, lt.enc_level.pe_both),
            "forced": (lt.enc_policy.pe_forced, lt.enc_level.pe_rc4),
            "disabled": (lt.enc_policy.pe_disabled, lt.enc_level.pe_plaintext),
        }
        if encryption in enc_map:
            policy, level = enc_map[encryption]
            s["out_enc_policy"] = policy
            s["in_enc_policy"] = policy
            s["allowed_enc_level"] = level

        self._session.apply_settings(s)
        logger.info("Torrent settings applied")

    def add_torrent_file(self, torrent_path: str, save_path: str, file_priorities: Optional[list[int]] = None) -> Optional[str]:
        """Add a torrent from a .torrent file."""
        if not self._session:
            return None

        try:
            ti = lt.torrent_info(torrent_path)
            params = {
                "ti": ti,
                "save_path": save_path,
            }
            if file_priorities:
                params["file_priorities"] = file_priorities

            handle = self._session.add_torrent(params)
            info_hash = str(handle.info_hash())
            self._handles[info_hash] = handle
            self._start_times[info_hash] = time.time()

            if self._db:
                self._db.save_torrent_state(
                    info_hash=info_hash,
                    name=ti.name(),
                    save_path=save_path,
                    total_size=ti.total_size(),
                    status="downloading",
                    file_priorities=file_priorities
                )

            self.torrent_added.emit(info_hash, ti.name())
            logger.info("Torrent added: %s (%s)", ti.name(), info_hash)
            return info_hash

        except Exception as e:
            logger.error("Failed to add torrent file: %s", e)
            self.torrent_error.emit("", str(e))
            return None

    def add_magnet(self, magnet_uri: str, save_path: str) -> Optional[str]:
        """Add a torrent from a magnet link."""
        if not self._session:
            return None

        try:
            params = lt.parse_magnet_uri(magnet_uri)
            params.save_path = save_path
            handle = self._session.add_torrent(params)
            info_hash = str(handle.info_hash())
            self._handles[info_hash] = handle
            self._start_times[info_hash] = time.time()

            if self._db:
                self._db.save_torrent_state(
                    info_hash=info_hash,
                    name=f"Magnet: {info_hash[:16]}",
                    save_path=save_path,
                    status="downloading"
                )

            self.torrent_added.emit(info_hash, f"Magnet: {info_hash[:16]}...")
            logger.info("Magnet added: %s", info_hash)
            return info_hash

        except Exception as e:
            logger.error("Failed to add magnet: %s", e)
            self.torrent_error.emit("", str(e))
            return None

    def get_torrent_info(self, torrent_path: str) -> Optional[TorrentInfo]:
        """Parse a .torrent file and return metadata (without adding)."""
        if not LIBTORRENT_AVAILABLE:
            return None

        try:
            ti = lt.torrent_info(torrent_path)
            info = TorrentInfo()
            info.name = ti.name()
            info.info_hash = str(ti.info_hash())
            info.total_size = ti.total_size()
            info.file_count = ti.num_files()
            info.comment = ti.comment()
            info.creator = ti.creator()

            fs = ti.files()
            for i in range(fs.num_files()):
                info.files.append({
                    "index": i,
                    "path": fs.file_path(i),
                    "size": fs.file_size(i),
                    "name": Path(fs.file_path(i)).name,
                })

            return info

        except Exception as e:
            logger.error("Failed to parse torrent: %s", e)
            return None

    def get_status(self, info_hash: str) -> Optional[TorrentStatus]:
        """Get current status of a torrent."""
        handle = self._handles.get(info_hash)
        if not handle:
            return None

        try:
            s = handle.status()
            status = TorrentStatus()
            status.info_hash = info_hash
            status.name = s.name if s.name else info_hash[:16]
            status.progress = s.progress * 100
            status.download_rate = s.download_rate
            status.upload_rate = s.upload_rate
            status.total_downloaded = s.total_done
            status.total_uploaded = s.total_upload
            status.total_size = s.total_wanted
            status.num_seeds = s.num_seeds
            status.num_peers = s.num_peers
            status.state = TorrentStatus.state_to_string(int(s.state))
            status.save_path = s.save_path

            if s.total_done > 0:
                status.share_ratio = s.total_upload / s.total_done
            if s.download_rate > 0:
                remaining = s.total_wanted - s.total_done
                status.eta_seconds = remaining / s.download_rate

            start = self._start_times.get(info_hash, time.time())
            status.elapsed_seconds = time.time() - start
            
            # Check for sequential download flag (libtorrent 2.0+ uses flags)
            try:
                status.sequential = bool(s.flags & lt.torrent_flags.sequential_download)
            except Exception:
                status.sequential = False

            ti = handle.torrent_file()
            if ti:
                status.pieces_total = ti.num_pieces()
                status.pieces_have = s.num_pieces

            return status

        except Exception as e:
            logger.error("Failed to get torrent status: %s", e)
            return None

    def get_peers(self, info_hash: str) -> list[PeerInfo]:
        """Get peer list for a torrent."""
        handle = self._handles.get(info_hash)
        if not handle:
            return []

        try:
            peers = handle.get_peer_info()
            result: list[PeerInfo] = []
            for p in peers:
                pi = PeerInfo()
                pi.ip = p.ip[0] if isinstance(p.ip, tuple) else str(p.ip)
                pi.port = p.ip[1] if isinstance(p.ip, tuple) else 0
                pi.client = str(p.client)
                pi.down_speed = p.down_speed
                pi.up_speed = p.up_speed
                pi.progress = p.progress * 100
                result.append(pi)
            return result

        except Exception as e:
            logger.error("Failed to get peers: %s", e)
            return []

    def pause_torrent(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.pause()

    def resume_torrent(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.resume()

    def remove_torrent(self, info_hash: str, delete_files: bool = False) -> None:
        handle = self._handles.get(info_hash)
        if handle and self._session:
            option = lt.options_t.delete_files if delete_files else 0
            self._session.remove_torrent(handle, option)
            self._handles.pop(info_hash, None)
            self._start_times.pop(info_hash, None)
            
            if self._db:
                self._db.delete_torrent_state(info_hash)
                
            self.torrent_removed.emit(info_hash)

    def force_recheck(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.force_recheck()

    def force_reannounce(self, info_hash: str) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.force_reannounce()

    def set_sequential(self, info_hash: str, sequential: bool) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.set_sequential_download(sequential)

    def get_magnet_uri(self, info_hash: str) -> str:
        handle = self._handles.get(info_hash)
        if handle and LIBTORRENT_AVAILABLE:
            return lt.make_magnet_uri(handle)
        return ""

    def set_file_priorities(self, info_hash: str, priorities: list[int]) -> None:
        handle = self._handles.get(info_hash)
        if handle:
            handle.prioritize_files(priorities)

    def _poll_alerts(self) -> None:
        """Poll libtorrent alerts and emit signals."""
        if not self._session:
            return

        alerts = self._session.pop_alerts()
        for alert in alerts:
            alert_type = type(alert).__name__

            if alert_type == "torrent_finished_alert":
                info_hash = str(alert.handle.info_hash())
                name = alert.handle.status().name
                self.torrent_complete.emit(info_hash, name)

            elif alert_type == "metadata_received_alert":
                handle = alert.handle
                info_hash = str(handle.info_hash())
                ti = handle.torrent_file()
                if ti:
                    info = TorrentInfo()
                    info.name = ti.name()
                    info.info_hash = info_hash
                    info.total_size = ti.total_size()
                    info.file_count = ti.num_files()
                    fs = ti.files()
                    for i in range(fs.num_files()):
                        info.files.append({
                            "index": i,
                            "path": fs.file_path(i),
                            "size": fs.file_size(i),
                            "name": Path(fs.file_path(i)).name,
                        })

                    if self._db:
                        # Update name in DB now that we have metadata
                        self._db.save_torrent_state(
                            info_hash=info_hash,
                            name=info.name,
                            save_path=handle.status().save_path,
                            total_size=info.total_size,
                            status=TorrentStatus.state_to_string(int(handle.status().state))
                        )

                    self.torrent_metadata_received.emit(info_hash, info)

            elif "error" in alert_type.lower():
                msg = str(alert.message()) if hasattr(alert, "message") else str(alert)
                info_hash = ""
                if hasattr(alert, "handle"):
                    try:
                        info_hash = str(alert.handle.info_hash())
                    except Exception:
                        pass
                self.torrent_error.emit(info_hash, msg)

        all_statuses: list[TorrentStatus] = []
        for ih in list(self._handles.keys()):
            s = self.get_status(ih)
            if s:
                all_statuses.append(s)
                self.torrent_status_update.emit(s)
        if all_statuses:
            self.all_status_update.emit(all_statuses)
            
        # Periodically save resume data (every ~30 seconds)
        if hasattr(self, "_last_save_time"):
            if time.time() - self._last_save_time > 30:
                self.save_all_resume_data()
                self._last_save_time = time.time()
        else:
            self._last_save_time = time.time()

    def save_all_resume_data(self) -> None:
        """Trigger save_resume_data for all torrents."""
        if not self._session:
            return
        for handle in self._handles.values():
            if handle.is_valid():
                handle.save_resume_data()

    def get_session_stats(self) -> dict[str, float]:
        """Get global session download/upload rates."""
        if not self._session:
            return {"download_rate": 0, "upload_rate": 0}
        status = self._session.status()
        return {
            "download_rate": status.download_rate,
            "upload_rate": status.upload_rate,
        }

    def save_resume_data(self) -> dict[str, bytes]:
        """Save resume data for all torrents."""
        result: dict[str, bytes] = {}
        if not self._session:
            return result

        for info_hash, handle in self._handles.items():
            try:
                handle.save_resume_data()
            except Exception:
                pass

        time.sleep(0.5)

        alerts = self._session.pop_alerts()
        for alert in alerts:
            if type(alert).__name__ == "save_resume_data_alert":
                info_hash = str(alert.handle.info_hash())
                try:
                    data = lt.write_resume_data_buf(alert.params)
                    result[info_hash] = data
                    if self._db:
                        self._db.update_torrent_resume_data(info_hash, data)
                except Exception as e:
                    logger.error("Failed to write resume data: %s", e)

        return result

    def shutdown(self) -> None:
        """Gracefully shut down the torrent engine."""
        if self._poll_timer:
            self._poll_timer.stop()

        if self._session:
            resume_data = self.save_resume_data()
            for info_hash, handle in list(self._handles.items()):
                try:
                    handle.pause()
                except Exception:
                    pass
            self._handles.clear()
            logger.info("Torrent engine shut down (%d resume data saved)", len(resume_data))

        self._initialized = False
