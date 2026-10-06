# Riwayat verifikasi frontend foundation (#71)

Issue: [#71](https://github.com/capstone-teams/capstone-projek/issues/71).
Tanggal: 3 Oktober 2026. Branch: `refactor/frontend-foundation-alignment`.
Baseline runtime: `accbc21035d378c5d3d9775728354ce2093bf244`.
Baseline lokal: `f3b0a38` (runtime/presentasi), `5fab886` (pemeriksaan kebutuhan).

Laporan historis untuk revisi tersebut; angka di bawah bukan jumlah tes terkini.
Verifikasi foundation mode mock lulus untuk review. Status issue tetap mengikuti
PR/review/merge pada [aturan kerja](../../aturan.md).

## Bukti verifikasi

verify:foundation selesai dengan exit code 0 pada tanggal laporan.

| Pemeriksaan | Hasil historis |
| --- | --- |
| Lint | Lulus, tanpa error/warning |
| Production build | Lulus, 83 modules; warning dynamic import Moodle |
| Unit/component | 68 lulus, 6 file: 50 baseline + 18 tambahan |
| Browser | 39 lulus: 17 runtime + 22 foundation; tanpa retry/skip/expected failure |
| Readiness | 39 passed, 0 blockers, 0 incomplete |
| Review screenshot | Form course baru dan rencana 375 px; kontrol tetap di viewport dan tab dapat digulir |

Suite presentasi tidak dijalankan ulang pada #71; sembilan tes presentasi pada
[laporan penyelarasan](frontend-runtime-alignment.md) adalah bukti baseline.

## Cakupan dan perbaikan

- Routing: sebelas route dosen, anonymous/login, menu, Back/Forward, not-found.
- Autentikasi: login benar/salah, restore setelah reload, invalid token, logout,
  role mahasiswa, akses langsung AI yang ditolak, dua sesi independen.
- State: initializing/loading, pending, error/retry, empty search/list, success;
  hasil request lama diabaikan dan profil tersedia setelah navigasi client.
- Komponen: label, spinner/alert, feedback sukses, dropdown/Escape, dialog revisi,
  keyboard dan pengembalian fokus. Fokus browser/body diperbolehkan ketika Tab,
  tetapi kontrol halaman belakang tidak menerima fokus.
- Service: API HTTP dengan fetch tiruan; encoding Moodle, role, file token,
  authorization backend mock, dan workflow approval hingga verification.
- Responsive: lima halaman pada 375/768/1440 px; bounds main, form, dan dropdown;
  lima screenshot mobile untuk review.

Kasus gagal sebelum perbaikan: respons restore/login setelah logout; error restore
lama menghapus sesi baru; login backend terlambat menyimpan token; invalidtoken
dari request lama mengeluarkan sesi baru; JSON HTTP 200 rusak terlihat seperti
data kosong. Guard generasi sesi/token melindungi sesi aktif, termasuk saat nilai
token digunakan ulang. API melempar INVALID_RESPONSE untuk JSON rusak dan tetap
menerima 204. Signature login dua argumen masih didukung.

Pengujian React DOM/jsdom mengendalikan promise/binding service tanpa fault
injection pada source produksi. Routing, endpoint, role, fixture, markup, dan
CSS dipertahankan oleh perbaikan tersebut.

## Reproduksi dan batas

Lingkungan historis: Node 22.16.0, npm 10.9.2, Windows, Chrome headless melalui
Playwright 1.63.0; server 127.0.0.1:4173. VITE_MOODLE_MOCK/VITE_USE_MOCK dipaksa true
pada server tes. Readiness menolak expected failure, skipped/flaky/incomplete,
dan error runner.

Suite historis terdiri dari 17 tes runtime dan 22 foundation. Nama file runtime
kini runtime.spec.js; skenario foundation tetap di foundation-71.spec.js.
Perintah dan konfigurasi terkini ada di [README frontend](../../frontend/README.md).
Report lokal berada di frontend/.cache/playwright/: report/index.html,
results.json, dan results/; diabaikan Git.

Hasil memakai mock, bukan bukti backend AI/Moodle/deployment nyata. Mock workflow
di memori kembali ke fixture saat reload. Alur protected-route saat revisi itu
berakhir di /my. Identitas Moodle/email backend dan boundary browser/backend
memerlukan verifikasi integrasi. Preview materi belum tercakup. Firefox/Safari,
seluruh state/breakpoint, dan kesamaan pixel desain historis tidak diuji.
