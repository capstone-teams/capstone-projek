# PROJECT CHARTER

## Agentic AI untuk Mengisi Konten Pembelajaran Moodle
**Project Type**: Capstone Project
**Project Manager**: Noel
**Document Version**: 0.1
**Status**: Draf

------------------------------------------------------------
## 1. Project Overview
Proyek Agentic AI untuk Mengisi Konten Pembelajaran Moodle merupakan proyek Capstone yang bertujuan mengembangkan sistem berbasis Agentic AI untuk membantu dosen mengubah Rencana Pembelajaran Semester (RPS) menjadi struktur dan konten pembelajaran yang siap digunakan pada Moodle.

Sistem memanfaatkan RPS sebagai sumber utama informasi akademik, kemudian menggunakan informasi profile/intruksi dosen untuk menyesuaikan penyampaian materi. Agent akan menjalankan proses secara bertahap mulai dari memahami RPS, menyusun perencanaan course, menghasilkan konten pembelajaran, melakukan validasi, meminta review dosen, hingga mengeksekusi hasil yang telah disetujui ke Moodle.

Target utama sistem adalah mengurangi pekerjaan manual dosen dalam menyiapkan konten pembelajaran satu semester pada Moodle, sekaligus mempertahankan kontrol dosen terhadap hasil yang dihasilkan AI.

## 2. Background
Moodle menyediakan berbagai fasilitas untuk mendukung pembelajaran, tetapi proses menyiapkan course tetap membutuhkan pekerjaan manual dari dosen. Dosen lalu menerjemahkan RPS menjadi struktur course, menyusun materi setiap minggu, menambahkan sumber belajar, serta apabila diperlukan menyiapkan aktivitas seperti tugas dan kuis.

Dalam konteks satu semester, proses tersebut dapat mencakup sejumlah besar konten yang harus disiapkan secara konsisten dengan RPS.

Generative AI dapat membantu menghasilkan materi pembelajaran, tetapi pendekatan chatbot atau text generation biasa belum cukup untuk menjalankan keseluruhan proses tersebut secara terstruktur. Sistem membutuhkan kemampuan untuk memahami dokumen sumber, merencanakan pekerjaan, menghasilkan konten, memvalidasi hasil, melakukan perbaikan, serta menjalankan tindakan pada sistem eskternal secara terkendali.

Oleh karena itu, proyek ini menggunakan pendekatan Agentic AI dengan Moodle sebagai platform tujuan.

## 3. Problem Statement
Dosen membutuhkan waktu dan usaha untuk menerjemahkan RPS menjadi course Moodle yang lengkap selama satu semester. Proses tersebut mencakup penyusunan struktur pembelajaran mingguan dan pembuatan berbagai jenis konten secara manual.

Permasalahan utama yang ingin diselesaikan adalah:
1. Tingginya pekerjaan manual dalam menyiapkan konten pembelajaran Moodle.
2. Kesulitan menjaga kesesuaian seluruh konten dengan RPS.
3. Kebuthan untuk menghasilkan konten dalam jumlah besar secara terstruktur untuk satu semester.
4. Risiko ketidakkonsistenan format dan penyampaian materi.
5. Kebutuhan dosen untuk tetap melakuakn review dan memiliki kontrol atas hasil AI
6. Belum adanya mekanisme agentic yang dapat menghubungkan proses pemahaman RPS, content generation, validation, dan eksekusi ke Moodle dalam satu workflow.

## 4. Project Purpose
Proyek ini bertujuan menghasilkan sistem Agentic AI yang dapat membantu dosen:
- Memproses dan memahami RPS
- Merencakan struktur course berdasarkan RPS
- Menghasilkan konten pembelajaran untuk satu semester
- Menyesuaikan penyampaian berdasarkan profil atau preferensi instruks
- Menerima instruksi tambahan dari dosen
- Memvalidasi hasil yang dihasilkan agent
- Memberikan kesempatan kepada dosen untuk melakukan review dan regenerasi
- Mengisi konten yang telah disetujui ke Moodle
- Memverifikasi hasil pengisian pada Moodle; dan
- Menyediakan antarmuka untuk memonitor proses yang dilakukan agent

## Project Objectives
### 5.1 Primary Objective
Mengembangkan sistem Agentic AI yang mampu mengotomatisasi proses transformasi RPS menjadi course dan konten pembelajaran Moodle selama satu semester dengan tetap menyediakan kontrol dan review oleh dosen.

