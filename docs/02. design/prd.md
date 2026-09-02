# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Agentic AI untuk Mengisi Konten Moodle

**Project:** Capstone Project — Institut Teknologi Kalimantan (ITK)
**Document:** Product Requirements Document
**Version:** 0.1
**Status:** Draft
**Product Owner / Project Manager:** Noel
**Related Document:** `project-charter.md`

---

## 1. Product Overview

Agentic AI untuk Mengisi Konten Moodle adalah sistem yang membantu dosen mengubah Rencana Pembelajaran Semester (RPS) menjadi course dan konten pembelajaran pada Moodle.

Sistem menggunakan pendekatan Agentic AI untuk menjalankan workflow:

```text
Understand
→ Plan
→ Generate
→ Validate
→ Review
→ Execute
→ Verify
→ Retry/Fix
```

RPS menjadi sumber utama informasi akademik. Instructor Profile dan Additional Prompt digunakan sebagai konteks tambahan untuk menyesuaikan hasil.

Produk dirancang sebagai **standard web application** dengan interface untuk dosen dan interface monitoring proses agent.

---

# 2. Product Vision

Menyediakan sistem yang memungkinkan dosen menyiapkan course pembelajaran Moodle satu semester secara lebih efisien dengan bantuan Agentic AI, tanpa menghilangkan kontrol dosen terhadap kualitas dan keputusan akhir konten pembelajaran.

---

# 3. Product Goals

Produk harus mampu:

1. Mengurangi pekerjaan manual dosen dalam menyiapkan course Moodle.
2. Mengubah informasi dalam RPS menjadi struktur pembelajaran yang terorganisasi.
3. Menghasilkan konten pembelajaran untuk semester berdasarkan RPS.
4. Mendukung personalisasi berdasarkan Instructor Profile.
5. Memungkinkan dosen memberikan instruksi tambahan.
6. Memungkinkan dosen memilih tipe aktivitas pembelajaran yang ingin dibuat.
7. Memvalidasi hasil AI sebelum execution.
8. Memberikan dosen kontrol melalui review dan regeneration.
9. Mengirim hasil yang telah disetujui ke Moodle.
10. Memverifikasi hasil execution menggunakan student role.
11. Memberikan transparansi terhadap proses agent melalui monitoring UI.

---

# 4. Target Users

## 4.1 Instructor / Dosen

Dosen merupakan pengguna utama produk.

Kebutuhan utama:

* memasukkan RPS;
* mendapatkan course plan;
* mendapatkan konten pembelajaran;
* mengatur preferensi penyampaian;
* memilih tipe aktivitas;
* memberikan instruksi tambahan;
* memonitor proses agent;
* mereview hasil;
* melakukan regeneration;
* mempublikasikan hasil ke Moodle.

## 4.2 Student / Mahasiswa

Student merupakan pengguna akhir dari course yang dibuat.

Kebutuhan utama:

* mengakses course;
* melihat struktur course;
* membaca materi;
* mengakses aktivitas yang tersedia;
* memverifikasi bahwa course dapat digunakan dari perspektif mahasiswa.

Student bukan target utama fitur AI dan bukan pengguna utama workflow generation.

---

# 5. Product Scope

## 5.1 In Scope

Produk mencakup:

1. RPS upload dan processing.
2. RPS analysis.
3. Instructor Profile.
4. Additional Prompt.
5. Course planning.
6. Weekly content generation.
7. Optional learning activity generation.
8. AI validation.
9. Retry/fix.
10. Instructor review.
11. Content regeneration.
12. Moodle execution.
13. Moodle verification.
14. Student access.
15. Agent monitoring.
16. Workflow status management.

---

# 6. Out of Scope

Fitur berikut tidak termasuk dalam scope produk:

1. Attendance / absensi.
2. Sistem akademik mahasiswa secara keseluruhan.
3. Student Information System.
4. Pengelolaan Kartu Rencana Studi.
5. Pengelolaan nilai akademik secara penuh.
6. Pengelolaan administrasi akademik dosen.
7. Pengembangan LMS baru.
8. Modifikasi core Moodle.
9. Pengembangan API Moodle khusus ITK.
10. Custom Chromium/browser sebagai produk.
11. Otomatisasi seluruh jenis Moodle activity.
12. Autonomous publishing tanpa kontrol yang ditentukan produk.

---

# 7. MVP Definition

