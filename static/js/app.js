// Renamarr Interactive Client Engine

let currentItems = [];
let currentBrowserPath = "ROOT";
let activeEditItemId = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  checkUndoStatus();
  loadSettings();
  loadNetworkInfo();
});

async function loadNetworkInfo() {
  try {
    const res = await fetch("/api/system/network");
    const data = await res.json();
    if (data.remote_urls && data.remote_urls.length > 0) {
      const primaryUrl = data.remote_urls.find(u => !u.includes("127.0.0.1") && !u.includes("169.254")) || data.remote_urls[0];
      const badge = document.getElementById("remoteBadge");
      const urlText = document.getElementById("remoteUrlText");
      if (badge && urlText) {
        urlText.innerText = primaryUrl;
        badge.style.display = "inline-flex";
        badge.title = "Click to copy remote access URL";
        badge.style.cursor = "pointer";
        badge.onclick = () => {
          navigator.clipboard.writeText(primaryUrl);
          showToast(`Copied ${primaryUrl} to clipboard!`);
        };
      }
    }
  } catch (e) {
    console.warn("Could not fetch network info:", e);
  }
}

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Preset Helper
function setPreset(path) {
  document.getElementById("targetPath").value = path;
  showToast(`Path set to: ${path}`);
}

// Load Settings
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    if (data.last_scan_path) {
      document.getElementById("targetPath").value = data.last_scan_path;
    }
    if (data.movie_template) {
      document.getElementById("settingMovieTemplate").value = data.movie_template;
    }
    if (data.tv_template) {
      document.getElementById("settingTvTemplate").value = data.tv_template;
    }
    document.getElementById("chkOrganize").checked = data.organize_folders;
    document.getElementById("chkDryRun").checked = data.dry_run;
  } catch (e) {
    console.error("Failed to load settings:", e);
  }
}

// Save Settings
async function saveSettings() {
  const payload = {
    movie_template: document.getElementById("settingMovieTemplate").value,
    tv_template: document.getElementById("settingTvTemplate").value,
    organize_folders: document.getElementById("chkOrganize").checked,
    dry_run: document.getElementById("chkDryRun").checked,
    last_scan_path: document.getElementById("targetPath").value
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast("Settings saved!", "success");
      closeSettingsModal();
    }
  } catch (e) {
    showToast("Error saving settings", "error");
  }
}

// Check Undo Status
async function checkUndoStatus() {
  try {
    const res = await fetch("/api/undo/status");
    const data = await res.json();
    const btnUndo = document.getElementById("btnUndo");
    if (data.has_undo) {
      btnUndo.style.display = "inline-flex";
      btnUndo.title = `Undo last batch of ${data.latest_batch.count} files from ${data.latest_batch.ts}`;
    } else {
      btnUndo.style.display = "none";
    }
  } catch (e) {
    console.error("Error checking undo:", e);
  }
}

// Start Scan
async function startScan() {
  const path = document.getElementById("targetPath").value.trim();
  if (!path) {
    showToast("Please enter a local path or network share.", "error");
    return;
  }

  const btnScan = document.getElementById("btnScan");
  const scanIcon = document.getElementById("scanIcon");
  const scanBtnText = document.getElementById("scanBtnText");

  btnScan.disabled = true;
  scanIcon.innerText = "⏳";
  scanBtnText.innerText = "Scanning & Querying IMDb...";

  const payload = {
    path: path,
    recursive: document.getElementById("chkRecursive").checked,
    organize_folders: document.getElementById("chkOrganize").checked
  };

  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!data.success) {
      showToast(`Scan Error: ${data.error}`, "error");
      return;
    }

    currentItems = data.items;
    renderTable(currentItems);
    updateStats(currentItems);
    showToast(`Scan complete: Found ${data.count} media files!`, "success");
  } catch (e) {
    showToast(`Failed to connect to scan service: ${e.message}`, "error");
  } finally {
    btnScan.disabled = false;
    scanIcon.innerText = "⚡";
    scanBtnText.innerText = "Scan & Match with IMDb";
  }
}