### 5.2 Supporting Objectives
1. Mengubah RPS dalam format dokumen menjadi representasi yang dapat diproses sistem.
2. Menghasilkan course plan berdasarkan informasi akademik dalam RPS
3. Menghasilkan konten pembelajaran mingguan berdasarkan course plan.
4. Menjaga keterkaitan konten yang dihasilkan dengan RPS
5. Menyediakan personalisasi melalui Instructor Profile dan instruksi tambahan
6. Mendukung beberapa tipe konten pembelajaran, termasuk materi pembelajaran serta aktivitas seperti tugas dan kuis secara opsional
7. Menyediakan mekanisme validasi dan perbaikan hasil AI
8. Mengintegrasikan hasil yang telah disetujui dengan Moodle melalui Moodle Web Service API
9. Menyediakan UI monitoring untuk memperlihatkan status dan aktivitas agent.
10. Menyediakan student role/account untuk melihat dan memverifikasi hasil course dari perspektif mahasiswa.

## High-Level Product Concept
Sistem mengikuti workflow utama:

`RPS` ➔ `RPS Processing` ➔ `RPS Analysis` ➔ `Instructor Profile` ➔ `Course Planning` ➔ `Weekly Content Generation` ➔ `Validation` ➔ `Instructor Review` ➔ `Moodle Execution` ➔ `Verification`

### Detail Tahapan Operasional

**1. RPS (Rencana Pembelajaran Semester)**
* Input: Dokumen silabus atau kurikulum mentah dari program studi.
* Tujuan: Menjadi sumber data utama seluruh materi kuliah.

**2. RPS Processing**
* Aktivitas: Digitalisasi dan ekstraksi teks dari dokumen RPS.
* Output: Data terstruktur yang siap dibaca oleh sistem.

**3. RPS Analysis**
* Aktivitas: Membedah Capaian Pembelajaran Lulusan (CPL) dan CPMK.
* Tujuan: Menentukan taksonomi Bloom dan bobot materi.

**4. Instructor Profile (+ Optional Prompt)**
* **Komponen:** Rekam jejak pengajar, gaya mengajar, dan keahlian utama.
* **Kustomisasi:** Penambahan instruksi khusus (*prompt*) sesuai preferensi instruktur.

**5. Course Planning**
* Aktivitas: Penyusunan peta jalan pembelajaran selama satu semester.
* Output: Struktur makro mata kuliah (topik besar dan alokasi waktu).

**6. Weekly Content Generation**
* Aktivitas: Pembuatan materi modular mingguan (teks, kuis, tugas).
* Metode: Otomatisasi berbasis AI menggunakan profil pengajar.

**7. Validation**
* Aktivitas: Pengecekan otomatis terhadap kualitas dan akurasi konten.
**Kriteri** Kesesuaian materi dengan standar akademik dan bebas plagiasi.

**8. Instructor Review**
* Aktivitas: Peninjauan langsung dan persetujuan oleh dosen pengampu.
* Output: Konten final yang telah divalidasi secara manual.

**9. Moodle Execution**
* Aktivitas: Migrasi dan *upload* otomatis seluruh konten ke platform Moodle.
* Komponen: Pengaturan *course*, *activity*, dan *resource* di LMS.

**10. Verification**
* Aktivitas: Pengujian akhir tampilan dan fungsi *link/kuis* di Moodle.
* Tujuan: Memastikan kursus siap diakses oleh mahasiswa tanpa kendala.

---
Agent tidak hanya menghasilkan teks, tetapi menghasilkan siklus:
`Understand` ➔ `Plan` ➔ `Generate` ➔ `Validate` ➔ `Execute` ➔ `Verify` ➔ `Retry/Fix`

Human-in-the-loop tetap dipertahankan pada tahap review sehingga dosen dapat menerima, mengubah, atau melakukan regenerasi terhadap hasil sebelum konten dieksekusi ke Moodle.

## 7. Scope
### 7.1 In Scope
#### A. RPS Processing
Sistem mendukung input RPS dalam format dikumen yang relevan, terutama PDF dan DOCX.

RPS diproses menjadi representasi yang dapat digunakan oleh sistem AI, termasuk representasi teks/Markdown dan structured data yang diperlukan untuk proses analisis dan generation. RPS menjadi sumber utama informasi akademik untuk proses pembuatan course.

#### B. RPS Analysis

Agent menganalisis informasi penting dari RPS, termasuk struktur pembelajaran, capaian pembelajaran, materi, pembagian pembelajaran, dan informasi relevan lainnya yang dibutuhkan untuk membangun course.

Hasil analisis digunakan sebagai dasar untuk course planning dan content generation.

