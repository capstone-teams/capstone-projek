# Decision Log

## Agentic AI untuk Mengisi Konten Moodle

**Project:** Capstone Project — Institut Teknologi Kalimantan (ITK)
**Document:** Decision Log
**Version:** 0.6
**Status:** Active
**Owner:** Project Manager (Noel)
**Related Documents:** `project-charter.md`, `prd.md`, `quality-plan.md`, `moodle-integration.md`, `design-system.md`, `design-api.md`, `agent-design.md`, `content-schema.md`, `data-model.md`

---

## 1. Tujuan

Decision Log mencatat keputusan project-level yang memengaruhi scope, architecture, technology, requirement, integration, jadwal, atau alokasi resource, sesuai Project Charter §19.2 dan §19.5.

Setiap keputusan dicatat beserta konteks, alternatif yang dipertimbangkan, alasan, dan dampaknya agar perubahan arah proyek dapat ditelusuri.

Keputusan teknis kecil yang tidak memengaruhi dokumen baseline cukup dicatat pada issue atau pull request terkait.

---

## 2. Status Keputusan

| Status     | Arti                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------- |
| Open       | Masalah sudah teridentifikasi, keputusan belum diambil. Memiliki target tanggal keputusan. |
| Proposed   | Rekomendasi sudah ada, menunggu konfirmasi atau evidence.                                 |
| Accepted   | Keputusan berlaku dan dokumen terkait sudah/akan disesuaikan.                             |
| Superseded | Digantikan oleh keputusan lain. Wajib menyebut ID pengganti.                              |
| Rejected   | Dipertimbangkan tetapi tidak diambil.                                                     |

Keputusan berstatus `Accepted` tidak diedit isinya. Jika arah berubah, buat entri baru yang men-supersede entri lama.

---

## 3. Register

| ID     | Tanggal    | Keputusan                                                     | Kategori           | Status   | Owner             |
| ------ | ---------- | ------------------------------------------------------------- | ------------------ | -------- | ----------------- |
| DL-001 | 2026-10-13 | Target integrasi menggunakan Moodle open-source self-hosted   | Scope, Integration | Accepted | Project Manager   |
| DL-002 | 2026-10-13 | Penetapan satu versi Moodle dan referensi dokumentasi         | Technology         | Proposed | Moodle Integration |
| DL-003 | 2026-10-13 | Mekanisme pembuatan activity Moodle (page, assignment, quiz)  | Architecture       | Open     | Moodle Integration |
| DL-004 | 2026-10-13 | Restrukturisasi milestone M03–M14 dan penerapan sprint 1 minggu | Schedule, Governance | Accepted | Project Manager   |
| DL-005 | 2026-10-13 | Penyesuaian kepemilikan stream pekerjaan backend              | Resource           | Accepted | Project Manager   |
| DL-006 | 2026-10-12 | Representasi data RPS: satu skema JSON tersimpan, YAML untuk input LLM | Architecture, Data | Accepted | Project Manager   |
| DL-007 | 2026-10-13 | LLM menggunakan OpenAI API melalui provider abstraction, menggantikan Ollama | Technology, Architecture | Accepted | Project Manager   |
| DL-008 | 2026-10-14 | Hasil Docling disimpan sebagai JSON; RPS tidak dikonversi ke Markdown | Architecture, Data | Accepted | Project Manager   |
| DL-009 | 2026-10-14 | Field akademik RPS dihasilkan oleh RPS Analysis berbasis LLM sesuai proposal | Architecture, Scope | Accepted | Project Manager   |
| DL-010 | 2026-10-19 | Pemadatan jadwal menjadi 4 minggu dengan milestone M02–M05      | Schedule, Scope    | Accepted | Project Manager   |
| DL-011 | 2026-10-19 | Istilah proposal (Workflow, role DOSEN/MAHASISWA) dan endpoint M02 | Architecture, API | Accepted | Project Manager   |

---

## 4. Detail Keputusan

### DL-001 — Target integrasi menggunakan Moodle open-source self-hosted

| Field    | Value                |
| -------- | -------------------- |
| Tanggal  | 2026-10-13           |
| Kategori | Scope, Integration   |
| Status   | Accepted             |
| Owner    | Project Manager      |

**Konteks**

Project Charter v0.1, PRD v0.1, dan seluruh design document menetapkan Moodle LMS ITK sebagai target integrasi dengan status `Confirmed`. Dalam pelaksanaannya, tim tidak menggunakan instance Moodle milik ITK. Integrasi dibangun terhadap instance Moodle open-source yang dipasang dan dikelola sendiri oleh tim berdasarkan dokumentasi resmi Moodle.

Akibatnya, beberapa asumsi, dependency, dan risiko pada dokumen baseline tidak lagi sesuai, misalnya ketergantungan pada administrator Moodle ITK untuk token, service, dan permission.

**Alternatif yang dipertimbangkan**

