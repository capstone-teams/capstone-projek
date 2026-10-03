# Penyelarasan approved UI dengan fondasi Rakha

Tanggal: 3 Oktober 2026. Branch lokal: `refactor/frontend-foundation-alignment`.

## Acuan dan keputusan

- Approved implemented mockup: `e9807a530771263dda11f460f59ed77653c6df71`.
- Pekerjaan frontend sebelumnya: FE-03.2, FE-04.1 (`fb88a88`), FE-04.2 (`3c4c1e0`).
- Sumber fondasi Rakha: `origin/feature/frontend-setup`, commit
  `accbc21035d378c5d3d9775728354ce2093bf244`.
- Pengguna menyetujui penyelarasan dengan JS/JSX Rakha sambil mempertahankan UI.

Integrasi dilakukan selektif terhadap source fondasi. Seluruh UI Moodle replica
Rakha tidak diambil. Tidak ada merge atau push langsung ke `develop`.

## Perubahan

1. Source, konfigurasi aktif, dan pengujian frontend menjadi JS/JSX. Build memakai
   Vite; Vitest menggantikan node test runner TypeScript. CSS Modules dipertahankan.
2. BrowserRouter menggantikan manipulasi history manual. URL semantik tetap ada;
   `/my` dan `/ai` memberi jalur masuk yang kompatibel dengan fondasi Rakha.
3. AuthProvider memulihkan session melalui backend `/auth/me`, memvalidasi login,
   mengambil role dari user, serta menghapus session pada logout/401. Respons
   lama tidak dapat memulihkan session setelah logout atau login berikutnya.
4. Guard mengarahkan pengguna anonim ke login, menolak role yang salah, dan
   menampilkan halaman tidak ditemukan untuk route yang tidak terdaftar.
   Halaman materi merupakan route bersama yang tetap memerlukan session.
   Aksi kembali/breadcrumb penampil materi mahasiswa menuju halaman mahasiswa,
   dengan layout dan label baseline tetap dipertahankan.
5. Service JS, mock backend workflow, hooks, dan helpers dari Rakha tersedia.
   API facade disambungkan ke validasi/error mapping HTTP FE-03.2. Request state
   pada approved pages menggunakan `useApi` bersama dengan cleanup request lama.
6. Auth aplikasi mengikuti dokumentasi `moodle-integration.md`: frontend menuju
   backend. Client Moodle browser dan token Moodle dari UI Rakha tidak diambil.
   Login backend nyata memakai email pada field `username` sesuai schema backend.

## Perubahan visual yang diperlukan

- Petunjuk login berisi akun/password demo yang sekarang divalidasi. Jumlah
  karakter password dan wrapping petunjuk berubah, sehingga posisi vertikal
  kartu login dapat bergeser. Tipografi, warna, ukuran kontrol, dan CSS tetap.
- Menu akun tidak lagi menyediakan tombol untuk mengganti role. Menu menampilkan
  role akun aktif, profil dosen, dan logout dengan style yang sudah ada.

Tidak ditambahkan sidebar atau navigasi utama baru. Halaman fitur, upload modal,
dan profile modal dibandingkan langsung dengan baseline yang disetujui.

## Batas integrasi

- Mata kuliah/silabus/materi masih memakai presentation fixture FE-03.2.
- Upload RPS, proses AI, perubahan profil, course plan, dan publish Moodle pada
  approved UI masih simulasi lokal; state workflow belum persisten pada backend.
- Mock backend Rakha memiliki fixture dan response shape berbeda. Adapter data
  dan penyambungan aksi fitur perlu dikerjakan per issue agar visual tetap sama.
- Mode mock tidak membutuhkan Docker. Mode auth nyata memerlukan backend dan
  CORS; Moodle Docker hanya diperlukan untuk pengujian Moodle nyata melalui
  backend. Compose repository saat ini menyediakan backend dan database.
- Mekanisme auth WebSocket nyata belum menjadi kontrak final. Service monitoring
  yang diambil dari Rakha belum digunakan pada approved UI.

## Verifikasi

Hasil final pada Node.js 22.16.0 dan Microsoft Edge (Playwright):

| Pemeriksaan | Hasil |
| --- | --- |
| `npm run lint` | Lulus tanpa error/warning |
| `npm run build` | Lulus, 82 modules |
| `npm test` | 86 tes lulus pada 5 file |
| `npm run test:e2e` | 32 tes lulus, tidak ada expected failure atau skip |
| `node scripts/check-foundation-readiness.mjs` | Exit 0; 0 blocker, 0 incomplete |
| `npm run test:design` | 55 tes lulus pada tiga viewport |
| `git diff --cached --check` | Lulus |

Gate dijalankan per tahap; tahap readiness membaca hasil full suite browser.
Pengujian mencakup credential invalid, restore session, logout/Back, role guard,
deep link, navigasi materi mahasiswa, race respons lama, HTTP Bearer/error mapping,
mock workflow, dan perbandingan desain. Lima blocker auth/routing pada laporan
FE-04.1 lama kini lulus sebagai tes normal.

Pengujian HTTP memakai fetch stub; belum dilakukan login ke backend nyata atau
pengujian Moodle nyata. Hasil ini memverifikasi fondasi frontend dengan mock.

Desain diuji pada 375, 768, dan 1440 px. Sebanyak 48 kasus tetap memakai
perbandingan screenshot nol perbedaan dan computed style terhadap commit
approved. Enam kasus login/menu mencatat pengecualian fungsi di atas: login
memeriksa style, ukuran dan posisi horizontal; menu memeriksa aksi yang tersedia.
Satu kasus tambahan membandingkan flow navigasi mahasiswa.

Perbandingan visual selesai sebelum penyesuaian callback navigasi balik materi
mahasiswa; penyesuaian itu tidak mengubah render/CSS. Gate browser final memeriksa
callback tersebut bersama seluruh 31 kasus lainnya. Screenshot dan HTML report
tersimpan pada `frontend/.cache/design-conformance/` dan `.cache/playwright/`.

## Status publikasi dan aturan integrasi

Perubahan pada branch ini belum dipush. Draft PR #85 tetap mengacu pada branch
FE-03.2 lama, sehingga PR tersebut belum memuat penyelarasan ini. Branch lama
disimpan sebagai riwayat; tidak dilakukan revert massal atau penghapusan branch.

Sebelum integrasi tim: sinkronkan dengan `develop`, review perbedaan dengan branch
Rakha, lalu ajukan PR yang jelas sumbernya. Ikuti `aturan.md`: review/approval
anggota lain, gate lulus, konflik diselesaikan, dan squash merge ke `develop`.
Jangan merge seluruh branch UI Rakha sesudah penyelarasan ini tanpa rekonsiliasi,
karena kedua branch mengubah source frontend yang sama dengan desain berbeda.