#### C. Instructor Profile

Sistem menyediakan profil instruktur untuk menyimpan informasi yang dapat memengaruhi cara konten pembelajaran dihasilkan, seperti preferensi gaya penyampaian atau karakteristik pembelajaran.

Instructor Profile digunakan sebagai konteks tambahan dan tidak menggantikan RPS sebagai sumber informasi akademik utama.

#### D. Additional Prompt

Dosen dapat memberikan instruksi tambahan kepada agent untuk memengaruhi proses planning atau content generation.

Prompt tambahan digunakan sebagai instruksi tambahan terhadap konteks RPS dan Instructor Profile.

#### E. Course Planning

Agent menghasilkan rancangan course berdasarkan RPS.

Course plan mencakup struktur pembelajaran satu semester, termasuk pembagian materi berdasarkan minggu pembelajaran.

Target utama adalah mendukung struktur pembelajaran sekitar satu semester, yang secara umum terdiri dari hingga 16 minggu sesuai struktur RPS/course yang digunakan.

#### F. Weekly Content Generation

Agent menghasilkan konten pembelajaran berdasarkan course plan.

Konten dapat mencakup:
- materi pembelajaran;
- penjelasan konsep;
- struktur materi per minggu;
- learning resources atau referensi yang relevan;
- aktivitas pembelajaran;
- tugas;
- kuis; dan
- tipe konten pembelajaran lain yang ditetapkan dalam scope implementasi.

Tugas dan kuis bersifat opsional dan penggunaannya harus dapat ditentukan oleh dosen melalui konfigurasi/pilihan sebelum atau selama proses generation.

Agent tidak secara otomatis menentukan seluruh tipe aktivitas tanpa mempertimbangkan pilihan dosen.

#### G. Instructor Review

Dosen dapat meninjau hasil course plan dan konten yang dihasilkan agent.

Dosen dapat:
- menerima hasil;
- melakukan perubahan;
- meminta regenerasi;
- memberikan instruksi tambahan; atau
- menolak hasil sebelum eksekusi ke Moodle.

#### H. Agent Validation

Agent melakukan validasi terhadap hasil generation sebelum eksekusi.

Validasi diarahkan antara lain untuk memastikan:
- kesesuaian dengan informasi RPS;
- kelengkapan struktur;
- konsistensi antarbagian;
- kesesuaian tipe konten dengan konfigurasi dosen; dan
- validitas struktur output yang dibutuhkan sistem.

Jika hasil tidak memenuhi kriteria validasi, agent dapat melakukan retry atau perbaikan sesuai mekanisme yang dirancang.

#### I. Moodle Integration

Sistem mengintegrasikan hasil yang telah disetujui dengan Moodle LMS ITK menggunakan Moodle Web Service API yang disediakan oleh platform Moodle.

Implementasi mengacu pada dokumentasi resmi Moodle serta kemampuan Web Service yang tersedia dan diaktifkan pada instance Moodle ITK.

Kapabilitas integrasi mencakup kebutuhan yang diperlukan untuk:
- mengakses atau menentukan course;
- mengelola struktur pembelajaran mingguan;
- menambahkan atau memperbarui konten materi;
- menambahkan aktivitas pembelajaran yang didukung;
- mengelola kebutuhan role/access yang diperlukan untuk pengujian;
- memastikan hasil generation dapat direpresentasikan pada Moodle; dan
- memverifikasi hasil setelah proses eksekusi.

Detail function, endpoint, parameter, authentication, dan permission Moodle ditentukan pada tahap technical design dan implementasi berdasarkan konfigurasi Moodle ITK.

#### J. Student Role and Verification

Sistem menyediakan atau menggunakan student role/account pada environment Moodle untuk memungkinkan hasil course dilihat dari perspektif mahasiswa.

Student role digunakan terutama untuk:
- mengakses course yang telah diisi;
- melihat materi pembelajaran;
- melihat aktivitas yang dibuat;
- memverifikasi tampilan dan ketersediaan konten; dan
- mendukung proses verification terhadap hasil eksekusi agent.

Sistem tidak ditujukan untuk menjadi platform student management atau sistem akademik mahasiswa secara penuh.

#### K. Agent Monitoring UI

Sistem menyediakan UI pada web application untuk memonitor proses yang dilakukan agent.

Monitoring dapat menampilkan informasi seperti:
- status proses;
- tahap workflow agent;
- aktivitas yang sedang dilakukan;
- hasil setiap tahap;
- validation status;
- execution status;
- error atau failure;
- retry/fix process; dan
- status akhir proses.

