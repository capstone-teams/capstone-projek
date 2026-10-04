# Frontend Module

Folder ini berisi *source code*, konfigurasi, dan pengujian untuk aplikasi web frontend yang dibangun menggunakan **React 19**, **Vite**, **React Router**, dan **Tailwind CSS**.

Frontend terdiri dari dua bagian dalam satu aplikasi:

1. **Tampilan Moodle** (dosen & mahasiswa) — dashboard, daftar course, isi course, peserta, nilai, dan aktivitas. Datanya diambil langsung dari **Moodle Web Service**.
2. **Generator Konten AI** (khusus dosen, prefix `/ai`) — unggah & analisis RPS, perencanaan course, generate/review konten, eksekusi ke Moodle, dan verifikasi. Datanya diambil dari **Backend API** (FastAPI, `/api/v1`).

---

## 🏗️ Structure Overview

```text
frontend/
├── public/                       # Aset statis yang disajikan apa adanya
│   └── moodle/mod/               # Ikon aktivitas Moodle (assign, quiz, forum, ...)
├── src/                          # Source code utama aplikasi
│   ├── main.jsx                  # Entry point: StrictMode, BrowserRouter, AuthProvider
│   ├── App.jsx                   # Definisi seluruh route (React Router)
│   ├── pages/                    # Satu komponen per halaman / route
│   │   ├── LoginPage.jsx         # /login (akun Moodle)
│   │   ├── StatusPage.jsx        # NotFoundPage (404) & ForbiddenPage (403)
│   │   ├── moodle/               # Halaman Moodle: /my, /my/courses, /user/profile
│   │   │   └── course/           # /course/:courseId (+ participants, grades, mod/:cmid)
│   │   └── ai/                   # Generator Konten AI: /ai, /ai/rps, /ai/profile, /ai/courses/new
│   │       └── course/           # /ai/courses/:courseId (+ plan, content, review, moodle)
│   ├── components/               # Komponen UI reusable (tanpa pemanggilan API)
│   │   ├── ui.jsx                # Primitif UI: Card, Badge, Alert, Modal, Spinner, Field, ...
│   │   ├── MoodleLayout.jsx      # Layout utama (navbar, drawer) bergaya Moodle
│   │   ├── RequireAuth.jsx       # Route guard: wajib login + pembatasan role
│   │   ├── moodle/               # Komponen spesifik tampilan Moodle (CourseCard, ActivityIcon, MoodleHtml)
│   │   └── *.jsx                 # WorkflowStepper, EventLog, InstructionModal, ActivityConfigFields
│   ├── context/                  # React Context (state global)
│   │   ├── authContext.js        # Objek AuthContext
│   │   └── AuthProvider.jsx      # Sesi login Moodle + login backend untuk dosen
│   ├── hooks/                    # Custom hooks (state, data fetching, polling, WebSocket)
│   │   ├── useApi.js             # useApi (load data) & useAction (POST/PUT + pending/error)
│   │   ├── useAuth.js            # Akses AuthContext
│   │   ├── usePolling.js         # Polling berkala selama kondisi aktif
│   │   ├── useCourseEvents.js    # Berlangganan event real-time course
│   │   ├── useCourse.js          # Outlet context course AI
│   │   ├── useMoodleCourse.js    # Outlet context course Moodle
│   │   └── useLatest.js          # Ref ke nilai terbaru (hindari stale closure)
│   ├── services/                 # Akses data: HTTP client, endpoint API, integrasi Moodle
│   │   ├── config.js             # Konfigurasi runtime dari variabel VITE_*
│   │   ├── apiClient.js          # Satu pintu request ke Backend API (+ ApiError, token)
│   │   ├── authService.js        # POST /auth/login, GET /auth/me
│   │   ├── rpsService.js         # Endpoint RPS
│   │   ├── courseService.js      # Endpoint course, plan, content, review, execution, verification
│   │   ├── profileService.js     # Endpoint profil mengajar dosen
│   │   ├── monitoringSocket.js   # WebSocket event course (+ reconnect)
│   │   ├── moodle/               # Integrasi Moodle Web Service
│   │   │   ├── moodleClient.js   # login/token.php & webservice/rest/server.php (+ MoodleError)
│   │   │   ├── moodleApi.js      # Fungsi WS per kebutuhan halaman + resolveSession (role)
│   │   │   └── mockMoodle.js     # Moodle dummy di browser
│   │   └── mock/                 # Backend dummy di browser (kontrak sama dengan design-api)
│   │       ├── mockServer.js
│   │       └── mockData.js
│   ├── styles/                   # CSS global & Tailwind (global.css, moodle-icon-filters.css)
│   ├── utils/                    # Helper murni (format tanggal/ukuran, label status workflow)
│   └── assets/                   # Aset yang di-import dari kode
├── tests/                        # Automated tests (Vitest + jsdom)
│   ├── apiClient.test.js         # Request, error mapping, token
│   ├── moodleClient.test.js      # Encoding parameter & panggilan Moodle WS
│   ├── workflow.test.js          # Alur service end-to-end terhadap mock backend
│   └── pages.test.jsx            # Render halaman, routing, dan guard role
├── .env.example                  # Contoh variabel environment (salin ke .env.local)
├── index.html                    # HTML entry Vite
├── vite.config.js                # Konfigurasi Vite, proxy /api, dan Vitest
├── eslint.config.js              # Konfigurasi ESLint
├── package.json                  # Dependensi & script npm
└── README.md                     # Dokumentasi arsitektur frontend
```

