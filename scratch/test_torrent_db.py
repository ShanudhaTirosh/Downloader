import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.db import DatabaseManager

def test_torrent_db():
    db = DatabaseManager(Path("test_downloader.db"))
    info_hash = "abcdef1234567890abcdef1234567890abcdef12"
    name = "Test Torrent"
    save_path = "C:/Downloads/Test"
    
    print("Saving torrent state...")
    db.save_torrent_state(info_hash, name, save_path, total_size=1024, status="downloading")
    
    print("Retrieving torrent states...")
    states = db.get_torrent_states()
    for s in states:
        print(f"Found: {s['name']} ({s['info_hash']}) - {s['status']}")
        assert s['info_hash'] == info_hash
        assert s['name'] == name
    
    print("Updating resume data...")
    dummy_resume = b"dummy resume data"
    db.update_torrent_resume_data(info_hash, dummy_resume)
    
    states = db.get_torrent_states()
    assert states[0]['resume_data'] == dummy_resume
    print("Resume data updated successfully.")
    
    print("Deleting torrent state...")
    db.delete_torrent_state(info_hash)
    states = db.get_torrent_states()
    assert len(states) == 0
    print("Torrent state deleted successfully.")
    
    db.shutdown()
    os.remove("test_downloader.db")
    print("Test passed!")

if __name__ == "__main__":
    test_torrent_db()