UI monitoring merupakan bagian dari produk dan bukan hanya debugging interface untuk developer.

### 7.2 Out of Scope

Fitur berikut tidak menjadi target utama proyek:
1. Sistem absensi mahasiswa.
2. Sistem pengelolaan kehadiran.
3. Sistem akademik mahasiswa secara menyeluruh.
4. Sistem pengelolaan nilai akademik secara menyeluruh.
5. Pengembangan LMS baru.
6. Pengembangan Moodle fork atau modifikasi core Moodle.
7. Pengembangan API Moodle khusus milik ITK.
8. Pembuatan custom browser/Chromium sebagai bagian wajib produk.
9. Pengelolaan seluruh administrasi akademik dosen.
10. Penggantian penuh peran dosen dalam proses pembelajaran.
11. Publikasi otomatis tanpa mekanisme kontrol/review yang ditentukan.
12. Fitur AI yang tidak berhubungan langsung dengan proses transformasi RPS menjadi konten Moodle.

Tugas dan kuis dapat menjadi bagian dari scope sebagai optional learning activities, tetapi bukan berarti seluruh jenis aktivitas Moodle harus didukung.

## 8. High-Level User Roles

****Dosen****

Dosen merupakan pengguna utama sistem.

Dosen bertanggung jawab untuk:
- mengunggah RPS;
- mengatur preferensi/profile;
- memberikan instruksi tambahan;
- menentukan konfigurasi content generation;
- memilih kebutuhan aktivitas seperti tugas atau kuis;
- menjalankan proses generation;
- memonitor proses agent;
- melakukan review;
- menerima atau meminta regenerasi hasil; dan
- mengizinkan hasil yang telah disetujui untuk dieksekusi ke Moodle.

****Student / Mahasiswa****

Student merupakan pengguna akhir dari course yang dihasilkan.

Student dapat digunakan untuk:
- mengakses course;
- melihat materi;
- mengakses aktivitas yang tersedia; dan
- membantu memverifikasi hasil course dari perspektif pengguna mahasiswa.

****Agent****

Agent merupakan komponen AI yang menjalankan workflow untuk memahami, merencanakan, menghasilkan, memvalidasi, mengeksekusi, dan memverifikasi pekerjaan.

Agent tidak diberikan akses langsung terhadap credential Moodle.

## 9. High-Level Architecture Direction

Arsitektur sistem secara konseptual terdiri dari:

`Web Application` → `Backend` → `Agent/LLM Layer` → `Controlled Tool Layer` → `Moodle Service` → `Moodle Web Service API` → `Moodle LMS`

LLM/agent tidak berkomunikasi langsung dengan credential atau API Moodle.

Akses terhadap sistem eksternal dilakukan melalui controlled tool layer sehingga authentication, authorization, request execution, validation, error handling, dan batasan operasi dapat dikontrol oleh backend.

Arsitektur harus menjaga pemisahan antara agent dan Moodle sehingga perubahan atau keterbatasan pada integrasi Moodle tidak mengharuskan perubahan pada core agent secara keseluruhan.

## 10. Technology Direction

Technology direction berikut merupakan baseline proyek dan tidak seluruhnya merupakan keputusan final.
| Komponen              | Teknologi             |
| :---                  | :---                  |
| Frontend              | React + TypeScript    |
| Backend               | FastAPI + Python      |
| Database              | PostgreSQL            |
| LLM Runtime           | Ollama                |
| LLM Model             | evaluated             |
| Document Processing   | Docling               |
| Content Representation| Markdown + JSON       |
| Moodle Integration    | Moodle Web Service API|
| Agent Monitoring      | WebScoket             |
| Client                | Web App               |

Pemilihan model LLM final dilakukan berdasarkan evaluasi terhadap instruction following, kemampuan Bahasa Indonesia, reasoning, structured output, tool calling, adherence terhadap RPS, latency, serta kebutuhan hardware.

## 11. Key Deliverables
Deliverable utama proyek meliputi:
1. Sistem web application untuk pengelolaan workflow Agentic AI.
2. RPS processing pipeline.
3. RPS analysis component.
4. Instructor Profile mechanism.
5. Course planning mechanism.
6. Weekly content generation mechanism.
7. Optional learning activity generation untuk tipe yang didukung.
8. Agent validation dan retry/fix mechanism.
9. Instructor review interface.
10. Agent monitoring interface.
11. Moodle integration layer.
12. Moodle course/content execution mechanism.
13. Student access/verification environment.
14. Documentation teknis dan dokumentasi proyek.
15. Hasil evaluasi kualitas dan performa sistem.

