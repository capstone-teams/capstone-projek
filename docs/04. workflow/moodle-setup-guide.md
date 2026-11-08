# Panduan Setup Moodle (Docker) & Testing Integrasi

| Item | Value |
| :--- | :--- |
| **Status** | Draft |
| **Issue** | #48 (BE-04 Moodle Integration), #138 (BE-12 Moodle Activity Operations) |
| **Target Version** | Moodle 5.2 (DL-002), branch `MOODLE_502_STABLE` |
| **Teruji pada** | Moodle 4.5.14+ (moodle-docker, laptop Windows), Moodle 4.5.15+ dan 5.2.4+ (instance uji, PHP 8.3, PostgreSQL 16), serta upgrade 4.5.15+ → 5.2.4+ |
| **Related Documents** | `moodle-integration-contract.md`, `moodle-integration.md`, `design-api.md`, `development-workflow.md`, `panduan-restart-server.md`, `moodle-plugin/local_capstonebridge/README.md` |

---

## 1. Tujuan

Panduan ini menjelaskan cara membuat Moodle yang dipakai tim dari nol sampai siap dipakai backend: menjalankan Moodle di Docker, memasang plugin `local_capstonebridge`, menyiapkan Web Service, menghubungkan backend, lalu menguji seluruh pekerjaan integrasi Moodle (BE-04 dan BE-12).

Panduan ini ditulis supaya anggota tim bisa membuat Moodle yang **sama persis** dengan Moodle yang dipakai saat development, baik di laptop (bagian 4–12) maupun di server deploy (bagian 13), tanpa perlu bertanya lagi.

| Issue | Isi | Bagian terkait |
| :--- | :--- | :--- |
| BE-04.1 | Integration contract & capability discovery | 7 |
| BE-04.2 | Moodle client & health check | 10.2 |
| BE-04.3 | Mapping ID internal ↔ ID Moodle | 10.1 |
| BE-04.6 | Plugin `local_capstonebridge` (Page, Assignment, URL, Quiz) | 6, 10.2 |
| BE-04.7 | Endpoint `/api/v1/integrations/moodle` | 11 |
| BE-12.1 | Learning resource (URL) | 10.2 |
| BE-12.2 | Assignment | 10.2 |
| BE-12.3 | Quiz beserta soal pilihan ganda | 10.2 |

---

## 2. Gambaran Singkat

```text
Browser / Swagger  ─►  Backend FastAPI  ─►  Moodle (Docker, moodle-docker)
                             │
                             └─►  PostgreSQL aplikasi (Docker, docker compose)
```

| Komponen | Laptop (development) | Server (deploy) | Dijalankan lewat |
| :--- | :--- | :--- | :--- |
| Moodle | `http://localhost:8000` | `http://<IP-server>:8081` | `moodle-docker` |
| Backend | `http://localhost:8001` | `http://<IP-server>:8000` | Laptop: `uv run uvicorn`. Server: `docker compose` |
| Database aplikasi | `localhost:5432` | container `capstone-postgres` | `docker compose` (root repo) |

**Aturan penting**

1. **Alamat Moodle harus selalu sama persis dengan alamat saat instalasi (`wwwroot`).** Moodle memaksa redirect ke alamat itu. Kalau backend memanggil `127.0.0.1` padahal Moodle dipasang di `localhost` (atau sebaliknya), semua request gagal.
2. Di laptop, port **8000 dipakai Moodle**, jadi backend dijalankan di **8001**. Di server, port 8000 dipakai backend, jadi Moodle dipindah ke **8081**.
3. Data Moodle hanya aman bila memakai `local.yml` (bagian 4.4). Tanpa file itu, `bin/moodle-docker-compose down` membuat seluruh isi Moodle hilang.
4. Token Moodle hanya ditulis di `backend/.env` (laptop) atau `.env` root repo (server). **Jangan** ditulis di dokumen, chat, commit, atau screenshot.
5. Moodle 5.2 membutuhkan **PHP 8.3** dan **PostgreSQL 16** ke atas. Nilai bawaan `moodle-docker` (PHP 8.3, PostgreSQL 17) sudah memenuhi.

---

## 3. Prasyarat

| Kebutuhan | Cek | Catatan |
| :--- | :--- | :--- |
| Docker Desktop (Windows) / Docker Engine (Linux) | `docker --version`, `docker compose version`, `docker ps` | Docker harus sudah berjalan |
| Git (+ Git Bash di Windows) | `git --version` | Git Bash ikut terpasang bersama Git for Windows |
| Python 3.13 | `python --version` | Untuk backend |
| uv | `uv --version` | Belum ada: `pip install uv` |
| Ruang disk | ±6 GB | Image Docker ±2,5 GB, source Moodle ±700 MB, data |

Docker Desktop → **Settings → Resources**: CPU minimal 4, Memory minimal 4 GB (ideal 6–8 GB), lalu **Apply & restart**. Resource kecil adalah penyebab utama Moodle lambat (bagian 14).

Semua perintah `moodle-docker` dijalankan di **Git Bash** (Windows) atau terminal biasa (Linux). Script `bin/moodle-docker-compose` adalah file bash, jadi tidak jalan di CMD/PowerShell.

---

## 4. Pasang Moodle (sekali saja)

### 4.1 Clone dua repo

```bash
cd /c/
mkdir moodle-dev
cd moodle-dev
git clone -b MOODLE_502_STABLE https://github.com/moodle/moodle.git
git clone https://github.com/moodlehq/moodle-docker.git
ls
```

`ls` harus menampilkan dua folder: `moodle` dan `moodle-docker`. Clone `moodle` cukup besar (beberapa ratus MB), tunggu sampai selesai.

| Repo | Fungsi |
| :--- | :--- |
| `github.com/moodle/moodle` (branch `MOODLE_502_STABLE`) | Source code Moodle asli, versi 5.2.x |
| `github.com/moodlehq/moodle-docker` | Tools resmi tim Moodle untuk menjalankan source itu di Docker |

Di Linux (server), ganti `/c/moodle-dev` dengan folder lain, misalnya `~/moodle-dev`. Sesuaikan juga path di bagian 4.2.

> **Struktur folder Moodle 5.x berbeda dari 4.5.** Sejak Moodle 5.1, kode yang diakses browser ada di folder `public/`, sedangkan `config.php` tetap di root folder `moodle`. Image webserver `moodle-docker` mendeteksi folder `public/` secara otomatis, jadi tidak ada pengaturan tambahan. Yang perlu diingat hanya lokasi plugin: `moodle/public/local/...` (bagian 6).

### 4.2 Buat file environment

`moodle-docker` membaca konfigurasi dari environment variable, dan variabel itu hilang setiap kali terminal ditutup. Supaya tidak perlu mengetik ulang, simpan di satu file.

Buat file `/c/moodle-dev/moodle-env.sh`:

```bash
cat > /c/moodle-dev/moodle-env.sh <<'EOF'
export MOODLE_DOCKER_WWWROOT=/c/moodle-dev/moodle
export MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_PHP_VERSION=8.3
EOF
```

Setiap kali membuka Git Bash baru untuk Moodle, jalankan dulu:

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
```

> **Jangan mengubah isi file ini setelah Moodle terpasang.** Alamat Moodle (`wwwroot`) dihitung dari variabel ini. Server deploy memakai isi berbeda (bagian 13.2).

### 4.3 Salin `config.php`

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
cp config.docker-template.php $MOODLE_DOCKER_WWWROOT/config.php
```

`config.php` berada di root folder `moodle` (bukan di `public/`), baik untuk 4.5 maupun 5.2.

### 4.4 Buat `local.yml` agar data tidak hilang

Secara bawaan, `moodle-docker` **tidak** menyimpan database dan `moodledata` di named volume. Akibatnya:

| Perintah | Tanpa `local.yml` | Dengan `local.yml` |
| :--- | :--- | :--- |
| `stop` lalu `start` | Data aman | Data aman |
| `down` lalu `up -d` | **Seluruh isi Moodle hilang** (course, user, token, plugin terdaftar) | Data aman |
| Ubah environment lalu `up -d` | File `moodledata` hilang | Data aman |
| Laptop/server restart | Container tidak menyala sendiri | Container menyala sendiri |

Buat file `local.yml` di folder `moodle-docker`. `moodle-docker` memuat file ini otomatis.

```bash
cat > /c/moodle-dev/moodle-docker/local.yml <<'EOF'
services:
  webserver:
    restart: unless-stopped
    volumes:
      - moodledata:/var/www/moodledata
  db:
    restart: unless-stopped
    volumes:
      - moodledb:/var/lib/postgresql/data
  mailpit:
    restart: unless-stopped

volumes:
  moodledata:
  moodledb:
EOF
```

> Lakukan langkah ini **sebelum** `up -d` yang pertama. Kalau Moodle sudah terpasang tanpa `local.yml`, jangan menambahkannya begitu saja: container akan dibuat ulang dengan volume kosong. Untuk instalasi lama, cukup jangan pernah memakai `down` (pakai `stop`/`start`).

### 4.5 Nyalakan container

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose up -d
bin/moodle-docker-wait-for-db
bin/moodle-docker-compose ps
```

Pertama kali, `up -d` mengunduh ±2,5 GB image. Jangan di-cancel (Ctrl+C). Selesai bila prompt `$` kembali. `ps` harus menampilkan `webserver`, `db`, `exttests`, `mailpit`, dan `selenium` berstatus `Up`.

### 4.6 Install database Moodle

```bash
bin/moodle-docker-compose exec webserver php admin/cli/install_database.php --agree-license --fullname="Capstone Local" --shortname="capstone" --summary="Moodle local test" --adminuser=admin --adminpass="AdminPass123!" --adminemail=admin@example.com
```

Proses ini 1–5 menit. Tunggu sampai muncul `Installation completed successfully.` Buka `http://localhost:8000` dan login:

| Username | Password |
| :--- | :--- |
| `admin` | `AdminPass123!` |

Password ini hanya untuk Moodle lokal. Untuk server deploy, pakai password lain (bagian 13).

Cek versi: **Site administration → Notifications**, lalu lihat bagian bawah halaman. Harus tertulis `Moodle 5.2.x+`.

---

## 5. Pengaturan Dasar Moodle

### 5.1 Matikan mode debug (disarankan)

`config.docker-template.php` menyalakan debug developer, yang membuat Moodle jauh lebih lambat. Nilai ini dipaksa dari `config.php`, jadi **tidak bisa** dimatikan dari menu *Development → Debugging*.

Buka `/c/moodle-dev/moodle/config.php`, cari blok `// Debug options`, lalu ubah menjadi:

```php
// Debug options - possible to be controlled by flag in future..
$CFG->debug = 0;
$CFG->debugdisplay = 0;
$CFG->debugstringids = 0;
$CFG->perfdebug = 7;
$CFG->debugpageinfo = 0;
```

Simpan. Tidak perlu restart container. Kalau sedang mencari error plugin, kembalikan sementara ke `$CFG->debug = (E_ALL); $CFG->debugdisplay = 1;`.

### 5.2 Aktifkan web service, REST, dan layanan mobile

Login sebagai `admin`. Menu Moodle lambat saat pertama dibuka; tunggu, jangan klik ulang.

1. **Site administration → General → Advanced features**:
   * centang **Enable web services**;
   * centang **Enable web services for mobile devices** (dipakai akun mahasiswa uji untuk login lewat test, bagian 10.2);
   * **Save changes**.
2. **Site administration → Server → Web services → Manage protocols**: klik ikon mata **REST protocol** sampai aktif (enabled).

> Halaman *Site administration → Mobile app* baru muncul setelah *Enable web services for mobile devices* dicentang. Tidak ada yang perlu diubah di sana.

---

## 6. Pasang Plugin `local_capstonebridge`

Moodle tidak menyediakan function bawaan untuk membuat activity (Page, Assignment, URL) lewat web service. Karena itu tim memakai plugin sendiri yang ada di repo: `moodle-plugin/local_capstonebridge` (DL-003). Detail function dan parameternya ada di `moodle-plugin/local_capstonebridge/README.md`.

| Versi plugin | Isi | Dibutuhkan oleh |
| :--- | :--- | :--- |
| 0.3.0 | Page, Assignment, URL (create & update) | BE-04.6, BE-12.1 |
| 0.4.0 | + nilai maksimum dan jenis submission Assignment | BE-12.2 |
| 0.5.0 | + Quiz beserta soal pilihan ganda dan kunci jawaban | BE-12.3 |

Selalu pakai plugin dari branch `develop` terbaru.

### 6.1 Salin plugin

Lokasi tujuan berbeda menurut versi Moodle:

| Versi Moodle | Folder tujuan |
| :--- | :--- |
| 5.2 | `moodle/public/local/capstonebridge` |
| 4.5 | `moodle/local/capstonebridge` |

Contoh (Moodle 5.2, repo capstone ada di `/c/capstone-projek`):

```bash
rm -rf /c/moodle-dev/moodle/public/local/capstonebridge
cp -r /c/capstone-projek/moodle-plugin/local_capstonebridge /c/moodle-dev/moodle/public/local/capstonebridge
ls /c/moodle-dev/moodle/public/local/capstonebridge
```

`ls` harus menampilkan `version.php`, `classes`, `db`, `lang`, `README.md`. Kalau yang muncul justru folder `local_capstonebridge`, berarti plugin tersalin bertingkat. Ulangi perintah `rm -rf` lalu `cp -r` di atas.

Folder `moodle` di-mount langsung ke container, jadi tidak perlu `docker cp`.

