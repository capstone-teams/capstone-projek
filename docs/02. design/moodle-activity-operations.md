# Moodle Activity Operations (BE-12)

| Item | Value |
| :--- | :--- |
| **Status** | Draft |
| **Issue** | #138 (BE-12), #139 (BE-12.1), #140 (BE-12.2), #141 (BE-12.3) |
| **Teruji pada** | Moodle 4.5.14+, 4.5.15+, dan 5.2.4+ dengan plugin `local_capstonebridge` 0.5.0 |
| **Related Documents** | `content-schema.md` (§14–§19, §32), `moodle-integration-contract.md`, `04. workflow/moodle-setup-guide.md`, `moodle-plugin/local_capstonebridge/README.md` |

---

## 1. Tujuan

Dokumen ini menjelaskan bagaimana konten hasil generation (resource, assignment, quiz) dipasang ke Moodle sebagai activity pada section minggu yang sesuai, tanpa input manual dosen, dan tanpa duplikat bila dieksekusi ulang.

Cara menyiapkan Moodle dan menjalankan test ada di `04. workflow/moodle-setup-guide.md`.

---

## 2. Gambaran

```text
activities / contents (database aplikasi)
        │  AssignmentData, QuizData, data resource
        ▼
Moodle*Service.publish(moodle_course_id, week, konten)
        │  validasi → cek mapping → create atau update
        ▼
MoodleClient ──► plugin local_capstonebridge ──► activity di section "week"
        │
        └─► moodle_entity_mappings (ID internal ↔ cmid Moodle)
```

| Konten | Sumber data | Service | Activity Moodle | Function plugin |
| :--- | :--- | :--- | :--- | :--- |
| Resource (BE-12.1) | Content Schema §14 | `MoodleResourceService` | URL | `create_url`, `update_url` |
| Assignment (BE-12.2) | `AssignmentData` (§15–§16) | `MoodleAssignmentService` | Assignment | `create_assign`, `update_assign` |
| Quiz (BE-12.3) | `QuizData` (§17–§19) | `MoodleQuizService` | Quiz + soal pilihan ganda | `create_quiz`, `update_quiz` |

Ketiga service ada di `backend/src/services/`.

---

## 3. Aturan Umum

### 3.1 Section dan minggu

Nomor minggu dipakai langsung sebagai nomor section Moodle. Bila section belum ada, Moodle membuatnya dengan nama bawaan. Penamaan section (`Minggu N - judul`) adalah tugas eksekusi struktur (BE-17). Saat disambungkan, nomor section yang dipakai BE-12 harus sama dengan nomor section yang dibuat BE-17.

### 3.2 Idempotency

| Lapisan | Isi | Fungsi |
| :--- | :--- | :--- |
| `moodle_entity_mappings` | `entity_type` + ID internal → `cmid` | Eksekusi ulang menjadi update, bukan create |
| ID number activity | `capstone-resource-<id>`, `capstone-assignment-<id>`, `capstone-quiz-<id>` | Bila proses terhenti setelah create tetapi sebelum mapping tersimpan, eksekusi berikutnya memakai activity yang sama |

| Konten | `entity_type` |
| :--- | :--- |
| Resource | `url_resource` |
| Assignment | `assignment` |
| Quiz | `quiz` |

Alur `publish()`:

1. Validasi data. Data tidak valid ditolak sebelum Moodle dipanggil.
2. Mapping belum ada → `create_*` dengan ID number. Bila Moodle menjawab `created = 0` (activity sudah ada), activity itu diperbarui dengan data terbaru.
3. Mapping sudah ada → `update_*` (isi, pengaturan, dan section).
4. `cmid` disimpan ke mapping. Error Moodle tidak menyimpan mapping.

### 3.3 Keamanan isi

Teks hasil generation di-escape sebelum dikirim. HTML mentah dari LLM tidak pernah dirender di Moodle.

---

## 4. Detail per Konten

### 4.1 Resource (BE-12.1)

* Hanya `resource_type = external_link`, URL wajib `http(s)`.
* Deskripsi menjadi paragraf HTML.

### 4.2 Assignment (BE-12.2)

* Deskripsi berisi instruksi (Markdown sederhana → HTML), daftar hasil yang dikumpulkan, dan tabel **Kriteria Penilaian** dari rubric. Rubric belum memakai advanced grading Moodle (sesuai catatan §16).
* Pengaturan tidak dihasilkan generation, sehingga memakai `AssignmentSettings`:

| Pengaturan | Default |
| :--- | :--- |
| Jenis pengumpulan | Online text dan file |
| Jumlah file maksimal | 5 |
| Nilai maksimum | 100 |
| Due date | Tidak ada (agent tidak boleh mengarang deadline, §15) |

### 4.3 Quiz (BE-12.3)

* Soal dibuat sebagai soal **pilihan ganda dengan satu jawaban benar** pada question bank course, dalam satu kategori per quiz (ID number kategori = ID number quiz). Pada Moodle 5.0+, question bank course adalah activity *System shared question bank* yang dibuat otomatis; pada 4.5, kategori soal berada di context course.
* `explanation` menjadi pembahasan (*general feedback*) yang tampil setelah attempt dikirim.

| `QuizData.config` | Moodle |
| :--- | :--- |
| `time_limit_minutes` | Time limit; `null` = tanpa batas |
| `max_attempts` | Attempts allowed |
| `passing_score_percent` | Grade to pass dari nilai maksimum 100; `null` = tidak diatur |
| `shuffle_questions` | Urutan soal diacak |

Pengaturan tetap plugin: nilai maksimum 100, setiap soal bernilai 1, satu soal per halaman, opsi jawaban diacak, *deferred feedback*, review jawaban dan kunci setelah attempt dikirim.

**Update quiz:**

| Kondisi | Yang diperbarui |
| :--- | :--- |
| Belum ada attempt | Judul, deskripsi, konfigurasi, section, dan **seluruh soal diganti** |
| Sudah ada attempt | Judul, deskripsi, konfigurasi, dan section. **Soal dipertahankan** agar jawaban dan nilai mahasiswa tidak rusak; hasil `publish()` berisi `questions_replaced = False` |

Pembuatan soal berhasil dengan mekanisme plugin (DL-003), sehingga tidak ada usulan penundaan quiz ke Decision Log.

---

## 5. Batasan Saat Ini

| Hal | Keterangan |
| :--- | :--- |
| Belum dipanggil dari workflow | Eksekusi di develop baru mencakup struktur section. Service BE-12 siap dipanggil dari eksekusi konten lengkap |
| Jenis soal | Hanya pilihan ganda satu jawaban (sesuai `QuizData`). True/false dan short answer (§18) belum didukung |
| Markdown assignment | Konversi sederhana (paragraf, list, heading, bold, italic, code). Konversi lengkap di BE-21.1 |
| Learning material (Page) | Bukan bagian BE-12; dikerjakan di BE-04.4 sebagai `MoodlePageService` dengan pola idempotency yang sama |

---

## 6. Testing

| File | Jenis |
| :--- | :--- |
| `tests/test_moodle_resource_service.py`, `test_moodle_assignment_service.py`, `test_moodle_quiz_service.py` | Unit test dengan Moodle tiruan |
| `tests/test_moodle_resource_live.py`, `test_moodle_assignment_live.py`, `test_moodle_quiz_live.py` | Live test ke Moodle (opt-in), termasuk akses mahasiswa uji |
| `tests/test_moodle_plugin_live.py` | Live test seluruh function plugin |

Cara menjalankan: `04. workflow/moodle-setup-guide.md` bagian 10.