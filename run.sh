#!/usr/bin/env bash
echo "===================================================================="
echo "  ⚡ Renamarr - Next-Gen Interactive Media Renamer & Organizer"
echo "===================================================================="
echo ""
echo "Starting Renamarr Web Dashboard on http://localhost:7879 ..."
echo ""

# Try opening default browser
if which xdg-open > /dev/null; then
  xdg-open "http://localhost:7879" &
elif which open > /dev/null; then
  open "http://localhost:7879" &
fi

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7879 --app-dir "$(dirname "$0")"
