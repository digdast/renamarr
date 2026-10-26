import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.renamer import scan_path, execute_renames, undo_latest_batch, get_filesystem_drives_and_dirs
from app.metadata import search_imdb
from app.database import get_setting, set_setting, get_latest_batch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Renamarr",
    description="Next-Gen Interactive Media Renamer & Organizer for Movies & TV Shows",
    version="1.0.0"
)

# Static and Templates
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class ScanRequest(BaseModel):
    path: str
    recursive: bool = True
    organize_folders: bool = True
    movie_template: Optional[str] = None
    tv_template: Optional[str] = None

class RenameItem(BaseModel):
    original_path: str
    target_path: str

class RenameRequest(BaseModel):
    items: List[RenameItem]
    dry_run: bool = False

class SettingsModel(BaseModel):
    movie_template: str
    tv_template: str
    organize_folders: bool
    dry_run: bool
    last_scan_path: str

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/scan")
async def api_scan(req: ScanRequest):
    try:
        set_setting("last_scan_path", req.path)
        items = scan_path(
            target_path=req.path,
            recursive=req.recursive,
            movie_template=req.movie_template or get_setting("movie_template"),
            tv_template=req.tv_template or get_setting("tv_template"),
            organize_folders=req.organize_folders
        )
        return {"success": True, "count": len(items), "items": items}
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

@app.post("/api/rename")
async def api_rename(req: RenameRequest):
    try:
        items_dict = [{"original_path": i.original_path, "target_path": i.target_path} for i in req.items]
        res = execute_renames(items_dict, dry_run=req.dry_run)
        return {"success": True, "result": res}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/api/undo")
async def api_undo():
    res = undo_latest_batch()
    return res

@app.get("/api/undo/status")
async def api_undo_status():
    latest = get_latest_batch()
    return {"has_undo": latest is not None, "latest_batch": latest}

@app.get("/api/browse")
async def api_browse(path: Optional[str] = None):
    try:
        res = get_filesystem_drives_and_dirs(path)
        return {"success": True, "data": res}
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

@app.get("/api/imdb/search")
async def api_imdb_search(q: str):
    res = search_imdb(q)
    return {"success": True, "results": res}

@app.get("/api/settings")
async def api_get_settings():
    return {
        "movie_template": get_setting("movie_template", "{title} ({year}) [{resolution}]"),
        "tv_template": get_setting("tv_template", "{show} - S{season:02d}E{episode:02d} - {title} [{resolution}]"),
        "organize_folders": get_setting("organize_folders", "true").lower() == "true",
        "dry_run": get_setting("dry_run", "false").lower() == "true",
        "last_scan_path": get_setting("last_scan_path", "C:\\Media")
    }

@app.post("/api/settings")
async def api_save_settings(s: SettingsModel):
    set_setting("movie_template", s.movie_template)
    set_setting("tv_template", s.tv_template)
    set_setting("organize_folders", "true" if s.organize_folders else "false")
    set_setting("dry_run", "true" if s.dry_run else "false")
    set_setting("last_scan_path", s.last_scan_path)
    return {"success": True, "message": "Settings saved successfully."}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=7879, reload=True)
