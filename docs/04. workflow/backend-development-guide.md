# Backend Development & Testing Guide

| Item | Value |
| :--- | :--- |
| **Status** | Draft |
| **Related Documents** | `moodle-integration-guide.md`, `moodle-integration-contract.md`, `development-workflow.md` |

## 1. Tujuan
Panduan ini menjelaskan cakupan integrasi Moodle, cara menyiapkan lingkungan, menjalankan backend, menjalankan test, menyiapkan Moodle lokal, dan checklist sebelum push — sehingga siapa pun dapat mencoba atau melanjutkan pekerjaan backend tanpa bertanya lebih dulu.

## 2. Prasyarat
- Python 3.13
- Docker Desktop (pastikan sudah berjalan)
- Git

Quickstart (asumsi dependency sudah terpasang, venv ada di root repo):

```
.venv\Scripts\activate
cd backend
pytest
```

Setup lengkap dari nol ada di bagian 4. Detail dan daftar perintah test ada di bagian 6.

## 3. Cakupan & Batasan Integrasi Moodle
`MoodleAdapter` mencakup:
- Mengambil informasi course.
- Membuat dan memperbarui course.
- Mencari course berdasarkan `shortname` (juga dipakai memulihkan `create_course` setelah timeout).
- Mengambil section dan module dari course.
- Memetakan ID internal aplikasi ke ID Moodle.
- Memeriksa kesehatan koneksi Moodle (health check).
- Menangani operasi yang belum didukung agar tidak memberi hasil sukses palsu.

**Batasan:** operasi pembuatan/pengubahan section, resource, assignment, dan quiz belum boleh dianggap tersedia sebelum implementasi dan pengujiannya dikonfirmasi.

Status setiap operasi mengikuti legenda berikut, dan acuan lengkapnya ada di `moodle-integration-contract.md`:

| Status | Keterangan |
| :--- | :--- |
| **Confirmed (local)** | Sudah dijalankan dan berhasil pada Moodle lokal. |
| **Candidate** | Terdaftar pada service/dokumentasi, belum diuji penuh. |
| **TBD / Not Available** | Belum teridentifikasi atau belum ada function core resmi yang sesuai. |

Jangan menganggap function berhasil hanya karena terdaftar di Moodle — status di atas harus disesuaikan dengan hasil pengujian aktual.

## 4. Setup Awal

### 4.1 Virtual environment dan dependency
Dari root repository:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

Venv ada di root repo, bukan di `backend` — jadi aktivasi harus dilakukan sebelum `cd backend`, bukan sesudahnya.

### 4.2 Environment
Salin `backend\.env.example` menjadi `backend\.env`, lalu isi:

| Variabel | Isi |
| :--- | :--- |
| `DB_PASSWORD` | Samakan dengan password pada `docker-compose.yml` |
| `SECRET_KEY` | Bebas untuk development lokal |
| `MOODLE_BASE_URL` | Alamat Moodle lokal, misalnya `http://localhost:8000` |
| `MOODLE_WEB_SERVICE_TOKEN` | Token dari bagian 7.2 |

File `.env` tidak boleh di-commit.

### 4.3 Database
Dari root repository:

```
docker compose up -d db
docker compose ps
```
Pastikan `capstone-postgres` berstatus `healthy`. Gunakan `up -d db`, bukan `up -d` saja, karena container backend memakai port 8000 yang bentrok dengan Moodle lokal.

Lalu jalankan migration:

```
cd backend
alembic upgrade head
```

## 5. Menjalankan Backend
Dari folder `backend`:

```
uvicorn src.main:app --reload --port 8001
```
Dokumentasi API tersedia di `http://localhost:8001/docs`. Port 8001 dipakai supaya tidak bentrok dengan Moodle lokal di port 8000.

## 6. Menjalankan Test
Dari folder `backend`:

| Perintah | Fungsi |
| :--- | :--- |
| `pytest` | Seluruh test. Tidak membutuhkan Moodle |
| `pytest tests\test_moodle_contract.py -v` | Memeriksa mock dan adapter Moodle satu kontrak |
| `pytest tests\test_moodle_live.py -v` | Test ke Moodle sungguhan (lihat bagian 7.4) |

Test yang membutuhkan PostgreSQL otomatis dilewati kalau database belum menyala, dan test live dilewati kalau tidak diaktifkan. Hasil yang diharapkan: semua test lulus, dengan sebagian dilewati sesuai kondisi di atas.

## 7. Moodle Lokal

