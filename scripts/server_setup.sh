#!/usr/bin/env bash
# ==============================================================
# server_setup.sh — Persiapan Debian VM untuk API Absensi
# Jalankan SEKALI saat pertama kali setup server
# ==============================================================
# Usage: bash server_setup.sh
# Requires: sudo / root access
# ==============================================================

set -euo pipefail

DEPLOY_PATH="/opt/facercg"
DEPLOY_USER="deploy"
REPO_NAME="api-absensi"   # Sesuaikan dengan nama repo GitHub Anda

echo "════════════════════════════════════════════════════"
echo " Absensi API — Server Setup Script (Debian VM)"
echo " Target RAM: 2GB | Stack: Docker + MySQL"
echo "════════════════════════════════════════════════════"

# ─── 1. Update system ─────────────────────────────────────────
echo ""
echo "📦 [1/8] Update system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop

# ─── 2. Install Docker ────────────────────────────────────────
echo ""
echo "🐳 [2/8] Install Docker Engine..."
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed: $(docker --version)"
else
    echo "✅ Docker sudah ada: $(docker --version)"
fi

# ─── 3. Buat deploy user ──────────────────────────────────────
echo ""
echo "👤 [3/8] Setup deploy user ($DEPLOY_USER)..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$DEPLOY_USER"
    echo "✅ User $DEPLOY_USER dibuat"
fi

# Tambah ke docker group (tidak perlu sudo untuk jalankan docker)
usermod -aG docker "$DEPLOY_USER"
echo "✅ User $DEPLOY_USER ditambahkan ke group docker"

# ─── 4. Setup SSH key untuk deploy user ───────────────────────
echo ""
echo "🔑 [4/8] Setup SSH authorized_keys untuk $DEPLOY_USER..."
SSH_DIR="/home/${DEPLOY_USER}/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

if [ ! -f "${SSH_DIR}/authorized_keys" ]; then
    touch "${SSH_DIR}/authorized_keys"
    chmod 600 "${SSH_DIR}/authorized_keys"
fi

echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │ Paste PUBLIC KEY untuk GitHub Actions deploy    │"
echo "  │ (ini adalah PUBLIC KEY, bukan private key)      │"
echo "  │ Tekan Enter 2x setelah paste untuk selesai:     │"
echo "  └─────────────────────────────────────────────────┘"
echo ""
read -r -d '' PUBLIC_KEY || true
if [ -n "$PUBLIC_KEY" ]; then
    echo "$PUBLIC_KEY" >> "${SSH_DIR}/authorized_keys"
    echo "✅ Public key ditambahkan"
fi
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$SSH_DIR"

# ─── 5. Buat direktori deploy ─────────────────────────────────
echo ""
echo "📁 [5/8] Buat direktori deployment: $DEPLOY_PATH"
mkdir -p "$DEPLOY_PATH"
mkdir -p "$DEPLOY_PATH/data/snapshots"
mkdir -p "$DEPLOY_PATH/logs"
mkdir -p "$DEPLOY_PATH/mysql_data"
mkdir -p "$DEPLOY_PATH/mysql_conf"

chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$DEPLOY_PATH"
echo "✅ Direktori dibuat dan ownership diset ke $DEPLOY_USER"

# ─── 6. Copy file konfigurasi ─────────────────────────────────
echo ""
echo "📋 [6/8] Instruksi: Copy file konfigurasi ke server"
echo ""
echo "  Dari laptop/PC Anda, jalankan perintah berikut:"
echo ""
echo "  # Copy docker-compose.yml"
echo "  scp docker-compose.yml ${DEPLOY_USER}@<IP_SERVER>:${DEPLOY_PATH}/"
echo ""
echo "  # Copy MySQL config"
echo "  scp mysql_conf/low_memory.cnf ${DEPLOY_USER}@<IP_SERVER>:${DEPLOY_PATH}/mysql_conf/"
echo ""
echo "  # Copy dan edit .env.production menjadi .env"
echo "  scp .env.production ${DEPLOY_USER}@<IP_SERVER>:${DEPLOY_PATH}/.env"
echo "  ssh ${DEPLOY_USER}@<IP_SERVER> 'nano ${DEPLOY_PATH}/.env'"
echo "    → Isi semua nilai GANTI_* dengan nilai asli"
echo ""

# ─── 7. Konfigurasi Firewall ──────────────────────────────────
echo ""
echo "🛡️  [7/8] Konfigurasi UFW Firewall..."
ufw --force reset
# SSH (jangan sampai terkunci!)
ufw allow 22/tcp comment 'SSH'
# API port
ufw allow 8001/tcp comment 'Absensi API'
# Tailscale (UDP)
ufw allow 41641/udp comment 'Tailscale'
# Block semua yang lain
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
echo "✅ Firewall dikonfigurasi (port 22, 8001, 41641)"
ufw status verbose

# ─── 8. Konfigurasi sistem untuk 2GB RAM ──────────────────────
echo ""
echo "⚙️  [8/8] Optimasi sistem untuk 2GB RAM..."

# Tambah swap 2GB jika belum ada
SWAP_FILE="/swapfile"
if [ ! -f "$SWAP_FILE" ]; then
    echo "  Membuat swap 2GB (safety net saat memory pressure)..."
    fallocate -l 2G "$SWAP_FILE"
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE"
    swapon "$SWAP_FILE"
    # Persist swap di reboot
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
    echo "✅ Swap 2GB dibuat dan aktif"
else
    echo "✅ Swap sudah ada: $(swapon --show)"
fi

# Turunkan swappiness — swap hanya dipakai darurat
echo "vm.swappiness=10" >> /etc/sysctl.conf
sysctl -p > /dev/null
echo "✅ vm.swappiness=10 (swap hanya darurat)"

# ─── Selesai ──────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo " ✅ SERVER SETUP SELESAI!"
echo ""
echo " LANGKAH SELANJUTNYA:"
echo " 1. Copy file konfigurasi (lihat instruksi di atas)"
echo " 2. Edit .env di server, isi semua nilai GANTI_*"
echo " 3. Add SSH_PRIVATE_KEY ke GitHub Secrets"
echo " 4. Push commit ke branch main → CI/CD akan otomatis"
echo ""
echo " GITHUB SECRETS yang diperlukan:"
echo "  SSH_HOST         → Tailscale IP atau hostname server"
echo "  SSH_USER         → $DEPLOY_USER"
echo "  SSH_PRIVATE_KEY  → Isi private key (pasangan dari"
echo "                     public key yang sudah di-add)"
echo "  TAILSCALE_AUTHKEY→ Dari Tailscale admin panel"
echo "  GHCR_PAT         → GitHub PAT (read:packages)"
echo "                     (jika repo private)"
echo "  DEPLOY_PATH      → $DEPLOY_PATH"
echo "════════════════════════════════════════════════════"