| Opsi | Deskripsi                                   | Catatan                                                                                       |
| ---- | ------------------------------------------- | --------------------------------------------------------------------------------------------- |
| A    | Moodle LMS ITK (production atau sandbox)    | Bergantung pada administrator kampus untuk web service, token, capability, dan akun pengujian. |
| B    | MoodleCloud                                 | Kontrol terbatas atas konfigurasi server dan instalasi plugin.                               |
| C    | Moodle open-source self-hosted              | Tim memiliki akses administrator penuh dan environment dapat direproduksi.                    |

**Keputusan**

Opsi C. Target integrasi MVP adalah instance Moodle open-source self-hosted yang dikelola tim, dipasang dari repository resmi `github.com/moodle/moodle` dan mengikuti dokumentasi resmi Moodle.

Integrasi dengan Moodle production ITK berada di luar scope MVP dan diposisikan sebagai pengembangan lanjutan.

**Alasan**

1. Menghilangkan dependency eksternal terhadap administrator Moodle ITK yang berada di luar kendali tim.
2. Tim dapat mengaktifkan web service, membuat service dan token, mengatur role/capability, serta memasang plugin apabila diperlukan (lihat DL-003).
3. Environment dapat di-reset dan direproduksi untuk pengujian tanpa risiko terhadap data production.

**Dampak**

| Area         | Dampak                                                                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Scope        | Target MVP berubah dari Moodle ITK menjadi Moodle self-hosted. Kebutuhan fungsional (FR-047 s.d. FR-056) tetap berlaku.                  |
| Risk         | Risiko "permission Moodle tidak mencukupi" dan "Moodle Web Service tidak tersedia" turun karena tim memegang akses administrator.         |
| Risk (baru)  | Tim bertanggung jawab atas instalasi, versi, backup, dan stabilitas instance Moodle. Hasil MVP belum terbukti pada konfigurasi Moodle ITK. |
| Architecture | Tidak berubah. Moodle Integration Layer dan `IMoodleService` tetap menjadi boundary sehingga target Moodle lain dapat ditambahkan kemudian. |
| Resource     | Moodle Integration engineer menangani operasional instance Moodle (instalasi, konfigurasi, data uji).                                   |
| Schedule     | Discovery tidak lagi menunggu pihak eksternal sehingga dapat dilakukan sejak M02/M03.                                                   |

**Dokumen yang disesuaikan**

`project-charter.md` (v0.2), `prd.md` (v0.2), `moodle-integration.md` (v0.2), `design-system.md`, `design-api.md`, `agent-design.md`, `quality-plan.md` (v0.3).

---

### DL-002 — Penetapan satu versi Moodle dan referensi dokumentasi

| Field    | Value                                             |
| -------- | ------------------------------------------------- |
| Tanggal  | 2026-10-13                                        |
| Kategori | Technology                                        |
| Status   | Proposed — menunggu konfirmasi versi terpasang    |
| Owner    | Moodle Integration Engineer                       |

**Konteks**

Referensi yang saat ini dibagikan ke tim menunjuk ke tiga versi Moodle yang berbeda:

| Referensi                                               | Versi       |
| ------------------------------------------------------- | ----------- |
| `https://moodledev.io/docs/5.3` (developer docs)         | 5.3         |
| `https://docs.moodle.org/502/en/Installing_Moodle`       | 5.2         |
| `https://www.examulator.com/er/4.0/` (ER diagram)        | 4.0         |
| `https://github.com/moodle/moodle`                       | Mengikuti branch yang di-checkout |

Perbedaan versi berisiko menimbulkan ketidaksesuaian antara dokumentasi yang dipelajari tim, kode yang dipasang, dan API yang dipanggil backend. Moodle 5.3 dirilis pada 5 Oktober 2026 sebagai versi LTS dengan kebutuhan minimum PHP 8.3 dan PostgreSQL 17.

**Rekomendasi**

1. Tim menggunakan satu versi Moodle untuk seluruh environment development dan pengujian. Rekomendasi: Moodle 5.3 LTS (branch `MOODLE_503_STABLE`), karena sesuai dengan developer docs yang sudah dibagikan dan memiliki masa dukungan panjang.
2. Jika instance yang sudah terpasang adalah 5.2 dan sudah stabil, tim boleh tetap menggunakan 5.2 selama MVP. Dalam kondisi tersebut, developer docs yang dirujuk diganti ke versi 5.2.
3. Dokumentasi instalasi mengikuti versi yang dipilih (`docs.moodle.org/503/...` untuk 5.3).
4. ER diagram Examulator 4.0 hanya digunakan sebagai referensi konseptual. Struktur tabel aktual mengacu pada file `install.xml` di branch yang dipilih. Backend aplikasi tidak mengakses database Moodle secara langsung; seluruh operasi melalui Web Service.
5. Versi terpilih dicatat pada `moodle-integration.md` §4 dan environment setup tim.

**Kriteria untuk menjadi Accepted**