## 12. Stackholders
Stakeholder utama proyek meliputi:
| Stakeholder           | Peran/Kepentingan             |
| :---                  | :---                  |
| Dosen Pembimbing      | Memberikan arahan, validasi, dan evaluasi proyek   |
| Dosen                 | Pengguna utama dan target utama solusi |
| Mahasiswa             | Pengguna akhir course dan pihak yang memverifikasi hasil |
| Tim Capstone          | Pengembang dan pengelola |
| Moodle                | Menyediakan environment Moodle yang menjadi target integrasi |

## 13. Constraints
Project memiliki beberapa constraint utama:
1. Proyek merupakan Capstone Project dengan waktu dan resource terbatas.
2. Kemampuan integrasi dibatasi oleh Web Service API dan permission yang tersedia
3. pada Moodle ITK.
4. Performa Agentic AI dipengaruhi oleh hardware yang tersedia untuk menjalankan local LLM.
5. Kualitas output AI tidak dapat diasumsikan selalu benar sehingga mekanisme validation dan human review diperlukan.
6. Scope harus dibatasi agar implementasi inti dapat diselesaikan dalam periode Capstone.
7. Sistem harus menjaga keamanan credential dan tidak memberikan akses langsung credential Moodle kepada LLM.

## 14. Assumptions
Asumsi awal proyek:
1. Moodle ITK menggunakan Moodle Web Service API yang mengikuti mekanisme dan dokumentasi Moodle.
2. Environment Moodle yang digunakan menyediakan Web Service dan permission yang dibutuhkan untuk operasi dalam scope proyek.
3. Dosen dapat menyediakan RPS sebagai sumber utama informasi pembelajaran.
4. Local LLM dapat dijalankan menggunakan environment/hardware yang tersedia bagi tim.
5. Dosen tetap menjadi pihak yang memiliki keputusan akhir terhadap konten yang dipublikasikan.
6. Student role/account tersedia atau dapat disiapkan pada environment pengujian Moodle.
7. Format dan struktur RPS yang digunakan dalam pengujian memiliki informasi yang cukup untuk menghasilkan course plan dan konten.

Asumsi yang terbukti tidak valid harus dicatat dan dievaluasi dampaknya terhadap scope, schedule, architecture, dan risk.

## 15. Dependencies
Project memiliki dependency terhadap:
1. Moodle LMS ITK dan environment pengujiannya.
2. Konfigurasi Moodle Web Service.
3. Authentication dan credential yang diperlukan untuk integrasi.
4. Permission/capability Moodle yang diperlukan untuk operasi dalam scope.
5. Hardware untuk menjalankan local LLM.
6. Ketersediaan RPS untuk development dan testing.
7. Arahan dan validasi dosen pembimbing.
8. Ketersediaan anggota tim untuk pengembangan dan pengujian.

## 16. Initial Risks

| Risk                                                         | Potential Impact                                    | Initial Mitigation                                                            |
| ------------------------------------------------------------ | --------------------------------------------------- | ----------------------------------------------------------------------------- |
| Output AI tidak sesuai RPS                                   | Quality konten menurun                              | RPS grounding, validation, review, dan regeneration                           |
| Model LLM tidak memenuhi kebutuhan                           | Kualitas generation dan performa agent rendah       | Evaluasi beberapa kandidat model berdasarkan benchmark yang ditentukan        |
| Local LLM terlalu lambat                                     | Workflow menjadi tidak praktis                      | Benchmark model, optimasi prompt, dan optimasi workflow                       |
| Moodle Web Service tidak mendukung kebutuhan tertentu        | Integrasi terhambat                                 | Identifikasi function yang dibutuhkan lebih awal dan gunakan abstraction/mock |
| Permission Moodle tidak mencukupi                            | Execution ke Moodle gagal                           | Validasi capability dan permission pada environment sejak awal                |
| RPS memiliki format atau struktur yang sulit diproses        | Analisis dan generation tidak akurat                | Document processing pipeline dan validation                                   |
| Agent melakukan kesalahan saat execution                     | Course atau konten Moodle dapat salah               | Controlled tool layer, validation, instructor review, dan verification        |
| Scope berkembang terlalu besar                               | Schedule dan quality terdampak                      | Menetapkan MVP boundary dan menerapkan change control                         |
| Konten AI tidak memenuhi kualitas pedagogis                  | Materi kurang layak digunakan                       | Instructor review dan quality evaluation                                      |
| Monitoring tidak merepresentasikan state agent secara akurat | Transparansi workflow rendah                        | Mendefinisikan state dan event agent sejak system design                      |
| Keterbatasan hardware local LLM                              | Generation lambat atau model tidak dapat dijalankan | Hardware benchmarking dan pemilihan model berdasarkan resource yang tersedia  |
| Integrasi antar komponen tidak konsisten                     | Sistem end-to-end gagal                             | Menetapkan interface dan contract antar komponen sejak tahap system design    |