### 6.2 Jalankan upgrade

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose exec webserver php admin/cli/upgrade.php --non-interactive
```

Hasil benar: baris terakhir `... completed successfully.`. Cek di **Site administration → Plugins → Plugins overview**, cari **Capstone Bridge**. Versinya harus sama dengan `version.php` plugin (misalnya `2026110900` untuk 0.5.0).

Setiap kali plugin di repo berubah, ulangi 6.1 dan 6.2.

---

## 7. Siapkan Web Service Moodle (sekali saja)

### 7.1 Buat External Service

1. **Site administration → Server → Web services → External services → Add**.
2. Isi **Name**: `Capstone Integration`, centang **Enabled**, biarkan **Authorised users only** tercentang → **Add service**.
3. Pada service itu, klik **Add functions** dan tambahkan **26 function** berikut. Cari satu per satu; satu kotak isian bisa diisi beberapa function sekaligus sebelum **Add functions**.

| # | Function | Dipakai oleh |
| :-- | :--- | :--- |
| 1 | `core_webservice_get_site_info` | Health check & status (BE-04.2, BE-04.7) |
| 2 | `core_course_get_courses` | Daftar & detail course |
| 3 | `core_course_get_courses_by_field` | Cari course |
| 4 | `core_course_create_courses` | Buat course |
| 5 | `core_course_update_courses` | Ubah course |
| 6 | `core_course_get_contents` | Isi course (section & module) |
| 7 | `core_course_edit_section` | Section |
| 8 | `core_courseformat_update_course` | Tambah section (eksekusi struktur, BE-17) |
| 9 | `core_update_inplace_editable` | Ganti nama section (BE-17) |
| 10 | `core_enrol_get_enrolled_users` | Discovery BE-04.1 |
| 11 | `core_user_get_users` | Discovery BE-04.1 |
| 12 | `core_files_get_files` | Discovery BE-04.1 |
| 13 | `mod_assign_get_assignments` | Baca assignment (test) |
| 14 | `mod_quiz_get_quizzes_by_courses` | Baca quiz (test BE-12.3) |
| 15 | `mod_page_get_pages_by_courses` | Baca isi Page |
| 16 | `mod_url_get_urls_by_courses` | Baca URL resource (test BE-12.1) |
| 17 | `local_capstonebridge_create_page` | Plugin (BE-04.6) |
| 18 | `local_capstonebridge_update_page` | Plugin |
| 19 | `local_capstonebridge_create_assign` | Plugin (BE-12.2) |
| 20 | `local_capstonebridge_update_assign` | Plugin (BE-12.2) |
| 21 | `local_capstonebridge_create_url` | Plugin (BE-12.1) |
| 22 | `local_capstonebridge_update_url` | Plugin (BE-12.1) |
| 23 | `core_user_get_users_by_field` | Test akses mahasiswa (cari akun uji) |
| 24 | `enrol_manual_enrol_users` | Test akses mahasiswa (enrol akun uji) |
| 25 | `local_capstonebridge_create_quiz` | Plugin (BE-12.3) |
| 26 | `local_capstonebridge_update_quiz` | Plugin (BE-12.3) |

Function 17–22, 25, dan 26 baru muncul setelah plugin terpasang (bagian 6).

4. Pada service itu, buka **Authorised users** → tambahkan `admin`. **Tanpa ini token ditolak** dengan `invalidtoken`.

### 7.2 Buat token

1. **Site administration → Server → Web services → Manage tokens → Create token**.
2. **User**: `admin`, **Service**: `Capstone Integration` → **Save changes**.
3. Salin token (32 karakter) tanpa spasi di awal/akhir. Simpan hanya di `backend/.env` (bagian 9).

Token hanya tampil penuh sekali. Kalau hilang, hapus token lama lalu buat baru.

### 7.3 Cek token jalan

PowerShell/CMD (pakai `curl.exe` supaya tidak terpakai alias PowerShell). Ganti `TOKEN_KAMU`:

```
curl.exe "http://localhost:8000/webservice/rest/server.php?wstoken=TOKEN_KAMU&wsfunction=core_webservice_get_site_info&moodlewsrestformat=json"
```

Hasil benar: JSON berisi `"sitename":"Capstone Local"`, `"release":"5.2.x+ (Build: ...)"`, dan daftar `functions` berisi 26 function di atas.

> Response ini juga memuat `sitesecret` dan `userprivateaccesskey`. **Jangan** di-screenshot atau dibagikan. Backend hanya mengambil nama site, versi, dan daftar function.

| Hasil | Arti |
| :--- | :--- |
| `invalidtoken` | Token salah/ada spasi, atau `admin` belum jadi Authorised user |
| `accessexception` | Function belum ditambahkan ke service |
| Halaman HTML "Redirect" | Alamat tidak sama dengan `wwwroot` (misalnya memakai `127.0.0.1`, padahal terpasang di `localhost`) |

---

## 8. Data Uji di Moodle

### 8.1 Course contoh

1. **Site administration → Courses → Add a new course**.
2. **Full name** `Test Course Capstone`, **Short name** `test-capstone` → **Save and display**.
3. Catat ID dari URL (`.../course/view.php?id=2` → ID `2`).

Course `id=1` adalah front page Moodle, bukan course sungguhan; endpoint backend sengaja tidak menampilkannya.

### 8.2 Akun mahasiswa uji

Dipakai untuk membuktikan activity hasil backend bisa dibuka mahasiswa (acceptance criteria BE-12).

1. **Site administration → Users → Accounts → Add a new user**.
2. Isi:

| Field | Nilai |
| :--- | :--- |
| Username | `mhs.uji` |
| New password | `Mhs#12345` (bebas, catat) |
| First name / Last name | `Mahasiswa` / `Uji` |
| Email | `mhs.uji@example.com` |

3. **Create user**. Tidak perlu di-enrol manual; test akan meng-enrol akun ini ke course uji secara otomatis.

Pastikan **Enable web services for mobile devices** sudah aktif (bagian 5.2). Tanpa itu akun mahasiswa tidak bisa mendapat token dan test akses mahasiswa gagal dengan `servicenotavailable`.

---

## 9. Siapkan Backend (laptop)

Dari root repo, di terminal biasa (PowerShell/CMD):

```
git checkout develop
git pull origin develop
cd backend
uv sync
copy .env.example .env
```

Buka `backend/.env`, lalu ubah/isi baris berikut:

```
APP_ENV="development"
MOODLE_BASE_URL="http://localhost:8000"
MOODLE_WEB_SERVICE_TOKEN="isi-token-dari-7.2"
MOODLE_TIMEOUT_SECONDS=60
```

`MOODLE_TIMEOUT_SECONDS=60` dipakai karena Moodle di Docker Desktop sering lambat. Nilai bawaan backend adalah 10 detik.

Pastikan nilai database di `.env` sama dengan compose (default: `DB_HOST=localhost`, `DB_PORT=5432`, `DB_USER=postgres`, `DB_PASSWORD=postgres`, `DB_NAME=lms_moodle_db`).

