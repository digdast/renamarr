import os
import shutil
import uuid
import string
import logging
from app.parser import parse_media_filename, VIDEO_EXTENSIONS
from app.metadata import resolve_metadata_for_parsed
from app.database import log_rename_batch, get_latest_batch, mark_batch_reverted, get_connection

logger = logging.getLogger("renamarr.renamer")

def sanitize_filename(name):
    # Remove characters forbidden in Windows and Linux filenames: < > : " / \ | ? *
    clean = re.sub(r'[<>:"/\\|?*]', '', name)
    return clean.strip()

import re

def build_target_filename(parsed, metadata, movie_template, tv_template):
    is_tv = parsed["is_tv"]
    ext = parsed["extension"]
    best = metadata.get("best_match")
    
    title = best["title"] if best else parsed["raw_title"]
    year = best.get("year") or parsed.get("year") or ""
    resolution = parsed.get("resolution") or ""
    codec = parsed.get("codec") or ""
    
    if is_tv:
        season = parsed.get("season", 1)
        episode = parsed.get("episode", 1)
        ep_title = metadata.get("episode_title") or f"Episode {episode}"
        
        # Render template
        try:
            filename = tv_template.format(
                show=title,
                season=season,
                episode=episode,
                title=ep_title,
                resolution=resolution,
                codec=codec,
                year=year
            )
        except Exception:
            filename = f"{title} - S{season:02d}E{episode:02d} - {ep_title}"
            if resolution:
                filename += f" [{resolution}]"
    else:
        try:
            filename = movie_template.format(
                title=title,
                year=year,
                resolution=resolution,
                codec=codec
            )
        except Exception:
            filename = f"{title}"
            if year:
                filename += f" ({year})"
            if resolution:
                filename += f" [{resolution}]"
                
    # Clean brackets if resolution is empty
    filename = filename.replace(" []", "").replace(" ()", "")
    filename = sanitize_filename(filename) + ext
    return filename

def build_target_directory(root_dir, parsed, metadata, organize_folders):
    if not organize_folders:
        return os.path.dirname(parsed["filepath"])
        
    best = metadata.get("best_match")
    title = sanitize_filename(best["title"] if best else parsed["raw_title"])
    year = best.get("year") or parsed.get("year") or ""
    is_tv = parsed["is_tv"]
    
    if is_tv:
        season = parsed.get("season", 1)
        # Plex standard: TV Shows/Show Name/Season 01/
        folder = os.path.join(root_dir, title, f"Season {season:02d}")
    else:
        # Plex standard: Movies/Movie Name (Year)/
        folder_name = f"{title} ({year})" if year else title
        folder = os.path.join(root_dir, folder_name)
        
    return folder

