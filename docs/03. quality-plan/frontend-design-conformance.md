# Riwayat verifikasi desain M01 (#72)

Issue: [#72](https://github.com/capstone-teams/capstone-projek/issues/72).
Tanggal: 3 Oktober 2026. Branch: `codex/fe-04-2-design-conformance`.
Source: hasil FE-03.2/FE-04.1 pada `fb88a88`.

Laporan ini merekam implementasi sebelum integrasi sesi Moodle dan penyelarasan
runtime. Prosedur baseline berikut sudah dihentikan; suite test:design sekarang
menguji presentasi aplikasi aktif. Lihat
[laporan penyelarasan](frontend-runtime-alignment.md) dan
[README frontend](../../frontend/README.md).

## Metode historis

Referensi: `e9807a530771263dda11f460f59ed77653c6df71` pada branch
`feature/verify-design-to-code`. Frontend diekspor dengan git archive ke
.cache/design-baseline/. Vite menyajikan baseline pada 4174 dan revisi pengujian
pada 4173 dengan Edge headless, environment/viewport/font/reduced motion sama.
Tidak ada backend atau credential. Referensi screenshot dibuat dari commit
baseline, bukan HEAD.

Screenshot dibandingkan dengan maxDiffPixels: 0 dan ambang warna 0.2; bounds dan
computed style header, heading, button, input, select, dialog diperiksa. Hasil
tidak menyatakan semua byte PNG identik. Metode mengikuti
[Playwright visual comparisons](https://playwright.dev/docs/test-snapshots).

## Cakupan dan bukti

Viewport: 375×812, 768×1024, 1440×900.

| Halaman/state | Jumlah per viewport |
| --- | --- |
| Login | 1 |
| Dashboard dosen kosong/berisi | 2 |
| Analisis RPS | 1 |
| Course plan empty/review/approved/published | 4 |
| Weekly content empty/review/synced | 3 |
| Material reader | 1 |
| Mahasiswa courses/course/week | 3 |
| Upload RPS, profil dosen, menu akun | 3 |

Total 18 tampilan × 3 viewport = 54 perbandingan visual/style; satu tes tambahan
membandingkan navigasi mahasiswa melalui keyboard pada kedua versi.

Hasil historis test:design: **55 passed**, 0 unexpected failures/skipped/flaky,
tanpa expected failure, sekitar dua menit. Lint dan typecheck juga lulus pada
revisi tersebut. Perintah typecheck hanya tersedia dalam implementasi historis.
Layout, komponen, spacing, typography, navigasi, dan responsive cocok dalam kasus
yang diuji; screenshot dashboard mobile, rencana desktop, profil mobile, detail
course tablet, dan reader desktop direview.

## Discrepancy dan batas

Loading/error/retry serta daftar service kosong belum mempunyai seluruh referensi
visual mandiri. Label login dan pemulihan fokus diperbaiki. Rumus reader tampil
sebagai teks LaTeX mentah. Autentikasi/role/session belum terintegrasi pada revisi
ini; kelulusan desain tidak menyelesaikan kebutuhan foundation #71.

Source App.tsx, suite baseline, konfigurasi .ts, dan script ekspor yang dipakai
pada verifikasi ini merupakan source historis di revisi fb88a88, bukan tautan ke
file aktif. Controller/suite baseline lama dihapus saat refactor pembersihan;
untuk mereproduksi hasil historis gunakan checkout revisi terpisah.

Artefak di .cache/design-conformance/: report/index.html, results.json,
reference/, dan results/. Artefak lokal dapat dibuat ulang dan diabaikan Git.
Ini bukan audit Figma, verifikasi semua workflow bisnis, atau seluruh state baru.
Firefox/Safari dan animasi/progress sementara tidak termasuk cakupan. Hasil
historis tidak berlaku sebagai bukti integrasi atau presentasi revisi terkini.