> **Jebakan umum:** bila `MOODLE_BASE_URL` tidak ada di `.env`, backend memakai nilai bawaan `.env.example`, yaitu `http://localhost:8080/moodle` (salah). Cek tanpa menampilkan token:
>
> ```
> uv run python -c "from src.config.settings import settings; print(settings.MOODLE_BASE_URL)"
> ```
>
> Hasil benar: `http://localhost:8000`.

`.env` tidak boleh ikut commit. `git status` tidak boleh menampilkan `.env`.

### 9.1 Database aplikasi dan akun uji

```
cd ..
docker compose up -d db
docker compose ps
cd backend
uv run alembic upgrade head
uv run python -m scripts.seed_test_accounts --generate-passwords
```

Hanya service `db` yang dinyalakan (`up -d db`), karena service `backend` di compose memakai port 8000 yang sudah dipakai Moodle. Seed menampilkan password acak **sekali**; catat. Akun yang dibuat:

| Role | Username | Dipakai untuk |
| :--- | :--- | :--- |
| `INSTRUCTOR` (= dosen) | `dosen.demo` | Satu-satunya role yang boleh memanggil `/integrations/moodle` |
| `STUDENT` (= mahasiswa) | `11231023` | Membuktikan akses ditolak (403) |

Akun ini adalah akun **aplikasi**, berbeda dari akun Moodle `mhs.uji` di bagian 8.2.

### 9.2 Jalankan backend

```
uv run uvicorn src.main:app --reload --port 8001
```

Cek dari terminal lain:

```
curl.exe http://localhost:8001/health
```

Hasil: `{"status":"ok"}`. Dokumentasi interaktif (Swagger): `http://localhost:8001/docs`.

---

## 10. Testing Otomatis

### 10.1 Test tanpa Moodle

Dari folder `backend`:

```
uv run pytest
```

Test yang butuh PostgreSQL dilewati bila `db` tidak menyala; nyalakan dulu (`docker compose up -d db`) agar semuanya jalan. Test yang relevan untuk Moodle memakai Moodle tiruan, jadi tidak memerlukan Moodle sungguhan:

| File | Isi |
| :--- | :--- |
| `tests/test_moodle_client.py` | Client: token terkirim, error ternormalisasi, token tidak bocor ke log/exception |
| `tests/test_moodle_health.py` | Health check dan daftar function wajib |
| `tests/test_moodle_adapter.py` | Mapping ID internal ↔ ID Moodle, idempotency create course |
| `tests/test_moodle_mapping_sql.py` | Penyimpanan mapping di tabel `moodle_entity_mappings` |
| `tests/test_moodle_integration_service.py` | Status, daftar course, isi course, buat course dan section |
| `tests/test_moodle_routes.py` | Endpoint `/integrations/moodle`: role, environment, error, tanpa kebocoran token |
| `tests/test_moodle_resource_service.py` | BE-12.1: resource URL per minggu, tanpa duplikat |
| `tests/test_moodle_assignment_service.py` | BE-12.2: assignment, rubric, pengaturan submission |
| `tests/test_moodle_quiz_service.py` | BE-12.3: quiz, soal dan kunci jawaban, konfigurasi, soal dipertahankan bila sudah ada attempt |

Jalankan hanya test Moodle:

```
uv run pytest tests -k moodle -v
```

### 10.2 Test live ke Moodle sungguhan (opt-in)

Test live memanggil Moodle yang sedang menyala dan **dilewati secara default**. Syarat: bagian 4–8 selesai dan `backend/.env` benar.

| File | Isi | Jumlah test |
| :--- | :--- | :--- |
| `tests/test_moodle_client_live.py` | Token benar diterima, token salah ditolak dengan error yang rapi (BE-04.2) | 2 |
| `tests/test_moodle_plugin_live.py` | Semua function plugin: create, idempotency, update, pindah section, validasi (BE-04.6, BE-12.2, BE-12.3) | 16 |
| `tests/test_moodle_resource_live.py` | Resource URL di section minggu, tanpa duplikat, bisa dibuka mahasiswa (BE-12.1) | 3 |
| `tests/test_moodle_assignment_live.py` | Assignment di section minggu, pengaturan submission, bisa dibuka dan dikumpulkan mahasiswa (BE-12.2) | 3 |
| `tests/test_moodle_quiz_live.py` | Quiz 3 soal di section minggu, tanpa duplikat, update mengganti soal, dikerjakan mahasiswa sampai selesai, kunci jawaban benar (BE-12.3) | 3 |

Jalankan hanya file yang sudah ada di branch-mu.

PowerShell (dari folder `backend`):

```
$env:MOODLE_LIVE_TESTS="1"
$env:MOODLE_STUDENT_USERNAME="mhs.uji"
$env:MOODLE_STUDENT_PASSWORD="Mhs#12345"
uv run pytest tests/test_moodle_client_live.py tests/test_moodle_plugin_live.py tests/test_moodle_resource_live.py tests/test_moodle_assignment_live.py tests/test_moodle_quiz_live.py -v
Remove-Item Env:MOODLE_LIVE_TESTS, Env:MOODLE_STUDENT_USERNAME, Env:MOODLE_STUDENT_PASSWORD
```

CMD:

```
set MOODLE_LIVE_TESTS=1
set MOODLE_STUDENT_USERNAME=mhs.uji
set MOODLE_STUDENT_PASSWORD=Mhs#12345
uv run pytest tests/test_moodle_client_live.py tests/test_moodle_plugin_live.py tests/test_moodle_resource_live.py tests/test_moodle_assignment_live.py tests/test_moodle_quiz_live.py -v
set MOODLE_LIVE_TESTS=
set MOODLE_STUDENT_USERNAME=
set MOODLE_STUDENT_PASSWORD=
```

Hasil yang diharapkan: **27 passed** bila kelima file ada. Tanpa `MOODLE_STUDENT_USERNAME`/`MOODLE_STUDENT_PASSWORD`, tiga test mahasiswa ditandai *skipped*. Pada Moodle lokal yang lambat, run bisa beberapa menit; itu wajar.

Baris terakhir (mengosongkan variabel) wajib dijalankan agar `pytest` biasa tidak ikut memanggil Moodle.

Setiap run meninggalkan course uji (`Plugin Test`, `Resource Test`, `Assignment Test`, `Quiz Test`) di Moodle, karena service sengaja tidak punya function hapus course. Hapus lewat **Site administration → Courses → Manage courses and categories** bila mengganggu.

### 10.3 Cek mata sebagai mahasiswa (untuk bukti PR)