MVP harus membuktikan kemampuan end-to-end utama produk:

```text
RPS
 ↓
Processing
 ↓
Analysis
 ↓
Course Planning
 ↓
Content Generation
 ↓
Validation
 ↓
Instructor Review
 ↓
Moodle Execution
 ↓
Student Verification
```

MVP diprioritaskan untuk menghasilkan course pembelajaran satu semester berdasarkan RPS, dengan target utama hingga 16 minggu sesuai struktur RPS/course.

Tidak setiap minggu harus memiliki seluruh jenis aktivitas. Jenis konten harus mengikuti informasi RPS dan konfigurasi dosen.

---

# 8. Feature Priorities

Prioritas requirement menggunakan metode MoSCoW:

| Priority | Meaning                                                        |
| -------- | -------------------------------------------------------------- |
| Must     | Wajib tersedia untuk MVP                                       |
| Should   | Penting tetapi masih dapat dipertimbangkan setelah fungsi inti |
| Could    | Nilai tambah apabila resource dan waktu tersedia               |
| Won't    | Tidak dikerjakan dalam scope saat ini                          |

---

# 9. Functional Requirements

## 9.1 User & Course Management

### FR-001 — Instructor Access

**Priority:** Must

Sistem harus menyediakan akses bagi instructor untuk menggunakan workflow pembuatan course.

### FR-002 — Student Access

**Priority:** Must

Sistem harus mendukung student role/account pada environment Moodle untuk mengakses course yang telah dibuat.

### FR-003 — Course Identification

**Priority:** Must

Sistem harus memungkinkan instructor menentukan atau memilih course Moodle yang menjadi target execution.

---

# 10. RPS Processing Requirements

### FR-004 — RPS Upload

**Priority:** Must

Sistem harus memungkinkan instructor mengunggah RPS sebagai input utama proses generation.

Format minimum yang ditargetkan:

* PDF
* DOCX

### FR-005 — RPS Processing

**Priority:** Must

Sistem harus memproses dokumen RPS menjadi representasi yang dapat digunakan oleh workflow AI.

### FR-006 — RPS Information Extraction

**Priority:** Must

Sistem harus dapat mengidentifikasi informasi pembelajaran yang relevan dari RPS, termasuk apabila tersedia:

* identitas mata kuliah;
* capaian pembelajaran;
* tujuan pembelajaran;
* materi/topik;
* pembagian minggu;
* metode pembelajaran;
* bentuk evaluasi;
* referensi;
* dan informasi akademik relevan lainnya.

### FR-007 — RPS as Primary Source

**Priority:** Must

Sistem harus menggunakan informasi RPS sebagai sumber utama dalam course planning dan content generation.

AI tidak boleh mengubah informasi akademik utama hanya untuk membuat struktur course menjadi lebih lengkap.

---

# 11. Instructor Profile Requirements

### FR-008 — Instructor Profile

**Priority:** Should

Sistem harus menyediakan profile yang memungkinkan instructor menyimpan preferensi atau karakteristik penyampaian materi.

### FR-009 — Profile as Generation Context

**Priority:** Should

Instructor Profile harus dapat digunakan sebagai konteks tambahan dalam content generation.

### FR-010 — Profile Independence

**Priority:** Must

Instructor Profile tidak boleh menggantikan informasi akademik yang berasal dari RPS.

Apabila terdapat konflik antara profile dan informasi akademik RPS, informasi akademik RPS harus diprioritaskan.

---

# 12. Additional Prompt Requirements

### FR-011 — Additional Prompt

**Priority:** Should

Sistem harus memungkinkan instructor memberikan instruksi tambahan kepada agent.

### FR-012 — Prompt as Additional Context

**Priority:** Must

Additional Prompt harus diperlakukan sebagai instruksi tambahan dan tidak boleh menghilangkan konteks akademik penting dari RPS.

### FR-013 — Prompt Traceability

**Priority:** Could

Sistem dapat menyimpan prompt yang digunakan dalam suatu generation untuk mendukung traceability dan evaluasi.

---

# 13. Course Planning Requirements

### FR-014 — Course Plan Generation

**Priority:** Must

Agent harus dapat menghasilkan course plan berdasarkan hasil analisis RPS.

### FR-015 — Weekly Structure

**Priority:** Must

Course plan harus dapat merepresentasikan struktur pembelajaran berdasarkan pembagian minggu yang terdapat dalam RPS.

