# Service aktif mengikuti Rakha

Acuan: `origin/feature/frontend-setup` pada commit `accbc21`.

- `moodle/moodleClient.js`: token Moodle dan Web Service transport.
- `moodle/moodleApi.js`: session/peran, kursus, peserta, nilai, aktivitas, profil.
- `moodle/mockMoodle.js`: fixture Moodle ketika VITE_MOODLE_MOCK=true.
- `apiClient.js`: facade HTTP/mock backend, Bearer token, ApiError.
- `authService.js`: login backend terpisah untuk fitur AI.
- `rpsService.js`, `profileService.js`, `courseService.js`: fitur backend aktif.
- `monitoringSocket.js`: event workflow yang digunakan layout project.
- `mock/`: state machine backend ketika VITE_USE_MOCK=true.

AuthProvider login melalui Moodle lalu mencoba backend untuk akun dosen.
Seluruh halaman aktif di src/pages memanggil service Rakha; tidak ada adapter
presentation fixture tambahan. Aksi generate/approve/review/execute/verify
menggunakan shared mock backend atau HTTP sesuai flag.

File `index.js`, `mockCourseService.js`, `apiError.js`, `useServiceResource.js`
dan `ServiceStatus.jsx` adalah implementasi sebelumnya yang tidak dipakai runtime
aktif. Jangan gunakan facade itu untuk fitur baru. File dipertahankan sebagai
referensi agar pekerjaan sebelumnya tetap tersedia.

Login Moodle dan backend nyata belum diuji. Khusus backend, credential dan role
perlu cocok dengan server capstone; provider Rakha tidak menjamin dua sistem akun
tersebut otomatis sama. Mock backend hilang saat reload.