---

## 🔀 Aliran Dependency Antar-Layer (Dependency Flow)

Setiap interaksi user melewati layer secara berurutan. Panah di bawah menunjukkan arah pemanggilan yang **diizinkan**:

```text
                       Browser / URL
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/App.jsx                 │
              │  Routing + RequireAuth guard │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/pages/                  │
              │  Halaman (komposisi UI +     │
              │  memanggil hooks/services)   │
              └──────────────────────────────┘
                 │                       │
                 ▼                       ▼
  ┌──────────────────────────┐  ┌──────────────────────────┐
  │  src/components/         │  │  src/hooks/ + context/   │
  │  UI reusable             │  │  State & data fetching   │
  └──────────────────────────┘  └──────────────────────────┘
                                         │
                                         ▼
              ┌──────────────────────────────┐
              │  src/services/               │
              │  Akses data (API & Moodle)   │
              └──────────────────────────────┘
                 │                       │
                 ▼                       ▼
  ┌──────────────────────────┐  ┌──────────────────────────┐
  │  apiClient.js            │  │  moodle/moodleClient.js  │
  │  → Backend API /api/v1   │  │  → Moodle Web Service    │
  │  (atau mock/ bila        │  │  (atau mockMoodle.js     │
  │   VITE_USE_MOCK=true)    │  │   bila VITE_MOODLE_MOCK) │
  └──────────────────────────┘  └──────────────────────────┘
```

Poin penting:

1. Dependency hanya boleh mengalir **satu arah (turun)**. Layer bawah **dilarang** mengimpor layer di atasnya (contoh: `services/` tidak boleh mengimpor `hooks/`, `components/`, atau `pages/`).
2. **Tidak ada `fetch` di luar `services/`.** Semua request ke Backend API lewat `apiClient.js`, semua request ke Moodle lewat `moodleClient.js`.
3. Pages boleh memanggil fungsi service langsung (dibungkus `useApi` / `useAction`); hooks khusus dibuat hanya jika logikanya dipakai ulang (polling, WebSocket, outlet context).
4. **Mode mock transparan bagi UI.** Pemilihan mock vs server sungguhan hanya terjadi di `apiClient.js`, `monitoringSocket.js`, dan `moodleClient.js`; pages dan components tidak tahu sedang memakai mock atau tidak.

---

## 🔒 Aturan Import Antar-Layer

