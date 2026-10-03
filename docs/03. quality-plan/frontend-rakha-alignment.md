# Penyelarasan runtime Rakha dan tampilan yang disetujui

Tanggal: 3 Oktober 2026. Branch: `refactor/frontend-foundation-alignment`.

## Keputusan terbaru pengguna

Pengguna meminta routing, login, akses Moodle dan data mengikuti Rakha karena
penyelarasan sebelumnya mengubah terlalu banyak bagian fungsional.
Laporan ini menggantikan hasil integrasi selektif pada commit `713f886`.

Sumber Rakha: `origin/feature/frontend-setup`, commit
`accbc21035d378c5d3d9775728354ce2093bf244`.
Desain sebelumnya: implemented mockup `e9807a530771263dda11f460f59ed77653c6df71`.

## Yang dikembalikan ke implementasi Rakha

- Route tree App.jsx dan main.jsx.
- AuthProvider/RequireAuth: login/token.php Moodle, resolveSession dan role Moodle,
  sesi Moodle, percobaan login backend terpisah untuk dosen, logout.
- Seluruh hooks, API client, services dan fixture mock asli Rakha.
- Halaman aktif di pages/: data Moodle, RPS, project, preferensi, generate plan,
  approval, generation content, review, execution dan verification.
- Konfigurasi env Moodle + backend, proxy Vite, Tailwind dan DOMPurify.

Aksi fitur sekarang terhubung dengan service Rakha. Fixture Aljabar dan controller
simulasi lokal lama tidak menjadi sumber aplikasi. Route lama tidak dibuat alias.

## Perubahan pada tampilan

- Header Agentic LMS + ITK, nama akun dan dropdown memakai CSS desain sebelumnya.
  Link menu menggunakan route Rakha; logout menggunakan provider Rakha.
- Form login menggunakan dua panel desain sebelumnya. Handler login, error
  Moodle, pemulihan password dan tujuan navigasi tetap mengikuti Rakha.
- Kartu kursus memakai CSS Modules desain sebelumnya, dengan field data Moodle.
- Warna, font, margin dan kontrol mengikuti token desain sebelumnya.
- Navbar utama dan drawer tidak dibuat. Sidebar kursus diganti indeks expandable
  dalam konten; API, context Outlet dan tautan kursus tidak berubah.
- Dashboard dan pemilih minggu ditata dalam konten, tanpa sidebar.

Halaman fitur memakai markup fungsional Rakha dengan tema desain sebelumnya.
Hasilnya belum dinyatakan identik pixel dengan mockup lama. Data dan kelengkapan
fitur Rakha membuat beberapa isi/tata letak berbeda dan perlu review visual tim.

## Source lama dan riwayat

Controller/facade lama dipertahankan sebagai source tidak aktif. Routing hanya
mengimpor pages Rakha. Penghapusan massal ditolak oleh automatic approval review;
revisi ini menggunakan perubahan file spesifik tanpa menghapus source tersebut.
Pekerjaan lama juga tersedia pada commit/branch sebelumnya.

## Moodle, backend dan Docker

Mode default: dua mock, tanpa Docker. VITE_MOODLE_MOCK=false menghubungkan browser
langsung ke Web Service Moodle. VITE_USE_MOCK=false mengaktifkan backend AI nyata.
Moodle biasanya pada 8080; proxy backend Vite menuju 8000 sesuai env Rakha.
Login Moodle dapat berhasil walaupun login backend AI gagal; ini perilaku Rakha.
Mock backend hanya in-memory, sehingga reload mengembalikan fixture awal.

Dokumen arsitektur sebelumnya menjelaskan Moodle lewat backend. Pengguna memilih
runtime Rakha sebagai dasar saat ini; perbedaan dokumen/implementasi perlu dibahas
tim saat review. Tidak dilakukan perubahan backend atau Moodle server.

## Verifikasi revisi ini

Hasil final revisi ini:

