# Frontend — Agentic LMS

Frontend React + JavaScript/JSX dengan Vite, npm, ESLint, React Router, dan Vitest.
Tampilan memakai implemented mockup yang disetujui. Fondasi routing, authentication,
session, hooks, dan service diselaraskan dengan pekerjaan Rakha (`accbc21`).
Data mata kuliah dan workflow feature masih memakai mock.

Keputusan migrasi dan batas integrasi dicatat pada
[laporan penyelarasan](../docs/03.%20quality-plan/frontend-rakha-alignment.md).

Hasil dan dependensi verifikasi FE-04.1 tersedia pada
[laporan verifikasi](../docs/03.%20quality-plan/frontend-foundation-verification.md).

## Prasyarat

- Node.js 22.13+ pada seri 22, atau >=24 (setup ini diverifikasi dengan Node.js 22.16.0).
- npm >=10 (setup ini menggunakan npm 10.9.2).
- Backend tidak diperlukan untuk menjalankan aplikasi dalam mode mock.

## Setup lokal

Dari root repository:

```bash
cd frontend
npm ci
npm run dev
```

Buka http://localhost:3000. Hentikan server dengan Ctrl+C.
Vite menggunakan port 3000 agar sesuai dengan origin development pada `backend/.env.example`.
Jika port sudah digunakan, hentikan proses yang menggunakan port tersebut. Server tidak otomatis berpindah port.

Gunakan `npm ci` untuk instalasi bersih sesuai `package-lock.json`.
Saat sengaja mengubah dependency, gunakan `npm install` lalu sertakan perubahan manifest dan lockfile dalam PR.

## Perintah