### FR-016 — Semester Coverage

**Priority:** Must

Agent harus dapat menghasilkan struktur course untuk seluruh periode pembelajaran yang ditentukan oleh RPS.

Target utama MVP adalah course dengan struktur hingga 16 minggu.

### FR-017 — RPS Traceability

**Priority:** Must

Setiap bagian utama course plan harus dapat ditelusuri kembali ke informasi yang relevan dari RPS.

### FR-018 — Instructor Review of Course Plan

**Priority:** Must

Instructor harus dapat melihat course plan sebelum proses content generation dilanjutkan.

### FR-019 — Course Plan Regeneration

**Priority:** Should

Instructor harus dapat meminta regeneration apabila course plan tidak sesuai dengan kebutuhan.

---

# 14. Content Generation Requirements

### FR-020 — Weekly Content Generation

**Priority:** Must

Agent harus dapat menghasilkan konten pembelajaran berdasarkan course plan untuk setiap minggu yang ditentukan.

### FR-021 — Learning Material

**Priority:** Must

Agent harus dapat menghasilkan materi pembelajaran yang relevan dengan topik dan tujuan pembelajaran.

### FR-022 — Learning Resources

**Priority:** Should

Agent harus dapat menghasilkan atau merekomendasikan learning resources yang relevan apabila dibutuhkan oleh course.

### FR-023 — Assignment Generation

**Priority:** Should

Sistem harus dapat mendukung pembuatan assignment sebagai aktivitas pembelajaran opsional.

Assignment hanya dibuat apabila dipilih atau dikonfigurasi oleh instructor.

### FR-024 — Quiz Generation

**Priority:** Should

Sistem harus dapat mendukung pembuatan quiz sebagai aktivitas pembelajaran opsional.

Quiz hanya dibuat apabila dipilih atau dikonfigurasi oleh instructor.

### FR-025 — Activity Configuration

**Priority:** Must

Instructor harus dapat menentukan tipe aktivitas pembelajaran yang ingin digunakan dalam proses generation.

Contoh konfigurasi:

```text
Learning Material: Enabled
Assignment: Enabled
Quiz: Disabled
```

### FR-026 — No Forced Activity

**Priority:** Must

Agent tidak boleh membuat assignment, quiz, atau aktivitas lain hanya karena aktivitas tersebut tersedia dalam sistem.

Generation harus mengikuti konfigurasi instructor dan kebutuhan RPS.

### FR-027 — Content Consistency

**Priority:** Must

Konten yang dihasilkan harus konsisten dengan course plan dan struktur pembelajaran.

### FR-028 — Cross-Week Consistency

**Priority:** Should

Konten antar minggu harus mempertahankan konsistensi konteks pembelajaran dan tidak menghasilkan kontradiksi yang tidak diperlukan.

### FR-029 — Content Regeneration

**Priority:** Must

Instructor harus dapat meminta regeneration terhadap konten tertentu tanpa harus selalu mengulang seluruh proses generation.

---

# 15. Agent Requirements

### FR-030 — Agentic Workflow

**Priority:** Must

Sistem harus menerapkan workflow agentic yang mencakup:

```text
Understand
→ Plan
→ Generate
→ Validate
→ Execute
→ Verify
→ Retry/Fix
```

### FR-031 — Planning Before Generation

**Priority:** Must

Agent harus melakukan planning sebelum menghasilkan keseluruhan konten.

### FR-032 — Validation

**Priority:** Must

Agent harus melakukan validation terhadap hasil generation berdasarkan kriteria yang ditentukan.

### FR-033 — Retry/Fix

**Priority:** Should

Agent harus dapat melakukan retry atau fix ketika hasil tidak memenuhi validation criteria.

### FR-034 — Controlled Tool Execution

**Priority:** Must

Agent harus melakukan operasi terhadap sistem eksternal melalui controlled tool layer.

### FR-035 — No Direct Moodle Credential Access

**Priority:** Must

LLM tidak boleh menerima atau menyimpan credential Moodle secara langsung.

### FR-036 — Execution Decision

**Priority:** Must

Execution ke Moodle harus dilakukan berdasarkan hasil yang telah melewati proses review/approval sesuai workflow produk.

### FR-037 — Agent State

**Priority:** Must

Sistem harus menyimpan status tahap workflow agent sehingga progress dapat diketahui.

---