// Update Stats Ribbon
function updateStats(items) {
  const ribbon = document.getElementById("statsRibbon");
  const resultsContainer = document.getElementById("resultsContainer");
  const bottomBar = document.getElementById("bottomBar");

  ribbon.style.display = "grid";
  resultsContainer.style.display = "block";
  bottomBar.style.display = "flex";

  const total = items.length;
  const tvCount = items.filter(i => i.is_tv).length;
  const movieCount = total - tvCount;
  const alreadyCount = items.filter(i => i.is_already_named).length;
  const readyCount = items.filter(i => i.selected).length;

  document.getElementById("statTotal").innerText = total;
  document.getElementById("statTV").innerText = tvCount;
  document.getElementById("statMovies").innerText = movieCount;
  document.getElementById("statAlready").innerText = alreadyCount;
  document.getElementById("statReady").innerText = readyCount;

  updateSelectionCount();
}

// Render Table
function renderTable(items) {
  const tbody = document.getElementById("diffTableBody");
  tbody.innerHTML = "";

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">No video files found in target folder.</td></tr>`;
    return;
  }

  items.forEach(item => {
    const tr = document.createElement("tr");
    tr.id = `row-${item.id}`;
    if (item.is_already_named) {
      tr.className = "already-named";
    }

    const posterHtml = item.poster 
      ? `<img src="${item.poster}" class="poster-thumb" alt="Poster" onerror="this.src='/static/img/placeholder.png';">`
      : `<div class="poster-thumb" style="display: flex; align-items: center; justify-content: center; font-size: 20px;">🎬</div>`;

    const typeBadge = item.is_tv 
      ? `<span class="media-badge badge-tv">TV SHOW</span>`
      : `<span class="media-badge badge-movie">MOVIE</span>`;

    const resBadge = item.resolution 
      ? `<span class="media-badge badge-res">${item.resolution}</span>`
      : "";

    const imdbLink = item.imdb_id 
      ? `<a href="https://www.imdb.com/title/${item.imdb_id}" target="_blank" style="color: var(--accent-amber); font-size: 11.5px; text-decoration: none; margin-left: 6px;">[IMDb ${item.imdb_id}]</a>`
      : "";

    tr.innerHTML = `
      <td>
        <input type="checkbox" ${item.selected ? "checked" : ""} onchange="toggleItemSelect('${item.id}', this.checked)">
      </td>
      <td>${posterHtml}</td>
      <td>
        ${typeBadge}<br>
        <span style="font-size: 11.5px; color: var(--text-dim);">${item.file_size}</span>
      </td>
      <td>
        <div class="file-orig-name">${escapeHtml(item.original_filename)}</div>
        <div class="file-meta-sub">${escapeHtml(item.original_path)}</div>
      </td>
      <td class="arrow-divider">➔</td>
      <td>
        <div>
          <span class="file-target-name editable-title" onclick="makeEditable('${item.id}', this)" title="Click to manually edit filename">
            ${escapeHtml(item.target_filename)}
          </span>
          ${resBadge}
        </div>
        <div class="file-meta-sub">
          <strong>Folder:</strong> ${escapeHtml(item.target_dir)}
          ${imdbLink}
        </div>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openManualImdbModal('${item.id}')" title="Match alternative title">
          🔍 Override
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  updateSelectionCount();
}

// Inline Editable Target Filename
function makeEditable(id, spanEl) {
  const item = currentItems.find(i => i.id === id);
  if (!item) return;

  const currentVal = item.target_filename;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "filter-input";
  input.style.width = "100%";
  input.style.fontFamily = "var(--font-mono)";
  input.value = currentVal;

  const finishEdit = () => {
    const newVal = input.value.trim() || currentVal;
    item.target_filename = newVal;
    item.target_path = item.target_dir + "\\" + newVal;
    spanEl.innerText = newVal;
    input.replaceWith(spanEl);
  };

  input.addEventListener("blur", finishEdit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") finishEdit();
    if (e.key === "Escape") {
      input.replaceWith(spanEl);
    }
  });

  spanEl.replaceWith(input);
  input.focus();
}

// Checkbox selection
function toggleItemSelect(id, isChecked) {
  const item = currentItems.find(i => i.id === id);
  if (item) {
    item.selected = isChecked;
    updateSelectionCount();
  }
}

function toggleSelectAll(isChecked) {
  currentItems.forEach(i => i.selected = isChecked);
  renderTable(currentItems);
}

function invertSelection() {
  currentItems.forEach(i => i.selected = !i.selected);
  renderTable(currentItems);
}

function updateSelectionCount() {
  const selectedCount = currentItems.filter(i => i.selected).length;
  document.getElementById("selectedCountPill").innerText = `${selectedCount} selected`;
  document.getElementById("statReady").innerText = selectedCount;

  const btnApply = document.getElementById("btnApplyRenames");
  btnApply.disabled = (selectedCount === 0);
}

// Filter table
function filterTable() {
  const q = document.getElementById("tableFilter").value.toLowerCase();
  const filtered = currentItems.filter(i => {
    return i.original_filename.toLowerCase().includes(q) ||
           i.target_filename.toLowerCase().includes(q) ||
           i.detected_title.toLowerCase().includes(q);
  });
  renderTable(filtered);
}

// Execute Batch
async function executeBatch(dryRun = false) {
  const selected = currentItems.filter(i => i.selected);
  if (selected.length === 0) {
    showToast("No items selected for renaming.", "error");
    return;
  }

  const payload = {
    items: selected.map(i => ({
      original_path: i.original_path,
      target_path: i.target_path
    })),
    dry_run: dryRun || document.getElementById("chkDryRun").checked
  };

  const actionName = payload.dry_run ? "Simulating Dry-Run" : "Executing Batch Rename";
  showToast(`${actionName} on ${selected.length} files...`, "info");

  try {
    const res = await fetch("/api/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!data.success) {
      showToast(`Execution Error: ${data.error}`, "error");
      return;
    }

    const r = data.result;
    if (r.dry_run) {
      showToast(`Dry-Run Success! Validated ${r.total_renamed} files with 0 errors.`, "success");
    } else {
      showToast(`Successfully renamed ${r.total_renamed} files!`, "success");
      checkUndoStatus();
      // Re-scan to reflect live directory state
      startScan();
    }
  } catch (e) {
    showToast(`Execution failed: ${e.message}`, "error");
  }
}

// Undo Last Batch
async function undoLastBatch() {
  if (!confirm("Are you sure you want to revert the latest rename batch back to original filenames?")) {
    return;
  }

  try {
    const res = await fetch("/api/undo", { method: "POST" });
    const data = await res.json();

    if (data.success) {
      showToast(`Reverted ${data.reverted_count} files back to original locations!`, "success");
      checkUndoStatus();
      startScan();
    } else {
      showToast(`Undo failed: ${data.message}`, "error");
    }
  } catch (e) {
    showToast(`Undo error: ${e.message}`, "error");
  }
}

// Folder Browser Modal
async function openFolderBrowser(path = null) {
  document.getElementById("folderModal").style.display = "flex";
  await navigateBrowser(path || document.getElementById("targetPath").value || "ROOT");
}

function closeFolderModal() {
  document.getElementById("folderModal").style.display = "none";
}

async function navigateBrowser(path) {
  currentBrowserPath = path;
  document.getElementById("browserCurrentPath").innerText = path;
  const list = document.getElementById("browserList");
  list.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">Loading directories...</div>`;

  try {
    const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
    const json = await res.json();
    if (!json.success) {
      list.innerHTML = `<div style="padding: 20px; color: var(--accent-rose);">Error: ${json.error}</div>`;
      return;
    }

    const data = json.data;
    list.innerHTML = "";

    // Parent item
    if (data.parent) {
      const upDiv = document.createElement("div");
      upDiv.className = "browser-item";
      upDiv.innerHTML = `<span>⬆️</span> <strong>.. (Up one level)</strong>`;
      upDiv.onclick = () => navigateBrowser(data.parent);
      list.appendChild(upDiv);
    }

    data.directories.forEach(d => {
      const itemDiv = document.createElement("div");
      itemDiv.className = "browser-item";
      itemDiv.innerHTML = `<span>${d.is_drive ? "💾" : "📁"}</span> <span>${escapeHtml(d.name)}</span>`;
      itemDiv.onclick = () => navigateBrowser(d.path);
      list.appendChild(itemDiv);
    });

    if (data.directories.length === 0 && !data.parent) {
      list.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">No accessible folders found.</div>`;
    }
  } catch (e) {
    list.innerHTML = `<div style="padding: 20px; color: var(--accent-rose);">Browse error: ${e.message}</div>`;
  }
}

function selectBrowserPath() {
  if (currentBrowserPath && currentBrowserPath !== "ROOT") {
    document.getElementById("targetPath").value = currentBrowserPath;
  }
  closeFolderModal();
}

// Manual IMDb Match Override Modal
function openManualImdbModal(itemId) {
  activeEditItemId = itemId;
  const item = currentItems.find(i => i.id === itemId);
  document.getElementById("imdbSearchQuery").value = item ? item.detected_title : "";
  document.getElementById("imdbSearchResults").innerHTML = "";
  document.getElementById("imdbModal").style.display = "flex";
  executeManualImdbSearch();
}

function closeImdbModal() {
  document.getElementById("imdbModal").style.display = "none";
  activeEditItemId = null;
}

async function executeManualImdbSearch() {
  const q = document.getElementById("imdbSearchQuery").value.trim();
  if (!q) return;

  const container = document.getElementById("imdbSearchResults");
  container.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">Searching IMDb...</div>`;

  try {
    const res = await fetch(`/api/imdb/search?q=${encodeURIComponent(q)}`);
    const json = await res.json();
    container.innerHTML = "";

    if (!json.results || json.results.length === 0) {
      container.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">No IMDb matches found.</div>`;
      return;
    }

    json.results.forEach(m => {
      const row = document.createElement("div");
      row.className = "browser-item";
      row.style.gap = "14px";
      const thumb = m.poster ? `<img src="${m.poster}" style="width: 32px; height: 46px; object-fit: cover; border-radius: 4px;">` : `🎬`;
      row.innerHTML = `
        ${thumb}
        <div style="flex: 1;">
          <div style="font-weight: 600;">${escapeHtml(m.title)} (${m.year || "Unknown"})</div>
          <div style="font-size: 12px; color: var(--text-dim);">${m.type_label} • ${m.imdb_id} ${m.actors ? "• " + escapeHtml(m.actors) : ""}</div>
        </div>
        <button class="btn btn-emerald btn-sm">Select</button>
      `;
      row.onclick = () => applyManualImdbSelection(m);
      container.appendChild(row);
    });
  } catch (e) {
    container.innerHTML = `<div style="padding: 20px; color: var(--accent-rose);">Search error: ${e.message}</div>`;
  }
}

function applyManualImdbSelection(selectedImdb) {
  const item = currentItems.find(i => i.id === activeEditItemId);
  if (!item) return;

  item.matched_title = selectedImdb.title;
  item.matched_year = selectedImdb.year;
  item.imdb_id = selectedImdb.imdb_id;
  item.poster = selectedImdb.poster;

  // Rebuild target name
  const ext = item.extension;
  const res = item.resolution ? ` [${item.resolution}]` : "";
  if (item.is_tv) {
    const epTitle = item.episode_title || `Episode ${item.episode}`;
    item.target_filename = `${selectedImdb.title} - S${item.season.toString().padStart(2, '0')}E${item.episode.toString().padStart(2, '0')} - ${epTitle}${res}${ext}`;
  } else {
    const yr = selectedImdb.year ? ` (${selectedImdb.year})` : "";
    item.target_filename = `${selectedImdb.title}${yr}${res}${ext}`;
  }
  item.target_path = item.target_dir + "\\" + item.target_filename;

  closeImdbModal();
  renderTable(currentItems);
  showToast(`Updated to: ${selectedImdb.title}`, "success");
}

// Settings Modal
function openSettingsModal() {
  document.getElementById("settingsModal").style.display = "flex";
}

function closeSettingsModal() {
  document.getElementById("settingsModal").style.display = "none";
}

// Utility
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
