# Frontend — Agentic LMS

Frontend React + TypeScript dengan Vite, npm, dan ESLint. Branch ini memuat
baseline UI yang disetujui dan service foundation FE-03.2. Data serta workflow
feature masih memakai mock; authentication/session foundation belum terintegrasi.

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
| `npm run typecheck` | Memeriksa TypeScript untuk source dan konfigurasi Vite |
| `npm run lint` | Memeriksa TypeScript, React Hooks, dan Fast Refresh |
| `npm run build` | Memeriksa TypeScript dan menghasilkan build di `dist/` |
| `npm test` | Menguji helper navigasi, lifecycle, mock data, dan API client |
| `npm run test:e2e` | Menguji halaman dan request state pada browser |
| `npm run verify:foundation` | Lint, build/typecheck, unit test, browser test, dan pemeriksaan kesiapan FE-04.1 |
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
    App.tsx          # Root component
    main.tsx         # Entry point React
  tests/             # Unit test dan browser test (e2e/)
  scripts/           # Pemeriksaan readiness dari hasil browser test
  playwright.config.ts # Browser, laporan, dan server pengujian
  index.html         # Dokumen HTML dan mount point
  vite.config.ts     # Plugin React dan port server
  tsconfig*.json     # Konfigurasi TypeScript strict
  eslint.config.js   # Konfigurasi lint
  package.json       # Dependency dan scripts
  package-lock.json  # Versi dependency yang dikunci
```

Folder kosong dilacak dengan `.gitkeep`; hapus placeholder ketika menambahkan file pertama.

## Konfigurasi dan batas integrasi

Mode mock belum membutuhkan file `.env` atau credential. Bila integrasi API ditambahkan, dokumentasikan variabelnya dan sediakan `.env.example` pada modul yang menggunakannya.
Variabel Vite berawalan `VITE_` masuk ke bundle browser sehingga hanya boleh berisi konfigurasi publik, bukan secret.
Frontend berkomunikasi dengan Backend API; prefix yang tertulis pada spesifikasi adalah `/api/v1`. Credential Moodle dan provider LLM tetap dikelola backend.

## Keputusan implementasi issue #18

- React + TypeScript mengikuti acceptance criteria issue.
- Vite dipakai sebagai build tool untuk web client yang terpisah dari backend FastAPI.
- npm dan lockfile digunakan untuk instalasi konsisten antar anggota tim.
- CSS biasa digunakan untuk placeholder. Library UI, routing, dan state management ditambahkan ketika kebutuhan fitur sudah jelas.
- Struktur mengikuti baseline README frontend sebelumnya; TypeScript menggunakan mode strict.

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

Lima tes authentication/role/route saat ini ditandai sebagai expected failure dengan
alasan dependensi FE-02/FE-03.1. `npm run test:e2e` dapat berhasil ketika kegagalan
tersebut sesuai ekspektasi Playwright. **Hal itu belum berarti foundation siap.**
`npm run verify:foundation` tetap mengembalikan exit code 1 ketika ada expected
failure, skipped test, regression, atau hasil yang belum lengkap. Setelah dependency
terintegrasi, hapus marker expected failure dan jalankan seluruh verifikasi lagi.

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