# 16. Validation Requirements

### FR-038 — RPS Validation

**Priority:** Must

Sistem harus memvalidasi kesesuaian output terhadap informasi yang berasal dari RPS.

### FR-039 — Structure Validation

**Priority:** Must

Sistem harus memvalidasi struktur output sebelum execution.

### FR-040 — Configuration Validation

**Priority:** Must

Sistem harus memastikan output mengikuti konfigurasi aktivitas yang dipilih instructor.

### FR-041 — Validation Result

**Priority:** Must

Sistem harus menyediakan hasil validation yang dapat digunakan untuk menentukan apakah proses dapat dilanjutkan, diperbaiki, atau direview ulang.

---

# 17. Instructor Review Requirements

### FR-042 — Review Interface

**Priority:** Must

Instructor harus dapat melihat hasil generation sebelum execution ke Moodle.

### FR-043 — Review by Section/Content

**Priority:** Should

Instructor sebaiknya dapat melakukan review pada level course, minggu, atau konten tertentu.

### FR-044 — Approve Content

**Priority:** Must

Instructor harus dapat menyetujui hasil yang telah direview.

### FR-045 — Reject/Regenerate

**Priority:** Must

Instructor harus dapat menolak atau meminta regeneration terhadap hasil yang tidak sesuai.

### FR-046 — Review Before Execution

**Priority:** Must

Konten tidak boleh dieksekusi ke Moodle sebelum memenuhi kondisi approval yang ditentukan workflow.

---

# 18. Moodle Integration Requirements

### FR-047 — Moodle Integration

**Priority:** Must

Sistem harus dapat berinteraksi dengan Moodle LMS ITK melalui Moodle Web Service API.

### FR-048 — Course Target

**Priority:** Must

Sistem harus dapat menentukan course Moodle yang menjadi target hasil generation.

### FR-049 — Weekly Course Structure

**Priority:** Must

Sistem harus dapat membuat atau memperbarui struktur pembelajaran mingguan pada course sesuai dengan course plan.

### FR-050 — Learning Material Execution

**Priority:** Must

Sistem harus dapat mengirim dan/atau membuat materi pembelajaran yang dihasilkan ke Moodle menggunakan capability yang tersedia.

### FR-051 — Assignment Execution

**Priority:** Should

Sistem harus dapat mengirim assignment yang dihasilkan apabila fitur assignment diaktifkan dan Web Service Moodle mendukung operasi yang dibutuhkan.

### FR-052 — Quiz Execution

**Priority:** Should

Sistem harus dapat mengirim quiz yang dihasilkan apabila fitur quiz diaktifkan dan Web Service Moodle mendukung operasi yang dibutuhkan.

### FR-053 — Student Access

**Priority:** Must

Course yang telah dieksekusi harus dapat diakses menggunakan student role/account pada environment pengujian.

### FR-054 — Moodle Verification

**Priority:** Must

Sistem harus melakukan atau mendukung verification terhadap hasil execution pada Moodle.

### FR-055 — Execution Result

**Priority:** Must

Sistem harus menyimpan atau menampilkan status execution, termasuk keberhasilan atau kegagalan operasi.

### FR-056 — Moodle Error Handling

**Priority:** Must

Sistem harus dapat menangani kegagalan operasi Moodle tanpa menyebabkan workflow agent kehilangan status proses secara keseluruhan.

---

# 19. Agent Monitoring Requirements

### FR-057 — Monitoring Interface

**Priority:** Must

Sistem harus menyediakan interface untuk memonitor proses agent.

### FR-058 — Workflow Status

**Priority:** Must

Monitoring harus menampilkan tahap workflow agent saat ini.

Contoh:

```text
Processing RPS
Analyzing RPS
Planning Course
Generating Content
Validating
Waiting for Review
Executing to Moodle
Verifying
Completed
Failed
Retrying
```

### FR-059 — Agent Activity

**Priority:** Must

Monitoring harus memberikan informasi mengenai aktivitas agent yang sedang atau telah dilakukan.

### FR-060 — Execution Status

**Priority:** Must

Monitoring harus menampilkan status execution ke Moodle.

### FR-061 — Error Visibility

**Priority:** Must

Monitoring harus menampilkan error atau failure yang relevan kepada instructor.

### FR-062 — Retry Visibility

**Priority:** Should

Monitoring sebaiknya menampilkan ketika agent melakukan retry atau fix.