Versi instance yang terpasang sudah dikonfirmasi oleh Moodle Integration Engineer dan seluruh referensi tim sudah diseragamkan.

---

### DL-003 — Mekanisme pembuatan activity Moodle (page, assignment, quiz)

| Field           | Value                                         |
| --------------- | --------------------------------------------- |
| Tanggal dibuka  | 2026-10-13                                    |
| Kategori        | Architecture, Integration                     |
| Status          | Open                                          |
| Owner           | Moodle Integration Engineer                   |
| Target keputusan | 2026-10-25 (Sprint S1, M02)                  |

**Konteks**

MVP membutuhkan pembuatan learning material (Must) serta assignment dan quiz (Should) pada Moodle (PRD §24, FR-050 s.d. FR-052).

Berdasarkan penelusuran awal terhadap dokumentasi dan release notes Moodle:

1. External functions bawaan Moodle mendukung operasi course (`core_course_create_courses`, `core_course_update_courses`), pembacaan konten (`core_course_get_contents`), user, dan enrolment.
2. Belum ditemukan external function bawaan untuk membuat course module baru secara umum (page, assign, quiz), maupun untuk membuat soal quiz pada question bank.
3. Release notes Moodle 5.3 tidak mencantumkan web service baru untuk pembuatan course module.
4. REST API baru (`/api/rest/v2`, routing subsystem sejak 4.5) adalah framework bagi komponen untuk mendefinisikan route sendiri. Belum ditemukan route bawaan untuk membuat course module.

Temuan ini belum diverifikasi langsung pada instance tim, sehingga statusnya masih `Open`.

**Alternatif**

| Opsi | Deskripsi                                                                                                                | Kelebihan                                                       | Kekurangan                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| A    | Hanya menggunakan external functions bawaan                                                                              | Tidak ada kode tambahan di sisi Moodle                          | Kemungkinan besar tidak dapat membuat page, assignment, dan quiz. FR-050 s.d. FR-052 tidak terpenuhi. |
| B    | Local plugin (`local_<nama>`) yang menyediakan external functions dan memanggil API internal Moodle untuk membuat module | Terkontrol, terdokumentasi, menggunakan mekanisme plugin resmi, tidak memodifikasi core | Membutuhkan pengembangan PHP; bertentangan dengan rumusan out-of-scope "custom Moodle API" sehingga scope perlu disesuaikan. |
| C    | Membangun file backup `.mbz` lalu melakukan restore ke course                                                            | Dapat membawa banyak jenis activity sekaligus                   | Kompleks, sulit diverifikasi per item, mekanisme restore melalui web service juga perlu diverifikasi. |
| D    | Plugin komunitas yang sudah ada                                                                                          | Tidak perlu membangun dari awal                                 | Plugin yang ditemukan (mis. `local_sync_service`) hanya mendukung URL, resource, dan folder, serta diuji sampai Moodle 4.1. |

**Rekomendasi awal**

Opsi B, dengan batasan:

1. Plugin hanya menyediakan operasi yang dibutuhkan MVP (create/update page, assignment, quiz, dan question dasar).
2. Setiap function melakukan capability check Moodle.
3. Kode plugin disimpan di repository proyek dan memiliki versi.
4. Tidak ada modifikasi pada core Moodle.

**Langkah verifikasi (spike)**

1. Ekspor daftar external functions dari instance tim (Site administration → Server → Web services → API documentation).
2. Uji pembuatan course dan section melalui fungsi bawaan.
3. Konfirmasi ada atau tidaknya fungsi bawaan untuk membuat page, assignment, dan quiz pada versi yang dipilih (DL-002).
4. Buat prototype local plugin dengan satu function (create page) dan panggil dari backend.
5. Catat hasil, pilihan final, dan dampaknya pada entri ini.

**Dampak bila Opsi B diambil**

| Area     | Dampak                                                                                                     |
| -------- | ---------------------------------------------------------------------------------------------------------- |
| Scope    | Project Charter §7.2 no. 7 dan PRD §6 no. 9 perlu dirumuskan ulang: custom API dibatasi pada local plugin minimal. |
| Resource | Tambahan pekerjaan PHP bagi Moodle Integration Engineer pada M03–M05.                                      |
| Risk     | Plugin harus kompatibel dengan versi Moodle terpilih dan diuji bersama upgrade.                            |

**Dokumen yang akan disesuaikan setelah keputusan**

`project-charter.md` §7.2, `prd.md` §6, `moodle-integration.md` §3.1, §5, §8, §11–§13, §32, §36.

---

### DL-004 — Restrukturisasi milestone M03–M14 dan penerapan sprint 1 minggu

| Field    | Value                 |
| -------- | --------------------- |
| Tanggal  | 2026-10-13            |
| Kategori | Schedule, Governance  |
| Status   | Accepted — jadwal diubah oleh DL-010              |
| Owner    | Project Manager       |

**Konteks**