1. Buka browser mode *incognito*, login Moodle sebagai `mhs.uji`.
2. Buka course `Resource Test`, `Assignment Test`, atau `Quiz Test` yang terbaru.
3. Pastikan:
   * resource tampil di section minggu 2 dan bisa diklik;
   * assignment tampil di section minggu 3, deskripsinya memuat tabel **Kriteria Penilaian**, dan ada tombol **Add submission**;
   * quiz tampil di section minggu 4 dengan 3 soal dan bisa dikerjakan (**Attempt quiz**). Course quiz yang sudah dikerjakan test menampilkan attempt beserta kunci jawaban di halaman review.
4. Ambil screenshot. Pastikan tidak ada token di layar.

---

## 11. Testing Endpoint `/integrations/moodle` (BE-04.7)

Syarat: Moodle menyala (bagian 12), `.env` benar (bagian 9), database dan backend jalan di port 8001 (bagian 9.1–9.2).

### 11.1 Login dan pasang token di Swagger

1. Buka `http://localhost:8001/docs`.
2. Cari `POST /api/v1/auth/login` → **Try it out** → isi:

```json
{ "username": "dosen.demo", "password": "<password dari seed>" }
```

3. **Execute**. Salin nilai `access_token` dari response.
4. Klik **Authorize** (kanan atas), tempel token, **Authorize**, lalu **Close**. Sekarang semua request memakai akun dosen.

`access_token` ini adalah token aplikasi, berbeda dari token Moodle. Login ulang bila mendapat `401`.

### 11.2 Daftar endpoint

Semua di bawah prefix `/api/v1/integrations/moodle`, hanya untuk role `INSTRUCTOR`.

| Method | Path | Fungsi | Aktif |
| :--- | :--- | :--- | :--- |
| GET | `/status` | Status koneksi, versi Moodle, ketersediaan function | Semua environment |
| GET | `/courses` | Daftar course Moodle (tanpa front page) | Semua environment |
| GET | `/courses/{moodle_course_id}` | Detail satu course | Semua environment |
| GET | `/courses/{moodle_course_id}/contents` | Section & module persis seperti di Moodle | Semua environment |
| POST | `/courses` | Buat course di Moodle (uji) | **Hanya `APP_ENV=development`** |
| POST | `/courses/{moodle_course_id}/sections` | Buat section, atau ganti nama section yang sudah ada (uji) | **Hanya `APP_ENV=development`** |

`{moodle_course_id}` adalah ID di Moodle (angka di URL `course/view.php?id=`), bukan ID internal aplikasi.

### 11.3 Skenario uji

Jalankan berurutan. Kolom **Hasil** adalah yang harus terlihat di Swagger.

| # | Langkah | Hasil yang diharapkan |
| :-- | :--- | :--- |
| 1 | `GET /status` | `200`. `status: CONNECTED`, `connected: true`, `release` berisi `5.2`, `all_functions_available: true`, seluruh `functions` `available: true` |
| 2 | `GET /courses` | `200`. `courses` berisi `Test Course Capstone`. Course `id=1` (front page) **tidak** ada |
| 3 | `GET /courses/2` | `200`. `shortname: test-capstone`, `fullname: Test Course Capstone` |
| 4 | `GET /courses/2/contents` | `200`. Section 0 `General` berisi module `forum` (Announcements). Tidak ada field `fileurl` |
| 5 | `GET /courses/999999` | `404`, `error.code: RESOURCE_NOT_FOUND` |
| 6 | `GET /courses/0` | `422`, `error.code: VALIDATION_FAILED` |
| 7 | `POST /courses` body `{"fullname":"Course Uji PM","shortname":"uji-pm-1","category_id":1}` | `201`. Berisi `moodle_course_id` baru |
| 8 | `GET /courses/{id dari #7}` | `200`, data sama dengan #7 (terbaca kembali) |
| 9 | `GET /courses` | Course dari #7 ikut tampil |
| 10 | Ulangi #7 dengan `shortname` yang sama | `422`, `error.code: MOODLE_ERROR`, `details` memuat `category: validation` dan `moodle_code: shortnametaken` |
| 11 | `POST /courses/{id dari #7}/sections` body `{"name":"Minggu 1 - Pengantar","section_number":1}` | `201`. `section_number: 1`, `name` sesuai |
| 12 | Ulangi #11 dengan `{"name":"Minggu 1 - Pengantar Basis Data","section_number":1}` | `200` (bukan 201). `moodle_section_id` **sama** dengan #11, nama berubah |
| 13 | `POST /courses/{id dari #7}/sections` body `{"name":"Minggu 2 - ERD"}` | `201`. Section baru ditambahkan di akhir (`section_number: 2`) |
| 14 | `POST /courses/999999/sections` body `{"name":"x"}` | `404` (course dicek lebih dulu) |
| 15 | `POST /courses/{id dari #7}/sections` body `{"name":""}` | `422`, `VALIDATION_FAILED` |

### 11.4 Cek mata di Moodle (2 menit)

Respons benar belum cukup; bandingkan dengan Moodle sendiri.

1. Buka Moodle → **Site administration → Courses → Manage courses and categories**.
2. Pastikan course dari skenario #7 (`Course Uji PM`) benar-benar ada, dengan *short name* `uji-pm-1`.
3. Buka course itu. Section `Minggu 1 - Pengantar Basis Data` dan `Minggu 2 - ERD` harus terlihat.
4. Tambahkan satu Page/Assignment lewat UI Moodle, lalu panggil `GET /courses/{id}/contents` lagi. Module baru harus muncul. Ini membuktikan endpoint menampilkan **apa yang benar-benar ada di Moodle**, termasuk isi yang dibuat di luar aplikasi.
5. Kalau ada module berikon mata tercoret ("Hidden from students"), pastikan field `visible` pada response juga `false`.

### 11.5 Uji keamanan dan konfigurasi

| # | Skenario | Cara | Hasil yang diharapkan |
| :-- | :--- | :--- | :--- |
| A | Tanpa login | **Authorize → Logout**, panggil `GET /status` | `401`, `AUTHENTICATION_FAILED` |
| B | Bukan dosen | Login `11231023` (STUDENT), panggil `GET /status` | `403`, `AUTHORIZATION_DENIED` |
| C | Endpoint tulis di production | Set `APP_ENV="production"` dan `SECRET_KEY` sembarang minimal 32 karakter di `.env`, restart backend, panggil `POST /courses` | `404` `RESOURCE_NOT_FOUND`. Course **tidak** terbuat di Moodle. `GET /status` tetap `200` |
| D | Moodle mati | `bin/moodle-docker-compose stop`, panggil `GET /status` | `502`, `MOODLE_ERROR`, `category: transient`, `retryable: true`. Bukan `401` |
| E | Token Moodle salah | Ubah `MOODLE_WEB_SERVICE_TOKEN` jadi asal, restart backend, panggil `GET /status` | `502`, `MOODLE_ERROR`, `category: authentication`, `moodle_code: invalidtoken`. Bukan `401` (agar frontend tidak logout) |
| F | Alamat Moodle salah | Ubah `MOODLE_BASE_URL` ke `http://127.0.0.1:8000`, restart backend, panggil `GET /status` | `502`, `MOODLE_ERROR`, `category: execution`, `moodle_code: invalid_response` |
| G | Tidak ada kebocoran | Pada semua response di atas dan log terminal backend, cari token Moodle | Token **tidak** muncul. Response tidak memuat `sitesecret`, `username`/`userid` pemilik token, maupun URL berkas |