### FR-063 — Process History

**Priority:** Should

Sistem sebaiknya menyimpan history workflow sehingga proses dapat ditinjau kembali.

---

# 20. Student Verification Requirements

### FR-064 — Student Perspective

**Priority:** Must

Sistem harus memungkinkan hasil course dilihat dari perspektif student.

### FR-065 — Content Accessibility

**Priority:** Must

Student harus dapat mengakses materi yang telah dipublikasikan.

### FR-066 — Activity Accessibility

**Priority:** Should

Student harus dapat mengakses assignment atau quiz apabila aktivitas tersebut dibuat dan dipublikasikan.

### FR-067 — Verification Feedback

**Priority:** Could

Sistem dapat menyediakan hasil verification yang menunjukkan apakah konten dapat diakses dengan benar oleh student.

---

# 21. Non-Functional Requirements

## 21.1 Performance

### NFR-001 — Responsive Interface

**Priority:** Must

Interface utama harus memberikan feedback yang jelas ketika sistem sedang menjalankan proses yang membutuhkan waktu.

### NFR-002 — Long-Running Process Handling

**Priority:** Must

Workflow generation yang membutuhkan waktu lama harus berjalan tanpa mengharuskan instructor mempertahankan request HTTP biasa secara terus-menerus.

### NFR-003 — Monitoring Responsiveness

**Priority:** Should

Perubahan status agent harus dapat ditampilkan pada monitoring interface secara near real-time.

---

## 21.2 Reliability

### NFR-004 — Workflow Recovery

**Priority:** Must

Kegagalan pada satu tahap workflow tidak boleh menyebabkan seluruh state proses hilang.

### NFR-005 — Execution Reliability

**Priority:** Must

Sistem harus dapat membedakan execution yang berhasil, gagal, dan belum selesai.

### NFR-006 — Idempotent Execution

**Priority:** Should

Operasi execution yang memungkinkan pengulangan sebaiknya dirancang agar retry tidak menyebabkan duplikasi konten yang tidak diinginkan.

---

## 21.3 Security

### NFR-007 — Credential Protection

**Priority:** Must

Credential Moodle harus disimpan dan diproses oleh komponen yang memiliki kontrol akses sesuai kebutuhan.

### NFR-008 — LLM Isolation

**Priority:** Must

LLM tidak boleh mendapatkan akses langsung terhadap credential Moodle.

### NFR-009 — Access Control

**Priority:** Must

Akses terhadap fungsi instructor dan student harus dipisahkan sesuai role.

### NFR-010 — Sensitive Data Handling

**Priority:** Must

Data sensitif yang tidak diperlukan untuk generation tidak boleh diberikan kepada model AI.

---

## 21.4 Usability

### NFR-011 — Understandable Workflow

**Priority:** Must

Workflow harus dapat dipahami oleh instructor tanpa membutuhkan pemahaman mengenai mekanisme internal Agentic AI.

### NFR-012 — Clear Status

**Priority:** Must

Sistem harus memberikan status yang jelas pada setiap tahap proses.

### NFR-013 — Action Feedback

**Priority:** Must

Sistem harus memberikan feedback setelah instructor melakukan action seperti approve, reject, regenerate, atau execute.

---

## 21.5 Maintainability

### NFR-014 — Component Separation

**Priority:** Must

Komponen utama sistem harus memiliki separation of concerns yang memungkinkan perubahan pada satu bagian tidak menyebabkan perubahan besar pada komponen yang tidak berkaitan.

### NFR-015 — Moodle Integration Isolation

**Priority:** Must

Moodle integration harus diisolasi dari core agent logic sehingga perubahan pada integration layer tidak memerlukan perubahan menyeluruh terhadap agent.

---

## 21.6 Observability

### NFR-016 — Agent Logging

**Priority:** Must

Sistem harus mencatat event penting selama workflow agent.

### NFR-017 — Execution Logging

**Priority:** Must

Operasi penting terhadap Moodle harus memiliki log yang cukup untuk troubleshooting dan verification.

---

# 22. Content Requirements

Konten yang dihasilkan agent harus memenuhi prinsip berikut:

1. Berbasis pada RPS.
2. Memiliki hubungan dengan tujuan pembelajaran.
3. Konsisten dengan course plan.
4. Mengikuti struktur minggu pembelajaran.
5. Mengikuti konfigurasi aktivitas instructor.
6. Tidak mengarang informasi akademik sebagai fakta yang berasal dari RPS.
7. Dapat direview oleh instructor.
8. Dapat diregenerate apabila tidak memenuhi kebutuhan.
9. Memiliki struktur yang sesuai dengan format yang dapat digunakan Moodle.

---

# 23. AI-Specific Requirements

## AIR-001 — RPS Grounding

**Priority:** Must

AI harus menggunakan informasi RPS sebagai context utama dalam menghasilkan course plan dan konten.

## AIR-002 — Instruction Following

**Priority:** Must

Agent harus mengikuti Instructor Profile dan Additional Prompt selama instruksi tersebut tidak bertentangan dengan constraint akademik dan sistem.

## AIR-003 — Structured Output

**Priority:** Must

Agent harus menghasilkan output dalam struktur yang dapat divalidasi dan diproses oleh sistem.

## AIR-004 — Validation-Aware Generation

**Priority:** Must

Generation harus dapat dievaluasi menggunakan validation criteria.

## AIR-005 — Retry/Fix

**Priority:** Should

Agent harus mampu memperbaiki output ketika validation menemukan masalah yang dapat diperbaiki secara otomatis.

## AIR-006 — Tool Use

**Priority:** Must

Agent harus dapat menggunakan tool yang tersedia melalui controlled tool layer untuk melakukan operasi yang diperlukan.

## AIR-007 — No Uncontrolled Execution

**Priority:** Must

Agent tidak boleh melakukan operasi eksternal di luar tool yang telah ditentukan dan dikontrol sistem.

## AIR-008 — Model Evaluation

**Priority:** Must

Model LLM harus dievaluasi sebelum ditetapkan sebagai model final berdasarkan:

* instruction following;
* Bahasa Indonesia;
* reasoning;
* structured output;
* tool calling;
* RPS adherence;
* content quality;
* latency;
* resource/hardware requirements.

---

# 24. Moodle Content Requirements

Produk menargetkan kemampuan untuk membangun course pembelajaran pada Moodle yang mencakup:

### Must

* Course structure
* Weekly sections
* Learning materials
* Basic learning resources
* Student access
* Verification

### Should

* Assignment
* Quiz

### Won't

* Attendance
* Full grade management
* Student academic administration
* Full Moodle administration

Tipe Moodle activity tambahan dapat dipertimbangkan apabila diperlukan, tetapi tidak boleh mengganggu penyelesaian MVP.

---

# 25. User Stories

## Instructor

### US-001

Sebagai dosen, saya ingin mengunggah RPS agar sistem dapat memahami struktur pembelajaran mata kuliah saya.

### US-002

Sebagai dosen, saya ingin melihat hasil analisis RPS agar saya dapat memastikan sistem memahami RPS dengan benar.

### US-003

Sebagai dosen, saya ingin mendapatkan course plan otomatis agar saya tidak perlu menyusun struktur course secara manual.

### US-004

Sebagai dosen, saya ingin menentukan preferensi penyampaian materi agar konten sesuai dengan gaya mengajar saya.

### US-005

Sebagai dosen, saya ingin memberikan prompt tambahan agar agent dapat mengikuti kebutuhan khusus saya.

### US-006

Sebagai dosen, saya ingin memilih apakah tugas dan kuis digunakan agar agent menghasilkan aktivitas sesuai kebutuhan saya.

### US-007

Sebagai dosen, saya ingin melihat konten yang dihasilkan sebelum dipublikasikan agar saya dapat mengontrol kualitas materi.

### US-008

Sebagai dosen, saya ingin meminta regeneration terhadap konten tertentu agar saya dapat memperbaiki hasil yang tidak sesuai.

### US-009

Sebagai dosen, saya ingin melihat proses agent agar saya mengetahui apa yang sedang dikerjakan sistem.

### US-010

Sebagai dosen, saya ingin mengirim konten yang telah saya setujui ke Moodle agar saya tidak perlu memasukkan konten secara manual.

### US-011

Sebagai dosen, saya ingin mengetahui apakah konten berhasil dimasukkan ke Moodle agar saya dapat memastikan course siap digunakan.

## Student

### US-012

Sebagai mahasiswa, saya ingin mengakses course yang telah dibuat agar saya dapat melihat materi pembelajaran.

### US-013