---

## 17. Quality Expectations

Kualitas sistem tidak hanya dinilai berdasarkan kemampuan menghasilkan konten, tetapi juga berdasarkan kualitas proses dan hasil akhir.

### 17.1 RPS Adherence

Konten yang dihasilkan harus memiliki keterkaitan yang jelas dengan informasi yang terdapat dalam RPS dan tidak menyimpang dari tujuan pembelajaran yang ditetapkan.

### 17.2 Content Completeness

Sistem harus mampu menghasilkan konten untuk struktur semester yang ditargetkan secara lengkap sesuai dengan course plan dan konfigurasi yang dipilih dosen.

### 17.3 Structural Consistency

Struktur course, materi mingguan, dan aktivitas pembelajaran harus memiliki format dan organisasi yang konsisten.

### 17.4 Content Quality

Konten yang dihasilkan harus memenuhi kriteria kualitas pembelajaran yang telah ditentukan dan dapat digunakan setelah melalui proses review dosen.

### 17.5 Agent Reliability

Agent harus mampu menangani kegagalan proses, melakukan validation, serta menjalankan retry atau fix ketika output tidak memenuhi kriteria yang telah ditentukan.

### 17.6 Execution Reliability

Konten yang telah disetujui harus dapat dieksekusi ke Moodle sesuai dengan struktur dan konfigurasi yang direncanakan.

### 17.7 Verification Accuracy

Sistem harus mampu memverifikasi bahwa hasil execution pada Moodle sesuai dengan hasil yang telah disetujui.

### 17.8 Usability

Dosen harus dapat memahami dan mengendalikan workflow sistem tanpa harus memahami detail internal Agentic AI.

### 17.9 Transparency

Proses yang dilakukan agent harus dapat dipantau melalui monitoring interface sehingga pengguna dapat mengetahui status dan aktivitas agent.

### 17.10 Security

Credential dan akses Moodle tidak boleh diberikan secara langsung kepada LLM. Seluruh operasi terhadap Moodle harus melalui controlled tool layer yang dikendalikan oleh backend.

Metrik kuantitatif dan metode pengukuran untuk setiap aspek kualitas akan didefinisikan lebih lanjut dalam **Quality Plan**.

---

## 18. Success Criteria

Project dianggap berhasil apabila MVP mampu menunjukkan workflow end-to-end berikut:

```text
RPS
 ↓
RPS Processing
 ↓
RPS Analysis
 ↓
Course Planning
 ↓
Weekly Content Generation
 ↓
Validation
 ↓
Instructor Review
 ↓
Moodle Execution
 ↓
Student Verification
```

Keberhasilan MVP ditunjukkan apabila:

1. RPS dapat diproses oleh sistem.
2. Agent dapat menganalisis informasi utama dari RPS.
3. Agent dapat menghasilkan course plan berdasarkan RPS.
4. Agent dapat menghasilkan konten pembelajaran untuk struktur semester yang ditargetkan.
5. Dosen dapat menentukan tipe aktivitas pembelajaran yang ingin digunakan, termasuk opsi tugas dan kuis.
6. Dosen dapat melakukan review terhadap hasil sebelum execution.
7. Dosen dapat meminta regeneration terhadap hasil yang tidak sesuai.
8. Sistem dapat melakukan validation terhadap hasil generation.
9. Sistem dapat mengirim hasil yang telah disetujui ke Moodle melalui Moodle Web Service API.
10. Course dan konten yang telah dibuat dapat diakses menggunakan student role/account.
11. Hasil course dapat diverifikasi dari perspektif student.
12. Proses agent dapat dimonitor melalui web interface.
13. Agent memiliki mekanisme retry/fix terhadap kegagalan yang dapat ditangani.
14. Credential Moodle tidak diberikan secara langsung kepada LLM.
15. Sistem memenuhi kriteria kualitas yang telah ditetapkan dalam Quality Plan.

---

## 19. Project Governance

Project dikelola dengan pendekatan yang berorientasi pada:

* scope;
* schedule;
* quality;
* resource;
* risk;
* communication;
* integration; dan
* deliverable.

