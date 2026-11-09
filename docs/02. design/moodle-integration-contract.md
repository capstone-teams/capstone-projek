# Moodle Integration Contract & Capability Discovery

## 1. Document Information

| Item                  | Value                                                                      |
| --------------------- | -------------------------------------------------------------------------- |
| Document              | Moodle Integration Contract & Capability Discovery                         |
| Project               | Agentic AI untuk Mengisi Konten Moodle                                     |
| Version               | 0.1                                                                        |
| Status                | Draft                                                                      |
| Owner                 | Moodle Integration                                                         |
| Issue                 | #52 (BE-04.1), parent #48 (BE-04)                                          |
| Related Documents     | Moodle Integration Design, API Specification, Decision Log (DL-001–DL-003) |
| External System       | Moodle open-source, self-hosted oleh tim (DL-001)                          |
| Integration Mechanism | Moodle Web Service API (REST)                                              |
| Tested On             | Moodle 4.5 (instance lokal, Docker)                                        |
| Target Version        | Moodle 5.2 (DL-002), verifikasi ulang belum dilakukan                      |

---

## 2. Purpose

Dokumen ini mencatat hasil capability discovery terhadap Moodle yang digunakan tim dan menetapkan integration contract antara backend aplikasi dan Moodle.

Seluruh operasi Moodle yang diimplementasikan pada BE-04.2 sampai BE-04.7 mengacu pada dokumen ini. Capability yang belum diverifikasi langsung pada instance Moodle tidak dianggap tersedia, walaupun tercantum pada dokumentasi Moodle generik.

Issue awal menyebut Moodle ITK sebagai target. Sesuai DL-001, target integrasi diubah menjadi instance Moodle self-hosted yang dikelola tim, sehingga seluruh discovery pada dokumen ini dilakukan terhadap instance tersebut.

---

## 3. Integration Boundary

Backend merupakan satu-satunya komponen yang berkomunikasi dengan Moodle. Frontend dan agent tidak menerima URL maupun token Moodle.

```text
Frontend / Agent
   │
   ▼
Application Backend API
   │
   ▼
Moodle Integration Layer (adapter + service)
   │
   ▼
MoodleClient
   │
   ▼
Moodle Web Service API (REST)
   │
   ▼
Moodle LMS (self-hosted)
```

Integration contract memisahkan dua tingkat operasi:

* **Application Operation** = operasi yang dipahami sistem Capstone, misalnya *get course* atau *create learning material*.
* **Moodle Operation** = external function Moodle yang benar-benar dipanggil untuk menjalankan application operation tersebut.

Moodle Integration Layer bertanggung jawab menerjemahkan application operation menjadi Moodle operation. Bagian lain sistem tidak memanggil external function Moodle secara langsung.

---

## 4. Environment

| Item                    | Value                                                         | Status    |
| ----------------------- | ------------------------------------------------------------- | --------- |
| Moodle version (teruji) | 4.5, instance lokal berbasis Docker                           | Confirmed |
| Moodle version (target) | 5.2 (DL-002)                                                  | TBD       |
| Web Service             | Aktif melalui *Site administration → Server → Web services*   | Confirmed |
| Protocol                | REST, format JSON, endpoint `/webservice/rest/server.php`     | Confirmed |
| External service        | `Capstone Integration`                                        | Confirmed |
| API documentation       | Tersedia pada *Site administration → Server → Web services → API Documentation* | Confirmed |
| Integration account     | Akun administrator lokal                                      | Confirmed |
| Dedicated service user  | Akun integrasi dengan role terbatas                           | TBD       |

---

## 5. Authentication

| Item                 | Value                                                                                   | Status    |
| -------------------- | --------------------------------------------------------------------------------------- | --------- |
| Mechanism            | Web service token (`wstoken`) yang dibuat melalui *Manage tokens*                       | Confirmed |
| Token scope          | Terikat pada service `Capstone Integration` dan hanya dapat memanggil function di service tersebut | Confirmed |
| Token owner          | Terdaftar sebagai *Authorised user* pada service                                         | Confirmed |
| Backend configuration | `MOODLE_BASE_URL` dan `MOODLE_WEB_SERVICE_TOKEN` dibaca dari environment variable      | Confirmed |
| Credential isolation | Token tidak di-hardcode, tidak di-log, dan tidak dikirim ke Frontend maupun agent        | Confirmed |

---

## 6. External Functions dan Capability

### 6.1 Function pada Service `Capstone Integration`

