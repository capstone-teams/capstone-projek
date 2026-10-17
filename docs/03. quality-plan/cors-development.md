# CORS & Frontend Development Access

**Issue:** BE-06.2 (parent BE-06) · **Status:** tersedia di development ·
**Implementasi:** `src/middlewares/cors.py`, `src/config/settings.py` ·
**Pengujian:** `tests/test_cors.py`, `tests/test_config.py`

Dokumen ini menjelaskan cara frontend development mengakses API backend tanpa
error CORS, konfigurasi environment yang dipakai, dan cara memverifikasinya.

---

## 1. Alamat development

| Komponen | Alamat |
| :--- | :--- |
| Backend API | `http://localhost:8000/api/v1` |
| Swagger UI | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |
| Frontend Vite | `http://localhost:3000` |
| Moodle (opsional) | `http://localhost:8080` |

Frontend dan backend berada pada **origin berbeda** (port berbeda), sehingga
browser menerapkan aturan CORS. Origin default yang diizinkan backend:

- `http://localhost:3000`
- `http://127.0.0.1:3000`

Jika `APP_PORT` Docker diubah (mis. `APP_PORT=8001`), base URL backend ikut
berubah menjadi `http://localhost:8001/api/v1`; origin frontend tetap
`http://localhost:3000` kecuali port Vite juga diubah.

---

## 2. Konfigurasi backend

`CORS_ORIGINS` dibaca dari environment (lihat `backend/.env.example`):

```dotenv
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

Format yang diterima:

- JSON array: `["http://localhost:3000", "http://127.0.0.1:3000"]`
- daftar dipisah koma: `http://localhost:3000,http://127.0.0.1:3000`
- string kosong: tidak ada origin yang diizinkan (bukan wildcard)

Aturan validasi (gagal saat **startup**, bukan saat preflight pertama):

| Nilai | Hasil |
| :--- | :--- |
| `http://localhost:3000/` | Diterima dan dinormalisasi menjadi `http://localhost:3000` |
| `HTTP://LOCALHOST:3000` | Dinormalisasi menjadi `http://localhost:3000` |
| Duplikat | Dihapus, urutan pertama dipertahankan |
| `*` | **Ditolak** — origin harus eksplisit |
| `http://localhost:3000/api` | **Ditolak** — origin tidak boleh memuat path |
| `localhost:3000` | **Ditolak** — scheme wajib ada |
| `ftp://localhost:3000` | **Ditolak** — hanya `http`/`https` |
| JSON array tidak valid | **Ditolak** |

Setelah mengubah `.env`, restart server (`uvicorn --reload` memuat ulang saat
file kode berubah; perubahan environment sebaiknya diikuti restart proses).
Pada Docker Compose, nilai dapat ditimpa dari shell:

```bash
CORS_ORIGINS='["http://localhost:3000","http://localhost:4173"]' \
  docker compose up -d backend
```

Origin production **tidak** di-hardcode di repository; nilainya ditentukan pada
environment deployment.

---

## 3. Konfigurasi frontend

Salin `frontend/.env.example` ke `frontend/.env.local`.