### 19.1 Task and Schedule Management

Kanban tim digunakan sebagai **source of truth untuk task dan schedule operasional**.

Project Charter tidak menggantikan Kanban dan tidak digunakan sebagai sistem task management kedua.

### 19.2 Decision Management

Keputusan penting yang berkaitan dengan:

* architecture;
* technology;
* scope;
* requirement;
* integration; atau
* perubahan besar terhadap project direction

harus dicatat dalam **Decision Log**.

### 19.3 Risk Management

Potensi masalah yang belum terjadi dicatat dan dikelola melalui **Risk Register**.

Risk harus dievaluasi berdasarkan probability, impact, mitigation, dan owner.

### 19.4 Issue Management

Masalah yang sudah terjadi dicatat dalam **Issue Log** dan harus memiliki owner serta tindakan penyelesaian yang jelas.

### 19.5 Change Management

Perubahan terhadap requirement atau scope harus dievaluasi berdasarkan dampaknya terhadap:

* scope;
* schedule;
* quality;
* resource;
* cost;
* risk; dan
* architecture.

Perubahan signifikan tidak boleh dilakukan hanya berdasarkan preferensi teknis tanpa mempertimbangkan dampaknya terhadap tujuan proyek.

---

## 20. High-Level Project Phases

Project secara umum terdiri dari beberapa fase berikut.

### Phase 1 — Project Initiation

Aktivitas:

* Project Charter
* stakeholder identification
* initial scope definition
* initial risk identification
* project governance setup

### Phase 2 — Requirement & Product Definition

Aktivitas:

* Product Requirements Document (PRD)
* user flow
* functional requirements
* non-functional requirements
* MVP definition
* acceptance criteria

### Phase 3 — System & Agent Design

Aktivitas:

* system architecture
* agent workflow
* data representation
* RPS processing design
* validation design
* tool architecture
* Moodle integration design
* monitoring architecture

### Phase 4 — Core Development

Aktivitas:

* RPS processing
* RPS analysis
* Instructor Profile
* course planning
* content generation
* validation
* retry/fix
* instructor review

### Phase 5 — Moodle Integration

Aktivitas:

* Moodle Web Service integration
* course structure execution
* content execution
* optional activity execution
* student access
* verification

### Phase 6 — Monitoring & Quality

Aktivitas:

* agent monitoring
* integration testing
* system testing
* content quality evaluation
* RPS adherence evaluation
* performance evaluation
* usability evaluation

### Phase 7 — Finalization

Aktivitas:

* bug fixing
* final integration
* documentation
* final testing
* demonstration preparation
* project evaluation

> Detail task, sprint, dan operational schedule dikelola melalui Kanban dan tidak didefinisikan di Project Charter.

---

## 21. Project Principles

Project mengikuti prinsip-prinsip berikut:

### 21.1 RPS-First

RPS menjadi sumber utama informasi akademik dalam proses course planning dan content generation.

Instructor Profile dan additional prompt berfungsi sebagai konteks tambahan dan tidak boleh menggantikan informasi akademik utama dari RPS.

### 21.2 Human-in-the-Loop

Dosen tetap memiliki kontrol terhadap hasil yang dihasilkan AI.

Konten tidak boleh dianggap final hanya karena telah berhasil dihasilkan oleh agent.

### 21.3 Agentic, Not Merely Generative

Sistem harus memiliki kemampuan workflow yang mencakup:

```text
Understand
→ Plan
→ Generate
→ Validate
→ Execute
→ Verify
→ Retry/Fix
```

Agent tidak hanya bertugas menghasilkan teks.

### 21.4 Controlled Execution

LLM tidak diberikan akses langsung terhadap credential atau Moodle API.

Operasi eksternal dilakukan melalui controlled tool layer yang dikendalikan oleh backend.

### 21.5 MVP-First

Pengembangan diprioritaskan pada fitur yang secara langsung mendukung tujuan utama proyek.

Fitur tambahan yang tidak diperlukan untuk membuktikan core value tidak boleh menggeser prioritas MVP.

### 21.6 Dependency Isolation

Dependency eksternal yang belum pasti harus diisolasi agar tidak menghambat pengembangan core system.

### 21.7 Evidence-Based Technology Selection

Pemilihan model LLM dan teknologi lainnya harus didasarkan pada kebutuhan proyek, hasil evaluasi, benchmark, dan resource yang tersedia, bukan semata-mata popularitas teknologi.

### 21.8 Traceability

Requirement, decision, risk, issue, dan perubahan scope harus dapat ditelusuri melalui dokumentasi proyek yang sesuai.