Rencana awal terdiri dari 14 milestone berbasis komponen dengan jarak sekitar satu minggu dan tanpa sprint. Kondisi yang ditemukan:

1. Milestone berfungsi sebagai pengelompokan fitur, bukan checkpoint hasil, sehingga keterlambatan satu milestone langsung bergeser ke milestone berikutnya.
2. Milestone tidak memiliki exit criteria yang dapat diuji.
3. Integrasi seluruh komponen baru terjadi pada M14 (11 Desember 2026).
4. Beberapa kebutuhan tidak memiliki milestone, antara lain Instructor Profile, Additional Prompt, Activity Configuration, dan evaluation dataset.
5. Tidak ada time-box operasional untuk komitmen tim.

M01 sudah selesai dan M02 sedang berjalan. Mengubah isi M02 di tengah pelaksanaan akan mengganggu pekerjaan yang sedang berlangsung.

**Keputusan**

1. M01 tidak diubah. M02 diganti nama menjadi "Application & Moodle Integration Foundation" agar sesuai dengan cakupan issue di dalamnya (fondasi aplikasi, fondasi integrasi Moodle, dan halaman awal course planning), serta ditambah satu task verifikasi versi Moodle dan mekanisme pembuatan activity (DL-002, DL-003).
2. M03 s.d. M14 diganti dengan empat milestone berbasis increment (M03–M06). Setiap milestone menghasilkan kemampuan yang dapat didemonstrasikan end-to-end dan memiliki exit criteria yang dihubungkan ke Acceptance Criteria PRD dan Quality Gate.
3. Sprint berdurasi 1 minggu (Senin–Minggu), dikelola melalui field Iteration pada GitHub Projects.
4. Due date M02 diperpanjang menjadi 25 Oktober 2026 dan diselesaikan dalam Sprint S0 (12–18 Oktober) dan S1 (19–25 Oktober).
5. Judul, deskripsi, exit criteria, dan due date milestone dikelola langsung pada GitHub Milestones.

**Alasan**

1. Increment end-to-end mendeteksi masalah integrasi sejak awal, sesuai risiko "integrasi antar komponen tidak konsisten" pada Project Charter §16.
2. Exit criteria yang terhubung ke AC dan Quality Gate membuat status milestone dapat diverifikasi.
3. Sprint mingguan memberikan titik kontrol yang lebih sering bagi tim yang juga memiliki beban perkuliahan.

**Dampak**

| Area     | Dampak                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------- |
| Schedule | Target MVP release 13 Desember 2026, buffer finalisasi 14–20 Desember 2026.                        |
| Kanban   | Milestone M03 dan seterusnya pada GitHub diganti dengan struktur baru.                           |
| Process  | Sprint planning, review, dan standup asinkron mulai diterapkan sejak Sprint S0 (12–18 Oktober 2026, sedang berjalan). |

---

### DL-005 — Penyesuaian kepemilikan stream pekerjaan backend

| Field    | Value            |
| -------- | ---------------- |
| Tanggal  | 2026-10-13       |
| Kategori | Resource         |
| Status   | Accepted         |
| Owner    | Project Manager  |

**Konteks**

Tim terdiri dari lima anggota: dua Frontend Engineer dan tiga Backend Engineer (Backend API, Moodle Integration, AI Engineer). Tanpa penyesuaian, AI Engineer menanggung RPS processing, RPS analysis, course planning, content generation, validation, dan evaluasi model sekaligus.

**Keputusan**

| Pekerjaan                                         | Pemilik                      |
| ------------------------------------------------- | ---------------------------- |
| RPS upload, document processing (Docling), penyimpanan representasi | Backend API Engineer |
| Agent run, state, event, dan WebSocket monitoring | Backend API Engineer         |
| Moodle instance, integration layer, execution, verification, student access | Moodle Integration Engineer |
| Model evaluation, prompt, RPS analysis, course planning, content generation, semantic validation | AI Engineer |
| Seluruh antarmuka pengguna                        | Frontend Engineer (2 orang)  |

AI Engineer tetap menentukan format representasi RPS yang dibutuhkan agent, sedangkan implementasi pipeline dikerjakan Backend API Engineer.

**Dampak**

Beban AI Engineer berkurang pada M03–M04. Kontrak antara output document processing dan input agent harus disepakati di awal M03 dan mengacu pada `content-schema.md`.

---

### DL-006 — Representasi data RPS: satu skema JSON tersimpan, YAML untuk input LLM

| Field    | Value                                          |
| -------- | ---------------------------------------------- |
| Tanggal  | 2026-10-12 (rapat mingguan tim)                |
| Kategori | Architecture, Data                             |
| Status   | Accepted — poin 1 diubah oleh DL-008; sumber field akademik diperjelas oleh DL-009 |
| Owner    | Project Manager                                |

**Konteks**

