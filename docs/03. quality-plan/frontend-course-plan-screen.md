# FE-05.1 — Course Plan Screen (#74)

Issue: [#74](https://github.com/capstone-teams/capstone-projek/issues/74).
Tanggal: 4 Oktober 2026. Branch: `feature/fe-05-1-course-plan-screen`.
Baseline: `7a21ec7` dari `refactor/frontend-foundation-alignment`.

Branch ini bergantung pada hasil penyelarasan runtime Rakha dan verifikasi #71
yang belum masuk develop. Dependency perlu disertakan pada review/PR; tidak ada
push langsung ke develop atau merge dalam pekerjaan ini.

## Tujuan dan cakupan

Melengkapi halaman Rencana yang sudah tersedia agar seluruh informasi #74 dapat
dibaca menggunakan mock. Acuan tampilan adalah UI sekarang yang dipilih pengguna,
dengan warna, header, routing, login dan workflow Rakha sebagai dasar.

| Requirement | Implementasi |
| --- | --- |
| Course information | Nama, kode, bobot SKS jika tersedia, jumlah minggu; description jika diberikan service |
| Weekly structure | Nomor minggu sesuai RPS, urutan ascending; 16 minggu pada fixture sekarang |
| Learning outcomes | Daftar CPMK course dan capaian tiap minggu; kode dijelaskan jika definisinya tersedia |
| Objectives | Tujuan mingguan ditampilkan terpisah dari capaian |
| Topics | Judul dan daftar topik mingguan |
| Teaching methods | Metode tiap minggu dari RPS mock, termasuk metode Ujian pada minggu 8/16 |
| Planned activities | Badge Materi/Tugas/Kuis mengikuti data rencana |
| Plan status | Draft/Disetujui/Perlu revisi; status tidak dikenal ditampilkan sebagaimana data, bukan dipaksa menjadi Draft |

## Perubahan kode

- `src/components/course-plan/CoursePlanDetails.jsx` dan CSS Module: komponen
  presentasi khusus domain rencana; tidak memiliki handler approve/regenerasi.
- `src/pages/ai/course/CoursePlanPage.jsx`: memakai detail baru, menyediakan retry
  saat read service gagal, dan membedakan error dari kondisi kosong.
- `src/services/coursePlanAdapter.js`: normalisasi response di service boundary.
- `src/services/courseService.js`: `getPlan` memanggil adapter; endpoint dan method
  API tetap sama.
- `src/services/mock/mockData.js`/`mockServer.js`: melengkapi field schema, metadata
  course dan definisi CPMK pada rencana seed, generate, serta regenerate.

Desktop mulai 1024 px memakai tabel enam kolom. Tabel mempunyai region scroll yang
dapat difokuskan dengan keyboard jika lebar konten tidak cukup. Di bawah 1024 px,
setiap minggu ditampilkan sebagai kartu berlabel, sehingga field tidak terjepit
dalam kolom kecil. Semua minggu langsung dapat dibaca; tidak ditambahkan sidebar.
Styling baru hanya ada dalam CSS Module Course Plan.

Handler approve, regenerate dan generate yang sudah ada tetap dipakai. Login,
route tree dan service eksekusi tidak diubah. #75 tetap merupakan tugas Rakha;
tes pada pekerjaan ini memeriksa kompatibilitas interaksi yang sudah tersedia,
bukan menyatakan acceptance criteria #75 seluruhnya selesai.

## Bentuk data dan kompatibilitas

Referensi: `docs/02. design/content-schema.md` section 8/9 dan `design-api.md` section 9.

| Field schema | Format sebelumnya yang masih didukung |
| --- | --- |
| week_number | week |
| title | topic |
| objectives | learning_objectives |
| topics | sub_topics |
| planned_activities | activities (contoh minimum section 9) |

`learning_outcomes` dan `teaching_methods` ditampilkan jika disediakan. Field baru
pada mock diambil dari weekly_plan RPS; data lama yang tidak memiliki field ini
menampilkan “Belum tersedia.”, tanpa mengarang capaian/metode. Field canonical
diprioritaskan bila kedua format tersedia. Alias week/topic/learning_objectives
tetap tersedia bagi GeneratePanel dan konsumen Rakha sebelumnya.

Adapter memeriksa struktur weeks, nomor minggu positif/unik, judul teks dan array
teks. Response yang rusak menjadi `INVALID_RESPONSE`, bukan sukses kosong. Status,
version, instruction dan metadata response tetap dipertahankan. Schema contoh
yang tidak menyediakan version/status tidak menghasilkan “versi undefined” atau
badge Draft palsu. Bentuk response backend nyata masih perlu dicocokkan saat
endpoint tersedia; pekerjaan ini tidak mengubah kontrak server.

## State halaman

- Course CREATED: “Rencana belum dibuat.”; generate memakai aksi Rakha yang ada.
- Read request pending: spinner Memuat.
- PLANNING tanpa hasil: feedback proses dan spinner Menyusun rencana.
- 404: “Rencana tidak ditemukan.”, tanpa error jaringan palsu.
- Rencana dengan weeks kosong: “Rencana mingguan belum tersedia.”, tanpa tabel kosong.
- Error jaringan/struktur: alert dan Coba lagi; sukses retry menghapus error.
- Refresh gagal ketika data sudah terlihat: data sebelumnya tetap dapat dibaca.
- Data tersedia: seluruh informasi dan status rencana ditampilkan.

## Pengujian

**Implementasi teknis mode mock lulus dan siap direview.**
`npm run verify:foundation` selesai dengan exit code 0 pada 4 Oktober 2026.

| Pemeriksaan | Hasil |
| --- | --- |
| Lint | Lulus, tanpa error/warning ESLint |
| Production build | Lulus, 86 modules; warning dynamic import Moodle sudah ada pada baseline |
| Unit/component | 85 lulus, 8 file; 17 tambahan untuk #74 |
| Browser | 45 lulus; 6 tambahan untuk #74, tanpa retry/skip/expected failure |
| Readiness | 45 checks passed, 0 known blockers, 0 incomplete checks |
| Review screenshot | Overview desktop 1440 px dan detail kartu 375/768 px diperiksa; header tabel dan field terbaca |

Build dijalankan kembali setelah penyesuaian akhir lebar kolom Minggu dan lulus.
Pada percobaan browser awal, Chrome sempat gagal launch sebelum tes pertama;
launch normal pada full pipeline berikutnya. Tes pemilih minggu juga diperbaiki
untuk mengklik label yang memang menjadi target interaksi, bukan input transparan
dengan pointer-events none. Kedua kasus tidak memerlukan perubahan runtime browser
atau handler pemilih minggu.

Acceptance criteria #74 terverifikasi: mock plan tampil, semua minggu dapat dibaca,
status tersedia, dan empty state tampil. Integrasi nyata dan review/merge masih
terpisah sebagaimana batas hasil di bawah.

Tes tambahan:

- `tests/course-plan-service.test.js`: response schema dan format Rakha, prioritas
  field, urutan minggu, data invalid dan 404 vs weeks kosong melalui service HTTP
  dengan fetch tiruan.
- `tests/course-plan.test.jsx`: komponen production dengan promise/service terkontrol
  untuk loading, error/retry, CREATED, PLANNING, missing/empty, data parsial dan
  kegagalan refresh.
- `tests/workflow.test.js`: field tambahan dari rencana yang benar-benar dihasilkan
  mock, di dalam workflow test yang sudah ada.
- `tests/e2e/course-plan-74.spec.js`: empat viewport 375/768/1024/1440 px, overflow
  dokumen, field terlihat, seluruh minggu, serta create → empty → generate dan
  regenerate → approve → pilih satu minggu → generate konten.

Jalankan dari directory frontend:

```powershell
npm run verify:foundation
```

Artefak screenshot lokal berada di
`frontend/.cache/playwright/results/course-plan-74-course-plan-stays-readable-at-<width>px/`:
`course-plan-<width>.png` (overview) dan `first-week-<width>.png` (detail minggu).
Report HTML/JSON tersedia di `.cache/playwright/`; seluruh artefak diabaikan Git.

## Batas hasil

Implementasi dan pengujian memakai Moodle/backend mock. Ini tidak membuktikan
generation AI atau publikasi Moodle nyata. Preview isi materi AI bukan bagian #74.
Uji responsive pada empat ukuran bukan perbandingan pixel penuh dengan mockup lama.
Issue tetap perlu review tim dan merge melalui PR sebelum disebut DONE.
