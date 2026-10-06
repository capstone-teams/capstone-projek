# Riwayat Course Plan Screen (#74)

Issue: [#74](https://github.com/capstone-teams/capstone-projek/issues/74).
Tanggal: 4 Oktober 2026. Branch: `feature/fe-05-1-course-plan-screen`.
Baseline: `7a21ec7` dari `refactor/frontend-foundation-alignment`.
Laporan historis; dependency penyelarasan dan #71 menjadi bagian review revisi ini.

## Implementasi

Halaman Rencana memakai CoursePlanDetails/CSS Module untuk menampilkan nama/kode
course, SKS, jumlah minggu, CPMK, objectives, topics, teaching methods, aktivitas,
dan status. Desktop mulai 1024 px menggunakan tabel enam kolom dengan region
scroll yang dapat difokuskan; viewport lebih kecil memakai kartu mingguan.
Enam belas minggu ditampilkan pada fixture tanpa sidebar tambahan.

CoursePlanPage mengelola generate/revisi/approve dan read retry. Adapter pada
service boundary menormalisasi response; endpoint/method tidak berubah.
Mock melengkapi metadata course/CPMK dari RPS pada seed, generate, dan regenerate.
Kompatibilitas pemilih minggu diuji; hasil ini tidak menyatakan seluruh #75 selesai.

## Kontrak data dan state

| Field schema | Alias yang tetap didukung |
| --- | --- |
| week_number | week |
| title | topic |
| objectives | learning_objectives |
| topics | sub_topics |
| planned_activities | activities |

Referensi: content-schema.md §8/9 dan design-api.md §9. Field canonical
diprioritaskan; alias week/topic/learning_objectives tetap melayani GeneratePanel.
Field learning_outcomes/teaching_methods yang tidak tersedia ditampilkan
“Belum tersedia.” tanpa mengarang data.

Adapter memeriksa weeks, nomor positif/unik, judul teks, dan array teks; response
rusak menjadi INVALID_RESPONSE. Status, version, instruction, metadata tetap
dipertahankan. Respons parsial tidak menghasilkan versi undefined/status palsu.

State yang diuji: CREATED/empty, pending, PLANNING, 404, weeks kosong,
network/structure error dan retry, data parsial, serta refresh gagal dengan data
sebelumnya tetap terbaca. Status tidak dikenal ditampilkan sesuai data.

## Bukti verifikasi historis

verify:foundation selesai dengan exit code 0 pada 4 Oktober 2026.

| Pemeriksaan | Hasil |
| --- | --- |
| Lint | Lulus, tanpa error/warning |
| Build | Lulus, 86 modules; warning dynamic import Moodle baseline |
| Unit/component | 85 lulus, 8 file; 17 tambahan #74 |
| Browser | 45 lulus; 6 tambahan #74, tanpa retry/skip/expected failure |
| Readiness | 45 passed, 0 blockers, 0 incomplete |
| Screenshot | Overview desktop 1440 px, detail kartu 375/768 px; field/header terbaca |

Build diulang setelah penyesuaian lebar kolom Minggu dan lulus. Percobaan browser
awal gagal launch Chrome; pipeline berikutnya lulus. Tes pemilih minggu memakai
label sebagai target input transparan; handler runtime tidak berubah.

course-plan-service.test.js memeriksa schema/alias, prioritas field, urutan minggu,
invalid response, 404/empty melalui fetch tiruan. course-plan.test.jsx memeriksa
state halaman dengan service terkontrol. workflow.test.js memeriksa enrichment
rencana mock. course-plan-74.spec.js memeriksa empat viewport 375/768/1024/1440,
seluruh minggu, overflow, create/generate, revisi/approve, dan generate satu minggu.

Screenshot historis berada di frontend/.cache/playwright/results/ pada direktori
suite course-plan-74: course-plan-<width>.png dan first-week-<width>.png. Report
HTML/JSON berada di .cache/playwright/; diabaikan Git. Setup terkini ada pada
[README frontend](../../frontend/README.md).

## Batas

Plan mock, seluruh minggu, status, dan empty state terverifikasi. Generation AI,
persistensi/publikasi Moodle nyata, dan preview materi AI tidak termasuk bukti ini.
Empat ukuran layar bukan perbandingan pixel terhadap mockup historis. Status issue
tetap mengikuti review dan merge melalui PR.