Setelah uji C–F, kembalikan `.env` ke nilai benar dan restart backend (`Ctrl+C`, lalu jalankan `uvicorn` lagi). Nyalakan lagi Moodle (`bin/moodle-docker-compose start`) setelah uji D.

### 11.6 Kode error yang akan terlihat

| HTTP | `error.code` | `category` | Penyebab |
| :--- | :--- | :--- | :--- |
| 401 | `AUTHENTICATION_FAILED` | — | Token aplikasi tidak ada/kedaluwarsa |
| 403 | `AUTHORIZATION_DENIED` | — | Bukan `INSTRUCTOR` |
| 404 | `RESOURCE_NOT_FOUND` | — | Course Moodle tidak ada, atau endpoint tulis nonaktif (bukan development) |
| 422 | `VALIDATION_FAILED` | — | Body/path salah bentuk |
| 422 | `MOODLE_ERROR` | `validation` | Moodle menolak data (misalnya shortname sudah dipakai) |
| 502 | `MOODLE_ERROR` | `authentication` | Token Moodle di backend ditolak |
| 502 | `MOODLE_ERROR` | `permission` | Function belum ada di service / tidak diizinkan |
| 502 | `MOODLE_ERROR` | `transient` | Moodle tidak terjangkau (aman diulang) |
| 502 | `MOODLE_ERROR` | `execution` | Moodle gagal memproses, atau balasan bukan JSON (alamat salah) |
| 504 | `MOODLE_ERROR` | `transient` | Moodle tidak menjawab dalam `MOODLE_TIMEOUT_SECONDS` |

Pesan error ke client selalu pesan tetap; teks mentah Moodle hanya masuk log server.

---

## 12. Rutin Harian (berhenti dan lanjut)

**Berhenti**

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose stop
```

**Lanjut lagi**

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose start
```

Tunggu 10–20 detik, buka `http://localhost:8000`. Lalu nyalakan database aplikasi dan backend seperti bagian 9.1 dan 9.2 (`docker compose up -d db`, lalu `uv run uvicorn ... --port 8001`).

| Perintah | Aman? | Keterangan |
| :--- | :--- | :--- |
| `bin/moodle-docker-compose stop` / `start` | Aman | Cara normal berhenti dan lanjut |
| `bin/moodle-docker-compose restart webserver` | Aman | Dipakai setelah ganti versi Moodle (bagian 15) |
| `bin/moodle-docker-compose up -d` | Aman **dengan** `local.yml` | Tanpa `local.yml`, isi `moodledata` hilang bila container dibuat ulang |
| `bin/moodle-docker-compose down` | Aman **hanya dengan** `local.yml` | Tanpa `local.yml`, seluruh isi Moodle hilang |
| `bin/moodle-docker-compose down -v` | **Tidak pernah** | Menghapus seluruh data Moodle, termasuk named volume. Instalasi harus diulang dari bagian 4.6 |

---

## 13. Deploy di Server

Bagian ini untuk menjalankan Moodle di server tim (mesin yang sama dengan backend, lihat `panduan-restart-server.md`). Langkahnya sama dengan bagian 4–8, dengan beberapa perbedaan karena port 8000 sudah dipakai backend dan Moodle harus bisa dijangkau dari container backend.

### 13.1 Tentukan alamat Moodle

Moodle dijangkau oleh **browser** dan oleh **container backend**. Keduanya harus memakai alamat yang sama, jadi `localhost` tidak bisa dipakai (di dalam container, `localhost` adalah container itu sendiri).

Cari IP server:

```bash
hostname -I
```

Pakai IP LAN pertama, misalnya `192.168.1.20`. Pastikan IP ini tetap (static/DHCP reservation). Kalau IP berubah, alamat Moodle ikut rusak.

| Item | Nilai contoh |
| :--- | :--- |
| Alamat Moodle (`wwwroot`) | `http://192.168.1.20:8081` |
| `MOODLE_BASE_URL` backend | `http://192.168.1.20:8081` (harus sama persis) |

### 13.2 Isi `moodle-env.sh` untuk server

```bash
mkdir -p ~/moodle-dev && cd ~/moodle-dev
git clone -b MOODLE_502_STABLE https://github.com/moodle/moodle.git
git clone https://github.com/moodlehq/moodle-docker.git

cat > ~/moodle-dev/moodle-env.sh <<'EOF'
export MOODLE_DOCKER_WWWROOT=$HOME/moodle-dev/moodle
export MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_PHP_VERSION=8.3
export MOODLE_DOCKER_WEB_HOST=192.168.1.20
export MOODLE_DOCKER_WEB_PORT=0.0.0.0:8081
EOF
```

`MOODLE_DOCKER_WEB_PORT=0.0.0.0:8081` membuat Moodle bisa diakses dari luar mesin. Tanpa `0.0.0.0:`, Moodle hanya terbuka untuk `127.0.0.1` dan container backend tidak bisa menjangkaunya.

Lanjutkan bagian 4.3 (salin `config.php`), **4.4 (`local.yml`, wajib di server)**, 4.5, dan 4.6. Ganti semua `/c/moodle-dev` dengan `~/moodle-dev`, dan pakai password admin yang kuat (bukan `AdminPass123!`). Setelah itu kerjakan bagian 5.1 (matikan debug, wajib di server), 5.2, 6, 7, dan 8. Uji token dengan:

```bash
curl -s "http://192.168.1.20:8081/webservice/rest/server.php?wstoken=TOKEN_KAMU&wsfunction=core_webservice_get_site_info&moodlewsrestformat=json" | head -c 300
```

Dengan `restart: unless-stopped` di `local.yml`, Moodle menyala sendiri setelah server reboot.

### 13.3 Hubungkan backend di server

Container `backend` di `docker-compose.yml` tidak membaca `backend/.env` (file itu sengaja tidak masuk image). Variabel Moodle harus dikirim lewat environment compose. Caranya tanpa mengubah file repo:

1. Di root repo server (`~/capstone-projek`), buat atau tambahkan `.env`. File ini sudah di-ignore git.

```bash
cd ~/capstone-projek
cat >> .env <<'EOF'
MOODLE_BASE_URL=http://192.168.1.20:8081
MOODLE_WEB_SERVICE_TOKEN=isi-token-dari-7.2
MOODLE_TIMEOUT_SECONDS=30
EOF
```

2. Buat `docker-compose.override.yml` di root repo server. Compose memuatnya otomatis bersama `docker-compose.yml`.

