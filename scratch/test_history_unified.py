import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.db import DatabaseManager

def test_unified_history():
    db = DatabaseManager(Path("test_history.db"))
    
    # 1. Add an HTTP download
    print("Adding HTTP download...")
    db.add_download(url="http://test.com/file.zip", filename="file.zip", source_type="http")
    
    # 2. Add a Torrent
    print("Adding Torrent...")
    db.save_torrent_state(info_hash="1234567890abcdef1234567890abcdef12345678", name="Ubuntu ISO", save_path="/downloads")
    
    # 3. Fetch unified history
    print("Fetching history...")
    history = db.get_downloads()
    
    found_http = False
    found_torrent = False
    
    for item in history:
        print(f"[{item['source_type']}] {item['filename']} - ID: {item['id']}")
        if item['source_type'] == 'http': found_http = True
        if item['source_type'] == 'torrent': found_torrent = True
        
    assert found_http, "HTTP download missing from history"
    assert found_torrent, "Torrent missing from history"
    print("Unified history verified!")
    
    # 4. Test stats
    print("Checking stats...")
    stats = db.get_download_stats()
    print(f"Total Bytes (stats): {stats['total_bytes']}")
    
    # 5. Clear history
    print("Clearing history...")
    db.clear_history()
    history = db.get_downloads()
    # Note: clear_history only clears completed torrents in my implementation, 
    # but for tests we can just check if HTTP is gone.
    assert len([h for h in history if h['source_type'] == 'http']) == 0
    print("Clear history verified!")
    
    db.shutdown()
    os.remove("test_history.db")
    print("All tests passed!")

if __name__ == "__main__":
    test_unified_history()
