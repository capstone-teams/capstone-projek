> Catatan riwayat: laporan ini merekam revisi sebelum runtime Rakha dipulihkan. Hasil dan metode pengujian terbaru ada di [laporan penyelarasan](frontend-rakha-alignment.md).

# FE-04.1 — Frontend Foundation Verification

> Laporan historis untuk branch verifikasi TS/TSX. Untuk hasil setelah integrasi
> fondasi Rakha dan migrasi JS/JSX, lihat [laporan penyelarasan](frontend-rakha-alignment.md).

Issue: [#71 — Verify Frontend Foundation](https://github.com/capstone-teams/capstone-projek/issues/71)

Tanggal: 3 Oktober 2026

Branch: `codex/fe-04-1-foundation-verification`

Baseline: `a55d35d` dari FE-03.2, ditambah perbaikan dan tes pada branch verifikasi ini.

## Status

**Verifikasi UI/service selesai untuk source yang tersedia; foundation belum siap dinyatakan selesai.**
Masih ada lima perilaku authentication/role/routing yang gagal karena implementasinya
belum terintegrasi pada source yang diuji. Gate readiness mengembalikan exit code 1.

Issue #65, #66, dan #77 milik Rakha sudah berstatus closed di GitHub pada waktu
pemeriksaan. Status tersebut belum tercermin pada branch ini atau `develop`.
[PR #83](https://github.com/capstone-teams/capstone-projek/pull/83) ditutup tanpa merge,
dan branch `feature-navigation-auth-role` tidak ada pada remote. Commit implementasi
Rakha `8c28119e3925b9ff11ea1dd2069a8775f5824e38` masih dapat dibaca lewat PR tersebut.
Versi final dan jalur integrasinya perlu dicocokkan sebelum verifikasi gabungan.

## Hasil pemeriksaan

Lingkungan: Node.js 22.16.0, npm 10.9.2, Playwright Test 1.63.0, Microsoft Edge headless
di Windows. Vite berjalan pada `127.0.0.1:4173` dengan context browser terisolasi.
Backend, credential, dan layanan eksternal tidak diperlukan.

| Pemeriksaan | Hasil |
| --- | --- |
| `npm run lint` | Lulus |
| TypeScript aplikasi, konfigurasi Vite, konfigurasi Playwright, dan browser tests | Lulus melalui `npm run build` |
| Vite production build | Lulus; 62 modules transformed |
| `npm test` | 59 tes lulus |
| Browser checks UI/service | 24 lulus |
| Browser checks authentication/role/routing yang belum terintegrasi | 5 expected failures; tetap merupakan blocker |
| Unexpected browser failures / skipped / flaky | 0 / 0 / 0 |
| `npm run verify:foundation` | Exit code 1 karena lima known blockers |

Playwright melaporkan total `29 passed` karena expected failures dianggap sesuai
ekspektasi test runner. Itu **bukan** berarti 29 perilaku aplikasi berhasil.
`scripts/check-foundation-readiness.mjs` memisahkannya menjadi 24 checks yang berhasil
dan 5 blockers, lalu menolak kesiapan FE-04.1.

## Cakupan requirement

| Requirement #71 | Bukti dan hasil | Status |
| --- | --- | --- |
| Layout | Kesembilan development routes render, heading terlihat, dan tidak ada exception browser pada smoke tests | Lulus untuk baseline demo |
| Routing | Navigasi course melalui keyboard serta browser Back/Forward memperbarui halaman, URL, dan title | Sebagian; protected/not-found behavior belum lulus |
| Authentication | Demo username dosen/mahasiswa dan feedback username tidak dikenal berjalan | Sebagian; auth service/session belum terintegrasi |
| Role | Demo landing page sesuai username; helper role juga diuji oleh unit tests | Sebagian; role guard aplikasi belum lulus |
| Shared component | Modal focus trap/Escape/scroll lock/focus return, input login berlabel, Card untuk empty state, feedback yang dapat ditutup | Lulus untuk skenario yang diuji |
| State | Perubahan profil memperbarui header; state modal dan request berubah melalui interaksi; completion request setelah pindah halaman tidak menimpa halaman baru | Sebagian; current-user/session dan shared application state FE-03.1 perlu verifikasi gabungan |
| Service abstraction | Service binding diubah hanya di context pengujian; halaman dan hook production tetap dipakai untuk loading/error/retry/success/empty | Lulus untuk read service yang diuji |
| Mock data | Halaman dapat berjalan tanpa Backend/API request pada smoke tests; integrity dan clone isolation diuji unit tests | Lulus untuk mock domain yang tersedia; mock auth/state FE-03.3 perlu integrasi |
| Responsive behavior | Sembilan routes dan dialog upload diuji pada 375×812, 768×1024, dan 1440×900; document/heading/dialog berada dalam batas viewport | Lulus pada tiga ukuran yang diuji |

Source pengujian browser: [foundation.spec.ts](../../frontend/tests/e2e/foundation.spec.ts).
Unit tests yang sebelumnya memeriksa metadata dan isi source tidak dianggap sebagai
bukti bahwa protected route/session authentication benar-benar bekerja di browser.

## Perbaikan dari temuan browser

Empat kasus berikut gagal sebelum perbaikan dan lulus setelah perbaikan:

1. **Label input login:** label Username dan Kata sandi belum terhubung ke input.
   Ditambahkan pasangan `htmlFor`/`id` sehingga browser dan pembaca layar mengenali
   nama input; tampilan form tetap menggunakan style yang sama.
2. **Focus return modal:** setelah Escape menutup dialog Upload RPS, fokus hilang ke body.
   Modal menyimpan elemen yang sebelumnya aktif dan mengembalikan fokus ketika dialog
   ditutup, selama elemen itu masih ada.
3. **Daftar mahasiswa kosong:** response service `[]` menampilkan grid kosong.
   Halaman kini menampilkan Card “Belum ada mata kuliah” dengan penjelasan.
4. **Daftar dosen kosong:** ketika `hasCourses=true` tetapi service menghasilkan `[]`,
   grid juga kosong. Halaman kini menggunakan empty state yang sudah ada pada baseline.

Server data, API endpoint, authentication implementation, dan workflow domain baru
tidak ditambahkan pada perbaikan tersebut.

## Blockers yang direproduksi

Masing-masing kasus memiliki browser test dengan marker expected failure dan alasan
dependensi. Kegagalan tersebut tetap memblokir readiness.

| Kasus | Langkah reproduksi | Hasil pada source yang diuji | Perilaku yang dibutuhkan | Dependensi |
| --- | --- | --- | --- | --- |
| Anonymous access | Context baru → buka `/dashboard` | Halaman dosen terbuka langsung | Login/protected-route handling | FE-02.1 #65, FE-02.2 #66 |
| Invalid password | Login `dosen` dengan `wrong-password` | Masuk ke dashboard karena form demo mengabaikan password | Mock auth service memproses credential dan error state | FE-02.2 #66 |
| Student role bypass | Login `mahasiswa` → buka `/dashboard` langsung | Aplikasi berubah ke role dosen berdasarkan URL | Role dibaca dari current user; akses instructor ditolak | FE-02.3 #77, FE-03.1 #68 |
| Logout + Back | Login dosen → Logout → browser Back | Halaman dosen terbuka lagi | Protected route merespons unauthenticated state | FE-02.1 #65, FE-02.2 #66 |
| Unknown route | Buka `/route-that-does-not-exist` | Redirect ke dashboard dosen | Not-found handling tanpa memberi akses instructor | FE-02.1 #65 |

Ini merupakan gap integrasi foundation pada baseline demo. Backend authentication
nyata tidak menjadi prasyarat: mock auth/role foundation pun harus dapat menegakkan
perilaku tersebut.

## Menjalankan ulang

Dari directory `frontend`:

```bash
npm ci
npm run verify:foundation
```

Pada Windows, suite memakai Microsoft Edge yang sudah terpasang. Untuk Chromium
bundled di sistem lain:

```bash
npx playwright install chromium
npm run verify:foundation
```

`npm run test:e2e` dapat dipakai saat memperbaiki browser test, tetapi kesiapan issue
ditentukan dari full pipeline `npm run verify:foundation`. Port 4173 harus kosong;
port development 3000 dapat tetap berjalan. Artefak di `.cache/playwright/` diabaikan Git:

- `report/index.html`: laporan HTML.
- `results.json`: hasil yang dibaca readiness gate.
- `results/`: screenshot/trace dan attachment responsive dari pengujian.

Service overrides dilakukan lewat interception modul binding service hanya di browser
context test. Loading ditahan sampai event pengujian dilepas; error tetap gagal sampai
event recovery dan pengguna menekan “Coba lagi”. Fixture tidak mengandalkan jumlah
pemanggilan loader, sehingga tetap deterministik saat React StrictMode menjalankan
effect lebih dari sekali.

Konfigurasi mengikuti [Playwright test configuration](https://playwright.dev/docs/test-configuration),
[web server](https://playwright.dev/docs/test-webserver), dan
[dukungan Chrome/Edge](https://playwright.dev/docs/browsers#google-chrome--microsoft-edge).

## Batas verifikasi dan tindak lanjut

- Browser engine yang diuji adalah Chromium melalui Edge. Firefox/Safari belum diuji.
- Pemeriksaan responsive mengukur bounds dan memakai screenshot; pixel comparison
  terhadap approved design berada pada FE-04.2.
- Backend/API feature nyata dan eksekusi Agent/Moodle masih berada di milestone terkait.
- Versi final authentication/role Rakha perlu dicocokkan dan diintegrasikan bersama
  state/mock foundation FE-03.1 (#68) dan FE-03.3 (#78).
- Setelah authentication terintegrasi, smoke/request-state tests perlu memakai session
  mock dengan role yang sesuai. Jalankan kelima kasus yang gagal tanpa expected-failure
  marker setelah perilakunya terverifikasi.
- Source FE-03.2 masih berada pada [PR #85](https://github.com/capstone-teams/capstone-projek/pull/85).
  Review, merge, dan verifikasi gabungan masih menjadi langkah berikutnya.

Acceptance criterion “seluruh foundation tanpa blocking issue” dan “semua major state”
belum terpenuhi. Issue #71 belum layak ditutup berdasarkan hasil ini.
