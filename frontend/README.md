# Frontend — Agentic LMS

Runtime React + JavaScript/JSX mengikuti Rakha di `origin/feature/frontend-setup`,
commit `accbc21035d378c5d3d9775728354ce2093bf244`. Routing, AuthProvider, hooks,
service, data mock, dan aksi fitur menggunakan implementasi tersebut, dengan
perbaikan penanganan respons sesi yang terlambat dan JSON invalid pada issue #71.
Penyesuaian kita ada pada presentasi: warna/typography, header akun, form login,
kartu kursus dan tata letak tanpa navbar utama/sidebar.

## Menjalankan

```powershell
cd frontend
npm ci
npm run dev
```

Buka http://localhost:3000. Jika sebelumnya ada Vite yang berjalan, restart setelah
perubahan dependency atau `.env.local`. Port 3000 tidak berganti otomatis.

Mode default tidak membutuhkan backend atau Moodle Docker:

| Akun Moodle mock | Kata sandi | Nama |
| --- | --- | --- |
| dosen | dosen123 | Rina Kartika |
| mahasiswa | mahasiswa123 | Andi Saputra |

Mata kuliah Pemrograman Web/Basis Data berasal dari fixture Rakha. Nama dan isi
halaman dapat berbeda dari mockup lama, karena sekarang halaman memakai sumber
data Rakha, bukan fixture Aljabar di UI lama.

## Routing Rakha

| URL | Fungsi |
| --- | --- |
| `/login` | Login Moodle |
| `/` | Mengarah ke `/my` setelah login |
| `/my` | Dasbor Moodle |
| `/my/courses` | Kursus yang diikuti/diajar |
| `/user/profile` | Profil pengguna Moodle |
| `/course/:courseId` | Isi kursus Moodle |
| `/course/:courseId/participants` | Peserta |
| `/course/:courseId/grades` | Nilai |
| `/course/:courseId/mod/:cmid` | Materi/aktivitas Moodle |
| `/ai` | Project Generator AI, khusus dosen |
| `/ai/rps` dan `/ai/rps/:rpsId` | RPS dan analisis |
| `/ai/profile` | Preferensi mengajar |
| `/ai/courses/new` | Membuat project |
| `/ai/courses/:courseId` | Ringkasan project |
| `/ai/courses/:courseId/plan`, `/content`, `/review`, `/moodle` | Tahapan workflow di bawah project yang sama |

URL lama seperti `/dashboard`, `/course-plan`, dan `/student/...` tidak dipasang
sebagai alias. Navigasi antarfungsi tersedia melalui menu akun dan tab halaman.
Tidak ada navbar utama atau sidebar baru.

## Login, Moodle, dan backend

1. AuthProvider meminta token Moodle lewat `login/token.php`, kemudian mengambil
   user dan peran dari hak akses kursus Moodle. Token sesi disimpan di
   `agentic-lms.moodle-session` seperti implementasi Rakha.
2. Untuk dosen, provider juga mencoba login ke backend capstone dan menyimpan
   token backend terpisah pada `agentic-lms.token`. Kegagalan login backend tidak
   menggagalkan login Moodle. Login Moodle berhasil belum menjamin fitur AI pada
   backend nyata bisa dipakai.
3. Kursus, peserta, nilai, timeline, profil dan aktivitas menggunakan
   `services/moodle/`. Fitur RPS, project, rencana, konten, review, eksekusi dan
   verifikasi menggunakan service backend Rakha. Aksi UI memanggil service itu.
4. Logout menghapus kedua sesi. Guard sesi pada #71 mencegah respons login/pemulihan
   lama memulihkan sesi atau menghapus sesi yang lebih baru. Alur mengikuti Rakha; perubahan auth
   backend-only pada commit `713f886` sudah digantikan.

Salin `.env.example` ke `.env.local` untuk memilih koneksi:

| Variabel | Default | Fungsi |
| --- | --- | --- |
| `VITE_MOODLE_MOCK` | true | false memakai Web Service Moodle nyata |
| `VITE_MOODLE_URL` | http://localhost:8080 | Alamat Moodle dan tautan Buka Moodle |
| `VITE_MOODLE_SERVICE` | moodle_mobile_app | Service login/token.php |
| `VITE_USE_MOCK` | true | false memakai backend capstone nyata |
| `VITE_API_BASE_URL` | /api/v1 | Prefix API backend |
| `VITE_BACKEND_URL` | http://localhost:8000 | Tujuan proxy Vite untuk /api |