Sebagai mahasiswa, saya ingin mengakses aktivitas pembelajaran yang tersedia agar saya dapat mengikuti pembelajaran.

---

# 26. Acceptance Criteria

MVP minimal harus memenuhi acceptance criteria berikut:

### AC-001 — RPS Processing

Given instructor mengunggah RPS yang valid,

When proses dijalankan,

Then sistem dapat memproses RPS dan menghasilkan representation yang dapat digunakan oleh agent.

### AC-002 — Course Planning

Given RPS telah dianalisis,

When instructor menjalankan course planning,

Then agent menghasilkan course plan berdasarkan informasi RPS.

### AC-003 — Weekly Generation

Given course plan telah tersedia,

When instructor menjalankan content generation,

Then agent menghasilkan konten berdasarkan minggu pembelajaran yang ditentukan.

### AC-004 — Activity Selection

Given instructor memilih jenis aktivitas tertentu,

When content generation dilakukan,

Then agent hanya menghasilkan aktivitas yang diaktifkan sesuai konfigurasi.

### AC-005 — Validation

Given agent menghasilkan konten,

When validation dijalankan,

Then sistem menghasilkan validation result yang menunjukkan status output.

### AC-006 — Instructor Review

Given konten telah dihasilkan,

When instructor membuka review interface,

Then instructor dapat melihat dan mengevaluasi hasil sebelum execution.

### AC-007 — Regeneration

Given instructor menolak hasil tertentu,

When instructor meminta regeneration,

Then sistem menghasilkan versi baru tanpa harus selalu mengulang keseluruhan workflow.

### AC-008 — Moodle Execution

Given hasil telah disetujui,

When instructor menjalankan execution,

Then sistem mengirim hasil ke Moodle melalui Moodle Web Service API yang tersedia.

### AC-009 — Student Access

Given execution berhasil,

When student mengakses course,

Then student dapat melihat konten yang telah dipublikasikan.

### AC-010 — Verification

Given course telah dieksekusi,

When verification dilakukan,

Then sistem dapat menentukan apakah hasil execution sesuai dengan hasil yang direncanakan.

### AC-011 — Monitoring

Given agent sedang menjalankan workflow,

When instructor membuka monitoring interface,

Then instructor dapat melihat tahap dan status proses agent.

### AC-012 — Failure Handling

Given salah satu tahap agent mengalami kegagalan,

When sistem mendeteksi failure,

Then sistem menyimpan status failure dan menjalankan retry/fix apabila kondisi memungkinkan.

---

# 27. Product Constraints

1. Sistem merupakan Capstone Project dengan waktu pengembangan terbatas.
2. MVP harus memprioritaskan workflow end-to-end.
3. Moodle integration bergantung pada Web Service functions dan permissions yang tersedia pada Moodle ITK.
4. Local LLM dibatasi oleh hardware yang tersedia.
5. Kualitas output AI tidak dapat diasumsikan selalu benar.
6. Instructor review tetap diperlukan sebagai kontrol kualitas.
7. Sistem tidak bertujuan menggantikan keputusan akademik dosen.
8. Custom browser bukan requirement produk.

---

# 28. Product Assumptions

1. RPS menyediakan informasi yang cukup untuk membangun course plan.
2. Moodle ITK menyediakan Web Service API yang diperlukan untuk operasi dalam scope.
3. Environment pengujian menyediakan akses instructor dan student.
4. Local LLM dapat dijalankan pada resource yang tersedia.
5. Instructor bersedia melakukan review terhadap hasil AI.
6. Struktur course yang digunakan dalam MVP dapat direpresentasikan pada Moodle.
7. Assignment dan quiz dapat digunakan apabila capability Moodle yang diperlukan tersedia.

---

# 29. Dependencies

Product bergantung pada:

1. Moodle LMS ITK.
2. Moodle Web Service API.
3. Moodle authentication.
4. Moodle permissions/capabilities.
5. Environment Moodle untuk testing.
6. RPS untuk development dan testing.
7. Hardware untuk local LLM.
8. Availability dan guidance dari supervisor.
9. Availability anggota tim untuk development dan testing.

---

# 30. Requirement Traceability

Setiap requirement utama harus dapat ditelusuri ke:

```text
Project Objective
       ↓
Product Requirement
       ↓
Feature
       ↓
Implementation Task
       ↓
Test Case
       ↓
Acceptance Result
```

