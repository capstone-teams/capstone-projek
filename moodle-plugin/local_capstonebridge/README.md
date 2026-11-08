# Capstone Bridge (`local_capstonebridge`)

Local plugin Moodle yang menyediakan external function untuk membuat dan memperbarui activity (Page, Assignment, dan URL resource) melalui Moodle Web Service. Plugin ini merupakan mekanisme pembuatan activity yang dipilih pada DL-003, karena Moodle tidak menyediakan external function bawaan untuk membuat course module.

| Item               | Value                                            |
| ------------------ | ------------------------------------------------ |
| Component          | `local_capstonebridge`                           |
| Release            | 0.4.0 (`2026110800`)                             |
| Requires           | Moodle 4.5 (`2024100700`) atau lebih baru        |
| Teruji pada        | Moodle 4.5.14+ dan 4.5.15+                       |
| Modifikasi core    | Tidak ada                                        |

---

## 1. External Functions

| Function                             | Fungsi                                                         | Capability                                                   |
| ------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------ |
| `local_capstonebridge_create_page`   | Membuat Page (HTML) pada nomor section tertentu                | `moodle/course:manageactivities`, `mod/page:addinstance`     |
| `local_capstonebridge_update_page`   | Memperbarui nama, isi, deskripsi, dan section Page             | `moodle/course:manageactivities`                             |
| `local_capstonebridge_create_assign` | Membuat Assignment beserta nilai maksimum dan jenis submission | `moodle/course:manageactivities`, `mod/assign:addinstance`   |
| `local_capstonebridge_update_assign` | Memperbarui nama, deskripsi, due date, nilai, submission, dan section Assignment | `moodle/course:manageactivities`                             |
| `local_capstonebridge_create_url`    | Membuat URL resource (tautan referensi)                        | `moodle/course:manageactivities`, `mod/url:addinstance`      |
| `local_capstonebridge_update_url`    | Memperbarui nama, alamat, deskripsi, dan section URL resource  | `moodle/course:manageactivities`                             |

Aturan umum:

* **Idempotency.** Function `create_*` menerima `idnumber`, yang disimpan sebagai *ID number* activity. Bila activity dengan `idnumber` yang sama sudah ada pada course tersebut, function mengembalikan activity lama dengan `created = 0` tanpa membuat duplikat.
* **Section.** Nomor section yang belum ada dibuat otomatis oleh Moodle. Pada function `update_*`, nilai `section = -1` (default) berarti section tidak diubah.
* **Validasi.** Function `update_*` menolak `cmid` yang bukan milik `courseid` atau bukan jenis activity yang sesuai. `externalurl` harus berupa URL `http(s)` yang valid.
* Setiap function melakukan capability check Moodle pada context course atau module.

### 1.1 Pengaturan Assignment

| Parameter        | Keterangan                                           | Default `create` | Default `update`    |
| ---------------- | ---------------------------------------------------- | ---------------- | ------------------- |
| `grade`          | Nilai maksimum, 1 sampai `gradepointmax` site        | `100`            | `-1` (tidak diubah) |
| `onlinetext`     | `1`/`0` mengaktifkan submission online text           | `1`              | `-1` (tidak diubah) |
| `filesubmission` | `1`/`0` mengaktifkan submission file                  | `0`              | `-1` (tidak diubah) |
| `maxfiles`       | Jumlah file maksimal, 1 sampai batas site (bawaan 20) | `1`              | `-1` (tidak diubah) |
| `duedate`        | Unix timestamp, `0` berarti tanpa due date            | `0`              | `0`                 |

Ukuran file mengikuti batas course dan semua jenis file diterima. Pengaturan lain (feedback comment aktif, tanpa draft, tanpa batas attempt) mengikuti nilai tetap plugin. Pada `update_assign`, setting plugin submission yang tidak dikirim tetap dipertahankan, termasuk jumlah file maksimal dan batas ukuran.

---

## 2. Installation

### 2.1 Salin plugin ke Moodle

Folder `local_capstonebridge` harus berada di `<moodle_root>/local/capstonebridge` (nama folder tanpa awalan `local_`).

Instalasi biasa:

```bash
cp -r moodle-plugin/local_capstonebridge <moodle_root>/local/capstonebridge
```

Moodle di Docker:

```bash
docker cp moodle-plugin/local_capstonebridge <container>:<moodle_root>/local/capstonebridge
```

`<moodle_root>` adalah folder yang berisi `config.php` milik Moodle di dalam container. Pastikan pemilik file sama dengan user web server (misalnya `docker exec <container> chown -R www-data:www-data <moodle_root>/local/capstonebridge`).

### 2.2 Jalankan upgrade

Pilih salah satu:

* Login sebagai admin, lalu buka *Site administration → Notifications* dan klik *Upgrade Moodle database now*.
* Lewat CLI: `php <moodle_root>/admin/cli/upgrade.php --non-interactive` (untuk Docker, jalankan melalui `docker exec <container> ...`).

Setelah upgrade, plugin tampil di *Site administration → Plugins → Plugins overview* dengan nama **Capstone Bridge**.

### 2.3 Daftarkan function ke service

Buka *Site administration → Server → Web services → External services → Capstone Integration → Functions → Add functions*, lalu tambahkan keenam function pada bagian 1.

Untuk test live, tambahkan juga `mod_page_get_pages_by_courses`, `mod_url_get_urls_by_courses`, dan `mod_assign_get_assignments` bila belum ada.

### 2.4 Pastikan capability tersedia

Akun pemilik token membutuhkan capability pada tabel bagian 1, ditambah `mod/url:addinstance` untuk URL resource. Daftar lengkap ada di `docs/04. workflow/moodle-service-account.md`.

---

## 3. Update Plugin

1. Salin ulang folder plugin (bagian 2.1), timpa versi lama.
2. Jalankan upgrade (bagian 2.2). Moodle mendeteksi versi baru dari `version.php`.
3. Bila ada function baru, daftarkan ke service (bagian 2.3).

Setiap perubahan kode plugin wajib menaikkan `$plugin->version` di `version.php`; tanpa itu Moodle tidak mendaftarkan function baru.

---

## 4. Verification

Dari folder `backend`, dengan `MOODLE_BASE_URL` dan `MOODLE_WEB_SERVICE_TOKEN` di `.env` mengarah ke Moodle tersebut:

```bash
MOODLE_LIVE_TESTS=1 pytest tests/test_moodle_plugin_live.py -v
```

PowerShell:

```powershell
$env:MOODLE_LIVE_TESTS="1"; pytest tests/test_moodle_plugin_live.py -v
```

Test membuat beberapa course uji. Course tersebut tidak dihapus otomatis karena service tidak memiliki function hapus course.

---

## 5. Troubleshooting

| Gejala                                                       | Penyebab dan solusi                                                                 |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `Access control exception` / `accessexception`               | Function belum ditambahkan ke service (bagian 2.3).                                 |
| `required_capability_exception`                              | Akun pemilik token belum memiliki capability (bagian 2.4).                          |
| `Can't find data record in database table external_functions` | Upgrade belum dijalankan setelah plugin disalin atau diperbarui (bagian 2.2).     |
| Plugin tidak muncul di *Plugins overview*                    | Nama folder salah. Harus `local/capstonebridge`, bukan `local/local_capstonebridge`. |