| Layer | BOLEH Mengimpor | DILARANG Mengimpor |
| :--- | :--- | :--- |
| **`src/pages/`** | `components/`, `hooks/`, `services/` (fungsi endpoint & konstanta), `utils/`, `react-router-dom` | `services/mock/`, `services/moodle/mockMoodle.js`, `fetch` langsung, page lain (kecuali layout) |
| **`src/components/`** | `components/` lain, `hooks/`, `utils/`, `services/config.js`, helper URL dari `moodleClient.js` (`withToken`, `moodleUrl`) | Fungsi service yang memanggil API (`courseService`, `moodleApi`, ...), `pages/` |
| **`src/hooks/`** | `context/`, `services/`, `hooks/` lain, `utils/` | `components/`, `pages/` |
| **`src/context/`** | `services/`, `utils/` | `components/`, `pages/` |
| **`src/services/`** | `services/config.js`, service lain di dalam `services/`, `services/mock/` (hanya di client & socket) | `react`, `hooks/`, `context/`, `components/`, `pages/` |
| **`src/services/mock/`** | `mock/mockData.js` | Seluruh layer aplikasi lain |
| **`src/utils/`** | library standar / library murni | Seluruh layer aplikasi (`pages/`, `components/`, `hooks/`, `services/`) |

Catatan tambahan:

- `src/services/` adalah **satu-satunya** layer yang boleh memegang token, URL backend/Moodle, dan memanggil `fetch` / `WebSocket`.
- `src/services/` tidak boleh menampilkan UI (alert, redirect). Error dilempar sebagai `ApiError` (Backend API) atau `MoodleError` (Moodle), lalu ditampilkan oleh page lewat `<ErrorAlert>`.
- Pengecualian yang disengaja: `RequireAuth.jsx` merender `ForbiddenPage` dari `pages/StatusPage.jsx` saat role tidak diizinkan.

---

## 🎯 Tanggung Jawab Setiap Layer (Separation of Concerns)

| Layer / Direktori | Responsibilitas Utama | Yang BOLEH Dilocate | Yang TIDAK BOLEH Dilocate |
| :--- | :--- | :--- | :--- |
| **`src/main.jsx`** | Application Entry Point | Mount React, `BrowserRouter`, provider global (`AuthProvider`), import CSS global. | Definisi route, logika halaman. |
| **`src/App.jsx`** | Routing | Pohon route, layout bersarang, pemasangan `RequireAuth` (termasuk `roles`). | Data fetching, markup halaman. |
| **`src/pages/`** | Halaman per route | Komposisi komponen, memanggil service via `useApi` / `useAction`, membaca `useParams` / outlet context, validasi form sisi klien (format/ukuran file). | `fetch` langsung, membangun URL API, menyimpan token, logika mock. |
| **`src/components/`** | UI reusable | Komponen presentasional yang menerima data lewat props, layout, route guard. | Pemanggilan API, state data domain milik halaman tertentu. |
| **`src/context/`** | State global | Sesi login (user, site, role), aksi `login` / `logout`. | Data per halaman, markup UI. |
| **`src/hooks/`** | Logika stateful reusable | Data fetching generik, polling, langganan WebSocket, akses context. | Markup / JSX, URL endpoint. |
| **`src/services/`** | Akses data & integrasi | Endpoint Backend API, fungsi Moodle WS, mapping error, penyimpanan token, mock. | React (state, hooks, JSX), teks/notifikasi UI. |
| **`src/utils/`** | Shared Utilities | Fungsi murni tanpa side-effect: format tanggal/ukuran, label & tone status workflow. | State aplikasi, pemanggilan API. |
| **`src/styles/`** | Styling global | Tailwind (`@import "tailwindcss"`), token warna/tema, CSS global. | Style yang hanya dipakai satu komponen (pakai class Tailwind di JSX). |
| **`tests/`** | Automated tests | Unit test service/util, render test halaman dengan mock aktif. | Ketergantungan ke server Moodle/backend sungguhan. |

---

## ⚠️ Aturan Pencegahan Duplikasi Layer

1. **`services/` vs `hooks/`**:
   - `services/` **hanya** berisi fungsi async biasa (tanpa React) yang mengembalikan data atau melempar error.
   - `hooks/` mengelola state React di sekitar pemanggilan tersebut (loading, error, polling).
   - **Dilarang** memanggil `useState` / `useEffect` di dalam `services/`, atau menulis `fetch` di dalam `hooks/`.