| Perintah | Fungsi |
| --- | --- |
| `npm run dev` | Development server dengan hot reload |
| `npm run lint` | Memeriksa JavaScript/JSX, React Hooks, dan Fast Refresh |
| `npm run build` | Menghasilkan build production di `dist/` |
| `npm test` | Vitest: navigasi, lifecycle, session, API client, dan mock workflow |
| `npm run test:e2e` | Menguji halaman dan request state pada browser |
| `npm run test:design` | Membandingkan visual/style dan navigasi dengan approved implemented mockup (#72) |
| `npm run verify:foundation` | Lint, build, unit test, browser test, dan pemeriksaan kesiapan FE-04.1 |
| `npm run preview` | Menyajikan hasil build secara lokal pada port 3000 |

Jalankan preview setelah build dan setelah menghentikan development server. Preview bukan server deployment production.

## Struktur

```text
frontend/
  public/            # Aset statis yang disalin apa adanya
  src/
    assets/          # Aset yang diimpor source code
    components/      # Komponen UI reusable
    hooks/           # Custom React hooks
    features/        # Halaman dan komponen per domain
    services/        # API client, service contract, mock adapter, dan request state
    styles/          # CSS global baseline UI
    utils/           # Fungsi utilitas
    context/         # AuthProvider dan session aplikasi
    App.jsx          # Routing dan komposisi halaman UI yang disetujui
    main.jsx         # Entry point React, BrowserRouter, AuthProvider
  tests/             # Unit test dan browser test (e2e/)
  scripts/           # Pemeriksaan readiness dari hasil browser test
  playwright.config.js # Browser, laporan, dan server pengujian
  index.html         # Dokumen HTML dan mount point
  vite.config.js     # Plugin React, Vitest, dan port server
  eslint.config.js   # Konfigurasi lint
  package.json       # Dependency dan scripts
  package-lock.json  # Versi dependency yang dikunci
```

Folder kosong dilacak dengan `.gitkeep`; hapus placeholder ketika menambahkan file pertama.

## Konfigurasi dan batas integrasi

Mode mock berjalan tanpa `.env`, backend, atau Docker. Akun demo:

| Username | Password | Role |
| --- | --- | --- |
| `dosen` | `dosen123` | Dosen |
| `mahasiswa` | `mahasiswa123` | Mahasiswa |

Password divalidasi. Role berasal dari `/auth/me`; pergantian role dilakukan dengan
logout lalu login ke akun lain. Semua feature page memerlukan session. Materi dapat
dibuka kedua role, sedangkan halaman dosen/mahasiswa memiliki guard masing-masing.
Route `/my` menuju beranda akun, `/ai` menuju halaman dosen, dan route yang tidak
terdaftar menampilkan halaman tidak ditemukan setelah login.

Untuk authentication backend nyata, salin `.env.example` ke `.env.local`, set
`VITE_USE_MOCK=false`, dan sesuaikan `VITE_API_BASE_URL`. Restart Vite. Isi kolom
Username dengan **email** user backend: kontrak login menamai field-nya `username`,
tetapi backend memverifikasi email. Akun demo tidak tersedia pada backend nyata.
Backend perlu berjalan dan mengizinkan origin `http://localhost:3000` pada CORS.

Token aplikasi disimpan oleh AuthProvider pada `agentic-lms.token`. Session dicek
kembali saat reload dan dihapus saat logout atau respons 401. Frontend tidak
mengirim request langsung ke Moodle dan tidak menyimpan token Moodle.
Variabel Vite berawalan `VITE_` masuk ke bundle browser sehingga hanya boleh berisi konfigurasi publik, bukan secret.
Frontend berkomunikasi dengan Backend API; prefix yang tertulis pada spesifikasi adalah `/api/v1`. Credential Moodle dan provider LLM tetap dikelola backend.

## Keputusan awal issue #18 dan perubahan berikutnya

- Setup awal React + TypeScript mengikuti acceptance criteria issue #18.
- Vite dipakai sebagai build tool untuk web client yang terpisah dari backend FastAPI.
- npm dan lockfile digunakan untuk instalasi konsisten antar anggota tim.
- Pada 3 Oktober 2026, pengguna menyetujui penyelarasan dengan source JS/JSX Rakha
  sambil mempertahankan desain yang sudah diimplementasikan. Konfigurasi TypeScript
  diganti dengan lint JS/JSX dan Vitest; CSS Modules yang disetujui dipertahankan.
- React Router dan AuthProvider menangani navigasi dan session. Service async
  memakai hook bersama; feature workflow lokal tetap simulasi UI sampai adapter
  response backend dan endpoint fitur disambungkan.

Acuan: [Vite Getting Started](https://vite.dev/guide/), [System Design](../docs/02.%20design/design-system.md), [API Specification](../docs/02.%20design/design-api.md), dan [aturan kerja](../aturan.md).

## Verifikasi sebelum PR

1. Jalankan `npm ci` pada checkout bersih.
2. Jalankan `npm run verify:foundation`.
3. Periksa laporan HTML di `.cache/playwright/report/index.html` dan laporan verifikasi FE-04.1.
4. Jalankan `npm run dev`, buka http://localhost:3000, dan review UI terhadap baseline yang disetujui.
5. Catat hasil, dependency, dan known blocking issue pada PR yang merujuk issue terkait.

### Browser test FE-04.1

Pada Windows, konfigurasi memakai Microsoft Edge yang sudah terpasang. Pada sistem
lain, pasang Chromium untuk Playwright dengan `npx playwright install chromium`.
Channel dapat dipilih melalui environment variable `PLAYWRIGHT_CHANNEL`, misalnya
`msedge` atau `chrome`; browser tersebut perlu terpasang.

Playwright menjalankan server Vite sendiri di `127.0.0.1:4173` dan menutupnya setelah
tes selesai. Port tersebut harus kosong. Server development port 3000 dapat tetap
berjalan. Browser menggunakan context terisolasi dan service mock tanpa Backend.
Laporan, screenshot, dan trace tersimpan di `.cache/playwright/`, yang diabaikan Git.

Lima kasus authentication/role/route yang sebelumnya expected failure kini menjadi
tes normal. `npm run verify:foundation` mengembalikan exit code 1 jika ada expected
failure, skipped test, regression, atau hasil yang belum lengkap; gate ini tidak
menganggap expected failure sebagai bukti kesiapan.

### Perbandingan desain FE-04.2

Jalankan `npm run test:design` untuk membandingkan source sekarang dengan implemented
mockup yang disetujui pada commit `e9807a530771263dda11f460f59ed77653c6df71`.
Suite ini memeriksa 18 halaman/state/overlay pada tiga viewport, serta alur navigasi
mahasiswa. Screenshot referensi dibuat dari commit baseline, lalu dibandingkan dengan
source saat ini pada browser yang sama. Sebanyak 48 kasus memakai perbandingan
pixel/style penuh; enam kasus login/menu memeriksa perubahan fungsi yang dicatat
di laporan penyelarasan. Alur navigasi mahasiswa menjadi kasus ke-55.

Git, `tar`, dan commit baseline perlu tersedia secara lokal. Dua server Vite memakai
port 4173 dan 4174; kedua port harus kosong. Tidak ada backend atau dependency npm
tambahan. Snapshot dan laporan berada di `.cache/design-conformance/`; buka
`report/index.html` untuk melihat attachment baseline/current. Suite ini terpisah dari
`test:e2e` dan tidak menimpa hasil readiness FE-04.1.

Hasil, cakupan, perubahan tambahan, dan batas verifikasi tersedia pada
[laporan kesesuaian desain](../docs/03.%20quality-plan/frontend-design-conformance.md).

## Troubleshooting: cache npm kehabisan ruang

Jika instalasi menampilkan `ENOSPC` karena drive cache npm penuh, gunakan cache lokal pada drive repository. Dari folder frontend, jalankan di PowerShell:

```powershell
$env:npm_config_cache = Join-Path (Get-Location) '.cache/npm'
$env:TEMP = Join-Path (Get-Location) '.cache/tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
npm ci
```

Pengaturan tersebut hanya berlaku pada sesi terminal itu. Folder `.cache/` sudah diabaikan Git.