| Function                             | Required capability (menurut Moodle)                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------ |
| `core_webservice_get_site_info`      | —                                                                                          |
| `core_course_get_courses`            | `moodle/course:view`, `moodle/course:update`, `moodle/course:viewhiddencourses`            |
| `core_course_get_courses_by_field`   | —                                                                                          |
| `core_course_get_contents`           | `moodle/course:update`, `moodle/course:viewhiddencourses`                                  |
| `core_course_create_courses`         | `moodle/course:create`, `moodle/course:visibility`                                         |
| `core_course_update_courses`         | `moodle/course:update`, `moodle/course:changecategory`, `moodle/course:changefullname`, `moodle/course:changeshortname`, `moodle/course:changeidnumber`, `moodle/course:changesummary`, `moodle/course:visibility` |
| `core_course_edit_section`           | —                                                                                          |
| `core_enrol_get_enrolled_users`      | `moodle/user:viewdetails`, `moodle/user:viewhiddendetails`, `moodle/course:useremail`, `moodle/user:update`, `moodle/site:accessallgroups` |
| `core_user_get_users`                | `moodle/user:viewdetails`, `moodle/user:viewhiddendetails`, `moodle/course:useremail`, `moodle/user:update` |
| `core_files_get_files`               | —                                                                                          |
| `mod_assign_get_assignments`         | —                                                                                          |
| `mod_quiz_get_quizzes_by_courses`    | `mod/quiz:view`                                                                            |
| `local_capstonebridge_create_page`   | `moodle/course:manageactivities`, `mod/page:addinstance`                                   |
| `local_capstonebridge_create_assign` | `moodle/course:manageactivities`, `mod/assign:addinstance`                                 |
| `local_capstonebridge_update_section` | `moodle/course:update` (BE-16.2)                                                          |

Tanda "—" berarti Moodle tidak menampilkan capability pada halaman *Functions*. Pemeriksaan capability tetap dilakukan di dalam function tersebut.

### 6.2 Function yang Dibutuhkan tetapi Belum Terdaftar

Function berikut digunakan oleh kode backend, tetapi belum ditambahkan ke service `Capstone Integration`:

| Function                          | Digunakan oleh                                      |
| --------------------------------- | --------------------------------------------------- |
| `core_courseformat_update_course` | Penambahan section (BE-04.7)                        |
| `core_update_inplace_editable`    | Penggantian nama section (BE-04.7)                  |
| `mod_page_get_pages_by_courses`   | Pembacaan isi Page pada course contents (BE-04.7)   |
| `enrol_manual_enrol_users`        | Enrolment akun uji (BE-04.5)                        |

---

## 7. Application-to-Moodle Operation Mapping

### 7.1 Status

* **Confirmed** = function sudah dipanggil dan berhasil pada instance Moodle lokal 4.5.
* **Candidate** = function tersedia pada service, tetapi belum diuji penuh.
* **TBD** = function belum diuji, belum terdaftar pada service, atau belum ada mekanismenya.

Status Confirmed berlaku untuk Moodle 4.5. Seluruh status perlu diverifikasi ulang pada Moodle 5.2 sebelum DL-002 berstatus Accepted.

### 7.2 Mapping

| Area               | Application Operation          | Moodle Operation                                      | Catatan hasil uji                                                                 | Status    |
| ------------------ | ------------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------------------- | --------- |
| Connection         | Check connection & version     | `core_webservice_get_site_info`                       | Mengembalikan nama site, versi, dan daftar function                               | Confirmed |
| Course             | List courses                   | `core_course_get_courses`                             | Course dengan format `site` (halaman depan) diabaikan                             | Confirmed |
| Course             | Get course                     | `core_course_get_courses` dengan `options[ids]`       | Parameter wajib dibungkus `options`; tanpa itu Moodle menolak dengan `Unexpected keys` | Confirmed |
| Course             | Find course by shortname       | `core_course_get_courses_by_field`                    | Berhasil                                                                          | Confirmed |
| Course             | Create course                  | `core_course_create_courses`                          | Berhasil melalui live test                                                        | Confirmed |
| Course             | Update course                  | `core_course_update_courses`                          | Berhasil melalui live test                                                        | Confirmed |
| Course             | Get course contents            | `core_course_get_contents`                            | Mengembalikan section beserta module                                              | Confirmed |
| Section            | Create section                 | Otomatis saat activity ditambahkan ke nomor section   | Moodle membuat section yang belum ada ketika activity ditambahkan ke section tersebut | Confirmed |
| Section            | Create section (eksplisit)     | `core_courseformat_update_course` (`section_add`)     | Belum terdaftar pada service                                                      | TBD       |
| Section            | Rename section                 | `core_update_inplace_editable`                        | Belum terdaftar pada service                                                      | TBD       |
| Section            | Update section name & summary  | `local_capstonebridge_update_section`                 | Berhasil pada Moodle 4.5.15+ dan 5.2.4+ melalui live test eksekusi struktur (BE-16.2) | Confirmed |
| Section            | Change section visibility      | `core_course_edit_section`                            | Terdaftar, belum diuji                                                            | Candidate |
| Learning material  | Create learning material (Page) | `local_capstonebridge_create_page`                   | Berhasil; idempotent melalui `idnumber`                                           | Confirmed |
| Learning material  | Read learning material (Page)  | `mod_page_get_pages_by_courses`                       | Belum terdaftar pada service                                                      | TBD       |
| File               | List files                     | `core_files_get_files`                                | Terdaftar, belum diuji                                                            | Candidate |
| File               | Upload file                    | `core_files_upload` / `/webservice/upload.php`        | Belum diuji, belum dibutuhkan MVP                                                 | TBD       |
| Assignment         | Create assignment              | `local_capstonebridge_create_assign`                  | Berhasil; idempotent melalui `idnumber`                                           | Confirmed |
| Assignment         | Read assignment                | `mod_assign_get_assignments`                          | Hanya mengembalikan course tempat pemilik token terdaftar                         | Confirmed |
| Quiz               | Read quiz                      | `mod_quiz_get_quizzes_by_courses`                     | Berhasil, hasil kosong pada course uji                                            | Confirmed |
| Quiz               | Create quiz & question         | —                                                     | Tidak ada function bawaan dan belum tersedia pada plugin                          | TBD       |
| Student            | List enrolled users            | `core_enrol_get_enrolled_users`                       | Berhasil                                                                          | Confirmed |
| Student            | Find user                      | `core_user_get_users`                                 | Berhasil                                                                          | Confirmed |
| Student            | Enrol user                     | `enrol_manual_enrol_users`                            | Belum terdaftar pada service                                                      | TBD       |
| Student            | Verify student access          | `core_enrol_get_enrolled_users` + login akun mahasiswa | Enrolment dapat dibaca; akses dari sisi akun mahasiswa belum diuji               | Candidate |