### 21.9 Quality Over Automation Rate

Keberhasilan sistem tidak hanya diukur berdasarkan jumlah konten yang dapat dibuat secara otomatis.

Kesesuaian dengan RPS, kualitas konten, reliability, dan usability juga menjadi faktor utama.

### 21.10 No Unnecessary Overengineering

Arsitektur dan teknologi harus proporsional terhadap kebutuhan Capstone.

Teknologi atau komponen tambahan tidak digunakan apabila tidak memberikan nilai yang jelas terhadap kebutuhan proyek.

---

## 22. Initial Technology Status

Status teknologi pada saat Project Charter dibuat dibagi menjadi beberapa kategori.

### 22.1 Confirmed

| Component             | Technology / Decision              |
| --------------------- | ---------------------------------- |
| Target LMS            | Moodle LMS ITK                     |
| Integration mechanism | Moodle Web Service API             |
| Client Platform       | Standard Web Application           |
| Agent Monitoring      | Monitoring UI pada Web Application |

### 22.2 Proposed

| Component              | Technology                                     |
| ---------------------- | ---------------------------------------------- |
| Frontend               | React + TypeScript                             |
| Backend                | FastAPI + Python                               |
| Database               | PostgreSQL                                     |
| LLM Runtime            | Ollama                                         |
| Content Representation | Markdown + Structured JSON                     |
| Real-Time Monitoring   | WebSocket atau mekanisme real-time yang sesuai |

### 22.3 Candidate

| Component           | Candidate                               |
| ------------------- | --------------------------------------- |
| Document Processing | Docling                                 |
| LLM Model           | Kandidat local LLM yang akan dievaluasi |

Pemilihan LLM final harus mempertimbangkan:

* instruction following;
* kemampuan Bahasa Indonesia;
* reasoning;
* structured output;
* tool calling;
* RPS adherence;
* content quality;
* latency; dan
* hardware requirements.

### 22.4 TBD

Hal berikut belum ditentukan secara final:

* model LLM final;
* document processing solution final;
* Moodle Web Service functions yang secara spesifik digunakan;
* authentication mechanism pada environment Moodle;
* permission/capability yang diperlukan;
* detail agent orchestration;
* detail monitoring protocol.

Status `TBD` berarti keputusan belum ditentukan dan tidak boleh dianggap sebagai keputusan final proyek.

---

## 23. Approval

Project Charter menjadi baseline awal proyek setelah mendapatkan persetujuan dari stakeholder yang berwenang.

Perubahan signifikan terhadap tujuan, scope, deliverable utama, constraint, atau project direction harus melalui proses evaluasi dan dicatat dalam **Decision Log**.

| Role                | Name | Approval | Date |
| ------------------- | ---- | -------- | ---- |
| Project Manager     | Noel |          |      |
| Project Supervisor  |      |          |      |
| Team Representative |      |          |      |

---

## 24. Related Project Documents

Project Charter berfungsi sebagai dokumen tingkat tinggi dan menjadi referensi bagi dokumen proyek lainnya.

Dokumen terkait:

| Document                            | Purpose                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------ |
| Project Charter                     | Mendefinisikan tujuan, scope, boundary, stakeholder, dan baseline proyek |
| Product Requirements Document (PRD) | Mendefinisikan kebutuhan dan fitur produk secara lebih detail            |
| Quality Plan                        | Mendefinisikan standar, metrik, metode pengujian, dan evaluasi kualitas  |
| Risk Register                       | Mengelola risiko proyek                                                  |
| Decision Log                        | Mencatat keputusan penting proyek                                        |
| Issue Log                           | Mengelola masalah yang sudah terjadi                                     |
| Meeting Notes                       | Mencatat hasil rapat dan pembahasan                                      |
| System Design                       | Mendefinisikan architecture dan technical design                         |
| Kanban                              | Source of truth untuk task dan schedule operasional                      |

---

## 25. Document Control

| Field         | Value                                  |
| ------------- | -------------------------------------- |
| Document      | Project Charter                        |
| Project       | Agentic AI untuk Mengisi Konten Moodle |
| Version       | 0.1                                    |
| Status        | Draft                                  |
| Owner         | Project Manager                        |
| Last Updated  | 2026-09-02                             |
| Review Status | Pending Supervisor Review              |

### Version History

| Version | Date       | Description                   | Author       |
| ------- | ---------- | ----------------------------- | ------------ |
| 0.1     | 2026-09-02 | Initial Project Charter draft | Project Team |
