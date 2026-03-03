# Panduan Deployment Absensi API ke Home Server
Dokumen ini adalah satu-satunya panduan yang Anda butuhkan untuk menjalankan API Absensi di Home Server Anda. Kami telah menyederhanakan prosesnya menjadi **SATU** perintah saja.

---

## Cara Menjalankan (Deployment)

### Persiapan Awal
1.  Pastikan Desktop/Server Anda sudah terinstall **Docker Desktop**.
2.  Pastikan Anda memiliki folder project `Api-Absensi` ini.

### Langkah-langkah (Deploy Manual Lokal)
1.  **Siapkan Env**:
    Aplikasi menolak dijalankan jika password memakai nilai default pabrikan. Copy template dan isi dengan rahasia Anda:
    ```bash
    copy .env.production.example .env
    ```
    *(Wajib: Buka file `.env` dan ganti semua teks "GANTI_...")*

2.  **Jalankan Docker**:
    ```bash
    docker-compose up -d --build
    ```

3.  **SELESAI!** 
    -   API Anda sekarang aktif di: `http://localhost:8001`
    -   Dashboard Database: `http://localhost:8080` (Login: Sesuai isi `.env`)

---

## Deployment Otomatis ke Server (CI/CD GitHub Actions)

Bagi Anda yang mendeploy di server produksi / VPS Cloud, **Anda disarankan menggunakan pipeline CI/CD bawaan**.
1. Siapkan SSH Keys & GitHub Secrets (lihat daftar rahasia di `.github/SECRETS_GUIDE.md`).
2. Login ke Server via SSH dan copy `.env.production.example` menjadi `.env` di folder deployment (e.g., `/opt/facercg`), lalu lengkapi.
3. Push Commit ke Branch 'main'. GitHub otomatis mem-build image, menghubungi server Anda, update docker-compose config, dan restart aplikasi secara aman (Zero Downtime).

---

## Apakah Saya Perlu Setting `.env`?

**YA, MUTLAK WAJIB.**
Karena setup ini dirancang aman kelas produksi, aplikasi **akan error di awal (Fast-Fail) dan mati** jika Anda hanya memakai kredensial kosongan.
Lengkapi `SECRET_KEY`, `DB_PASSWORD`, dan sebagainya di file `.env` sebelum menjalankan container docker.

---

## Pindah Data dari Laptop Lama (Migrasi)
*Lakukan ini HANYA jika Anda ingin membawa data absensi lama ke server baru.*

1.  Di komputer lama (yang ada datanya), jalankan script: `scripts/backup_db.bat`.
2.  Akan muncul file `init.sql`. Copy file ini ke folder project di server baru Anda.
3.  Buat folder baru bernama `mysql_init` di server baru.
4.  Masukkan file `init.sql` ke dalam folder `mysql_init/`.
5.  Edit file `docker-compose.yml`, tambahkan baris ini di bagian `services -> db -> volumes`:
    ```yaml
    volumes:
      - ./mysql_data:/var/lib/mysql
      - ./mysql_init:/docker-entrypoint-initdb.d  # Baris Tambahan
    ``` 
6.  Restart docker dengan perintah: `docker-compose down` lalu `docker-compose up -d`.

---

## Akses dari Komputer Lain (Client App)

Agar Aplikasi Desktop bisa absen ke server ini:
1.  Cari tahu IP Address server ini (misal: `192.168.1.50`).
2.  Di Aplikasi Desktop, ubah settingan `API_URL` menjadi:
    `http://192.168.1.50:8001`

---

*Selamat! Server Absensi Anda sekarang berjalan otomatis.*
