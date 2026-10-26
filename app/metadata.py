import urllib.request
import urllib.parse
import json
import logging
from app.database import get_cached_metadata, set_cached_metadata

logger = logging.getLogger("renamarr.metadata")

IMDB_SUGGEST_URL = "https://v3.sg.media-imdb.com/suggestion/x/{}.json"
TVMAZE_URL = "https://api.tvmaze.com/singlesearch/shows?q={}&embed=episodes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def search_imdb(query):
    query_clean = query.strip()
    if not query_clean:
        return []

    cache_key = f"imdb:{query_clean}"
    cached = get_cached_metadata(cache_key)
    if cached is not None:
        return cached

    url = IMDB_SUGGEST_URL.format(urllib.parse.quote(query_clean.lower()))
    req = urllib.request.Request(url, headers=HEADERS)
    
    results = []
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("d", [])
            for item in items:
                # filter out non-video entries (e.g. actors/directors which start with 'nm')
                item_id = item.get("id", "")
                if not item_id.startswith("tt"):
                    continue
                
                title = item.get("l", "")
                year = item.get("y")
                q_type = item.get("q", "").lower()
                poster = item.get("i", {}).get("imageUrl") if isinstance(item.get("i"), dict) else None
                
                is_tv = any(tv_keyword in q_type for tv_keyword in ["tv", "series", "mini"])
                
                results.append({
                    "imdb_id": item_id,
                    "title": title,
                    "year": year,
                    "is_tv": is_tv,
                    "type_label": "TV Series" if is_tv else "Movie",
                    "poster": poster,
                    "actors": item.get("s", "")
                })
        set_cached_metadata(cache_key, "imdb", results)
    except Exception as e:
        logger.warning(f"IMDb search failed for '{query_clean}': {e}")
        
    return results

def get_tv_episode_title(show_title, season, episode):
    cache_key = f"tvmaze:{show_title}"
    show_data = get_cached_metadata(cache_key)
    
    if show_data is None:
        url = TVMAZE_URL.format(urllib.parse.quote(show_title))
        req = urllib.request.Request(url, headers={"User-Agent": "Renamarr/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                show_data = json.loads(resp.read().decode("utf-8"))
                set_cached_metadata(cache_key, "tvmaze", show_data)
        except Exception as e:
            logger.warning(f"TVMaze query failed for '{show_title}': {e}")
            show_data = {}

    episodes = show_data.get("_embedded", {}).get("episodes", [])
    for ep in episodes:
        if ep.get("season") == season and ep.get("number") == episode:
            return ep.get("name")
            
    return None

def resolve_metadata_for_parsed(parsed):
    title = parsed["raw_title"]
    year = parsed.get("year")
    is_tv = parsed.get("is_tv", False)
    
    imdb_results = search_imdb(title)
    
    best_match = None
    if imdb_results:
        # Prioritize matching TV/Movie type
        type_filtered = [r for r in imdb_results if r["is_tv"] == is_tv]
        candidates = type_filtered if type_filtered else imdb_results
        
        # If year is known, prioritize matching year
        if year:
            for c in candidates:
                if c.get("year") == year:
                    best_match = c
                    break
        if not best_match and candidates:
            best_match = candidates[0]

    # Episode title lookup for TV
    episode_title = None
    if is_tv and parsed.get("season") is not None and parsed.get("episode") is not None:
        canonical_show = best_match["title"] if best_match else title
        episode_title = get_tv_episode_title(canonical_show, parsed["season"], parsed["episode"])
        if not episode_title:
            episode_title = f"Episode {parsed['episode']}"

    return {
        "best_match": best_match,
        "all_matches": imdb_results[:5],
        "episode_title": episode_title
    }