Design document menetapkan representasi RPS sebagai Markdown dan structured JSON, tetapi field RPS dan cara penggunaannya oleh backend, frontend, dan LLM belum ditentukan (Content Schema §52: "Exact RPS analysis fields — TBD"). Pada rapat mingguan, tim menetapkan bahwa hasil Docling diubah menjadi JSON dan YAML.

Docling membutuhkan waktu pemrosesan yang tidak kecil dan hanya menghasilkan struktur dokumen (teks, heading, tabel), bukan field akademik seperti CPMK atau Sub-CPMK. Pemetaan ke field akademik memerlukan langkah tambahan.

**Alternatif yang dipertimbangkan**

| Opsi | Deskripsi                                                                 | Catatan                                                                        |
| ---- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A    | JSON dan YAML diekstraksi secara terpisah dari dokumen                    | Isi kedua format berisiko berbeda; dosen dan LLM dapat melihat data yang tidak sama. |
| B    | LLM membaca Markdown mentah hasil Docling secara langsung                 | Penggunaan token lebih besar, struktur tidak terkontrol, risiko halusinasi lebih tinggi. |
| C    | Satu skema terstruktur disimpan sebagai JSON; YAML diserialisasi dari JSON | Satu sumber data untuk seluruh kebutuhan backend.                             |

**Keputusan**

Opsi C, dengan aturan:

1. Docling dijalankan satu kali per file RPS, diidentifikasi melalui `file_hash`. Hasilnya disimpan sebagai `source_markdown` dan sebagai RPS Structured Data (JSON) yang divalidasi dengan model Pydantic, pada kolom `rps.structured_data`.
2. JSON tersimpan menjadi sumber tunggal yang dipanggil ulang oleh backend untuk seluruh kebutuhan berikutnya: response REST API, input LLM, dan tahap analysis serta planning. Dokumen tidak diproses ulang kecuali file berubah atau versi skema berubah.
3. Frontend tidak membaca file JSON secara langsung. Seluruh data RPS diakses melalui REST API backend.
4. Input LLM berupa YAML yang diserialisasi dari JSON yang sama dan hanya memuat field akademik yang relevan. YAML yang dikirim pada setiap agent run disimpan sebagai jejak run (FR-013).
5. Field yang tidak ditemukan pada RPS ditandai pada metadata ekstraksi dan tidak diisi dengan asumsi.

**Alasan**

1. Menghindari pemrosesan Docling berulang untuk dokumen yang sama.
2. Data yang ditampilkan kepada dosen dan data yang diterima LLM berasal dari sumber yang sama.
3. YAML umumnya lebih ringkas dan lebih mudah dibaca LLM dibandingkan JSON untuk data yang sama.
4. Jejak input LLM per run mendukung traceability dan evaluasi prompt.

**Dampak**

| Area         | Dampak                                                                                                      |
| ------------ | ----------------------------------------------------------------------------------------------------------- |
| Architecture | Content Schema §6–§7 diperbarui menjadi RPS Structured Data Schema. System Design dan Data Model disesuaikan. |
| Resource     | Backend API Engineer membangun pemetaan hasil Docling ke field skema, diawali dengan template RPS prodi.    |
| Resource     | AI Engineer menentukan subset field yang diserialisasi ke YAML untuk prompt.                                |
| Quality      | Field skema harus dicocokkan dengan 3–5 RPS asli sebelum M02 ditutup.                                       |

**Dokumen yang disesuaikan**

`content-schema.md`, `data-model.md`, `design-system.md`, `project-charter.md`.

---

### DL-007 — LLM menggunakan OpenAI API melalui provider abstraction