2. **`pages/` vs `components/`**:
   - Komponen yang dipakai di lebih dari satu halaman dipindahkan ke `components/`.
   - Komponen di `components/` menerima data lewat props; pengambilan data tetap di page.

3. **Backend API vs Moodle**:
   - Data course/peserta/nilai/aktivitas Moodle diambil dari `services/moodle/moodleApi.js`.
   - Data Generator Konten AI (RPS, plan, konten, eksekusi) diambil dari `rpsService.js`, `courseService.js`, `profileService.js`.
   - **Dilarang** memanggil Moodle dari service backend atau sebaliknya.

4. **`utils/` vs `services/`**:
   - Label dan tone status (`STATUS_LABELS`, `statusTone`, `describeEvent`) berada di `utils/workflow.js`, bukan di halaman.
   - Format tanggal/ukuran berada di `utils/format.js`; jangan memformat ulang di setiap halaman.

---

## 🌐 Akses Data

### Backend API (`services/apiClient.js`)

Seluruh endpoint Backend API dipanggil lewat objek `api`:

```js
// src/services/rpsService.js
import { api } from './apiClient';

export function getRps(rpsId) {
  return api.get(`/rps/${rpsId}`);
}
```

| Fitur | Keterangan |
| :--- | :--- |
| Base URL | `VITE_API_BASE_URL` (default `/api/v1`); saat development `/api` di-proxy Vite ke `VITE_BACKEND_URL` sehingga tidak perlu CORS |
| Token | Disimpan di `localStorage` (`agentic-lms.token`) dan dikirim sebagai `Authorization: Bearer <token>` |
| Error | Response `{ "error": { "code", "message", "details" } }` (design-api §18) diubah menjadi `ApiError(status, code, message, details)`; gagal jaringan → `NETWORK_ERROR` |
| 401 | Memanggil handler `onUnauthorized` agar sesi dapat di-logout |
| Idempotency | `idempotencyHeader()` menambahkan `Idempotency-Key` untuk operasi yang idempoten (design-api §21) |
| Resource opsional | `.catch(nullOn404)` mengubah 404 menjadi `null` ("belum ada"), bukan error |
| Real-time | `subscribeCourseEvents(courseId, onEvent)` di `monitoringSocket.js` (design-api §17), reconnect otomatis dengan backoff maksimal 15 detik |

### Moodle Web Service (`services/moodle/`)

| Komponen | Keterangan |
| :--- | :--- |
| `requestToken(username, password)` | `POST {VITE_MOODLE_URL}/login/token.php` dengan layanan `VITE_MOODLE_SERVICE` |
| `callWs(wsfunction, params)` | `POST /webservice/rest/server.php`; parameter bersarang di-encode ke format form Moodle (`courseids[0]=2`) |
| `withToken(url)` | Menambahkan token pada URL `pluginfile.php` agar file Moodle dapat dibuka |
| `moodleUrl(path)` | URL absolut ke halaman Moodle asli (tombol "Buka di Moodle") |
| `MoodleError` | Error dari Moodle (`errorcode`, `message`); `invalidtoken` otomatis me-logout sesi |

Fungsi WS yang dipakai halaman ditulis di `moodleApi.js` (satu fungsi per kebutuhan, mis. `getUserCourses`, `getCourseContents`, `getGradeItems`). Halaman **tidak** memanggil `callWs` secara langsung.

---

## 🔐 Authentication & Role

Login memakai **akun Moodle**. Alurnya:

```text
LoginPage → AuthProvider.login(username, password)
   → moodleClient.requestToken()       (login/token.php)
   → moodleApi.resolveSession()        (site info + role)
   → simpan token Moodle (localStorage: agentic-lms.moodle-session)
   → bila role = dosen: authService.login() ke Backend API (gagal tidak menghalangi akses Moodle)
```

Role ditentukan oleh `resolveSession()` dari data Moodle, **bukan** dari input user:

