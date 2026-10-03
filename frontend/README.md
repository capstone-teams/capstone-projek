# Frontend — Agentic LMS

Fondasi frontend untuk issue #18: React + TypeScript dengan Vite, npm, dan ESLint.
Halaman awal merupakan placeholder; application shell sesuai Figma dikerjakan pada issue #19 dan verifikasi desain pada issue #20.

## Prasyarat

- Node.js 22.13+ pada seri 22, atau >=24 (setup ini diverifikasi dengan Node.js 22.16.0).
- npm >=10 (setup ini menggunakan npm 10.9.2).
- Backend tidak diperlukan untuk menjalankan halaman awal.

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
    pages/           # Komponen halaman; HomePage adalah placeholder awal
    services/        # Integrasi Backend API pada pengembangan berikutnya
    styles/          # CSS global; styling awal belum merupakan design system Figma
    utils/           # Fungsi utilitas
    App.tsx          # Root component
    main.tsx         # Entry point React
  tests/             # Lokasi pengujian ketika fitur mulai ditambahkan
  index.html         # Dokumen HTML dan mount point
  vite.config.ts     # Plugin React dan port server
  tsconfig*.json     # Konfigurasi TypeScript strict
  eslint.config.js   # Konfigurasi lint
  package.json       # Dependency dan scripts
  package-lock.json  # Versi dependency yang dikunci
```

Folder kosong dilacak dengan `.gitkeep`; hapus placeholder ketika menambahkan file pertama.

## Konfigurasi dan batas integrasi

Setup awal belum membutuhkan file `.env` atau credential. Bila integrasi API ditambahkan, dokumentasikan variabelnya dan sediakan `.env.example` pada modul yang menggunakannya.
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
2. Jalankan `npm run lint`, `npm run typecheck`, dan `npm run build`.
3. Jalankan `npm run dev`, buka http://localhost:3000, dan pastikan halaman Agentic LMS muncul tanpa error browser.
4. Pastikan perubahan source memperbarui tampilan melalui hot reload.
5. Catat hasil verifikasi pada PR ke `develop` yang merujuk issue #18.

Unit test belum ditambahkan karena halaman awal hanya berisi konten statis tanpa logic fitur.

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