```bash
cat > docker-compose.override.yml <<'EOF'
services:
  backend:
    environment:
      MOODLE_BASE_URL: ${MOODLE_BASE_URL}
      MOODLE_WEB_SERVICE_TOKEN: ${MOODLE_WEB_SERVICE_TOKEN}
      MOODLE_TIMEOUT_SECONDS: ${MOODLE_TIMEOUT_SECONDS:-30}
EOF
```

> `docker-compose.override.yml` khusus server dan **tidak boleh di-commit** (tidak termasuk `.gitignore`, jadi akan terlihat di `git status`). Token hanya ada di `.env`.

3. Terapkan dan cek:

```bash
docker compose up -d backend
docker compose exec backend .venv/bin/python -c "from src.config.settings import settings; print(settings.MOODLE_BASE_URL)"
docker compose exec backend .venv/bin/python -c "import urllib.request; print(urllib.request.urlopen('http://192.168.1.20:8081/login/index.php').status)"
```

Hasil benar: `http://192.168.1.20:8081`, lalu `200`. Setelah itu login ke Swagger backend server dan panggil `GET /api/v1/integrations/moodle/status`. Harus `connected: true`.

### 13.4 Catatan server

| Hal | Penjelasan |
| :--- | :--- |
| Container tambahan | `moodle-docker` ikut menyalakan `selenium`, `exttests`, dan `mailpit` (untuk testing Moodle). Ini wajar, hanya menambah pemakaian RAM |
| Email | Email Moodle tidak benar-benar terkirim; tertangkap `mailpit` di `http://<alamat-moodle>/_/mail/` |
| Cron | `moodle-docker` tidak menjalankan cron. Integrasi tidak membutuhkannya. Bila perlu (misalnya penghapusan course di background): `bin/moodle-docker-compose exec webserver php admin/cli/cron.php` |
| Akses dari internet | Panduan ini hanya untuk jaringan lokal/server. Membuka Moodle ke internet (tunnel/domain + HTTPS) membutuhkan `wwwroot` yang berbeda dan di luar cakupan dokumen ini |
| Firewall | Bila Moodle tidak terbuka dari laptop lain, izinkan port 8081 (misalnya `sudo ufw allow 8081/tcp`) |

---

## 14. Troubleshooting

| Gejala | Penyebab | Solusi |
| :--- | :--- | :--- |
| `port is already allocated` (8000) | Moodle dan backend sama-sama memakai 8000 | Laptop: jalankan backend dengan `--port 8001`; jangan `docker compose up` service `backend`. Server: Moodle di 8081 (bagian 13) |
| Halaman Moodle error *"... public directory ..."* (`rootdirpublic`) | Webserver masih mengarah ke root folder, biasanya setelah ganti 4.5 → 5.2 tanpa restart | `bin/moodle-docker-compose restart webserver` |
| Install/upgrade gagal karena versi PHP | `MOODLE_DOCKER_PHP_VERSION` di bawah 8.3 | Set `8.3` di `moodle-env.sh`, lalu `bin/moodle-docker-compose up -d` |
| Plugin tidak muncul di *Plugins overview* | Folder salah: plugin ada di `local/` padahal Moodle 5.2 membaca `public/local/`, atau tersalin bertingkat (`capstonebridge/local_capstonebridge`) | Ulangi bagian 6.1 dan 6.2 |
| Plugin berstatus *Missing from disk* | Folder plugin tidak ada di lokasi yang dibaca Moodle (sering terjadi setelah upgrade ke 5.2) | Salin plugin ke `public/local/capstonebridge`, lalu jalankan upgrade (bagian 6) |
| Function `local_capstonebridge_*` tidak bisa dicari di *Add functions* | Upgrade belum dijalankan setelah plugin disalin | Bagian 6.2 |
| Test plugin gagal: `Can't find data record in database table external_functions` | Sama seperti di atas | Bagian 6.2 |
| Test live gagal *"not valid JSON"* / HTTP 303, atau endpoint `502 execution invalid_response` | `MOODLE_BASE_URL` tidak sama persis dengan `wwwroot` (`localhost` lawan `127.0.0.1`, port beda), atau upgrade plugin belum dijalankan | Samakan `MOODLE_BASE_URL` dengan alamat di browser; jalankan bagian 6.2 |
| Test/endpoint `connection_error` | `MOODLE_BASE_URL` masih nilai bawaan `localhost:8080/moodle`, atau Moodle mati | Perbaiki `.env` (bagian 9), pastikan Moodle terbuka di browser |
| `invalidtoken` | Token salah/spasi, atau `admin` bukan Authorised user | Salin ulang token; tambahkan `admin` di Authorised users (7.1) |
| `accessexception` | Function belum ada di service | Tambahkan di *External services → Functions → Add functions* (7.1) |
| `status.all_functions_available: false` | Ada function wajib yang belum ditambahkan | Lihat `functions` yang `available: false`, tambahkan ke service |
| Test mahasiswa gagal: `servicenotavailable` / token mahasiswa tidak didapat | *Enable web services for mobile devices* belum aktif | Bagian 5.2 |
| Test mahasiswa gagal: akun tidak ditemukan | Akun `mhs.uji` belum dibuat atau username beda | Bagian 8.2; samakan `MOODLE_STUDENT_USERNAME` |
| Test assignment gagal di setting `grade`/`filesubmission` | Plugin masih 0.3.0 | Pasang plugin terbaru dari `develop` (bagian 6) |
| Test quiz gagal: `Can't find data record in database table external_functions` atau `accessexception` untuk `create_quiz` | Plugin masih 0.4.0, atau function quiz belum ditambahkan ke service | Pasang plugin 0.5.0 (bagian 6), lalu tambahkan function 25–26 (bagian 7.1) |
| `504` atau timeout pada panggilan pertama | Moodle lambat saat cache dingin | Panggil ulang. Naikkan `MOODLE_TIMEOUT_SECONDS` (60 di laptop). Matikan debug (5.1), naikkan CPU/RAM Docker, *Site administration → Development → Purge caches* |
| Moodle sangat lambat di Windows walau resource cukup | Source Moodle di drive Windows (`/c/...`) dibaca container lewat bind-mount yang lambat | Matikan debug (5.1). Alternatif: simpan `moodle-dev` di filesystem WSL2 (misalnya `\\wsl$\Ubuntu\home\<user>\moodle-dev`) dan jalankan perintah dari terminal WSL |
| Klik menu Moodle berputar lama | Resource Docker kurang | Naikkan CPU/RAM (bagian 3) |
| `curl` di PowerShell error aneh | `curl` adalah alias `Invoke-WebRequest` | Pakai `curl.exe` |
| `bin/moodle-docker-compose: command not found` | Memakai CMD/PowerShell, atau belum `cd` | Pakai Git Bash di folder `moodle-docker` |
| `Error: $MOODLE_DOCKER_WWWROOT is not set` | `moodle-env.sh` belum dijalankan di terminal ini | `source /c/moodle-dev/moodle-env.sh` |
| Moodle kosong setelah restart | Container dibuat ulang tanpa `local.yml` (`down` lalu `up`) | Ulangi bagian 4.6 sampai 8. Untuk instalasi berikutnya pakai `local.yml` (4.4) |
| Backend gagal start: koneksi database | `db` belum menyala | `docker compose up -d db`, tunggu `healthy` |
| `alembic upgrade head` gagal pada database lama | Histori migrasi ditulis ulang | `docker compose down -v` di **root repo** (menghapus database aplikasi, bukan Moodle), lalu `up -d db` dan migrasi ulang |
| Server: backend `connected: false` tapi Moodle terbuka di browser | Container backend belum menerima `MOODLE_*`, atau `MOODLE_DOCKER_WEB_PORT` tanpa `0.0.0.0:` | Bagian 13.2 dan 13.3 |