| Field    | Value                                                         |
| -------- | ------------------------------------------------------------- |
| Tanggal  | 2026-10-13 (diimplementasikan melalui issue #12, 2026-09-18)  |
| Kategori | Technology, Architecture                                      |
| Status   | Accepted                                                      |
| Owner    | Project Manager                                               |

**Konteks**

Project Charter, PRD, dan design document menetapkan local LLM melalui Ollama sebagai arah teknologi (status Proposed). Dalam pelaksanaan, tim telah mengimplementasikan konfigurasi LLM provider untuk OpenAI dan Gemini melalui provider abstraction (issue #12, Configure LLM Providers). Tim menggunakan OpenAI sebagai LLM proyek. Dokumen baseline belum mencerminkan keputusan tersebut.

**Alternatif yang dipertimbangkan**

| Opsi | Deskripsi                         | Catatan                                                                                   |
| ---- | --------------------------------- | ----------------------------------------------------------------------------------------- |
| A    | Local LLM melalui Ollama          | Tidak ada biaya per token, tetapi kualitas dan latency dibatasi hardware yang tersedia bagi tim. |
| B    | OpenAI API                        | Kualitas instruction following, Bahasa Indonesia, dan structured output lebih terjamin; memerlukan biaya dan koneksi internet. |
| C    | Gemini API                        | Sudah dikonfigurasi pada provider abstraction sebagai alternatif.                        |

**Keputusan**

1. LLM proyek menggunakan OpenAI API sebagai provider utama.
2. Akses LLM tetap melalui provider abstraction yang dibangun pada issue #12, sehingga provider dapat diganti tanpa mengubah logic agent. Gemini tetap tersedia sebagai alternatif.
3. Model OpenAI yang digunakan untuk MVP ditentukan melalui evaluasi model pada M03.
4. API key disimpan pada konfigurasi backend dan tidak pernah dikirim ke frontend, log, maupun konteks agent.

**Alasan**

1. Menghilangkan ketergantungan kualitas dan kecepatan agent pada hardware lokal tim.
2. Mendukung structured output dan tool calling yang dibutuhkan agent workflow.
3. Sesuai dengan implementasi yang sudah berjalan pada repository.

**Dampak**

| Area     | Dampak                                                                                                           |
| -------- | ---------------------------------------------------------------------------------------------------------------- |
| Cost     | Terdapat biaya penggunaan API per token. Estimasi dan batas penggunaan perlu dicatat pada dokumen budget.        |
| Risk     | Ketergantungan pada layanan eksternal: rate limit, ketersediaan layanan, koneksi internet, dan perubahan model.  |
| Risk     | Data RPS dikirim ke pihak ketiga. Mitigasi: hanya subset field akademik dalam YAML yang dikirim (DL-006), tanpa identitas dosen dan data administratif. |
| Security | API key OpenAI diperlakukan setara dengan credential Moodle.                                                    |
| Quality  | Kriteria evaluasi model mengganti "hardware requirement" menjadi biaya per run, latency API, dan stabilitas output. |
| Risk (berkurang) | Risiko "local LLM terlalu lambat" dan "keterbatasan hardware local LLM" tidak lagi berlaku.             |

**Dokumen yang disesuaikan**

`project-charter.md`, `prd.md`, `design-system.md`, `agent-design.md`, `data-model.md`, `content-schema.md`, `quality-plan.md`.

---

### DL-008 — Hasil Docling disimpan sebagai JSON; RPS tidak dikonversi ke Markdown

| Field    | Value                         |
| -------- | ----------------------------- |
| Tanggal  | 2026-10-14                    |
| Kategori | Architecture, Data            |
| Status   | Accepted                      |
| Owner    | Project Manager               |
| Mengubah | DL-006 poin 1                 |

**Konteks**

DL-006 poin 1 menetapkan bahwa hasil Docling disimpan sebagai `source_markdown`. Tim menetapkan bahwa RPS hanya dikonversi ke JSON dan YAML, tanpa representasi Markdown.

Pemrosesan RPS dibagi menjadi dua tahap pada sprint yang berbeda: konversi Docling (BE-05, Sprint S0) dan pemetaan field (BE-08, Sprint S1). Hasil konversi Docling tetap perlu disimpan agar pemetaan field dapat dijalankan dan diperbaiki tanpa menjalankan Docling ulang.

**Keputusan**

1. Hasil konversi Docling disimpan dalam format JSON (ekspor DoclingDocument) pada kolom `rps.source_document`, menggantikan `source_markdown`.
2. RPS Structured Data tetap disimpan sebagai JSON pada `rps.structured_data` dan menjadi sumber tunggal untuk REST API dan input LLM.
3. YAML untuk input LLM diserialisasi dari `rps.structured_data` saat dibutuhkan, sesuai DL-006.
4. Tidak ada konversi RPS ke Markdown pada pipeline pemrosesan RPS.

**Alasan**

1. Sesuai keputusan tim bahwa format RPS yang digunakan hanya JSON dan YAML.
2. Ekspor JSON Docling mempertahankan struktur dokumen (teks, heading, tabel, dan nomor halaman) yang dibutuhkan pemetaan field, termasuk pengisian `extraction.source_pages`.
3. Pemetaan field dapat diulang atau diperbaiki tanpa menjalankan Docling kembali.

**Dampak**

| Area         | Dampak                                                                                  |
| ------------ | --------------------------------------------------------------------------------------- |
| Data Model   | Kolom `source_markdown` diganti `source_document` (JSONB).                              |
| Architecture | Content Schema §6, System Design §10, dan Agent Design state PROCESSING_RPS disesuaikan. |

Representasi Markdown untuk learning material hasil generation (Content Schema §12) tidak terpengaruh keputusan ini.

---

### DL-009 — Field akademik RPS dihasilkan oleh RPS Analysis berbasis LLM sesuai proposal

| Field    | Value                         |
| -------- | ----------------------------- |
| Tanggal  | 2026-10-14                    |
| Kategori | Architecture, Scope           |
| Status   | Accepted                      |
| Owner    | Project Manager               |
| Mengubah | Mekanisme pengisian field pada DL-006 |

**Konteks**

Rancangan task M02 sebelumnya menempatkan pengisian field akademik RPS (identitas mata kuliah, CPL, CPMK, Sub-CPMK, rencana mingguan, penilaian, referensi) pada pemetaan berbasis aturan oleh Backend RESTful. Proposal Capstone (§3.2.2, §3.3.3, §3.4.3, §3.5.2, §3.6.6) menetapkan alur berbeda: sistem memproses dokumen (parsing, ekstraksi teks, representasi terstruktur), kemudian Agent mengirimkan hasil ekstraksi beserta output schema ke OpenAI API untuk menghasilkan analisis RPS, memvalidasi hasilnya, mengulang apabila tidak valid, menyimpan hasil analisis, dan dosen melihat hasil analisis tersebut.

**Keputusan**

1. Document processing (Docling) menghasilkan hasil ekstraksi dalam bentuk JSON (`rps.source_document`, DL-008). Tahap ini dikerjakan Backend RESTful.
2. Hasil ekstraksi diserialisasi menjadi YAML dan dikirim ke OpenAI API bersama output schema RPS Structured Data (Content Schema §6). Tahap RPS Analysis ini dikerjakan Backend AI.
3. Output LLM divalidasi terhadap skema. Output yang tidak valid diulang dengan batas retry.
4. Hasil analisis yang valid disimpan sebagai JSON pada `rps.structured_data` dan disajikan kepada frontend melalui `GET /api/v1/rps/{rps_id}/analysis`.
5. Untuk tahap course planning, `rps.structured_data` kembali diserialisasi menjadi YAML sebagai input LLM (DL-006).

**Alasan**

1. Sesuai rancangan yang telah ditetapkan pada proposal dan diagram (use case, activity, sequence, class, ERD).
2. Pembagian tugas pada proposal menempatkan RPS analysis pada Backend AI dan document processing serta persistence pada Backend RESTful.
3. Variasi format RPS antarmata kuliah lebih mudah ditangani oleh LLM dengan output schema dan validasi dibandingkan aturan pemetaan tetap.

**Dampak**

| Area     | Dampak                                                                                              |
| -------- | --------------------------------------------------------------------------------------------------- |
| Task     | BE-08 (S1) menjadi alur dan API hasil analisis; pemetaan field berbasis aturan tidak dikerjakan. BE-09 (S1) menjadi implementasi RPS Analysis menggunakan OpenAI. |
| Task     | BE-05.3 menghasilkan skema yang digunakan sebagai output schema RPS Analysis. BE-07 menjadi baseline prompt RPS Analysis. |
| API      | API Specification §6.4 menjadi endpoint hasil analisis; §6.5 digabungkan ke §6.4.                    |
| Cost     | Setiap RPS memerlukan pemanggilan OpenAI pada tahap analisis.                                       |

---

### DL-010 — Pemadatan jadwal menjadi 4 minggu dengan milestone M02–M05

| Field    | Value                              |
| -------- | ---------------------------------- |
| Tanggal  | 2026-10-19                         |
| Kategori | Schedule, Scope                    |
| Status   | Accepted                           |
| Owner    | Project Manager                    |
| Mengubah | Jadwal pada DL-004                 |

**Konteks**

DL-004 menargetkan MVP pada 13 Desember 2026. Per 19 Oktober 2026, sisa waktu Capstone adalah 4 minggu termasuk minggu berjalan. Tanggal pasti deadline belum diumumkan; perencanaan menggunakan target kerja 15 November 2026.

**Keputusan**

1. Sprint tetap berdurasi 1 minggu. Sprint 0 (12–18 Oktober) telah selesai.
2. Milestone yang digunakan:

| Milestone | Sprint | Periode | Due |
| --------- | ------ | ------- | --- |
| M02 - Application & Core Integration Foundation | Sprint 0–1 | 12–25 Okt | 25 Okt 2026 |
| M03 - Course Planning & Moodle Structure Execution | Sprint 2 | 26 Okt–1 Nov | 1 Nov 2026 |
| M04 - Content Generation, Review & Moodle Execution | Sprint 3 | 2–8 Nov | 8 Nov 2026 |
| M05 - MVP Validation, Evaluation & Release | Sprint 4 | 9–15 Nov | 15 Nov 2026 |

3. Pekerjaan yang dapat dikerjakan paralel ditarik ke Sprint 1: Instructor Setup, fondasi workflow dan monitoring, halaman unggah dan hasil analisis RPS, pemilihan course target, serta operasi activity Moodle.
4. Milestone lama selain M01–M05 dihapus dari GitHub.
5. Apabila tanggal deadline resmi lebih awal dari 15 November 2026, M05 dipadatkan dan perubahan dicatat sebagai entri baru.

**Kandidat pengurangan scope bila terjadi keterlambatan (urutan)**

1. Quiz (prioritas Should pada PRD).
2. Regenerasi dengan scope COURSE (tetap mendukung MINGGU dan ITEM).
3. Usability test formal (diganti uji singkat oleh pengguna representatif).

Setiap pengurangan scope yang diambil dicatat sebagai entri Decision Log tersendiri.

**Dampak**

| Area     | Dampak                                                                  |
| -------- | ----------------------------------------------------------------------- |
| Schedule | Seluruh MVP diselesaikan dalam 4 sprint.                                |
| Resource | Beban per anggota pada Sprint 1 meningkat; standup dilakukan harian.    |
| Risk     | Ruang buffer berkurang; integrasi antar-stream bergantung pada kontrak data yang disepakati di awal sprint. |

---

### DL-011 — Istilah proposal (Workflow, role DOSEN/MAHASISWA) dan endpoint M02

| Field    | Value                         |
| -------- | ----------------------------- |
| Tanggal  | 2026-10-19                    |
| Kategori | Architecture, API             |
| Status   | Accepted                      |
| Owner    | Project Manager               |

**Konteks**

Agent Design, Data Model, dan API Specification menggunakan istilah Agent Run, Agent Event, state machine 15 state, dan role `INSTRUCTOR`/`STUDENT`. Proposal Capstone (class diagram dan ERD) menggunakan Workflow, WorkflowEvent, `WorkflowStatus` (11 status), `EventType`, dan role `DOSEN`/`MAHASISWA`. Selain itu, beberapa endpoint yang dibutuhkan M02 belum didefinisikan pada API Specification.

**Keputusan**

1. Implementasi menggunakan istilah proposal: Workflow, WorkflowEvent, `WorkflowStatus`, `EventType`, dan role `DOSEN`/`MAHASISWA`.
2. State rinci pada Agent Design dipetakan ke `WorkflowStatus` (Agent Design §8).
3. Endpoint berikut ditambahkan pada API Specification:

| Endpoint | Section |
| -------- | ------- |
| `GET /api/v1/rps`, `POST /api/v1/rps/{rps_id}/reanalyze` | §6.6–§6.7 |
| `GET` dan `PUT /api/v1/instructors/me/setup` | §7 |
| `GET /api/v1/integrations/moodle/courses` | §13.4 |
| `GET /api/v1/workflows`, `GET /api/v1/workflows/{workflow_id}`, `GET /api/v1/workflows/{workflow_id}/events`, `PUT /api/v1/workflows/{workflow_id}/moodle-target` | §15 |
| `WS /api/v1/ws/workflows/{workflow_id}` | §17 |

4. Endpoint berbasis `/courses/{course_id}` pada API Specification §8–§14 diselaraskan menjadi `/workflows/{workflow_id}/...` saat tahap terkait diimplementasikan pada M03–M04.
5. Activity Configuration dikelola per dosen bersama Additional Prompt melalui Instructor Setup.

**Dampak**

| Area   | Dampak                                                                                           |
| ------ | ------------------------------------------------------------------------------------------------ |
| Task   | BE-14 dan FE-13 menyeragamkan role; BE-11 mengimplementasikan Workflow dan WorkflowEvent.        |
| Docs   | API Specification v0.5, Data Model v0.4, dan Agent Design v0.2 diperbarui.                       |

---

## 5. Keputusan yang Dijadwalkan

Keputusan berikut belum diambil dan menjadi bagian dari exit criteria milestone.

| Topik                                     | Target       | Milestone | Referensi                  |
| ----------------------------------------- | ------------ | --------- | -------------------------- |
| Mekanisme pembuatan activity Moodle       | 2026-10-25   | M02       | DL-003                     |
| Model OpenAI untuk MVP                     | 2026-10-25   | M02       | DL-007, Agent Design §39, Quality Plan §16 |
| Document processing final (Docling atau alternatif) | 2026-10-25 | M02 | Project Charter §22.3     |
| Mekanisme structured output dan tool calling | 2026-10-25 | M02       | Agent Design §52           |
| Retry limit dan validation threshold      | 2026-11-08   | M04       | Agent Design §30, Quality Plan §66 |

---

## 6. Document Control

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| Document     | Decision Log                           |
| Project      | Agentic AI untuk Mengisi Konten Moodle |
| Version      | 0.6                                    |
| Status       | Active                                 |
| Owner        | Project Manager                        |
| Last Updated | 2026-10-19                             |

### Version History

| Version | Date       | Description                                   | Author          |
| ------- | ---------- | --------------------------------------------- | --------------- |
| 0.1     | 2026-10-13 | Initial Decision Log, entri DL-001 s.d. DL-005 | Project Manager |
| 0.2     | 2026-10-13 | Penambahan DL-006; penyesuaian DL-003 dan DL-004 | Project Manager |
| 0.3     | 2026-10-13 | Penambahan DL-007 | Project Manager |
| 0.4     | 2026-10-14 | Penambahan DL-008 | Project Manager |
| 0.5     | 2026-10-14 | Penambahan DL-009 | Project Manager |
| 0.6     | 2026-10-19 | Penambahan DL-010 dan DL-011 | Project Manager |
