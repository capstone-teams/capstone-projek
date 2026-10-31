# Service frontend

Halaman di src/pages memakai dua boundary service yang dikontrol secara terpisah.

| Modul | Tanggung jawab |
| --- | --- |
| moodle/moodleClient.js | Token Moodle, REST/form transport, invalid-token handler, dan URL file |
| moodle/moodleApi.js | Pemulihan sesi/peran, kursus, peserta, nilai, aktivitas, dan profil |
| moodle/courseEditing.js | Mode edit kursus: aksi `core_courseformat_update_course`, ubah nama `core_update_inplace_editable`, dan URL halaman edit Moodle |
| mock/mockMoodle.js | Fixture Moodle ketika VITE_MOODLE_MOCK=true, termasuk aksi Mode edit (hanya editingteacher) dan `resetMockMoodle()` untuk test |
| apiClient.js | HTTP/mock backend, Bearer token, ApiError, handler 401 bila token ditolak, dan pemeriksaan respons |
| authService.js | Login (`POST /auth/login`), current user (`GET /auth/me`), pemetaan role backend → UI, dan logout client |
| rpsService.js | RPS: validasi file di klien (PDF/DOCX, maks. 20 MB), unggah dengan progres, proses, daftar, dan status enum backend |
| instructorService.js, courseService.js | Setup/preferensi dosen (BE-10) dan workflow backend |
| coursePlanAdapter.js | Normalisasi schema rencana dan alias field pemilih minggu |
| monitoringSocket.js | WebSocket dengan reconnect: event course dan event workflow (`subscribeWorkflowEvents`, design-api §17) |
| mock/ | State machine backend ketika VITE_USE_MOCK=true; auth mengikuti kontrak backend (role huruf besar, pesan error identik, kata sandi `<username>123`) |
| config.js | URL, mode mock, dan kunci penyimpanan dari environment |

AuthProvider login melalui backend (`authService.login` lalu `getCurrentUser`),
kemudian Moodle dengan username dari backend; kegagalan salah satunya membatalkan
login. Peran berasal dari backend, sedangkan hak mengajar per kursus dari Moodle.
Token backend dan Moodle disimpan terpisah dan keduanya diperlukan untuk
memulihkan sesi. apiClient memanggil handler unauthorized hanya bila request
membawa token, sehingga password salah saat login tidak mengakhiri sesi. Guard
generasi sesi mencegah request lama memulihkan sesi atau menyimpan token setelah
logout. Kontrak endpoint: `docs/02. design/auth-api-integration.md`.

Kursus LMS dibaca langsung melalui service Moodle. Generate, approve, review,
execute, dan verify konten AI menggunakan backend HTTP atau shared mock backend.
Transport serta alias payload tetap sama pada kedua mode. Mock backend berada di
memori dan kembali ke fixture awal saat reload.

Login terhadap backend dan publikasi nyata belum diverifikasi pada server yang
berjalan. Akun backend dan Moodle harus memiliki username dan kata sandi yang
sama; keduanya tidak otomatis merupakan satu sistem akun. Lihat [konfigurasi frontend](../../README.md).
