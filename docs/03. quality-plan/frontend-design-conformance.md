# FE-04.2 — Verify M01 Design Conformance

Issue: [#72](https://github.com/capstone-teams/capstone-projek/issues/72)

Tanggal: 3 Oktober 2026

Branch: `codex/fe-04-2-design-conformance`

Source yang diperiksa: hasil FE-03.2 dan FE-04.1 pada `fb88a88`.

## Baseline dan metode

Sesuai keputusan pengguna, approved design adalah UI yang sudah diimplementasikan
di directory `frontend` dan dijalankan dengan `npm run dev` pada port 3000.
Referensi historisnya adalah commit `e9807a530771263dda11f460f59ed77653c6df71`
pada branch `feature/verify-design-to-code`, sebelum penambahan service layer.
Verifikasi ini membandingkan dengan implemented mockup tersebut.

Pengujian mengekspor hanya directory frontend dari commit referensi lewat `git archive`
ke `.cache/design-baseline/`. Vite menyajikan referensi di port 4174 dan source saat ini
di port 4173. Keduanya menggunakan Microsoft Edge headless, OS, dependency, viewport,
font, dan pengaturan reduced motion yang sama. Tidak ada backend atau credential.

Screenshot full-page referensi dibuat **hanya dari source commit baseline** pada setiap
run; screenshot source saat ini dibandingkan terhadap referensi tersebut. Snapshot
tidak dihasilkan dari HEAD untuk menyetujui perubahan pada HEAD.

Pembanding memakai `maxDiffPixels: 0` dengan ambang warna bawaan Playwright `0.2`.
Selain screenshot, tes membandingkan bounds dan computed style elemen header,
heading, button, input, select, dan dialog: font family/size/weight/line-height,
warna, background, padding, margin, gap, border radius/color, dan shadow.
Dengan demikian, hasil bukan klaim bahwa seluruh byte PNG identik.

Metode mengikuti [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots).

## Cakupan

Ukuran layar: **375×812**, **768×1024**, dan **1440×900**.

| Halaman/state | Jumlah state per viewport |
| --- | --- |
| Login | 1 |
| Dashboard dosen: kosong dan berisi mata kuliah | 2 |
| RPS analysis | 1 |
| Course plan: empty, review, approved, published | 4 |
| Weekly content: empty, review, synced | 3 |
| Material reader | 1 |
| Mahasiswa: daftar mata kuliah, detail course, detail minggu | 3 |
| Overlay: Upload RPS, Profil Dosen, menu akun | 3 |

Total: **18 tampilan × 3 ukuran = 54 perbandingan visual/style**.
Satu tes tambahan membandingkan navigasi mahasiswa pada kedua versi:
daftar course → detail course → minggu 03 melalui keyboard → kembali ke course
→ brand header menuju daftar course.

Navigasi dosen menggunakan keyboard serta Back/Forward sudah diuji pada FE-04.1.
Source `App.tsx`, route metadata/helper, layout, dan navigasi header tidak berubah
antara baseline dan source yang diperiksa. Hasil foundation dan batas pengujian
tercatat pada [laporan FE-04.1](frontend-foundation-verification.md).

## Hasil

`npm run test:design`: **55 passed**, 0 unexpected failures, 0 skipped, 0 flaky,
durasi sekitar 2 menit. Tidak ada expected-failure marker dalam suite desain.
`npm run lint` dan `npm run typecheck` juga lulus.

Screenshot dashboard mobile, course-plan review desktop, profil mobile, detail course
tablet, dan material reader desktop diperiksa secara visual setelah tes selesai.

| Requirement #72 | Hasil |
| --- | --- |
| Layout | Cocok pada 54 tampilan/ukuran yang dibandingkan |
| Component appearance | Screenshot dan computed style cocok untuk kasus yang diuji |
| Spacing | Bounds, padding, margin, dan gap elemen yang diperiksa cocok |
| Typography | Font family, size, weight, line-height, warna, dan rendering cocok |
| Navigation behavior | Alur demo mahasiswa cocok; navigasi dosen/Back/Forward tercakup FE-04.1 |
| Responsive behavior | Baseline dan versi sekarang cocok pada mobile, tablet, dan desktop yang diuji |
| Record discrepancy | Perubahan tambahan dan batas integrasi dicatat di bawah |

Tidak ditemukan penyimpangan visual yang memblokir terhadap implemented baseline
pada kasus yang diuji. Pengerjaan issue ini menambahkan tes dan dokumentasi;
tidak memerlukan perubahan source UI berdasarkan hasil perbandingan tersebut.

## Catatan perubahan dan discrepancy

| Perbedaan sejak baseline | Penilaian |
| --- | --- |
| Halaman membaca mock service alih-alih array langsung | Data berhasil dimuat; tampilan settled cocok dengan baseline |
| Loading/error/retry dari service abstraction | State tambahan FE-03.2, tidak memiliki screenshot referensi pada mockup lama; perilaku diuji FE-04.1 |
| Daftar service kosong untuk mahasiswa | State tambahan FE-04.1 dengan Card, heading, dan warna slate yang sudah digunakan aplikasi; belum memiliki referensi visual terpisah yang disetujui |
| Daftar service dosen kosong | Memakai kembali empty state baseline; response `[]` telah diuji FE-04.1 |
| Label login terhubung ke input | Perbaikan aksesibilitas; tampilan login tetap cocok |
| Fokus kembali setelah modal ditutup | Perbaikan interaksi FE-04.1; tampilan modal terbuka tetap cocok |
| Rumus pada material reader tampil sebagai teks LaTeX mentah | Batas baseline yang juga terlihat pada source sekarang; tidak ada penyimpangan baru, rendering matematika belum diverifikasi sebagai feature |
| Authentication/session/protected route belum terintegrasi | Gap fungsional #71; bukan perbedaan baru terhadap demo baseline. Verifikasi ulang navigasi/session setelah integrasi Rakha |

State tambahan yang belum mempunyai referensi visual mandiri dicatat untuk review.
Kelulusan perbandingan baseline tidak otomatis menyetujui semua desain tambahan.
Header brand dan akun tetap mengikuti approved mockup. Tidak ditambahkan menu
navigasi utama atau sidebar navigasi aplikasi.

## Menjalankan ulang dan bukti

Dari directory `frontend`, setelah dependency terpasang:

```bash
npm run lint
npm run typecheck
npm run test:design
```

Prasyarat tambahan: Git, `tar`, commit baseline tersedia di history lokal, dan port
4173/4174 kosong. Checkout dangkal perlu menyediakan commit baseline sebelum tes.
Pada Windows digunakan Microsoft Edge yang sudah terpasang. Pada sistem lain,
pasang Chromium melalui `npx playwright install chromium`, atau pilih browser
terpasang menggunakan `PLAYWRIGHT_CHANNEL` sebagaimana konfigurasi FE-04.1.

Port development 3000 dapat tetap digunakan. Server pengujian ditutup oleh Playwright.
Tidak ada dependency npm baru yang diperlukan untuk issue ini.

Source:

- [Browser tests](../../frontend/tests/e2e/design-conformance.spec.ts).
- [Konfigurasi desain](../../frontend/playwright.design.config.ts).
- [Ekspor baseline](../../frontend/scripts/prepare-design-baseline.mjs).

Artefak di `.cache/design-conformance/` diabaikan Git:

- `report/index.html`: laporan HTML dengan attachment approved baseline dan current.
- `results.json`: hasil tes terstruktur.
- `reference/`: screenshot dari commit baseline pada lingkungan run.
- `results/`: attachment, screenshot kegagalan/diff, dan trace jika ada kegagalan.

## Batas dan status pekerjaan

Perbandingan ini memeriksa kesesuaian source terhadap approved implemented mockup,
bukan audit ulang desain Figma, validasi seluruh workflow bisnis, atau persetujuan
desain state tambahan. Browser yang diuji adalah Chromium melalui Edge; Safari dan
Firefox belum diuji. Animasi/progress sementara tidak menjadi target screenshot.

Review dan integrasi branch tetap diperlukan sebelum issue ditutup menurut workflow
repository. Issue #71 masih memiliki blocker authentication/role/state tersendiri;
kelulusan perbandingan desain #72 tidak menyelesaikan blocker tersebut.
