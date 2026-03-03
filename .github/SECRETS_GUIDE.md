# GitHub Repository Secrets — Setup Guide

Panduan ini menjelaskan semua secrets yang dibutuhkan pipeline CI/CD (`facercg.yml`).

> **Cara tambah secret:**  
> GitHub Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

---

## Secrets Wajib

### 1. `TAILSCALE_AUTHKEY`
Digunakan untuk menghubungkan GitHub Actions runner ke jaringan Tailscale sehingga bisa SSH ke VM.

**Cara dapat:**
1. Buka [tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys)
2. Klik **Generate auth key**
3. Pilih: ✅ Reusable, ✅ Ephemeral
4. Expiry: **90 hari** (set pengingat kalender untuk renew)
5. Copy key → paste sebagai secret

```
Contoh format: tskey-auth-kXXXXXXXXXXXXXX-XXXXXXXX
```

---

### 2. `SSH_HOST`
IP address Tailscale dari VM Debian. **Bukan** IP lokal biasa.

**Cara dapat (jalankan di VM):**
```bash
tailscale ip -4
# Output: 100.x.x.x
```

---

### 3. `SSH_USER`
Username yang digunakan untuk SSH ke server. Dibuat oleh `scripts/server_setup.sh`.

```
Value default: deploy
```

---

### 4. `SSH_PRIVATE_KEY`
Private key untuk autentikasi SSH. Harus sesuai dengan public key yang ada di server.

**Cara buat key pair baru (jalankan di laptop):**
```bash
ssh-keygen -t ed25519 -C "github-actions-absensi" -f ~/.ssh/absensi_deploy
```

Menghasilkan 2 file:
- `~/.ssh/absensi_deploy` → **PRIVATE KEY** → paste isi file ini ke secret
- `~/.ssh/absensi_deploy.pub` → Public key → taruh di server

**Cara pasang public key di server:**
```bash
cat ~/.ssh/absensi_deploy.pub | ssh deploy@<SERVER_IP> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Format secret** (copy seluruh isi termasuk baris header/footer):
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAA...
...
-----END OPENSSH PRIVATE KEY-----
```

> ⚠️ **Jangan** copy hanya isi tengahnya saja — header dan footer wajib ikut.

---

### 5. `GHCR_PAT`
Personal Access Token untuk `docker login ghcr.io` di server saat pull image.

**Cara dapat:**
1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Klik **Generate new token (classic)**
3. Nama: `absensi-ghcr-deploy`
4. Scope: centang ✅ `read:packages` (cukup untuk pull)
5. Expiry: **90 hari**
6. Generate → copy token

```
Contoh format: ghp_xxxxxxxxxxxxxxxxxxxx
```

---

## Secrets Opsional (Ada Default)

| Secret | Default | Keterangan |
|--------|---------|-----------|
| `SSH_PORT` | `22` | Ganti jika SSH server kamu pakai port custom |
| `DEPLOY_PATH` | `/opt/absensi-api` | Path deployment di server |

---

## `GITHUB_TOKEN` — Otomatis, Tidak Perlu Dibuat

Secret ini dipakai untuk push Docker image ke GHCR (build job). GitHub menyediakannya otomatis di setiap workflow run — kamu tidak perlu buat manual.

---

## Checklist

Sebelum push ke `main`, pastikan semua sudah diisi:

```
☐ TAILSCALE_AUTHKEY    ← dari tailscale.com/admin/settings/keys
☐ SSH_HOST             ← IP Tailscale VM (tailscale ip -4)
☐ SSH_USER             ← "deploy"
☐ SSH_PRIVATE_KEY      ← isi file ~/.ssh/absensi_deploy
☐ GHCR_PAT             ← GitHub PAT dengan scope read:packages
```

---

## Urutan Setup yang Benar

```
1. Jalankan scripts/server_setup.sh di VM    ← buat user deploy + direktori
2. Generate SSH key pair di laptop           ← ssh-keygen -t ed25519
3. Copy public key ke server                 ← cat pub >> authorized_keys
4. Install & connect Tailscale di VM         ← catat Tailscale IP
5. Buat GHCR PAT di GitHub                  ← scope: read:packages
6. Buat Tailscale auth key                  ← reusable + ephemeral
7. Isi semua 5 secrets di GitHub             ← Settings → Secrets → Actions
8. Push commit ke branch main               ← pipeline otomatis jalan
```

---

## Renewal Berkala

Secrets yang perlu diperbarui setelah masa berlaku habis:

| Secret | Expiry | Cara Renew |
|--------|--------|------------|
| `TAILSCALE_AUTHKEY` | 90 hari | Buat auth key baru di Tailscale admin |
| `GHCR_PAT` | 90 hari | Generate token baru di GitHub Settings |
| `SSH_PRIVATE_KEY` | Tidak expire | Hanya perlu diganti jika key compromise |

> 💡 Buat event kalender pengingat renewal setiap 80 hari.

---

## Troubleshooting

| Error di Pipeline | Penyebab | Solusi |
|------------------|----------|--------|
| `Tailscale: auth error` | `TAILSCALE_AUTHKEY` expired atau salah | Buat auth key baru |
| `ssh-keyscan gagal` | `SSH_HOST` salah atau VM mati | Cek Tailscale IP + pastikan VM running |
| `Permission denied (publickey)` | Public key tidak ada di server atau format private key salah | Cek `~/.ssh/authorized_keys` di server |
| `docker login: unauthorized` | `GHCR_PAT` expired atau scope kurang | Buat PAT baru dengan `read:packages` |
| `❌ .env tidak ada` | File `.env` belum dibuat di server | `cp .env.production.example .env` lalu isi di server |