---

## 15. Upgrade Moodle 4.5 ke 5.2

Untuk yang sudah memasang Moodle 4.5 dengan panduan versi sebelumnya (`MOODLE_405_STABLE`). Moodle 5.2 bisa di-upgrade langsung dari 4.4 ke atas. Course, user, service, token, dan akun uji tetap ada.

### 15.1 Backup dulu

```bash
source /c/moodle-dev/moodle-env.sh
cd /c/moodle-dev/moodle-docker
mkdir -p /c/moodle-dev/backup
bin/moodle-docker-compose exec -T db pg_dump -U moodle moodle > /c/moodle-dev/backup/moodle-45.sql
MSYS_NO_PATHCONV=1 bin/moodle-docker-compose exec -T webserver tar -C /var/www -cf - moodledata > /c/moodle-dev/backup/moodledata-45.tar
ls -lh /c/moodle-dev/backup
```

Kedua file harus berukuran lebih dari 0. `MSYS_NO_PATHCONV=1` mencegah Git Bash mengubah `/var/www` menjadi path Windows (di Linux tidak perlu).

### 15.2 Ganti source ke 5.2

```bash
cd /c/moodle-dev/moodle
git status
git fetch origin
git checkout -b MOODLE_502_STABLE origin/MOODLE_502_STABLE
```

`git status` sebelum checkout seharusnya hanya menampilkan folder *untracked* `local/capstonebridge/` (`config.php` sudah di-ignore oleh repo Moodle). Kalau ada file Moodle lain yang berubah, jangan lanjut; tanyakan dulu.

`config.php` tetap di tempatnya dan tidak perlu diubah.

### 15.3 Pindahkan plugin, restart, upgrade

```bash
rm -rf /c/moodle-dev/moodle/local/capstonebridge
rm -rf /c/moodle-dev/moodle/public/local/capstonebridge
cp -r /c/capstone-projek/moodle-plugin/local_capstonebridge /c/moodle-dev/moodle/public/local/capstonebridge

cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose restart webserver
bin/moodle-docker-compose exec webserver php admin/cli/upgrade.php --non-interactive
```

`restart webserver` wajib, supaya webserver mendeteksi folder `public/`. Upgrade 4.5 → 5.2 butuh beberapa menit. Hasil benar: baris terakhir `... completed successfully.`

Kalau plugin lupa dipindah, core tetap ter-upgrade, tetapi plugin berstatus *Missing from disk* dan semua function `local_capstonebridge_*` gagal. Salin plugin ke `public/local/capstonebridge`, lalu jalankan upgrade sekali lagi.

### 15.4 Cek setelah upgrade

1. **Site administration → Notifications**: versi `5.2.x+`, tidak ada upgrade tertunda.
2. **Plugins overview**: Capstone Bridge berstatus normal (bukan *Missing from disk*).
3. *Site administration → Development → Purge caches → Purge all caches*.
4. Jalankan `curl.exe` bagian 7.3 dengan token lama. `release` harus `5.2.x+`.
5. Jalankan test live bagian 10.2. Target sama: **27 passed**.

Token, service *Capstone Integration*, dan akun `mhs.uji` tidak perlu dibuat ulang.

### 15.5 Kalau harus kembali ke 4.5

```bash
cd /c/moodle-dev/moodle
git checkout MOODLE_405_STABLE
rm -rf /c/moodle-dev/moodle/public/local/capstonebridge
cp -r /c/capstone-projek/moodle-plugin/local_capstonebridge /c/moodle-dev/moodle/local/capstonebridge
cd /c/moodle-dev/moodle-docker
bin/moodle-docker-compose stop webserver
bin/moodle-docker-compose exec -T db psql -U moodle -d postgres -c "DROP DATABASE moodle;" -c "CREATE DATABASE moodle OWNER moodle;"
bin/moodle-docker-compose exec -T db psql -U moodle -d moodle < /c/moodle-dev/backup/moodle-45.sql
bin/moodle-docker-compose start webserver
MSYS_NO_PATHCONV=1 bin/moodle-docker-compose exec -T webserver sh -c "rm -rf /var/www/moodledata/* && tar -C /var/www -xf -" < /c/moodle-dev/backup/moodledata-45.tar
bin/moodle-docker-compose restart webserver
```

Webserver dihentikan dulu supaya database tidak sedang dipakai saat dihapus.

Database Moodle tidak bisa diturunkan versinya tanpa backup, jadi langkah 15.1 wajib.

---

## 16. Checklist Sebelum Menyatakan Selesai

- [ ] Moodle terbuka di alamatnya (`http://localhost:8000` atau alamat server), login `admin` berhasil, versi `5.2.x+`.
- [ ] `local.yml` ada di folder `moodle-docker` (wajib di server).
- [ ] Debug dimatikan di `config.php` (wajib di server).
- [ ] Plugin Capstone Bridge terpasang dengan versi sama dengan `develop`.
- [ ] Web service aktif, REST aktif, *Enable web services for mobile devices* aktif.
- [ ] Service `Capstone Integration` berisi 26 function, `admin` terdaftar sebagai Authorised user.
- [ ] `curl` ke `core_webservice_get_site_info` mengembalikan JSON dengan `release` `5.2.x+`.
- [ ] Akun Moodle `mhs.uji` ada.
- [ ] `MOODLE_BASE_URL` sama persis dengan alamat Moodle di browser; `.env` tidak muncul di `git status`.
- [ ] `uv run pytest` tidak memiliki test Moodle yang gagal.
- [ ] Test live (10.2): 27 passed, lalu variabel `MOODLE_LIVE_TESTS` dikosongkan.
- [ ] Skenario 1–15 (11.3) sesuai hasil yang diharapkan.
- [ ] Cek mata (10.3 dan 11.4) sesuai.
- [ ] Uji keamanan A–G (11.5) sesuai.
- [ ] Tidak ada token Moodle di response, log, dokumen, maupun screenshot.