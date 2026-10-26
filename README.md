<div align="center">

# ⚡ Renamarr

### Next-Gen Interactive Media Renamer & Organizer for Movies & TV Shows
**The free, modern, web-based alternative to FileBot for Plex, Jellyfin & Emby.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-Async-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/IMDb-Zero--Config-F5C518?style=for-the-badge&logo=imdb&logoColor=black" />
  <img src="https://img.shields.io/badge/Compliance-Plex%20%7C%20Jellyfin%20%7C%20Emby-E5A00D?style=for-the-badge" />
</p>

</div>

---

## 🚀 Overview

**Renamarr** is a self-hosted, interactive media organizer that recursively scans your local drives or network shares (`\\nas\media`, SMB, NFS), matches movies and TV shows against **IMDb** and **TVMaze**, and renames/organizes them into strict **Plex / Jellyfin / Emby** compliant directory structures.

Unlike legacy tools that require paid licenses, command-line scripts, or cumbersome Java runtimes, Renamarr provides an ultra-fast, modern, dark-mode web dashboard featuring **interactive side-by-side diff previews, atomic renames, and instant 1-click batch undo**.

---

## ✨ Features

- 🔍 **Zero-Config Metadata Matching**: Automatically queries canonical movie titles, release years, and poster art directly from IMDb without requiring any paid API keys or registration.
- 📺 **Full TV Show & Episode Intelligence**: Accurately parses season and episode numbering (`S01E02`, `1x02`, `Season 1 Episode 2`) and resolves official episode titles using TVMaze.
- 🌐 **Local & Network Share Native**: Seamlessly scans local disks (`C:\Media`), mapped drives (`Z:\`), and UNC network shares (`\\192.168.0.3\data\media`).
- ⚡ **Interactive Side-by-Side Diff Table**: Preview original filenames alongside proposed target names and poster art before changing a single byte on disk.
- ✏️ **Manual Inline Editing & Overrides**: Click any proposed filename to edit it directly, or click "Override" to search IMDb for alternative titles in real-time.
- 🛡️ **Safe Dry-Run Mode**: Test and simulate your renaming rules safely across thousands of files without touching the filesystem.
- ↺ **1-Click Undo Ledger**: Every rename batch is tracked in an SQLite audit ledger. Made a mistake? Click "Undo Last Batch" to instantly restore files to their exact original names and paths.
- 📁 **Automated Library Structuring**:
  - **Movies**: `Movies/Inception (2010)/Inception (2010) [1080p].mkv`
  - **TV Shows**: `TV Shows/Breaking Bad/Season 01/Breaking Bad - S01E01 - Pilot [1080p].mkv`

---

## 📊 Feature Comparison

| Feature | Renamarr ⚡ | FileBot | TinyMediaManager | Sonarr / Radarr |
|---|:---:|:---:|:---:|:---:|
| **Cost** | **100% Free & Open Source** | Paid ($6/yr or $48 lifetime) | Freemium ($15/yr for full) | Free |
| **Interface** | **Modern Responsive Web UI** | Desktop Java GUI | Desktop Java GUI | Complex PVR Web UI |
| **Setup Overhead** | **Zero Config (No API Keys)** | Paid License Key | Account / API keys | Needs Downloader / Indexer setup |
| **Interactive Diff Table** | **Side-by-Side + Poster Art** | Basic List | Basic List | Limited preview |
| **Inline Title Editing** | **1-Click Click-to-Edit** | Clunky | Complex modal | Not supported |
| **1-Click Undo Ledger** | **Full History Rollback** | Basic History | Limited | No native undo |
| **UNC Network Share Support** | **Full Native Support** | Yes | Yes | Yes |

---

## 🛠️ Quickstart

### Option A: Windows 1-Click Launcher (Recommended)
1. Clone the repository:
   ```bash
   git clone https://github.com/digdast/renamarr.git
   cd renamarr
   ```
2. Run [`run.bat`](run.bat):
   ```cmd
   run.bat
   ```
   *Renamarr will automatically start and open `http://localhost:7879` in your default browser.*

---

### Option B: Linux / macOS
```bash
git clone https://github.com/digdast/renamarr.git
cd renamarr
pip install -r requirements.txt
./run.sh
```

---

### Option C: Remote Linux Host / Proxmox LXC / unRAID (1-Command Install)
Run this single command on any remote Debian/Ubuntu/Proxmox node to automatically install, configure, and launch Renamarr as a background `systemd` service:
```bash
curl -sSL https://raw.githubusercontent.com/digdast/renamarr/main/install_remote.sh | sudo bash
```

---

### Option D: Docker & Docker Compose
```yaml
name: renamarr

services:
  renamarr:
    image: ghcr.io/digdast/renamarr:latest
    container_name: renamarr
    restart: unless-stopped
    ports:
      - "7879:7879"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
    volumes:
      - ./data:/app/data
      # Mount your local or unRAID/NFS/SMB media shares:
      - /mnt/user/data/media:/media:rw
```
Launch with:
```bash
docker compose up -d
```

---

## 🌐 Running From a Remote Host

Renamarr is fully architected for remote network environments and can be operated from any machine:

### 1. Web Access from Any Device on the Network
Renamarr binds to `0.0.0.0:7879`. Simply open your browser on any phone, tablet, or remote PC on your LAN:
```
http://<HOST_IP>:7879   (e.g., http://192.168.0.25:7879)
```

### 2. Remote Headless CLI & Automation Client (`renamarr_cli.py`)
Run renames from any remote terminal, SSH session, or post-download script (qBittorrent, Transmission, SABnzbd):

```bash
# Check remote server connectivity
python renamarr_cli.py --remote http://192.168.0.25:7879 status

# Remotely scan a network share
python renamarr_cli.py --remote http://192.168.0.25:7879 scan --path "\\192.168.0.3\data\media"

# Remotely execute batch rename (with -y to auto-confirm)
python renamarr_cli.py --remote http://192.168.0.25:7879 rename --path "\\192.168.0.3\data\media" -y

# 1-Click Rollback / Undo latest batch
python renamarr_cli.py --remote http://192.168.0.25:7879 undo
```

---

## 🎨 Interactive Dashboard Preview

```
[📂 Directory Input] [Browse...] [⚡ Scan & Match with IMDb]
---------------------------------------------------------------------------------------------
[🎬 48 Files Found]  [📺 32 Episodes]  [🍿 16 Movies]  [✓ 42 Ready to Rename]  [ℹ 6 Compliant]
---------------------------------------------------------------------------------------------
[✓] | Poster | Type   | Original Source                       ➔ | Proposed Plex/Jellyfin Target
[✓] | [IMG]  | MOVIE  | Inception.2010.1080p.BluRay.x264.mkv  ➔ | Inception (2010) [1080P].mkv
[✓] | [IMG]  | TV     | Breaking.Bad.S01E01.Pilot.720p.mkv    ➔ | Breaking Bad - S01E01 - Pilot [720P].mkv
```

---

## ⚙️ Custom Naming Templates

Renamarr allows customizable formatting tokens in the **Settings** menu:

### Movie Template
`{title} ({year}) [{resolution}]`
- Supported tokens: `{title}`, `{year}`, `{resolution}`, `{codec}`

### TV Show Template
`{show} - S{season:02d}E{episode:02d} - {title} [{resolution}]`
- Supported tokens: `{show}`, `{season}`, `{episode}`, `{title}`, `{resolution}`, `{codec}`

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  ⭐ <b>Drop a star if Renamarr saves you hours of manual media organization!</b> ⭐
</div>