Requirement yang menghasilkan perubahan scope harus dievaluasi sebelum dimasukkan ke backlog.

---

# 31. Requirement Change Management

Requirement baru tidak otomatis menjadi bagian dari MVP.

Setiap proposed requirement harus dievaluasi berdasarkan:

* nilai terhadap user;
* kontribusi terhadap project objective;
* development effort;
* schedule impact;
* technical complexity;
* dependency;
* risk;
* quality impact.

Requirement yang tidak memberikan kontribusi signifikan terhadap tujuan utama dapat ditunda atau ditempatkan di luar MVP.

---

# 32. Requirement Status

Requirement dapat memiliki status:

| Status       | Meaning                                        |
| ------------ | ---------------------------------------------- |
| Proposed     | Requirement diusulkan tetapi belum disepakati  |
| Confirmed    | Requirement telah disepakati                   |
| In Progress  | Requirement sedang diimplementasikan           |
| Implemented  | Requirement telah diimplementasikan            |
| Tested       | Requirement telah diuji                        |
| Accepted     | Requirement telah memenuhi acceptance criteria |
| Rejected     | Requirement tidak diterima                     |
| Deferred     | Requirement ditunda                            |
| Out of Scope | Requirement berada di luar scope               |

---

# 33. Open Questions

Hal-hal berikut masih perlu dikonfirmasi atau ditentukan pada tahap lanjutan:

1. Moodle Web Service functions spesifik yang diperlukan untuk setiap operasi.
2. Authentication mechanism yang digunakan pada environment Moodle ITK.
3. Permission/capability Moodle yang tersedia.
4. Model LLM final.
5. Document processing solution final.
6. Detail struktur output konten yang akan digunakan untuk Moodle.
7. Detail validation criteria dan scoring.
8. Detail state machine Agent.
9. Detail monitoring event dan real-time communication.
10. Batas maksimum ukuran RPS yang akan didukung MVP.
11. Apakah seluruh 16 minggu diproses sekaligus atau dapat diproses bertahap.
12. Mekanisme penyimpanan version hasil generation dan regeneration.

---

# 34. MVP Boundary

Untuk mencegah scope creep, MVP difokuskan pada satu workflow utama:

```text
Instructor
    ↓
Upload RPS
    ↓
Analyze RPS
    ↓
Generate Course Plan
    ↓
Review Course Plan
    ↓
Generate Weekly Content
    ↓
Validate
    ↓
Review
    ↓
Approve
    ↓
Execute to Moodle
    ↓
Verify as Student
```

Fitur yang tidak secara langsung mendukung workflow tersebut tidak menjadi prioritas MVP.

---

# 35. Product Success Indicators

Indikator keberhasilan produk akan dievaluasi berdasarkan:

1. Persentase course plan yang sesuai dengan RPS.
2. Kualitas konten pembelajaran.
3. Kelengkapan konten semester.
4. Keberhasilan execution ke Moodle.
5. Keberhasilan student access.
6. Keakuratan verification.
7. Waktu yang dibutuhkan untuk menghasilkan course dibandingkan proses manual.
8. Jumlah intervention yang diperlukan dari instructor.
9. Reliability agent.
10. Usability sistem bagi instructor.

Nilai target dan metode pengukuran ditentukan dalam **Quality Plan**.

---

# 36. Related Documents

| Document             | Relationship                             |
| -------------------- | ---------------------------------------- |
| `project-charter.md` | Baseline tujuan dan scope proyek         |
| `quality-plan.md`    | Metode pengujian dan pengukuran kualitas |
| `risk-register.md`   | Pengelolaan risiko                       |
| `decision-log.md`    | Pencatatan keputusan proyek              |
| `issue-log.md`       | Pengelolaan masalah yang telah terjadi   |
| `meeting-notes/`     | Dokumentasi hasil rapat                  |
| `system-design.md`   | Desain teknis sistem                     |
| Kanban               | Source of truth untuk task dan schedule  |

---

# 37. Document Control

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| Document     | Product Requirements Document          |
| Project      | Agentic AI untuk Mengisi Konten Moodle |
| Version      | 0.1                                    |
| Status       | Draft                                  |
| Owner        | Project Manager                        |
| Last Updated | 2026-09-02                             |

## Version History

| Version | Date       | Description | Author       |
| ------- | ---------- | ----------- | ------------ |
| 0.1     | 2026-09-02 | Initial PRD | Project Team |