---

## 8. Capability yang Tidak Tersedia

| Capability                        | Kondisi                                                           | Penanganan                                                    |
| --------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| Create Page                       | Tidak ada external function bawaan Moodle                         | Local plugin `local_capstonebridge` (DL-003)                  |
| Create assignment                 | Tidak ada external function bawaan Moodle                         | Local plugin `local_capstonebridge` (DL-003)                  |
| Create quiz & question            | Tidak ada external function bawaan Moodle, belum ada pada plugin  | Ditunda (prioritas Should); fallback ke mock                  |
| Upload file                       | Belum diuji                                                       | Ditunda karena belum dibutuhkan MVP                           |

Local plugin tidak memodifikasi core Moodle dan hanya menambahkan external function yang dibutuhkan MVP.

---

## 9. Fallback & Mock Strategy

* Operasi yang belum tersedia pada instance yang terhubung menghasilkan `MoodleCapabilityUnavailableError`, sehingga sistem tidak mengembalikan hasil sukses palsu.
* `MockMoodleIntegration` mengikuti kontrak yang sama dengan adapter asli dan digunakan untuk development serta test ketika Moodle tidak tersedia.
* Kesamaan perilaku mock dan adapter asli dijaga oleh contract test.
* Error dari Moodle dinormalisasi ke kategori `authentication`, `permission`, `validation`, `transient`, dan `execution`, sehingga pemanggil tidak bergantung pada kode error Moodle yang spesifik.

---

## 10. Dependencies & Risks

| No | Dependency / Risk                                        | Dampak                                                       | Tindak lanjut                                                    |
| -- | -------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------- |
| 1  | Verifikasi pada Moodle 5.2 belum dilakukan               | Status Confirmed baru berlaku untuk 4.5                      | Upgrade instance Docker ke 5.2, lalu jalankan ulang live test    |
| 2  | Pengujian menggunakan akun administrator                 | Permission error pada akun terbatas belum terdeteksi         | Buat akun integrasi dengan role terbatas dan uji ulang           |
| 3  | Empat function pada bagian 6.2 belum terdaftar           | Endpoint section, pembacaan Page, dan enrolment belum dapat diuji | Tambahkan function ke service `Capstone Integration`         |
| 4  | Local plugin wajib terpasang pada setiap instance        | Pembuatan Page dan assignment gagal tanpa plugin             | Sertakan langkah instalasi plugin pada panduan setup             |
| 5  | Pembuatan quiz belum memiliki mekanisme                  | Konten quiz belum dapat dipublikasikan ke Moodle             | Diputuskan lebih lanjut melalui DL-003                           |

---

## 11. Usage untuk BE-04.2 sampai BE-04.5

| Subtask | Bagian yang menjadi acuan                                                       |
| ------- | ------------------------------------------------------------------------------- |
| BE-04.2 | Bagian 4 dan 5: protocol, endpoint, token, dan konfigurasi environment          |
| BE-04.3 | Bagian 3 dan 7: pemisahan application operation dan Moodle operation           |
| BE-04.4 | Bagian 7 dan 8: operasi berstatus Confirmed serta mekanisme melalui plugin      |
| BE-04.5 | Bagian 9 dan 10: fallback, mock, normalisasi error, dan live test               |

---

## 12. Conclusion

Operasi inti MVP sudah terverifikasi pada Moodle lokal 4.5: pemeriksaan koneksi, pembacaan dan pembuatan course, pembacaan isi course, pembuatan section melalui activity, serta pembuatan Page dan assignment melalui local plugin.

Operasi yang belum dapat diverifikasi ditandai Candidate atau TBD dan tidak dianggap sebagai capability yang tersedia. Dokumen ini diperbarui setelah verifikasi pada Moodle 5.2 dan setelah function pada bagian 6.2 ditambahkan.