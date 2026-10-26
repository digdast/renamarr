#!/usr/bin/env bash
# ==============================================================================
# Renamarr Remote Host Installer (Linux / Proxmox LXC / unRAID / Debian / Ubuntu)
# Deploys Renamarr as a systemd service bound to 0.0.0.0:7879
# ==============================================================================
set -euo pipefail

INSTALL_DIR="/opt/renamarr"
SERVICE_NAME="renamarr"
PORT="7879"

echo "==================================================================="
echo "  ⚡ Installing Renamarr on Remote Host ($(hostname))"
echo "==================================================================="

# Ensure root privileges
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] This installer must be run as root (or with sudo)."
   exit 1
fi

# 1. Install prerequisites
echo "[+] Updating apt and installing dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip git curl
elif command -v yum >/dev/null 2>&1; then
    yum install -y python3 git curl
fi

# 2. Clone or update repository
if [[ -d "${INSTALL_DIR}" ]]; then
    echo "[+] Updating existing installation in ${INSTALL_DIR}..."
    cd "${INSTALL_DIR}"
    git pull || true
else
    echo "[+] Cloning Renamarr to ${INSTALL_DIR}..."
    git clone https://github.com/digdast/renamarr.git "${INSTALL_DIR}"
    cd "${INSTALL_DIR}"
fi

# 3. Setup Python virtual environment
echo "[+] Setting up Python virtual environment..."
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip -q
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" -q

# 4. Create systemd service
echo "[+] Configuring systemd service at /etc/systemd/system/${SERVICE_NAME}.service..."
cat <<EOF > "/etc/systemd/system/${SERVICE_NAME}.service"
[Unit]
Description=Renamarr - Interactive Media Renamer & Organizer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable and start service
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

HOST_IP=$(hostname -I | awk '{print $1}')
echo "==================================================================="
echo "  [✓] Renamarr Successfully Deployed & Running!"
echo "  Web Dashboard: http://${HOST_IP}:${PORT}"
echo "  Service Status: systemctl status ${SERVICE_NAME}"
echo "  Service Logs:   journalctl -u ${SERVICE_NAME} -f"
echo "==================================================================="