| Pemeriksaan | Hasil |
| --- | --- |
| npm run lint | Lulus, tanpa error/warning |
| npm run build | Lulus, 83 modules; warning dynamic import yang juga ada pada source Rakha |
| npm test | 50 tes Rakha lulus, 4 file |
| npm run test:e2e | 17 tes lulus, tanpa skip/expected failure |
| npm run test:design | 9 pemeriksaan presentasi lulus pada 375/768/1440 px |
| Perbandingan source | 54 file source identik dengan Rakha setelah normalisasi newline; 6 file berbeda untuk presentasi |

Enam file presentasi: MoodleLayout, CourseCard, LoginPage, Moodle CourseLayout,
Moodle DashboardPage dan global.css. CSS Modules desain sebelumnya ditambahkan
sebagai aset presentasi. Controller lama tetap tidak aktif.

Screenshot lokal untuk review ada di frontend/.cache/review-1440-login.png,
review-1440-dashboard.png, review-1440-content.png dan review-375-content.png.
Pemeriksaan desain menguji style dan batas konten, bukan kesamaan pixel dengan
mockup lama. Pengguna kemudian memilih mempertahankan tampilan saat ini sebagai acuan pengerjaan.

Alur login pada pengujian browser berakhir di /my seperti runtime Rakha, termasuk
ketika masuk dari halaman yang terproteksi. Tidak ditambahkan pengubahan redirect.
Suite sebelumnya 86 unit/32 browser/55 design bukan bukti untuk revisi ini.
Browser suite memakai Chrome terisolasi. Pengujian memakai mock; Moodle dan backend
nyata serta deployment belum diverifikasi.

Tidak ada push, merge develop atau perubahan PR draft #85 pada revisi ini.

## Keputusan tampilan dan pemeriksaan kebutuhan berikutnya

Pengguna memilih tampilan saat ini, sehingga tidak direncanakan pemulihan layout
mockup lama. Acuan lokal saat keputusan: commit f3b0a38. Keputusan ini belum
berarti seluruh requirement proyek/MVP telah terpenuhi.

Pemeriksaan source terhadap PRD dan issue #69/#71/#72 menunjukkan:

- UI tersedia untuk upload/proses RPS, analisis, profil mengajar, prompt tambahan,
  course target, konfigurasi aktivitas, rencana/revisi/approval, generate konten,
  validasi/review, monitoring, eksekusi/verifikasi dan akses mahasiswa.
- Kekurangan utama: WeekDetail pada pages/ai/course/CourseContentPage.jsx tidak
  merender week.materials atau body_markdown. Data mock sudah memiliki materi;
  UI hanya memperlihatkan tujuan, tugas/kuis dan sumber belajar. Review materi
  lengkap sebelum execution (PRD FR-042/FR-043/AC-006) belum tercakup.
- Tes yang lulus menguji mode mock. Persistensi, real AI, publikasi Moodle dan
  akses mahasiswa ke hasil publikasi yang sama belum terbukti end-to-end.
- Checkout backend lokal baru meregistrasikan health/auth/admin; endpoint RPS, course dan workflow AI belum terdaftar di backend/src/routes/__init__.py. Ketersediaan pada branch backend lain belum diperiksa dalam audit ini.
- AuthProvider memakai username/password Moodle yang sama untuk mencoba login
  backend. Backend lokal memakai email sebagai identitas login. Keselarasan akun
  dan feedback jika login backend gagal perlu diverifikasi, tanpa mengubah
  autentikasi/routing Rakha secara sepihak.
- Moodle browser client/token berbeda dengan dokumen moodle-integration.md
  section 3.2/3.3 yang menetapkan boundary backend. Catat perbedaan pada review
  tim sebelum menyatakan kesesuaian arsitektur penuh.
- Issue #72 masih menamai baseline M01. Pilihan tampilan terbaru dan perbedaan
  terhadap M01 perlu dicatat pada laporan/PR; sembilan pemeriksaan presentasi
  bukan verifikasi semua halaman dan semua major state.

Rekomendasi berikutnya: melengkapi preview materi dalam tampilan sekarang, lalu
memverifikasi seluruh major state dan integrasi nyata saat dependensi tersedia.
Belum dilakukan perubahan kode runtime sebagai bagian dari pemeriksaan ini.
