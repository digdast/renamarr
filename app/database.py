import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(r"C:\scripts\renamarr\data", "renamarr.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    
    # Default settings
    defaults = {
        "movie_template": "{title} ({year}) [{resolution}]",
        "tv_template": "{show} - S{season:02d}E{episode:02d} - {title} [{resolution}]",
        "organize_folders": "true",
        "dry_run": "false",
        "last_scan_path": "C:\\Media"
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);", (k, v))
        
    # 2. Metadata Cache Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metadata_cache (
        cache_key TEXT PRIMARY KEY,
        media_type TEXT,
        data_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. Rename History Table (Undo Ledger)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rename_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id TEXT,
        original_path TEXT,
        new_path TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reverted INTEGER DEFAULT 0
    );
    """)
    
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, str(value)))
    conn.commit()
    conn.close()

def get_cached_metadata(cache_key):
    conn = get_connection()
    row = conn.execute("SELECT data_json FROM metadata_cache WHERE cache_key = ?;", (cache_key.lower().strip(),)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["data_json"])
        except:
            return None
    return None

def set_cached_metadata(cache_key, media_type, data):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO metadata_cache (cache_key, media_type, data_json) VALUES (?, ?, ?);",
        (cache_key.lower().strip(), media_type, json.dumps(data))
    )
    conn.commit()
    conn.close()

def log_rename_batch(batch_id, items):
    conn = get_connection()
    for item in items:
        conn.execute(
            "INSERT INTO rename_history (batch_id, original_path, new_path) VALUES (?, ?, ?);",
            (batch_id, item["original_path"], item["new_path"])
        )
    conn.commit()
    conn.close()

def get_latest_batch():
    conn = get_connection()
    row = conn.execute("SELECT batch_id, COUNT(*) as count, MAX(timestamp) as ts FROM rename_history WHERE reverted = 0 GROUP BY batch_id ORDER BY id DESC LIMIT 1;").fetchone()
    conn.close()
    return dict(row) if row else None

def mark_batch_reverted(batch_id):
    conn = get_connection()
    conn.execute("UPDATE rename_history SET reverted = 1 WHERE batch_id = ?;", (batch_id,))
    conn.commit()
    conn.close()

# Auto initialize
init_db()
