# Panduan Deployment Absensi API ke Home Server
Dokumen ini adalah satu-satunya panduan yang Anda butuhkan untuk menjalankan API Absensi di Home Server Anda. Kami telah menyederhanakan prosesnya menjadi **SATU** perintah saja.

---

## Cara Menjalankan (Deployment)

### Persiapan Awal
1.  Pastikan Desktop/Server Anda sudah terinstall **Docker Desktop**.
2.  Pastikan Anda memiliki folder project `Api-Absensi` ini.

### Langkah-langkah
1.  **Duplicate Env File**:
    Copy file konfigurasi contoh agar aktif:
    ```bash
    copy .env.example .env
    ```
    *(Jangan khawatir, file `.env` ini aman dan tidak akan ter-upload ke GitHub)*

2.  **Jalankan Docker**:
    ```bash
    docker-compose up -d --build
    ```

3.  **SELESAI!** 
    -   API Anda sekarang aktif di: `http://localhost:8001`
    -   Dashboard Database: `http://localhost:8080` (Login: `root` / `root`)

---

## Apakah Saya Perlu Setting `.env`?

**YA, SEKALI SAJA.**
Karena setup ini dirancang aman untuk publik (GitHub), password database tidak lagi di-hardcode di dalam kode.

Nilai default di `.env.example` sudah diset ke `root` / `root`. Jadi jika Anda hanya copy-paste file tersebut, aplikasi **PASTI LANGSUNG JALAN** tanpa error.

Namun, untuk keamanan (setelah deploy), silakan ubah `SECRET_KEY` dan password database di file `.env` Anda sendiri.

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
