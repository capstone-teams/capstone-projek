# Service frontend

Halaman di `src/pages` berkomunikasi dengan Backend API (Single Gateway) melalui klien HTTP terpusat.

| Modul | Tanggung jawab |
| --- | --- |
| `moodle/moodleClient.js` | Klien Web Service LMS opsional (`VITE_MOODLE_URL`), encoding parameter form, dan URL file |
| `moodle/moodleApi.js` | Fallback ke Backend Gateway (`/integrations/moodle/*`, `/courses/*`) untuk kursus, konten, dan utilitas LMS |
| `moodle/courseEditing.js` | Mode edit kursus (`core_courseformat_update_course`, `core_update_inplace_editable`) saat endpoint tersedia |
| `apiClient.js` | HTTP backend, Bearer token, `ApiError`, handler `401`/`403`, dan pemeriksaan respons |
| `authService.js` | Login (`POST /auth/login`), current user (`GET /auth/me`), pemetaan role backend -> UI, dan logout client |
| `rpsService.js` | RPS: validasi file di klien (PDF, maks. 20 MB), unggah dengan progres, proses, daftar, dan status enum backend |
| `instructorService.js` | Instructor setup (`/instructors/me/setup`) dengan `instructor_profile` untuk preferensi dosen |
| `workflowService.js` | Monitoring workflow, event stream, dan binding course target Moodle |
| `coursePlanService.js` | API course plan per workflow (`/workflows/{id}/plan`) beserta versi dan approval |
| `contentService.js` | API konten mingguan per workflow (`/workflows/{id}/contents`) beserta generasi dan review |
| `executionService.js` | API eksekusi struktur dan konten ke Moodle (`/workflows/{id}/executions`) |
| `coursePlanAdapter.js` | Normalisasi schema rencana dan alias field pemilih minggu |
| `monitoringSocket.js` | WebSocket dengan reconnect, status koneksi (`SOCKET_STATUS`), dan `subscribeWorkflowEvents` |
| `config.js` | `API_BASE_URL`, feature flag opsional, dan kunci penyimpanan lokal |
