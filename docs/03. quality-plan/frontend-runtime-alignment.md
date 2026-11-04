# Riwayat penyelarasan runtime frontend

Tanggal: 3 Oktober 2026. Branch: `refactor/frontend-foundation-alignment`.
Laporan historis; hasil di bawah berlaku untuk revisi yang disebutkan, bukan hasil
verifikasi working tree terkini.

## Revisi dan perilaku

Baseline runtime: `origin/feature/frontend-setup`, commit
`accbc21035d378c5d3d9775728354ce2093bf244`. Referensi tampilan sebelumnya:
`e9807a530771263dda11f460f59ed77653c6df71`. Penyelarasan pada `f3b0a38`
menggantikan integrasi selektif `713f886`.

Routing dan halaman memakai provider sesi Moodle, service backend AI, serta dua
mock independen. Login meminta token Moodle, menentukan role dari hak akses
kursus, lalu mencoba login backend untuk dosen. Kegagalan backend tidak memblokir
Moodle. Rute lama tidak dibuat alias. Header akun, login dua panel, kartu kursus,
warna, dan spacing menggunakan presentasi aplikasi yang dipertahankan.

Pada revisi tersebut controller/facade lama masih tersimpan tanpa dipakai routing.
Implementasi itu dihapus dalam refactor pembersihan; riwayatnya tersedia di Git.
Sesi, rute, endpoint, role, dan alias payload dipertahankan saat pembersihan.

## Bukti verifikasi historis

| Pemeriksaan pada f3b0a38 | Hasil |
| --- | --- |
| Lint | Lulus, tanpa error/warning |
| Build | Lulus, 83 modules; warning dynamic import Moodle |
| Unit | 50 tes lulus, 4 file |
| Browser runtime | 17 tes lulus, tanpa skip/expected failure |
| Presentasi | 9 tes lulus pada 375/768/1440 px |
| Perbandingan source | 54 file identik dengan baseline setelah normalisasi newline; 6 berbeda untuk presentasi |

Enam file presentasi: MoodleLayout, CourseCard, LoginPage, Moodle CourseLayout,
Moodle DashboardPage, dan global.css. Perbandingan source hanya menjelaskan
snapshot f3b0a38; perbaikan sesi #71 mengubah sebagian runtime setelah itu.

Screenshot lokal direkam pada frontend/.cache/review-1440-login.png,
review-1440-dashboard.png, review-1440-content.png, dan review-375-content.png.
Pengujian memakai Chrome terisolasi dan mock. Sembilan tes presentasi memeriksa
style/batas konten, bukan kesamaan pixel atau semua halaman/state. Hasil suite
historis 86 unit/32 browser/55 desain berasal dari revisi lain.

## Batas arsitektur dan kebutuhan lanjutan

Pemeriksaan pada `5fab886` menemukan UI untuk upload/analisis RPS, preferensi,
prompt, konfigurasi aktivitas, rencana/approval, generation/review, monitoring,
eksekusi/verifikasi, dan akses mahasiswa. Preview week.materials/body_markdown
belum dirender oleh halaman konten; kebutuhan FR-042/FR-043/AC-006 belum tercakup.

Backend lokal pada pemeriksaan itu hanya meregistrasikan health/auth/admin;
endpoint workflow AI belum tersedia. Backend menerima email sebagai identitas
login, sedangkan provider mencoba credential Moodle. Kesesuaian akun, real AI,
persistensi, publikasi Moodle, dan akses mahasiswa ke hasil publikasi yang sama
belum diverifikasi end-to-end.

Browser membaca Moodle langsung, berbeda dari boundary backend pada
moodle-integration.md §3.2/3.3. Mode mock tidak membuktikan kesesuaian arsitektur
atau integrasi nyata. Tampilan aplikasi merupakan acuan pekerjaan berikutnya,
bukan klaim bahwa seluruh MVP sudah selesai.

Perbaikan #71 menambahkan guard untuk respons sesi/token lama dan error JSON
backend. Bukti serta batasnya tercatat pada
[laporan foundation](frontend-foundation-verification.md). Hasil #74 dicatat pada
[laporan Course Plan](frontend-course-plan-screen.md). Setup dan suite aktif ada
di [README frontend](../../frontend/README.md).