Untuk integrasi nyata, server, akun, izin web service dan CORS perlu disiapkan.
Tidak cukup hanya mengubah satu flag: mock Moodle dan mock backend dikontrol
secara terpisah. Jangan memasukkan secret deployment ke variabel VITE_*.
Dokumen arsitektur sebelumnya mendeskripsikan akses Moodle melalui backend;
perbedaan dengan runtime Rakha ini dicatat di laporan penyelarasan untuk review tim.

Mock backend berjalan di memori dan workflow kembali ke fixture awal saat reload.
Persistensi dan eksekusi Moodle nyata belum diverifikasi.

## Rencana kuliah (#74)

Tab Rencana pada project AI menampilkan informasi course, CPMK, tujuan, topik,
metode mengajar, aktivitas dan status per minggu. Desktop mulai 1024 px memakai
tabel; layar lebih kecil memakai kartu mingguan. CoursePlanDetails hanya mengatur
presentasi; approve/regenerasi memakai handler Rakha pada CoursePlanPage.

`getPlan` memetakan Course Plan Schema ke data halaman dan mempertahankan alias
format Rakha untuk pemilihan minggu pada halaman Konten. Data yang belum mempunyai
capaian/metode ditandai “Belum tersedia.”. Read error memiliki tombol Coba lagi.
Mock memakai CPMK/metode dari RPS dan tetap kembali ke fixture awal saat reload.

## Struktur aktif

- `src/App.jsx`: route tree Rakha.
- `src/pages/`: seluruh halaman aktif, termasuk login.
- `src/context/`, `src/hooks/`, `src/services/`: runtime Rakha.
- `src/components/MoodleLayout.jsx`: header desain lama dengan session Rakha.
- `src/styles/`: Tailwind untuk komponen Rakha serta token desain yang disetujui.
- CSS Modules login/header/kartu kursus lama digunakan kembali.

Controller JS/JSX lama di `src/features/`, `src/components/layout/` dan facade
`services/index.js`/`mockCourseService.js` tidak dipakai oleh aplikasi aktif.
File tersebut tetap tersimpan sebagai referensi; entry point hanya memakai pages
Rakha. Jangan menyambungkan fitur baru ke controller/facade lama tersebut.

## Verifikasi

```powershell
npm run lint
npm run build
npm test
npm run test:e2e
npm run test:design
```

Unit test menjalankan suite API/Moodle/workflow/pages Rakha, ditambah lifecycle sesi,
request state dan recovery halaman untuk #71. Browser test aktif:
`rakha-runtime.spec.js` untuk route/login/workflow dan `foundation-71.spec.js`
untuk pemulihan sesi, shared state, keyboard, empty/error serta responsive.
`course-plan-74.spec.js` memeriksa detail rencana pada empat ukuran layar,
generate/revisi/approve dan kompatibilitas pemilihan minggu pada halaman Konten.
`rakha-presentation.spec.js` dijalankan terpisah melalui `test:design`
untuk style dan batas konten pada 375/768/1440 px, dengan screenshot review.
`verify:foundation` memeriksa lint/build/unit/browser dan hasil readiness.

Ini bukan perbandingan pixel penuh dengan mockup lama: data, route dan isi fitur
sekarang mengikuti Rakha. Suite lama foundation/design-conformance tetap tersimpan
sebagai referensi historis dan tidak dijalankan oleh konfigurasi saat ini.
Laporan sebelumnya (86/32/55 tes) tidak berlaku untuk revisi ini.

Di Windows browser test memakai Chrome terisolasi. `PLAYWRIGHT_CHANNEL` bisa
mengubah channel; pada sistem lain pasang Chromium menggunakan
`npx playwright install chromium`. Server pengujian memakai port 4173, bukan 3000.
Laporan ada di `.cache/playwright/` dan `.cache/design-conformance/`.

Jika cache npm di drive C penuh, gunakan `npm ci --cache .cache/npm`.

Lihat [laporan Course Plan #74](../docs/03.%20quality-plan/frontend-course-plan-screen.md),
[laporan verifikasi #71](../docs/03.%20quality-plan/frontend-foundation-verification.md),
[laporan penyelarasan](../docs/03.%20quality-plan/frontend-rakha-alignment.md)
dan [aturan kerja](../aturan.md). Pekerjaan #74 di branch
`feature/fe-05-1-course-plan-screen` bergantung pada
`refactor/frontend-foundation-alignment`; tidak push langsung ke develop.