| Role | Kondisi |
| :--- | :--- |
| `dosen` | Admin situs, atau memiliki opsi administrasi pengajar (`update`, `reports`, `backup`, `gradebook`) di minimal satu course |
| `mahasiswa` | Selain kondisi di atas |

### Melindungi route

```jsx
// src/App.jsx
<Route element={<RequireAuth />}>                       {/* wajib login */}
  <Route path="my" element={<DashboardPage />} />

  <Route element={<RequireAuth roles={['dosen']} />}>   {/* khusus dosen */}
    <Route path="ai" element={<AiLayout />}>...</Route>
  </Route>
</Route>
```

| Kondisi | Hasil |
| :--- | :--- |
| Sesi sedang dipulihkan dari `localStorage` | Spinner "Menghubungkan ke Moodle…" |
| Belum login | Redirect ke `/login` (lokasi asal disimpan di `state.from`) |
| Role tidak termasuk `roles` | `ForbiddenPage` (403) |

Membaca user di komponen:

```jsx
import { useAuth } from '../hooks/useAuth';

const { user, logout } = useAuth(); // user.role: 'dosen' | 'mahasiswa'
```

> **Catatan:** pembatasan role di frontend hanya untuk tampilan. Keamanan sesungguhnya tetap ditegakkan backend (401 `AUTHENTICATION_FAILED` / 403 `AUTHORIZATION_DENIED`) dan Moodle.

---

## 🧪 Mode Mock

Frontend dapat dijalankan **tanpa Moodle dan tanpa backend**. Mock meniru kontrak `docs/02. design/design-api.md` (path, payload, kode error, operasi async 202 + agent run + event WebSocket, dan transisi status workflow §20). Data hanya di memori dan hilang saat halaman di-reload.

| Variabel | Default | `true` | `false` |
| :--- | :--- | :--- | :--- |
| `VITE_MOODLE_MOCK` | `true` | Moodle dummy (`services/moodle/mockMoodle.js`) | Moodle sungguhan di `VITE_MOODLE_URL` |
| `VITE_USE_MOCK` | `true` | Backend dummy (`services/mock/mockServer.js`) | FastAPI lewat `VITE_API_BASE_URL` |

Akun Moodle dummy (password = `<username>123`):

| Username | Password | Role |
| :--- | :--- | :--- |
| `dosen` / `dosen2` | `dosen123` / `dosen2123` | dosen |
| `mahasiswa` / `mahasiswa2` / `mahasiswa3` | `mahasiswa123` / ... | mahasiswa |

---

## ✅ Contoh Penerapan Boundary (Benar vs Salah)

**1. Page — benar (memanggil service lewat hook, menampilkan state):**

```jsx
// src/pages/ai/RpsAnalysisPage.jsx  ✅ (disederhanakan)
import { useParams } from 'react-router-dom';
import { getRpsAnalysis } from '../../services/rpsService';
import { useApi } from '../../hooks/useApi';
import { ErrorAlert, Spinner } from '../../components/ui';

export default function RpsAnalysisPage() {
  const { rpsId } = useParams();
  const { data, error, loading } = useApi(() => getRpsAnalysis(rpsId), [rpsId]);

  if (loading) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;
  return <AnalysisView analysis={data} />;
}
```

**Page — salah (fetch, URL, dan token ditulis di halaman):**

