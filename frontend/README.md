# Frontend — Agentic LMS

Aplikasi React dengan JavaScript/JSX untuk akses kursus Moodle dan workflow
penyusunan konten pembelajaran berbasis RPS. Dosen pengampu membuka
Generator AI dari tab di halaman kursus; mahasiswa mengakses kursus Moodle.

## Menjalankan

Gunakan Node.js ^22.13.0 atau >=24.0.0 dan npm >=10.

```powershell
cd frontend
npm ci
npm run dev
```

Buka http://localhost:3000. Port tidak berganti otomatis; restart Vite setelah
perubahan dependency atau environment. Mode default menggunakan dua mock di
browser sehingga tidak memerlukan backend atau server Moodle.

Kata sandi akun mock selalu `<username>123`. Akun yang sama tersedia di mock
backend dan mock Moodle; kolom Username juga menerima email akun.

| Akun mock | Kata sandi | Nama | Role backend |
| --- | --- | --- | --- |
| dosen.demo | dosen.demo123 | Dosen Demo (akun uji BE-06.3) | INSTRUCTOR |
| 11231023 | 11231023123 | Mahasiswa Demo (akun uji BE-06.3) | STUDENT |
| dosen | dosen123 | Rina Kartika | INSTRUCTOR |
| mahasiswa | mahasiswa123 | Andi Saputra | STUDENT |

Akun lain: dosen2, mahasiswa2, dan mahasiswa3.

Fixture kursus mencakup Pemrograman Web (kelas A dan B) dan Basis Data. Workflow backend mock
berjalan di memori: navigasi client mempertahankan perubahan, full reload
mengembalikan fixture awal. Sesi login dan preferensi UI disimpan terpisah.

## Konfigurasi koneksi

Salin `.env.example` ke `.env.local` dan sesuaikan:

| Variabel | Default | Fungsi |
| --- | --- | --- |
| VITE_MOODLE_MOCK | true | false memakai Web Service Moodle nyata |
| VITE_MOODLE_URL | http://localhost:8080 | Instance Moodle dan tautan Buka Moodle |
| VITE_MOODLE_SERVICE | moodle_mobile_app | Service login/token.php |
| VITE_USE_MOCK | true | false memakai backend capstone nyata |
| VITE_API_BASE_URL | /api/v1 | Prefix API backend; `/api/v1` memakai proxy, URL absolut memanggil backend langsung |
| VITE_BACKEND_URL | http://localhost:8000 | Tujuan proxy Vite untuk /api |

Backend development berjalan di `http://localhost:8000` dengan base URL API
`/api/v1`. Pada konfigurasi default, Vite mem-proxy `/api` ke
`VITE_BACKEND_URL`, sehingga request dianggap same-origin dan tidak memerlukan
CORS. Bila `VITE_API_BASE_URL` diarahkan langsung ke
`http://localhost:8000/api/v1`, browser mengirim request cross-origin dari
`http://localhost:3000`; origin tersebut harus terdaftar pada `CORS_ORIGINS`
backend (nilai default `backend/.env.example` sudah mencakupnya). Panduan
lengkap ada di
[`docs/03. quality-plan/cors-development.md`](../docs/03.%20quality-plan/cors-development.md).

Mock Moodle dan mock backend dikontrol secara independen. Integrasi nyata
memerlukan server, akun, izin web service, dan CORS yang sesuai. Semua variabel
VITE_* tersedia di browser; jangan gunakan untuk secret deployment.

## Routing

