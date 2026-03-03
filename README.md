# Absensi AI API

![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0-009688.svg?style=flat&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![MySQL](https://img.shields.io/badge/mysql-%2300f.svg?style=flat&logo=mysql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=flat&logo=PyTorch&logoColor=white)

Backend API untuk sistem absensi cerdas berbasis pengenalan wajah (Face Recognition). Dibangun untuk efisiensi, skalabilitas, dan kemudahan deployment menggunakan teknologi containerisasi modern.

## Tentang Project

Sistem ini dirancang untuk menangani proses absensi otomatis menggunakan kamera (CCTV/Webcam) dengan memanfaatkan Deep Learning untuk identifikasi wajah.

### Fitur Utama
*   **High Accuracy Face Recognition**: Menggunakan arsitektur Inception Resnet V1 (FaceNet) pre-trained pada dataset VGGFace2.
*   **Fast API Response**: Dibangun di atas FastAPI yang menawarkan performa tinggi (asynchronous).
*   **Anti-Spoofing Dasar**: Mekanisme validasi jarak euclidean dan confidence score.
*   **Containerized Environment**: Siap dijalankan di mana saja (Home Server, Cloud, Mini PC) tanpa "dependency hell".
*   **Database Agnostic**: Mendukung MySQL (Production) dan SQLite (Development/Test).
*   **Admin Dashboard Ready**: Terintegrasi dengan phpMyAdmin untuk manajemen data visual.

## Arsitektur Teknologi

*   **Framework**: FastAPI, Uvicorn
*   **ML Core**: PyTorch, Facenet-PyTorch, OpenCV
*   **Database**: MySQL 8.0, SQLAlchemy ORM
*   **Infrastructure**: Docker, Docker Compose

## Persiapan (Prerequisites)

Sebelum memulai, pastikan sistem Anda memiliki:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop) (Wajib untuk deployment mudah)
*   Git

## Panduan Instalasi (Deployment)

Kami merekomendasikan penggunaan Docker untuk isolasi yang sempurna.

### 1. Clone Repository
```bash
git clone https://github.com/eLsann/Api-Absensi.git
cd Api-Absensi
```

### 2. Konfigurasi Environment
Secara keamanan, tidak ada nilai default yang tersimpan di kode. Anda harus meng-copy file konfigurasi production dan mengisinya:
```bash
cp .env.production.example .env
# Windows: copy .env.production.example .env
```
*   **Wajib Diisi**: Anda **harus** mengisi nilai `SECRET_KEY`, `DATABASE_URL`, dan variabel lain berawalan `GANTI_` di file `.env` sebelum menjalankan server. Jika tidak diisi, aplikasi akan menolak untuk start (Fail-Fast).

### 3. Jalankan Server
Gunakan perintah Docker Compose untuk membangun dan menjalankan container:
```bash
docker-compose up -d --build
```

Layanan akan tersedia di:
*   **API Root**: `http://localhost:8001`
*   **API Documentation (Swagger)**: `http://localhost:8001/docs`
*   **Database Admin**: `http://localhost:8080` (Akses sesuai kredensial DB di `.env`)

## Pengembangan Lokal (Manual)

Jika Anda perlu menjalankan tanpa Docker untuk keperluan debugging:

```bash
# Buat Virtual Environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt

# Jalankan Server (Dev Mode)
python -m uvicorn app.main:app --reload
```

## Struktur Project

*   `/app`: Source code utama API.
*   `/scripts`: Alat bantu migrasi dan maintenance.
*   `/data`: Direktori untuk menyimpan file snapshot wajah.
*   `docker-compose.yml`: Orkestrasi service (API + Database).

## Lisensi

Project ini dilisensikan di bawah [MIT License](LICENSE).