```jsx
// src/pages/ai/RpsAnalysisPage.jsx  ❌
useEffect(() => {
  fetch(`http://localhost:8000/api/v1/rps/${rpsId}/analysis`, {   // URL hard-coded
    headers: { Authorization: `Bearer ${localStorage.getItem('agentic-lms.token')}` },
  })
    .then((r) => r.json())
    .then(setData)
    .catch(() => alert('Gagal'));                                  // error tidak lewat ApiError
}, [rpsId]);
```

**2. Aksi (POST/PUT) — benar (`useAction` di page, header `Idempotency-Key` di service):**

```jsx
// src/pages/ai/course/CourseReviewPage.jsx  ✅ (disederhanakan)
const approve = useAction(() => approveContent(course.id));
...
<ErrorAlert error={approve.error} onClose={approve.clearError} />
<button disabled={approve.pending} onClick={() => approve.run().then(refresh)}>Setujui</button>
```

```js
// src/services/courseService.js  ✅
export function executeCourse(courseId) {
  return api.post(`/courses/${courseId}/execute`, undefined, { headers: idempotencyHeader() });
}
```

**3. Component — benar (presentasional, data dari props):**

```jsx
// src/components/moodle/CourseCard.jsx  ✅
export default function CourseCard({ course, isTeacher }) { ... }
```

**Component — salah (mengambil data sendiri):**

```jsx
// src/components/moodle/CourseCard.jsx  ❌
export default function CourseCard({ courseId }) {
  const { data } = useApi(() => getCourse(courseId), [courseId]); // fetching milik page
  ...
}
```

---

## 🧾 Checklist Review Boundary Layer

Gunakan checklist ini saat me-review PR frontend:

- [ ] Tidak ada `fetch` / `WebSocket` / URL backend atau Moodle di luar `src/services/`.
- [ ] Endpoint baru ditambahkan sebagai fungsi di service yang sesuai (`rpsService`, `courseService`, `moodleApi`, ...), dan mock-nya diperbarui di `services/mock/` atau `mockMoodle.js`.
- [ ] Page menampilkan state loading (`<Spinner>`), error (`<ErrorAlert>`), dan kosong (`<EmptyState>`).
- [ ] Komponen di `components/` tidak memanggil API dan menerima data lewat props.
- [ ] Route baru yang khusus dosen berada di bawah `<RequireAuth roles={['dosen']} />`.
- [ ] Label status & format tanggal memakai `utils/`, bukan ditulis ulang di halaman.
- [ ] Layer bawah tidak mengimpor layer di atasnya.
- [ ] `npm run lint`, `npm test`, dan `npm run build` lulus.

---

## 🛠️ Workflow Pengembangan & Testing

### 1. Instalasi Dependensi

```bash
npm install

# Menambah dependensi baru
npm install <package-name>
npm install -D <package-name>   # devDependency
```

### 2. Konfigurasi Environment

```bash
cp .env.example .env.local
```

| Variabel | Default | Keterangan |
| :--- | :--- | :--- |
| `VITE_MOODLE_URL` | `http://localhost:8080` | Alamat Moodle (`$CFG->wwwroot`) |
| `VITE_MOODLE_SERVICE` | `moodle_mobile_app` | Layanan web service untuk `login/token.php` |
| `VITE_MOODLE_MOCK` | `true` | Pakai Moodle dummy |
| `VITE_USE_MOCK` | `true` | Pakai backend dummy |
| `VITE_API_BASE_URL` | `/api/v1` | Base path Backend API |
| `VITE_BACKEND_URL` | `http://localhost:8000` | Target proxy `/api` (dan WebSocket) saat `npm run dev` |

Untuk memakai Moodle sungguhan, aktifkan *Site administration > General > Mobile app > Enable web services for mobile devices* di instance Moodle.

> Variabel `VITE_*` ikut ter-bundle ke browser dan **dapat dibaca siapa pun**. Jangan menaruh secret di sini.

### 3. Jalankan Server Development

```bash
npm run dev          # http://localhost:3000
```

Untuk menghubungkan ke backend sungguhan, jalankan backend (lihat `backend/README.md`) lalu set `VITE_USE_MOCK=false`.

### 4. Lint, Test, dan Build

Seluruh perintah berikut harus lulus sebelum membuat Pull Request:

```bash
npm run lint         # ESLint
npm test             # Vitest (jsdom) — tests/**/*.test.{js,jsx}
npm run build        # Build produksi ke dist/
npm run preview      # Menyajikan hasil build secara lokal
```

Test selalu berjalan dengan `VITE_MOODLE_MOCK=true` dan `VITE_USE_MOCK=true` (diatur di `vite.config.js`), sehingga tidak membutuhkan server Moodle maupun backend.