| URL | Fungsi |
| --- | --- |
| /login | Login akun backend lalu Moodle |
| /forgot-password | Pemulihan kata sandi melalui Moodle |
| / | Halaman awal sesuai role: DOSEN ke /my, MAHASISWA ke /my/courses |
| /my | Dashboard dosen (khusus DOSEN; role lain melihat halaman 403) |
| /my/courses | Kursus yang diikuti/diajar; halaman awal mahasiswa |
| /user/profile | Profil pengguna Moodle; dosen juga mengatur preferensi mengajar AI |
| /course/:courseId | Isi kursus Moodle |
| /course/:courseId/participants | Peserta |
| /course/:courseId/grades | Nilai |
| /course/:courseId/mod/:cmid | Materi/aktivitas Moodle |
| /course/:courseId/ai | Tab Generator AI (dosen pengampu): mulai project atau ringkasannya |
| /course/:courseId/ai/rps, /plan, /content, /review, /publish | Tahapan workflow generator |
| /ai/* | Rute lama; diarahkan ke /my/courses |

Satu kursus Moodle memiliki satu project generator. Project dicari lewat
`GET /courses?moodle_course_id=<id>` (lihat `findCourseByMoodleId` di
courseService); hasil tetap disaring di frontend bila backend belum mendukung
filter tersebut. Status project tampil sebagai badge di kartu Kursusku.

Navigasi tersedia melalui menu akun dan tab halaman. Rute seperti /dashboard,
/course-plan, dan /student/... tidak dipasang sebagai alias.

## Autentikasi dan state

Autentikasi mengikuti kontrak backend pada
[`docs/02. design/auth-api-integration.md`](../docs/02.%20design/auth-api-integration.md)
(BE-06.1). Login mewajibkan akun backend dan akun Moodle dengan kredensial yang
sama:

1. `POST /api/v1/auth/login` dengan `{ username, password }`; `username` boleh
   berisi email. Token disimpan pada `agentic-lms.token`.
2. `GET /api/v1/auth/me` menentukan identitas dan role. Backend mengirim enum
   kanonik `INSTRUCTOR`/`STUDENT`/`ADMIN`; aplikasi memakai istilah proposal
   `ROLE.DOSEN`/`ROLE.MAHASISWA` (`src/types/auth.js`) dengan padanan satu-satu
   sesuai BE-06.4. Role `ADMIN` belum memiliki tampilan khusus.
3. Login Moodle (login/token.php) memakai `username` dari `/auth/me`, sehingga
   login dengan email tetap berhasil. Token disimpan pada
   `agentic-lms.moodle-session`; hak mengajar per kursus tetap dibaca dari Moodle.

Kegagalan langkah mana pun membatalkan login dan tidak meninggalkan token.
Error backend ditampilkan apa adanya dari `error.message` (mis. "Autentikasi
gagal."), sedangkan kegagalan Moodle diberi judul "Login Moodle gagal". Selama
request berjalan, tombol Masuk nonaktif dan input dikunci.

Saat aplikasi dimuat ulang, sesi dipulihkan melalui `GET /auth/me` dan Moodle
bila kedua token tersimpan; token yang hanya ada salah satunya dibuang. Token
yang ditolak (401) mengakhiri sesi dan menampilkan "Sesi berakhir". Server yang
tidak terjangkau (network/5xx) tidak menghapus token sehingga reload berikutnya
dapat memulihkan sesi. 401 pada request terproteksi juga mengakhiri sesi; 401
tanpa token (password salah) dan 403 tidak.

Role hanya berasal dari backend; data Moodle tidak lagi menentukan role dan hanya
dipakai untuk hak per kursus (`teacherCourseIds`, misalnya tab Generator AI dan
Mode edit). Setelah login, DOSEN dibuka di dashboard (`/my`) dan MAHASISWA di
halaman course (`/my/courses`), lihat `homePathFor()`. Menu Dasbor hanya tampil
untuk DOSEN. Halaman dosen Sprint 1 (Dashboard, Instructor Setup di Profil, serta
RPS, Course Target, dan Monitoring di tab Generator AI) dijaga `RequireAuth`
dengan `ROLE.DOSEN`; akses lewat URL langsung oleh role lain menampilkan halaman
403 "Akses ditolak". Response `403 AUTHORIZATION_DENIED` dari backend juga
menampilkan halaman 403 (`onForbidden` di apiClient, ditangani `MoodleLayout`)
sampai pengguna berpindah halaman.

Backend tidak menyediakan endpoint logout maupun refresh token: logout menghapus
kedua token dan data pengguna dari state, dan token kedaluwarsa setelah
`ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 menit). Guard generasi sesi
mengabaikan respons login atau pemulihan lama setelah sesi berganti. Halaman
login menyediakan tombol tampil/sembunyi kata sandi; tombol Google menampilkan
pemberitahuan bahwa Google OAuth belum tersedia.

Pada backend nyata, akun uji dibuat dengan
`uv run python -m scripts.seed_test_accounts` (lihat
[backend/README.md](../backend/README.md)); kata sandinya tidak disimpan di
repository. Bila `VITE_MOODLE_MOCK=false`, akun yang sama harus ada di Moodle.
Backend belum menyediakan endpoint course/plan/konten, sehingga
`VITE_USE_MOCK=false` membuat tab Generator AI gagal (404).

Halaman /forgot-password menampilkan feedback pada mode mock dan mengirim form ke
halaman pemulihan Moodle pada mode nyata; alur pemulihan nyata masih perlu diuji.

AppStateProvider mengelola preferensi UI, notifikasi, loading, dan error global.
Filter Kursus saya disimpan di localStorage per pengguna. Logout atau pergantian
pengguna menghapus state sementara dan memuat preferensi akun aktif. useAction
menerima loadingLabel untuk indikator loading global.

## Unggah RPS

Unggah RPS berada di tab **Generator AI** kursus, pada kartu "1. RPS mata kuliah"
yang tampil selama kursus belum punya project generator (`AiProjectStart`). Kartu
memuat formulir unggah, daftar RPS milik dosen, dan pilihan RPS yang sudah diproses
untuk kursus tersebut. File dipilih lewat klik atau diseret ke area unggah, lalu divalidasi
di klien sebelum dikirim: format PDF atau DOCX dan ukuran 1 byte–20 MB (mengikuti
default `RPS_MAX_UPLOAD_BYTES` backend). File yang tidak valid ditandai dengan
pesan di bawah area unggah dan tidak dikirim. DOCX ditampilkan sebagai format
didukung, tetapi backend saat ini hanya menerima PDF (`RPS_ALLOWED_EXTENSIONS`);
pemrosesan DOCX menyusul pada M03, sehingga unggahan DOCX dijawab
`400 INVALID_FILE` dan pesannya ditampilkan.

Unggahan memakai `POST /api/v1/rps` dengan indikator progres (`api.upload`
berbasis XHR; di mode mock progresnya disimulasikan), lalu langsung `POST /api/v1/rps/{rps_id}/process`. RPS baru muncul
di daftar dengan penanda "Baru" dan statusnya dipantau setiap 2 detik sampai
selesai. Status mengikuti enum backend (`UPLOADED`, `PROCESSING`, `PROCESSED`,
`FAILED`); RPS gagal menampilkan pesan dari `processing_error_message` dan tombol
Proses ulang. Unggahan isi yang sama (`deduplicated`) dan pemrosesan ulang dokumen
yang sudah diproses (`reused`) ditampilkan sebagai informasi.

Daftar memakai `GET /api/v1/rps`. Selama endpoint itu masih stub `501` di backend
(BE-08.3), kartu menampilkan RPS yang diunggah pada sesi ini dan memantau
statusnya lewat `GET /api/v1/rps/{rps_id}`. Response pemrosesan belum memuat
`workflow_id` (menyusul bersama Agent Run); nilainya disimpan bila tersedia dan
diambil dari item daftar (`workflow_id`, terisi setelah BE-11.2). Di mock, nama
file yang memuat kata `rusak` disimulasikan gagal diproses.

### Status pemrosesan RPS (FE-08.2)

Konstanta status ada di `src/utils/rpsStatus.js` (dipakai juga FE-11.1): enum
backend `UPLOADED`, `PROCESSING`, `PROCESSED`, `ANALYZING`, `ANALYZED`, `FAILED`
beserta label Bahasa Indonesia, warna, dan penanda visual (`RpsStatusBadge`:
indikator berputar saat berjalan, ✓ selesai, ✕ gagal). Urutan normal: konversi
(`PROCESSING` → `PROCESSED`) lalu analisis sebagai workflow (`ANALYZING` →
`ANALYZED`).

Daftar RPS memperbarui status tanpa memuat ulang halaman. Status dokumen dibaca
dari `GET /api/v1/rps/{rps_id}`; event workflow (`WS /api/v1/ws/workflows/{id}`,
design-api §17, `subscribeWorkflowEvents`) memicu pembaruan segera beserta tahap
dan progresnya, sedangkan polling setiap 3 detik menjadi cadangan sampai status
`ANALYZED` atau `FAILED`. `PROCESSED` dianggap masih berjalan hanya bila workflow
analisis sudah ada (`workflow_id`); karena `GET /rps/{id}` tidak memuat
`workflow_id`, nilainya diambil dari `GET /rps`.

RPS gagal menampilkan `processing_error_message`. Bila dokumen sudah terkonversi
(`has_source_document`), tombol **Analisis ulang** memanggil
`POST /api/v1/rps/{rps_id}/reanalyze`; bila konversinya yang gagal, tombol
**Proses ulang** memanggil `POST /rps/{id}/process`. RPS yang selesai dianalisis
menampilkan **Lihat hasil analisis**: ringkasan langsung di kartu selama project
belum dibuat. Tab RPS kursus (halaman hasil analisis yang sudah ada) menampilkan
status RPS dan tautan **Pantau workflow** ke tab Ringkasan (Aktivitas agent).

Status backend saat ini: enum belum memuat `ANALYZING`/`ANALYZED` (BE-08.2), dan
`/rps/{id}/reanalyze`, `/rps/{id}/analysis`, `/workflows/*`, serta WebSocket
workflow belum tersedia (stub `501`, BE-08.3/BE-11.3). Mock mengikuti kontrak;
nama file berisi `gagal-analisis` gagal saat analisis pertama untuk mencoba
Analisis ulang.

### Hasil analisis RPS (FE-08.3)

Tab **RPS** di Generator AI kursus adalah halaman Hasil Analisis RPS (Proposal
§3.7.5), dibuka setelah project dibuat dan sebelum course planning. Datanya dari
`GET /api/v1/rps/{rps_id}/analysis` (design-api §6.4) berupa RPS Structured Data
(content-schema §6.2/§7), dinormalisasi oleh `src/utils/rpsAnalysis.js` dan
ditampilkan `RpsAnalysisDetails` (`src/components/ai/course/`):

- identitas mata kuliah; CPL, CPMK, dan Sub-CPMK beserta relasinya (CPMK → CPL,
  Sub-CPMK → CPMK, dan relasi baliknya); kode yang dirujuk tetapi tidak
  tercantum diberi tanda ⚠;
- tabel rencana mingguan: minggu (dengan label UTS/UAS), Sub-CPMK, materi,
  indikator, metode, penilaian, dan bobot. Indikator diambil dari
  `assessment.description` karena RPS Week Schema tidak memiliki field indikator;
- penilaian (dengan total bobot) dan referensi;
- peringatan ekstraksi (`extraction.warnings`), keyakinan, dan halaman sumber.

Setiap bagian bertanda **Lengkap**, **Sebagian** (`partial`), atau **Tidak
ditemukan** (`not_found`). Kontrak backend belum memuat status per bagian, jadi
status diturunkan dari data: bagian kosong = tidak ditemukan; bagian yang
terisi tetapi tidak utuh (field identitas kosong, capaian tanpa relasi, minggu
tanpa materi/Sub-CPMK/metode, atau rujukan tanpa sasaran seperti
`validate_references` backend) = sebagian, beserta catatannya.

Tombol **Lanjut ke Course Planning** membuka tab Rencana (FE-05). Dengan backend
nyata tombol nonaktif bertuliskan "Course planning aktif pada M03"; di mode mock
tombol aktif. `GET /rps/{id}/analysis` masih stub `501` sampai BE-08.3; di mock,
nama file berisi `tidak-lengkap` menghasilkan analisis dengan bagian yang tidak
ditemukan.

## Edit mode kursus

Pengajar yang boleh mengubah kursus (opsi `update` pada
`core_course_get_user_administration_options`, yaitu editing teacher atau admin)
langsung berada dalam mode edit saat membuka tab Kursus; tidak ada saklar Mode
edit. Mahasiswa dan non-editing teacher melihat kursus tanpa kontrol edit.

Kontrol yang tersedia:

- ikon pensil mengganti nama section dan aktivitas (Enter atau keluar dari kolom
  menyimpan, Escape membatalkan);
- menu ⋮ aktivitas: Edit pengaturan, Pindahkan, Geser ke kanan/kiri,
  Sembunyikan/Tampilkan, Duplikat, Atur peran, dan Hapus (dengan konfirmasi);
- menu ⋮ section: Edit pengaturan dan Sembunyikan/Tampilkan section (section
  umum tidak dapat disembunyikan);
- tombol "Tambah aktivitas atau sumber" di setiap section dan "Tambah section"
  di akhir kursus. Tombol itu membuka dialog "Add an activity or resource" seperti
  di Moodle: kolom pencarian, tab Starred/All/Activities/Resources/Recommended,
  dan kartu dengan bintang (tersimpan per pengguna) serta info. Jenis yang tersedia
  baru Assignment, Quiz, dan Text and media area. Memilih jenis membuka halaman
  **New ‹aktivitas›** (lihat di bawah). Jenis baru ditambahkan di `ACTIVITY_TYPES`
  pada `AddActivityModal.jsx` dan `TYPES` pada `ModEditPage.jsx`;
- badge "Disembunyikan dari mahasiswa" pada item tersembunyi.

Pindahkan memakai dialog pilihan section dan posisi sehingga dapat dipakai dengan
keyboard; drag-and-drop dan blok (Add a block) belum tersedia. Edit pengaturan
dan Atur peran dibuka di Moodle pada tab baru.

Moodle core belum menyediakan Web Service untuk membuat Tugas atau Teks dan media
beserta isinya (`core_courseformat_create_module` hanya untuk modul dengan
`FEATURE_QUICKCREATE`, yaitu `mod_subsection`). Karena itu pembuatan aktivitas
dari formulir aplikasi baru berjalan di mock Moodle (`mock_course_create_activity`).
Dengan `VITE_MOODLE_MOCK=false`, tombol simpan di halaman New ‹aktivitas› diganti
"Lanjutkan di Moodle" yang membuka formulir `modedit.php`, sampai tim memutuskan jalurnya (plugin Moodle atau
endpoint backend). Setiap
aksi memuat ulang isi kursus agar tampilan mengikuti Moodle, termasuk saat aksi
gagal.

Aksi memakai `core_courseformat_update_course` dan `core_update_inplace_editable`
(editor kursus Moodle 4.x/5.x). Keduanya tidak termasuk layanan
`moodle_mobile_app`, sehingga pada Moodle nyata harus ditambahkan ke external
service yang dipakai frontend. Mock Moodle mendukung aksi yang sama; isi kursus
kembali ke fixture awal saat reload.

Rujukan dokumentasi Moodle (moodledev.io) dan pengecekannya pada source Moodle 5.3:

| Hal | Dokumentasi | Hasil cek source |
| --- | --- | --- |
| `core_courseformat_update_course` menggantikan `core_course_edit_section`/`edit_module` sejak 4.0 | [Migrating 3.11 formats](https://moodledev.io/docs/4.4/apis/plugintypes/format/migration) | Ada di `lib/db/services.php`: `'ajax' => true`, tanpa `'services'` |
| Fungsi baru tersedia di aplikasi mobile bila memuat `MOODLE_OFFICIAL_MOBILE_SERVICE` pada `'services'` | [Function Declarations](https://moodledev.io/docs/5.1/apis/subsystems/external/description) | Hanya fungsi baca seperti `core_course_get_contents` yang memuatnya; fungsi editor tidak |
| Fungsi di luar layanan bawaan dibuka lewat service kustom | [Service creation](https://moodledev.io/docs/5.0/apis/subsystems/external/advanced/custom-services) | Dipakai bila fungsi editor ditambahkan ke service frontend |
| Tidak ada external function pembuat Tugas; yang ada hanya fungsi PHP `assign_add_instance()` | [mod_assign](https://phpdoc.moodledev.io/4.4/d3/d4f/group__mod__assign.html) | `mod/assign/db/services.php` tidak memuat fungsi create |
| Menulis external function sendiri | [Writing a new service](https://moodledev.io/docs/5.0/apis/subsystems/external/writing-a-service) | Jalur yang perlu dipilih tim untuk pembuatan aktivitas |

## Pengumpulan tugas

### Halaman New ‹aktivitas›

Halaman `/course/:id/modedit?add=<modname>&section=<n>` setara `course/modedit.php`
Moodle: breadcrumb `section / New Assignment`, judul **New Assignment** dengan ikon,
tautan **Expand all/Collapse all**, bagian yang dapat dilipat, label di kiri dan isian
di kanan, ikon wajib, serta tombol **Save and return to course**, **Save and display**
(tidak ada untuk Text and media area), dan **Cancel**. Field, bawaan, dan pesan
validasi diambil dari `mod_form.php` dan `lang/en` Moodle 5.3; hanya setelan yang
benar-benar disimpan yang ditampilkan (`src/components/moodle/modedit/`):

- **Assignment**: General (Assignment name, Description dengan editor),
  Availability (Allow submissions from, Due date, Cut-off date sebagai
  date_time_selector dengan Enable), Submission types (Online text, File
  submissions, Word limit dengan Enable, Maximum number of uploaded files,
  Maximum submission size), dan Grade (Type Point, Maximum grade 1–100).
  General, Availability, dan Submission types terbuka seperti `setExpanded` Moodle.
- **Quiz**: General (Name, Description) dan Timing (Open the quiz, Close the quiz).
- **Text and media area**: General (Title in course index, Text dengan editor).

Pesan validasi Moodle: "You must supply a value here.", "Due date cannot be earlier
than the allow submissions from date.", "Cut-off date cannot be earlier than the due
date.", "The close date must be after the open date.", dan "Invalid grade value. This
must be an integer between 1 and 100". Saat validasi gagal, bagian yang berisi error
dibuka dan field pertama difokuskan. Setelan jenis pengumpulan disimpan dengan nama
plugin Moodle dan dibaca kembali dari `configs` pada `mod_assign_get_assignments`
(`src/utils/assignSubmission.js`).

Tampilan mahasiswa mengikuti
[Using Assignment › Student view](https://docs.moodle.org/503/en/Using_Assignment#What_are_the_options_for_submitting_work_in_Moodle?)
dan memakai string bahasa Inggris Moodle (`mod_assign`, `repository`):

- Halaman tugas (`/course/:id/mod/:cmid`): kotak **Opened/Due** dan deskripsi,
  tombol **Add submission** (atau **Edit submission** bila sudah ada isi) selama
  tugas sudah dibuka dan `canedit`, lalu tabel **Submission status** (status,
  grading status, time remaining, last modified, online text, file submissions).
- Halaman **Edit submission** (`/course/:id/mod/:cmid/editsubmission`, setara
  `view.php?action=editsubmission`): breadcrumb `… / Edit submission`, judul
  dengan ikon tugas, kotak Opened/Due, lalu bagian lipat **Add submission** dengan
  label di kiri:
  - **Online text**: editor bergaya TinyMCE (`MoodleEditor`) dengan menu bar
    Edit/View/Insert/Format/Tools/Table/Help, toolbar Undo, Redo, Bold, Italic,
    Image, Multimedia, Link, Unlink, Full screen, dan tombol "more" (Underline,
    Strikethrough, daftar, Clear formatting), serta status bar berisi jalur elemen
    (`p`) dan jumlah kata. Melebihi batas kata menampilkan pesan
    `wordlimitexceeded` Moodle saat menyimpan.
  - **File submissions**: "Maximum file size: 1 MB, maximum number of files: 20"
    dan file manager seperti Moodle (`FileManager`): Add..., Create folder,
    tampilan ikon/detail/pohon, jalur folder **Files**, area "You can drag and
    drop files here to add them.", dialog file untuk ganti nama, hapus, dan unduh.
    Nama ganda diberi akhiran "(1)" seperti Moodle.
  - **Save changes** / **Cancel** kembali ke halaman tugas.

Editor memakai `contentEditable` + `document.execCommand`, bukan paket TinyMCE.
Gambar dan media disisipkan lewat URL; perekaman audio/video dan unggah gambar ke
editor belum tersedia. HTML dari editor disanitasi DOMPurify saat ditampilkan.

Penyimpanan memakai `mod_assign_save_submission` (`plugindata`
`onlinetext_editor` dan `files_filemanager`), keduanya termasuk
`moodle_mobile_app`:

- File tidak diubah: `files_filemanager` tidak dikirim sehingga file di Moodle
  tetap (`file_postupdate_standard_filemanager` tidak menyentuh area tanpa draft).
- File diubah: seluruh isi file manager diunggah ke satu draft lewat
  `webservice/upload.php` (per folder dengan `filepath`, `itemid` yang sama). File
  lama diunduh lalu diunggah ulang seperti aplikasi Moodle. Bila semua file
  dihapus, draft kosong dari `core_files_get_unused_draft_itemid` dikirim. Folder
  kosong tidak ikut tersimpan karena upload.php tidak membuat folder.

Alur ini baru diuji di mock Moodle. Tugas dibuat tanpa opsi "Require students to
click the submit button", sehingga pengumpulan langsung berstatus Submitted for
grading; isi pengumpulan dibaca dari `lastattempt.submission.plugins` pada
`mod_assign_get_submission_status`.

## Rencana kuliah

Tab Rencana menampilkan informasi course, CPMK, tujuan, topik, metode mengajar,
aktivitas, dan status per minggu. Desktop mulai 1024 px memakai tabel; layar
lebih kecil memakai kartu mingguan. CoursePlanDetails mengatur presentasi,
sedangkan aksi generate/revisi/approve berada pada CoursePlanPage.

getPlan menormalisasi Course Plan Schema dan mempertahankan alias week/topic
untuk pemilihan minggu pada halaman Konten. Data capaian/metode yang belum
tersedia ditandai “Belum tersedia.”. Read error menyediakan tombol Coba lagi.
Mock mengambil CPMK/metode dari RPS.

## Struktur

- src/main.jsx dan App.jsx: provider aplikasi dan routing.
- src/pages/: satu folder per area — auth/ (login, lupa password), moodle/
  (tampilan Moodle, course/ untuk halaman di dalam kursus), ai/course/ (tab
  Generator AI di dalam kursus). StatusPage berisi halaman 403/404.
- src/components/: dikelompokkan mengikuti pemakainya —
  - ui/: komponen dasar lintas halaman (Card, Badge, Alert, Modal, Toast, ...),
    satu file per komponen; import lewat `components/ui`.
  - layout/: kerangka aplikasi (MoodleLayout, ApplicationHeader, UserMenu,
    RequireAuth, AppStatus).
  - auth/: potongan halaman pages/auth (AuthLayout, AuthField, PasswordField,
    AuthSubmitButton, GoogleLoginButton); import lewat `components/auth`.
  - moodle/: komponen tampilan Moodle (CourseCard, ActivityIcon, MoodleHtml,
    AssignSubmission); submission/ berisi MoodleEditor dan FileManager untuk
    halaman Edit submission;
    course/ berisi potongan halaman kursus (CourseSection, ActivityRow) dan
    editing/ berisi komponen mode edit (ActionMenu,
    InlineNameEditor, ActivityEditMenu, SectionEditMenu, dialog Pindahkan/Hapus/
    Tambah aktivitas); import lewat `components/moodle/editing`.
  - ai/: komponen generator AI (WorkflowStepper, EventLog, InstructionModal,
    ActivityConfigFields, RpsUploadForm, InstructorSetupForm, TeachingProfileForm,
    TeachingPreferencesCard); ai/course/ berisi potongan halaman
    pages/ai/course (AiProjectStart, CoursePlanDetails, ActivityConfigForm,
    ContentGeneratePanel, WeekContentDetail, MoodleExecutionCard,
    MoodleVerificationCard).
  Halaman di pages/ hanya merangkai komponen; form/panel/card dibuat di
  components/.
- Styling: Tailwind langsung di className, memakai token warna di
  src/styles/global.css (`primary`, `ink`, `muted`, `line`, `surface`, ...).
  Tidak ada CSS per komponen. Breakpoint desain tersedia sebagai varian
  `max-laptop:` (≤1024px), `max-tablet:` (≤768px), dan `max-phone:` (≤480px).
  Pola yang dipakai berulang (tombol .btn, .table, .tabs, dsb.) ada di
  global.css bagian `@layer components`.
- src/context/, hooks/, state/, types/, utils/: sesi, state bersama, dan helper.
- src/services/: transport Moodle/backend, adapter course plan, monitoring,
  serta mock. Lihat [panduan service](src/services/README.md).
- src/styles/: Tailwind, token/reset dasar, dan filter ikon aktivitas.
- public/moodle/mod/: ikon aktivitas yang dimuat melalui URL dinamis.

## Verifikasi

```powershell
npm run lint
npm run build
npm test
npm run test:e2e
npm run test:design
npm run verify:foundation
```

Unit test mencakup API, Moodle, workflow, halaman, sesi, shared state, dan detail
rencana. Suite browser runtime.spec.js menguji routing/login/workflow;
auth-06-2.spec.js menguji login akun uji, error kredensial, pemulihan sesi saat
reload, dan logout; role-guard-06-3.spec.js menguji halaman awal per role, menu,
dan halaman 403; course-edit-mode.spec.js menguji mode edit dan pengumpulan tugas mahasiswa pada 375/1440 px; rps-upload-08-1.spec.js
menguji validasi, unggah, dan pemrosesan RPS di Generator AI pada 375/1440 px;
rps-analysis.spec.js menguji halaman hasil analisis RPS pada 375/1440 px;
foundation-71.spec.js menguji sesi, state, keyboard, empty/error, serta responsive;
course-plan-74.spec.js menguji rencana pada 375/768/1024/1440 px dan pemilihan minggu.
presentation.spec.js berjalan melalui test:design untuk style dan batas konten
pada 375/768/1440 px. Screenshot presentasi adalah bahan review; suite ini tidak
membandingkan pixel terhadap baseline mockup historis.

verify:foundation menjalankan lint/build/unit/browser dan readiness gate yang
menolak hasil skipped, expected failure, flaky, atau incomplete. Di Windows,
tes browser memakai Chrome terisolasi. PLAYWRIGHT_CHANNEL dapat memilih channel
lain; di sistem lain pasang Chromium melalui `npx playwright install chromium`.
Server pengujian memakai port 4173. Report berada di .cache/playwright/ dan
.cache/design-conformance/. Jika cache npm di drive C penuh, gunakan
`npm ci --cache .cache/npm`.

Pengujian mock tidak membuktikan persistensi, generation AI, atau publikasi Moodle
nyata. Pembacaan Moodle melalui browser berbeda dari boundary backend pada
dokumen arsitektur; perbedaan tersebut tercatat dalam laporan penyelarasan.

Riwayat teknis: [penyelarasan runtime](../docs/03.%20quality-plan/frontend-runtime-alignment.md),
[verifikasi foundation #71](../docs/03.%20quality-plan/frontend-foundation-verification.md),
[Course Plan #74](../docs/03.%20quality-plan/frontend-course-plan-screen.md), dan
[desain historis #72](../docs/03.%20quality-plan/frontend-design-conformance.md).
Hasil pada laporan historis berlaku untuk revisi/tanggal yang dicatat di sana.
Alur review dan integrasi mengikuti [aturan kerja](../aturan.md).
