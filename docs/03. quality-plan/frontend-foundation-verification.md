# FE-04.1 — Verify Frontend Foundation (#71)

Issue: [#71](https://github.com/capstone-teams/capstone-projek/issues/71).
Tanggal: 3 Oktober 2026. Branch: `refactor/frontend-foundation-alignment`.

Baseline runtime Rakha: `accbc21035d378c5d3d9775728354ce2093bf244`.
Baseline lokal sebelum verifikasi: `f3b0a38` (runtime/presentasi), `5fab886` (keputusan desain).
Pengguna memilih mempertahankan tampilan sekarang dan melanjutkan #71 pada branch ini.

Laporan ini menggantikan hasil verifikasi TS/TSX lama. Lima blocker pada laporan
lama tidak berlaku pada runtime Rakha yang sekarang: akses anonymous, password
salah, role mahasiswa, logout/Back, dan unknown route sudah diuji sebagai kasus
normal, tanpa expected failure. Riwayat laporan lama tetap tersedia di Git.

## Status

**Verifikasi teknis foundation mode mock lulus dan siap direview.**
Issue tetap memerlukan PR, review, dan merge sesuai `aturan.md` sebelum disebut DONE.
Tidak ada push ke `develop`, merge, atau penutupan issue dalam pekerjaan ini.

| Acceptance criterion #71 | Hasil |
| --- | --- |
| Seluruh foundation dapat digunakan tanpa blocking issue | Lulus dalam cakupan mock yang diuji; readiness gate tidak menemukan blocker |
| Semua major state dapat diuji | Loading/initializing, error, empty, success, pending/retry dan session/access diuji pada hooks, halaman dan browser sebagaimana rincian di bawah |
| Aplikasi dapat dijalankan dengan mock service | Lulus; browser memakai Moodle mock dan backend mock tanpa server eksternal |

## Hasil akhir

`npm run verify:foundation` selesai dengan exit code **0** pada 3 Oktober 2026.

| Pemeriksaan | Hasil |
| --- | --- |
| Lint | Lulus, tanpa error/warning ESLint |
| Production build | Lulus, 83 modules; warning dynamic import Moodle yang sudah ada pada baseline Rakha |
| Unit/component tests | 68 lulus, 6 file (50 baseline + 18 tambahan) |
| Browser tests | 39 lulus (17 runtime + 22 foundation), tanpa retry/skip/expected failure |
| Readiness gate | 39 checks passed, 0 known blockers, 0 other incomplete checks |
| Review screenshot | Form course baru dan rencana pada 375 px diperiksa; konten dan kontrol tetap di viewport, tab dapat digulir horizontal |

Suite presentasi #72 tidak dijalankan ulang pada pekerjaan #71; hasil 9 tes di
laporan penyelarasan merupakan bukti revisi baseline sebelumnya.

## Cakupan requirement

| Requirement #71 | Bukti pengujian |
| --- | --- |
| Layout | Sebelas route dosen render tanpa page exception; header, halaman Moodle dan halaman AI tetap memakai UI sekarang; tanpa navbar utama/sidebar |
| Routing | Anonymous diarahkan ke login; link menu, Back/Forward, URL halaman dan not-found diuji di browser |
| Authentication | Login benar/salah, pemulihan sesi setelah reload, token invalid, logout, respons sesi/login yang terlambat, dan backend login terpisah |
| Role | Akun mahasiswa melihat data Moodle; menu AI tidak tersedia; akses langsung `/ai` ditolak; authorization mock backend juga diuji |
| Shared component | Label login, spinner, error alert, empty state, feedback sukses, tombol pending, dropdown/Escape, dialog revisi dan pengembalian fokus |
| State | `useApi` loading/error/reload/success; hasil request lama diabaikan; `useAction` pending/error/clear/retry; perubahan profil tersedia setelah client navigation |
| Service abstraction | Halaman memakai service Rakha; API HTTP diuji dengan fetch tiruan; Moodle REST/form encoding, error, role resolution dan file token diuji |
| Mock data | Moodle dan backend mock aktif; pencarian/filter serta workflow approval → generate → review → execution → verification memakai service mock |
| Responsive | Lima halaman tambahan di 375/768/1440 px; bounds main, input/select/textarea dan dropdown; lima screenshot mobile untuk review |

### Major state yang diverifikasi

- **Initializing/loading:** sesi tersimpan belum selesai dipulihkan, daftar kursus
  menunggu service, hook menunggu request, aksi simpan pending dan tombol disabled.
- **Error:** credential salah, sesi expired, service unavailable, kegagalan simpan,
  token backend invalid, network failure, JSON backend rusak, serta recovery/retry.
- **Empty:** response daftar kursus `[]` dan hasil pencarian/filter tanpa kecocokan.
- **Success:** login, pemulihan sesi, daftar kursus, simpan profil, retry request,
  dan workflow mock rencana/konten/review/eksekusi/verifikasi.
- **Access/session:** anonymous, dosen, mahasiswa, forbidden AI page, logout/Back,
  not-found dan respons async yang selesai setelah sesi berganti.

State loading/error deterministik diuji dengan React DOM/jsdom dan promise yang
dikendalikan melalui mock binding service. Komponen halaman dan hooks production
tetap digunakan; tidak ada fault injection pada source production. Browser memakai
dua mock Rakha, termasuk error token backend dan filter kosong.

## Temuan dan perbaikan

Kasus berikut gagal sebelum perbaikan, lalu diverifikasi kembali:

1. **Pemulihan/login lama setelah logout:** respons lama dapat mengaktifkan user
   atau menyimpan credential kembali. `AuthProvider` sekarang menggunakan generasi
   sesi; logout dan cleanup membatalkan hak respons lama untuk memperbarui sesi.
2. **Error pemulihan lama setelah login baru:** error dari sesi lama dapat menghapus
   sesi mahasiswa yang baru berhasil login. Guard yang sama melindungi sesi terbaru.
3. **Login backend yang terlambat:** token backend dapat tersimpan setelah sesi
   Moodle sudah berakhir. `authService.login` menerima guard sesi dari provider
   sebelum menyimpan token; pemanggilan lama dengan dua argumen tetap didukung.
4. **Moodle invalidtoken dari request lama:** callback global dapat mengeluarkan
   sesi baru. Moodle client menangkap generasi token saat request dimulai dan hanya
   menjalankan callback untuk generasi aktif, termasuk jika nilai token digunakan ulang.
5. **JSON sukses yang rusak:** HTTP 200 berisi JSON tidak valid sebelumnya menjadi
   `null` dan terlihat seperti data kosong. API client sekarang melempar
   `INVALID_RESPONSE`; respons kosong yang sah (204) tetap diterima.

Routing, penentuan role Moodle, dua sesi Moodle/backend, endpoint, fixture data,
markup halaman dan CSS tidak diubah oleh perbaikan #71. Perubahan fungsional di atas
terbatas pada bug async/error yang direproduksi oleh tes.

Tes dialog awal terlalu ketat karena menganggap setiap Tab harus berakhir pada
elemen halaman. Chrome dapat menyerahkan fokus ke kontrol browser sehingga
`document.activeElement` menjadi body. Tes diperbaiki untuk memastikan kontrol
halaman belakang tidak menerima fokus, Tab berikutnya kembali ke dialog, Shift+Tab
juga aman, dan Escape mengembalikan fokus ke tombol pemicu. Komponen dialog tidak diubah.

## Menjalankan ulang

Dari directory `frontend` setelah dependencies terpasang:

```powershell
npm run verify:foundation
```

Pipeline menjalankan lint, build, unit/component tests, browser tests, lalu
`scripts/check-foundation-readiness.mjs`. Readiness menolak expected failure,
skipped/flaky/incomplete checks dan error runner, walaupun Playwright menganggap
expected failure sebagai hasil sesuai ekspektasi.

Browser suite aktif: `tests/e2e/rakha-runtime.spec.js` (17 tes) dan
`tests/e2e/foundation-71.spec.js` (22 tes). Konfigurasi memaksa
`VITE_MOODLE_MOCK=true` dan `VITE_USE_MOCK=true` hanya pada server pengujian,
sehingga `.env.local` pengguna tidak mengubah mode suite.

Lingkungan: Node 22.16.0, npm 10.9.2, Windows, Chrome headless terisolasi melalui
Playwright 1.63.0. Server pengujian memakai `127.0.0.1:4173`; port 3000 untuk pengguna
tetap terpisah. Chrome tersedia lokal; sistem lain dapat memakai Chromium bundled.

Artefak lokal (diabaikan Git):

- `frontend/.cache/playwright/report/index.html`: laporan browser.
- `frontend/.cache/playwright/results.json`: input readiness gate.
- `frontend/.cache/playwright/results/`: screenshot mobile dan trace jika gagal.

## Batas verifikasi dan langkah sesudah review

- Hasil berlaku untuk foundation **mode mock** pada skenario di atas. Backend AI,
  Moodle Docker, deployment, persistensi nyata dan publikasi konten nyata belum diuji.
- Mock backend berada di memori; client navigation mempertahankan perubahan,
  full reload mengembalikan fixture awal. Sesi login tersimpan diuji terpisah.
- Login dari protected route tetap berakhir di `/my` mengikuti perilaku Rakha;
  tidak ditambahkan pengubahan redirect ke URL semula.
- Ketidaksesuaian username Moodle/email backend dan boundary Moodle browser vs
  dokumen backend masih perlu keputusan integrasi tim. Ini tidak menghalangi mock
  foundation, tetapi menghalangi klaim integrasi nyata lengkap.
- Preview body materi yang dihasilkan AI belum tersedia pada UI saat ini; kebutuhan
  fitur tersebut dicatat pada [laporan penyelarasan](frontend-rakha-alignment.md).
  Kelulusan #71 tidak menyatakan seluruh PRD/MVP sudah selesai.
- Firefox/Safari, semua breakpoint, seluruh state tiap feature page, dan kesamaan
  pixel terhadap desain lama tidak tercakup. Kesesuaian desain #72 adalah review terpisah
  dengan keputusan pengguna mempertahankan tampilan saat ini sebagai acuan.
- Sebelum PR/merge, ikuti `aturan.md`: dependency baseline disertakan dalam review,
  perbarui terhadap develop terbaru, review tim dan squash merge melalui PR.
