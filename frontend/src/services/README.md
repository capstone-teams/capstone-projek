# Service frontend

Halaman di src/pages memakai dua boundary service yang dikontrol secara terpisah.

| Modul | Tanggung jawab |
| --- | --- |
| moodle/moodleClient.js | Token Moodle, REST/form transport, invalid-token handler, dan URL file |
| moodle/moodleApi.js | Pemulihan sesi/peran, kursus, peserta, nilai, aktivitas, dan profil |
| moodle/mockMoodle.js | Fixture Moodle ketika VITE_MOODLE_MOCK=true |
| apiClient.js | HTTP/mock backend, Bearer token, ApiError, dan pemeriksaan respons |
| authService.js | Login backend terpisah untuk fitur AI |
| rpsService.js, profileService.js, courseService.js | RPS, preferensi, dan workflow backend |
| coursePlanAdapter.js | Normalisasi schema rencana dan alias field pemilih minggu |
| monitoringSocket.js | Event workflow dan reconnect WebSocket |
| mock/ | State machine backend ketika VITE_USE_MOCK=true |
| config.js | URL, mode mock, dan kunci penyimpanan dari environment |

AuthProvider login melalui Moodle lalu mencoba backend untuk akun dosen. Token
Moodle dan backend disimpan terpisah; kegagalan backend ditampilkan melalui state
global tanpa menggagalkan sesi Moodle. Guard generasi sesi mencegah request lama
memulihkan sesi atau menyimpan token setelah logout.

Kursus LMS dibaca langsung melalui service Moodle. Generate, approve, review,
execute, dan verify konten AI menggunakan backend HTTP atau shared mock backend.
Transport serta alias payload tetap sama pada kedua mode. Mock backend berada di
memori dan kembali ke fixture awal saat reload.

Login dan publikasi nyata belum diverifikasi. Identitas login serta role Moodle
dan backend harus sesuai dengan server masing-masing; keduanya tidak otomatis
merupakan satu sistem akun. Lihat [konfigurasi frontend](../../README.md).
