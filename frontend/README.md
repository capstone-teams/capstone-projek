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
| / | Mengarah ke /my setelah login |
| /my | Dasbor Moodle |
| /my/courses | Kursus yang diikuti/diajar |
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
2. `GET /api/v1/auth/me` menentukan identitas dan peran: `INSTRUCTOR` menjadi
   dosen dan `STUDENT` menjadi mahasiswa. Role `ADMIN` belum memiliki tampilan.
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
  - moodle/: komponen tampilan Moodle (CourseCard, ActivityIcon, MoodleHtml).
  - ai/: komponen generator AI (WorkflowStepper, EventLog, InstructionModal,
    ActivityConfigFields, RpsUploadForm, TeachingProfileForm,
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
reload, dan logout;
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