### Mode default — proxy Vite (tanpa CORS)

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_URL=http://localhost:8000
```

Vite meneruskan `/api/*` ke `VITE_BACKEND_URL` (lihat `frontend/vite.config.js`).
Dari sudut pandang browser, request menuju origin frontend sendiri
(`http://localhost:3000/api/...`) sehingga tidak ada preflight CORS. Ini adalah
konfigurasi yang dipakai sehari-hari dan oleh mock/backend nyata.

### Mode langsung — backend cross-origin (menguji CORS)

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_BACKEND_URL=http://localhost:8000
```

Browser mengirim request langsung ke backend. `Origin: http://localhost:3000`
harus ada pada `CORS_ORIGINS`; nilai default sudah mencakupnya. Gunakan mode ini
untuk membuktikan integrasi CORS berjalan, misalnya saat menguji `fetch` login
dari console browser.

> Jangan menaruh token atau credential backend pada variabel `VITE_*`; semua
> variabel tersebut tersedia di browser.

---

## 4. Perilaku middleware

Implementasi: `src/middlewares/cors.py` (dipasang di `create_app`).

| Request | Hasil |
| :--- | :--- |
| Preflight (`OPTIONS`) dari origin terdaftar | `200`, header `Access-Control-Allow-Origin` berisi origin tersebut |
| Preflight dari origin tidak terdaftar | `400 Disallowed CORS origin`, tanpa header CORS |
| Request sederhana dari origin terdaftar | Response normal + header CORS |
| Request sederhana dari origin tidak terdaftar | Response diproses server, tetapi tanpa header CORS → browser memblokir |
| Response error (`401`, `422`, `403`, dst.) dari origin terdaftar | Tetap memuat header CORS |

Detail konfigurasi:

| Pengaturan | Nilai | Alasan |
| :--- | :--- | :--- |
| `allow_origins` | `settings.CORS_ORIGINS` | Daftar eksplisit dari environment |
| `allow_credentials` | `False` | Authentication memakai bearer token, bukan cookie |
| `allow_methods` | `GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS` | Seluruh method API |
| `allow_headers` | `Accept, Authorization, Content-Type, Idempotency-Key` | Termasuk header login dan operasi idempoten (design-api §21) |
| `expose_headers` | `WWW-Authenticate` | Frontend dapat membaca challenge 401 |
| `max_age` | `600` detik | Browser meng-cache hasil preflight |

`Authorization` dan `Content-Type: application/json` adalah header yang memicu
preflight pada request login; keduanya diizinkan.

---

## 5. Verifikasi

### 5.1 Preflight dari origin frontend

```bash
curl -i -X OPTIONS http://127.0.0.1:8000/api/v1/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type"
```

Response yang diharapkan:

```http
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:3000
access-control-allow-methods: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
access-control-allow-headers: authorization, content-type
access-control-max-age: 600
vary: Origin
```

Nilai urutan method/header dapat berbeda, tetapi harus memuat `POST` dan header
yang diminta.

### 5.2 Origin tidak terdaftar

```bash
curl -i -X OPTIONS http://127.0.0.1:8000/api/v1/auth/login \
  -H "Origin: http://evil.example" \
  -H "Access-Control-Request-Method: POST"
```

Response yang diharapkan: `HTTP/1.1 400 Bad Request` dengan body
`Disallowed CORS origin`, tanpa `access-control-allow-origin`.

### 5.3 Request login langsung dari browser

Jalankan backend dan frontend mode langsung, lalu dari DevTools Console pada
`http://localhost:3000`:

```js
fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'dosen.demo@itk.ac.id', password: '<password>' }),
}).then(async (response) => console.log(response.status, await response.json()));
```

Tidak boleh muncul error `blocked by CORS policy`. Status `401`/`422` tetap
bukan error CORS; keduanya adalah response API yang valid dan header CORS-nya
ikut terkirim.

### 5.4 Dari test suite

```bash
cd backend
uv run pytest tests/test_cors.py tests/test_config.py
```

Pengujian mencakup preflight origin terdaftar/tidak terdaftar, seluruh method,
header `Authorization`/`Idempotency-Key`, header CORS pada response `401`/`422`,
normalisasi environment, dan penolakan wildcard/path/port tidak valid.

---

## 6. Troubleshooting

| Gejala | Penyebab umum | Tindakan |
| :--- | :--- | :--- |
| `blocked by CORS policy: No 'Access-Control-Allow-Origin' header` | Origin tidak terdaftar atau berbeda (mis. frontend di port 5173) | Tambahkan origin persis tersebut ke `CORS_ORIGINS`, restart backend |
| Preflight `400 Disallowed CORS origin` | Sama seperti di atas; cek skema/host/port, bukan hanya nama host | Cocokkan dengan header `Origin` di DevTools Network |
| Preflight lolos, request sebenarnya gagal CORS | Header yang dikirim tidak ada di `allow_headers` (mis. header kustom baru) | Tambahkan header ke `ALLOWED_HEADERS` di `src/middlewares/cors.py` |
| Berhasil via proxy, gagal saat direct | `VITE_API_BASE_URL` absolut tetapi origin belum terdaftar | Daftarkan origin frontend, atau kembali ke mode proxy |
| Konfigurasi ditolak saat startup | Wildcard, path, scheme/port salah | Perbaiki `CORS_ORIGINS`; pesan error menyebut nilai yang salah |
| Origin benar tetapi tetap ditolak | Nilai environment lama masih dipakai proses yang berjalan | Restart backend/Docker setelah mengubah `.env` |

Catatan: browser tidak mengirim header `Origin` untuk navigasi biasa. CORS hanya
relevan untuk request `fetch`/XHR lintas origin, bukan untuk membuka Swagger UI
atau halaman frontend.

---

## 7. Acceptance criteria dan traceability

| Requirement BE-06.2 | Bukti |
| :--- | :--- |
| Konfigurasi CORS untuk origin frontend development melalui environment | `CORS_ORIGINS` pada `src/config/settings.py`, dipasang `src/middlewares/cors.py` |
| Base URL API dan port backend terdokumentasi | §1 dokumen ini; `backend/README.md`; root `README.md` |
| Contoh konfigurasi environment frontend (`.env.example`) diperbarui | `frontend/.env.example` (mode proxy vs direct) dan `backend/.env.example` |
| Request frontend development ke endpoint authentication berhasil tanpa error CORS | `tests/test_cors.py` (preflight login, header CORS pada 401/422) + verifikasi §5 |
| Origin yang tidak terdaftar ditolak | Preflight `400`, tanpa `Access-Control-Allow-Origin`; diuji `test_preflight_from_an_unregistered_origin_is_rejected` |
| Origin production tidak di-hardcode | Origin berasal dari environment; `.env.example` hanya berisi origin development |

Dokumentasi authentication (endpoint login/current user) ada di
[`docs/02. design/auth-api-integration.md`](../02.%20design/auth-api-integration.md)
(BE-06.1).
