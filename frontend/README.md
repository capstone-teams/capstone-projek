# Frontend — Agentic LMS

Aplikasi React dengan JavaScript/JSX untuk akses kursus Moodle dan workflow
penyusunan konten pembelajaran berbasis RPS. Peran dosen dapat menggunakan
Generator AI; mahasiswa mengakses kursus Moodle.

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

| Akun mock | Kata sandi | Nama |
| --- | --- | --- |
| dosen | dosen123 | Rina Kartika |
| mahasiswa | mahasiswa123 | Andi Saputra |

Fixture kursus mencakup Pemrograman Web dan Basis Data. Workflow backend mock
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
| VITE_API_BASE_URL | /api/v1 | Prefix API backend |
| VITE_BACKEND_URL | http://localhost:8000 | Tujuan proxy Vite untuk /api |

Mock Moodle dan mock backend dikontrol secara independen. Integrasi nyata
memerlukan server, akun, izin web service, dan CORS yang sesuai. Semua variabel
VITE_* tersedia di browser; jangan gunakan untuk secret deployment.

## Routing

| URL | Fungsi |
| --- | --- |
| /login | Login Moodle |
| /forgot-password | Pemulihan kata sandi melalui Moodle |
| / | Mengarah ke /my setelah login |
| /my | Dasbor Moodle |
| /my/courses | Kursus yang diikuti/diajar |
| /user/profile | Profil pengguna Moodle |
| /course/:courseId | Isi kursus Moodle |
| /course/:courseId/participants | Peserta |
| /course/:courseId/grades | Nilai |
| /course/:courseId/mod/:cmid | Materi/aktivitas Moodle |
| /ai | Project Generator AI, khusus dosen |
| /ai/rps dan /ai/rps/:rpsId | RPS dan analisis |
| /ai/profile | Preferensi mengajar |
| /ai/courses/new | Membuat project |
| /ai/courses/:courseId | Ringkasan project |
| /ai/courses/:courseId/plan, /content, /review, /moodle | Tahapan workflow project |

Navigasi tersedia melalui menu akun dan tab halaman. Rute seperti /dashboard,
/course-plan, dan /student/... tidak dipasang sebagai alias.

## Autentikasi dan state

AuthProvider meminta token Moodle melalui login/token.php dan menentukan peran
dari hak akses kursus. Sesi disimpan pada `agentic-lms.moodle-session`. Untuk dosen,
provider juga mencoba login backend dan menyimpan token pada `agentic-lms.token`.
Kegagalan login backend AI ditampilkan sebagai error global; sesi Moodle tetap
dapat digunakan. Keberhasilan login Moodle belum menjamin akses backend AI nyata.

Logout menghapus kedua sesi. Guard generasi sesi mengabaikan respons login atau
pemulihan lama setelah sesi berganti. Halaman login menyediakan tombol
tampil/sembunyi kata sandi dan pemberitahuan sesi berakhir. Tombol Google
menampilkan pemberitahuan bahwa Google OAuth belum tersedia.

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
- src/pages/: halaman Moodle, autentikasi, dan workflow AI; AuthPages.module.css
  dipakai login serta pemulihan password.
- src/components/: header MoodleLayout, komponen UI, kartu Moodle, dan detail
  rencana; CSS Modules berada di dekat konsumennya.
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