### 7.1 Menyalakan Moodle
Gunakan [moodle-docker](https://github.com/moodlehq/moodle-docker) dengan kode sumber Moodle, lalu buka `http://localhost:8000`. Versi yang sudah diuji adalah Moodle 4.5.14+; verifikasi pada Moodle 5.2 sedang dikerjakan.

### 7.2 Mengaktifkan web service (sekali saja)
Sebagai administrator di Moodle:

1. Aktifkan web service dan protokol REST: *Site administration > Server > Web services > Overview*.
2. Buat external service bernama `Capstone Integration`, lalu tambahkan 12 function yang tercantum pada bagian 4 `moodle-integration-contract.md`.
3. Buat token: *Site administration > Server > Web services > Manage tokens*, untuk user yang terdaftar sebagai *Authorised user* pada service tersebut.
4. Salin token ke `MOODLE_WEB_SERVICE_TOKEN` di `backend\.env`. Token bersifat rahasia dan tidak boleh ditulis di dokumen, commit, atau chat.

### 7.3 Cek cepat
Buka di browser (ganti `TOKEN` dengan tokenmu):

```
http://localhost:8000/webservice/rest/server.php?wstoken=TOKEN&wsfunction=core_webservice_get_site_info&moodlewsrestformat=json
```
Kalau berhasil, muncul JSON berisi versi Moodle.

### 7.4 Test live
Dengan Moodle menyala dan `.env` terisi:

```
set MOODLE_LIVE_TESTS=1
pytest tests\test_moodle_live.py -v
set MOODLE_LIVE_TESTS=
```
Hasil yang diharapkan: 4 test `PASSED`. Test ini membuat course uji di Moodle lokal (`Integration Test Updated`) setiap kali dijalankan. Hapus lewat *Site administration > Courses* bila perlu. Jangan jalankan terhadap Moodle ITK.

## 8. Masalah Umum

| Gejala | Penyebab | Solusi |
| :--- | :--- | :--- |
| `ConnectionRefusedError` saat `alembic` atau test Postgres | Database belum menyala | `docker compose up -d db` |
| `port is already allocated` pada port 8000 | Container backend bentrok dengan Moodle lokal | Gunakan `docker compose up -d db`, dan jalankan backend dengan `uvicorn` di port 8001 |
| Test live: `Could not connect to Moodle` | `MOODLE_BASE_URL` salah atau Moodle mati. Nilai bawaan `.env.example` mengarah ke `http://localhost:8080/moodle` | Isi `MOODLE_BASE_URL` di `backend\.env` dan pastikan Moodle menyala |
| Test live: timeout | Moodle lokal lambat pada permintaan pertama | Tunggu Moodle hangat, atau tambah memori Docker Desktop |
| Test live: `invalidtoken` | Token salah atau user bukan *Authorised user* | Buat ulang token (bagian 7.2) |
| Test live: `accessexception` | Function belum ditambahkan ke service | Tambahkan function yang kurang |
| Test live: health check gagal | Endpoint atau kredensial yang dipakai `MoodleClient` salah | Periksa `MOODLE_BASE_URL` dan `MOODLE_WEB_SERVICE_TOKEN` di `.env` |
| `alembic heads` menampilkan dua baris | Migration bercabang | Jangan hapus migration, kabari tim |

## 9. Checklist Sebelum Push

1. **Periksa perubahan** — dari root repository: `git status`, `git diff`, `git diff --check`. Pastikan tidak ada perubahan tidak disengaja, whitespace error, token, atau file `.env` yang ikut masuk commit.
2. **Jalankan test unit** — dari folder `backend`: `pytest` (mencakup `test_moodle_contract.py`). Pastikan test yang relevan lulus.
3. **Jalankan test live jika perubahan menyentuh Moodle Integration Layer** — lihat bagian 7.4. Periksa hasil aktual, termasuk test yang gagal atau dilewati.
4. **Periksa backend** — pastikan backend jalan sesuai bagian 5, tanpa error startup.
5. **Commit dan push** — dari root repository:
```
   git add backend
   git commit -m "pesan commit"
   git push
```
   Kalau dokumen di `docs` ikut berubah, tambahkan eksplisit, misalnya: `git add "docs/02. design/moodle-integration-contract.md"`. Jangan pakai `git add .` tanpa cek `git status` lebih dulu.

## 10. Catatan Teknis
- HTTP 200 tidak selalu berarti operasi Moodle berhasil — periksa isi response, termasuk `warnings` dan exception.
- Test unit (mock) tidak menggantikan test live; untuk perubahan di integrasi Moodle, jalankan keduanya sebelum push.
- Jumlah test dan status kelulusan mengikuti hasil aktual pada branch yang sedang diuji, bukan angka di dokumen ini kalau branch sudah berubah.
- Jangan menghapus atau mengubah data Moodle bersama tanpa memastikan dampaknya.
- Jangan menjalankan test live terhadap Moodle ITK.

## 11. Dokumen Terkait
- Struktur dan cara memakai integrasi Moodle: `moodle-integration-guide.md`
- Hasil capability discovery Moodle: `moodle-integration-contract.md`
- Alur Git dan PR: `development-workflow.md`