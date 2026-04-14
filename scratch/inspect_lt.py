import libtorrent as lt
import time

def inspect_libtorrent():
    ses = lt.session()
    # Create a dummy torrent to get a handle
    params = {
        'save_path': '.',
        'info_hash': b'12345678901234567890'
    }
    handle = ses.add_torrent(params)
    print(f"Handle type: {type(handle)}")
    print(f"Has is_sequential_download: {hasattr(handle, 'is_sequential_download')}")
    print(f"Has set_sequential_download: {hasattr(handle, 'set_sequential_download')}")
    
    status = handle.status()
    print(f"Status type: {type(status)}")
    if hasattr(status, 'flags'):
        print(f"Status flags: {status.flags}")
        # Check if sequential_download is a flag
        try:
            from libtorrent import torrent_flags
            print(f"Sequential flag: {torrent_flags.sequential_download}")
            is_seq = bool(status.flags & torrent_flags.sequential_download)
            print(f"Is sequential (via flags): {is_seq}")
        except ImportError:
            print("Could not import torrent_flags")
        except Exception as e:
            print(f"Error checking flags: {e}")

if __name__ == "__main__":
    inspect_libtorrent()