def scan_path(target_path, recursive=True, movie_template=None, tv_template=None, organize_folders=True):
    norm_path = os.path.abspath(target_path)
    if not os.path.exists(norm_path):
        raise ValueError(f"Directory does not exist or is not reachable: {norm_path}")

    if not movie_template:
        movie_template = "{title} ({year}) [{resolution}]"
    if not tv_template:
        tv_template = "{show} - S{season:02d}E{episode:02d} - {title} [{resolution}]"

    items = []
    
    if recursive:
        for root, _, files in os.walk(norm_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    items.append(os.path.join(root, f))
    else:
        for f in os.listdir(norm_path):
            p = os.path.join(norm_path, f)
            if os.path.isfile(p):
                ext = os.path.splitext(f)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    items.append(p)

    results = []
    for filepath in items:
        try:
            file_size_bytes = os.path.getsize(filepath)
            size_mb = round(file_size_bytes / (1024 * 1024), 1)
            size_str = f"{round(size_mb / 1024, 2)} GB" if size_mb >= 1000 else f"{size_mb} MB"
        except:
            size_str = "Unknown"

        parsed = parse_media_filename(filepath)
        if not parsed:
            continue
            
        metadata = resolve_metadata_for_parsed(parsed)
        target_filename = build_target_filename(parsed, metadata, movie_template, tv_template)
        target_dir = build_target_directory(norm_path, parsed, metadata, organize_folders)
        target_filepath = os.path.join(target_dir, target_filename)

        # Check if already compliant
        is_already_named = (os.path.normpath(filepath).lower() == os.path.normpath(target_filepath).lower())

        results.append({
            "id": str(uuid.uuid4())[:8],
            "original_path": filepath,
            "original_filename": parsed["filename"],
            "extension": parsed["extension"],
            "file_size": size_str,
            "is_tv": parsed["is_tv"],
            "media_type": "TV Series" if parsed["is_tv"] else "Movie",
            "detected_title": parsed["raw_title"],
            "season": parsed["season"],
            "episode": parsed["episode"],
            "resolution": parsed["resolution"] or "Standard",
            "codec": parsed["codec"] or "",
            "imdb_id": metadata["best_match"]["imdb_id"] if metadata["best_match"] else None,
            "matched_title": metadata["best_match"]["title"] if metadata["best_match"] else parsed["raw_title"],
            "matched_year": metadata["best_match"]["year"] if metadata["best_match"] else parsed["year"],
            "poster": metadata["best_match"]["poster"] if metadata["best_match"] else None,
            "episode_title": metadata.get("episode_title"),
            "target_dir": target_dir,
            "target_filename": target_filename,
            "target_path": target_filepath,
            "is_already_named": is_already_named,
            "selected": not is_already_named
        })

    return results

def execute_renames(items, dry_run=False):
    batch_id = str(uuid.uuid4())[:8]
    renamed_items = []
    errors = []

    for item in items:
        orig = item["original_path"]
        target = item["target_path"]
        
        if os.path.normpath(orig) == os.path.normpath(target):
            continue

        if dry_run:
            renamed_items.append({
                "original_path": orig,
                "new_path": target,
                "status": "Dry-run success"
            })
            continue

        try:
            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)
            
            # Atomic rename / move
            shutil.move(orig, target)
            renamed_items.append({
                "original_path": orig,
                "new_path": target,
                "status": "Renamed"
            })
        except Exception as e:
            errors.append({"path": orig, "error": str(e)})

    if not dry_run and renamed_items:
        log_rename_batch(batch_id, renamed_items)

    return {
        "batch_id": batch_id,
        "dry_run": dry_run,
        "total_renamed": len(renamed_items),
        "total_errors": len(errors),
        "renamed": renamed_items,
        "errors": errors
    }

def undo_latest_batch():
    latest = get_latest_batch()
    if not latest:
        return {"success": False, "message": "No rename history found to undo."}

    batch_id = latest["batch_id"]
    conn = get_connection()
    rows = conn.execute("SELECT original_path, new_path FROM rename_history WHERE batch_id = ? AND reverted = 0;", (batch_id,)).fetchall()
    conn.close()

    reverted_count = 0
    errors = []

    for row in rows:
        orig = row["original_path"]
        current = row["new_path"]
        
        if os.path.exists(current):
            try:
                os.makedirs(os.path.dirname(orig), exist_ok=True)
                shutil.move(current, orig)
                reverted_count += 1
            except Exception as e:
                errors.append({"current": current, "error": str(e)})

    mark_batch_reverted(batch_id)
    return {
        "success": True,
        "batch_id": batch_id,
        "reverted_count": reverted_count,
        "errors": errors
    }

def get_filesystem_drives_and_dirs(current_dir=None):
    if not current_dir or current_dir == "ROOT":
        drives = []
        if os.name == 'nt':
            # List Windows drives
            for letter in string.ascii_uppercase:
                d = f"{letter}:\\"
                if os.path.exists(d):
                    drives.append({"name": f"Drive ({letter}:)", "path": d, "is_drive": True})
        else:
            # Linux / Unix / Container roots
            drives.append({"name": "Root (/)", "path": "/", "is_drive": True})
            for common in ["/media", "/mnt", "/data", "/mnt/user/data", "/mnt/user/data/media"]:
                if os.path.exists(common):
                    drives.append({"name": f"Mount ({common})", "path": common, "is_drive": True})
        return {"current": "ROOT", "parent": None, "directories": drives}

    norm = os.path.abspath(current_dir)
    if not os.path.exists(norm):
        return {"current": norm, "parent": None, "directories": []}

    parent = os.path.dirname(norm)
    if parent == norm:
        parent = "ROOT"

    dirs = []
    try:
        with os.scandir(norm) as entries:
            for entry in entries:
                if entry.is_dir() and not entry.name.startswith(('.', '$')):
                    dirs.append({
                        "name": entry.name,
                        "path": entry.path,
                        "is_drive": False
                    })
    except Exception as e:
        logger.warning(f"Error reading directory {norm}: {e}")

    dirs.sort(key=lambda x: x["name"].lower())
    return {
        "current": norm,
        "parent": parent,
        "directories": dirs
    }
