import re
import os

# Video extensions supported
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.ts', '.wmv', '.iso', '.flv'}

# Standard junk tokens in scene/P2P filenames
JUNK_TOKENS = [
    r'1080p', r'720p', r'2160p', r'4k', r'480p', r'360p', r'uhd', r'hdr', r'hdr10', r'dv', r'dovi',
    r'bluray', r'blu-ray', r'bdrip', r'brrip', r'web-dl', r'webrip', r'web', r'hdtv', r'dvdrip', r'remux',
    r'x264', r'x265', r'hevc', r'h264', r'h265', r'avc', r'av1', r'xvid',
    r'dts-hd', r'dts', r'truehd', r'atmos', r'ddp5\.1', r'dd5\.1', r'ac3', r'aac', r'flac', r'mp3',
    r'yify', r'rarbg', r'sparks', r'fgt', r'galaxyrg', r'ettv', r'eztv', r'psa', r'amzn', r'nf', r'proper', r'repack', r'extended', r'unrated', r'imax'
]

# Resolution regex
RES_PATTERN = re.compile(r'\b(2160p|4k|1080p|1080i|720p|576p|480p)\b', re.IGNORECASE)
CODEC_PATTERN = re.compile(r'\b(x265|hevc|h\.?265|x264|h\.?264|av1|xvid)\b', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\b(19\d{2}|20\d{2})\b')

# TV patterns: S01E02, S1E2, 1x02, Season 1 Episode 2
TV_PATTERNS = [
    re.compile(r'[._\s-]s(\d{1,2})e(\d{1,3})[._\s-]', re.IGNORECASE),
    re.compile(r'[._\s-](\d{1,2})x(\d{1,3})[._\s-]', re.IGNORECASE),
    re.compile(r'season[._\s-]*(\d{1,2})[._\s-]*episode[._\s-]*(\d{1,3})', re.IGNORECASE),
    re.compile(r'\bs(\d{1,2})e(\d{1,3})\b', re.IGNORECASE)
]

def parse_media_filename(filepath):
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    
    if ext.lower() not in VIDEO_EXTENSIONS:
        return None

    # Detect resolution
    res_match = RES_PATTERN.search(name)
    resolution = res_match.group(1).upper() if res_match else None
    if resolution == "4K":
        resolution = "2160P"

    # Detect codec
    codec_match = CODEC_PATTERN.search(name)
    codec = codec_match.group(1).upper() if codec_match else None

    # Detect TV show season & episode
    is_tv = False
    season = None
    episode = None
    title_raw = name

    for pat in TV_PATTERNS:
        tv_match = pat.search(name)
        if tv_match:
            is_tv = True
            season = int(tv_match.group(1))
            episode = int(tv_match.group(2))
            # Everything before the SxxExx pattern is the show title
            title_raw = name[:tv_match.start()]
            break

    # Extract year if present
    year = None
    year_matches = list(YEAR_PATTERN.finditer(name))
    if year_matches:
        # If TV show, year might be in title (e.g. Doctor Who 2005)
        # For movie, year is typically the last matching 4-digit number
        y_val = int(year_matches[-1].group(1))
        if 1900 <= y_val <= 2030:
            year = y_val
            if not is_tv:
                title_raw = name[:year_matches[-1].start()]

    # Clean up title: replace dots, underscores, dashes with spaces
    cleaned_title = re.sub(r'[._+]', ' ', title_raw)
    
    # Strip brackets and parentheses
    cleaned_title = re.sub(r'[\(\)\[\]\{\}]', ' ', cleaned_title)

    # Strip junk tokens
    for jt in JUNK_TOKENS:
        cleaned_title = re.sub(r'\b' + jt + r'\b', '', cleaned_title, flags=re.IGNORECASE)

    # Remove extra spaces and strip
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    
    # Handle empty title fallback
    if not cleaned_title:
        cleaned_title = name

    return {
        "filepath": filepath,
        "filename": filename,
        "extension": ext.lower(),
        "is_tv": is_tv,
        "raw_title": cleaned_title,
        "year": year,
        "season": season,
        "episode": episode,
        "resolution": resolution,
        "codec": codec
    }
