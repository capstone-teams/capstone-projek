# Panduan Restart Server (Backend + Cloudflare Tunnel)

Panduan untuk anggota tim backend yang perlu menyalakan ulang server demo di
mesin `thinkpad`, termasuk tunnel Cloudflare yang membuatnya bisa diakses publik.

## 1. Akses

```bash
ssh capstone@thinkpad
cd ~/capstone-projek
```

| Hal | Nilai |
| --- | --- |
| Lokasi repo | `/home/capstone/capstone-projek` |
| Branch yang dipakai server | `develop` |
| Port backend | `8000` (host dan container) |
| Port database | `5432` (PostgreSQL 16, container `capstone-postgres`) |
| Tunnel | `cloudflared-quick.service` → `127.0.0.1:8000` |
| Akses `docker` | user `capstone` sudah masuk grup `docker` |

Kalau perintah `docker` menjawab *permission denied*, berarti sesi SSH-mu dibuat
sebelum user ditambahkan ke grup. Keluar lalu masuk lagi (`exit`, `ssh ...`).
Sementara itu bisa pakai `sudo docker ...` — akun ini punya sudo tanpa password.

## 2. Cek status (selalu lakukan ini dulu)

```bash
cd ~/capstone-projek
docker compose ps                      # harus "healthy" semua
curl -s http://127.0.0.1:8000/health   # harus {"status":"ok"}
systemctl status cloudflared-quick --no-pager
```

Mengambil URL publik yang sedang aktif:

```bash
journalctl -u cloudflared-quick -o cat |
  grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1
```

## 3. Restart backend saja (paling sering dipakai)

```bash
cd ~/capstone-projek
docker compose restart backend
```

Sekitar 5–10 detik, lalu cek `curl -s http://127.0.0.1:8000/health`.
Database tidak ikut disentuh dan data tetap aman.

## 4. Restart semuanya (backend + database)

```bash
cd ~/capstone-projek
docker compose down
docker compose up -d
```

Migrasi database dijalankan otomatis oleh entrypoint container backend
(`alembic upgrade head`), jadi tidak perlu langkah tambahan.

Data PostgreSQL aman karena disimpan di volume `capstone-projek_postgres-data`.
**Jangan** pakai `docker compose down -v` — flag `-v` menghapus volume, artinya
seluruh isi database hilang.

## 5. Deploy kode terbaru (otomatis)

Server mengecek `origin/develop` tiap menit lewat `capstone-autodeploy.timer`.
Begitu ada commit baru, `capstone-autodeploy.service` menjalankan
`git merge --ff-only`, `docker compose up -d --build`, lalu cek `/health`
sampai 120 detik.

```bash
systemctl list-timers capstone-autodeploy.timer      # jadwal berikutnya
journalctl -u capstone-autodeploy -n 50             # log deploy
sudo systemctl start capstone-autodeploy.service    # deploy sekarang juga
```

Deploy berhenti dan gagal (bukan menimpa) kalau server punya perubahan lokal
yang belum di-commit — commit + push dulu, lalu jalankan service-nya lagi.

`.github/workflows/deploy-main.yml` (runner self-hosted `thinkpad`) sudah
ada di repo tetapi belum aktif karena mendaftarkan runner butuh akses admin
repo. Kalau nanti admin mendaftarkannya, push ke `main` juga memicu deploy
dari GitHub Actions; keduanya idempoten.

Langkah manual berikut hanya untuk darurat:

```bash
cd ~/capstone-projek
git checkout develop
git pull --ff-only
docker compose up -d --build     # perlu --build kalau dependency berubah
```

Kode di `backend/src` dan `backend/tests` di-bind-mount dan uvicorn jalan dengan
`--reload`, jadi perubahan kode Python langsung terpakai tanpa restart.
`--build` hanya wajib kalau `pyproject.toml`/`uv.lock` berubah (ada dependency
baru) — kalau tidak, `docker compose restart backend` sudah cukup.

## 6. Restart tunnel Cloudflare

```bash
sudo systemctl restart cloudflared-quick
sleep 10
journalctl -u cloudflared-quick -o cat |
  grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1
```

Tanpa `sudo` juga bisa (`systemctl restart cloudflared-quick`), karena service
ini berjalan sebagai user `capstone`.

> **Penting:** ini *quick tunnel*, jadi **setiap restart menghasilkan URL baru**
> dan URL lama langsung mati. Setelah restart, kirim URL yang baru ke tim/grup.
> Kalau butuh URL permanen, perlu named tunnel dengan akun Cloudflare
> (`cloudflared tunnel login`, `cloudflared tunnel create`, tambah route DNS) —
> bukan quick tunnel.

Cek tunnel dengan membuka `https://<url-baru>/health` dari browser atau HP.
Kalau tunnel hidup tapi backend mati, halaman akan menampilkan error **502**;
kalau backend sehat, hasilnya `{"status":"ok"}`.

## 7. Urutan kalau semuanya mati (mis. setelah mesin reboot)

Kedua service sudah `enabled`, jadi seharusnya hidup sendiri saat boot. Kalau
tidak:

```bash
sudo systemctl start docker
cd ~/capstone-projek && docker compose up -d
sudo systemctl start cloudflared-quick
```

Cek `systemctl is-enabled docker cloudflared-quick` → harus `enabled`.

## 8. Troubleshooting

| Gejala | Penyebab & solusi |
| --- | --- |
| `502` di URL publik | Backend mati. `docker compose ps` → `docker compose restart backend`. |
| `{"error":{"code":"AUTHENTICATION_FAILED"...}}` HTTP 401 | Normal. Endpoint memang butuh token; berarti server hidup dan tunnel benar. |
| Backend `unhealthy` | `docker compose logs --tail=100 backend`. Seringnya migrasi gagal atau DB belum siap. |
| `permission denied ... docker.sock` | Sesi SSH lama. Re-login, atau pakai `sudo docker`. |
| Port 8000 sudah dipakai | `ss -ltnp | grep 8000`, hentikan prosesnya, atau jalankan dengan `APP_PORT=8001 docker compose up -d` lalu arahkan tunnel ke port itu. |
| Halaman browser diblokir CORS | `CORS_ORIGINS` hanya mengizinkan origin lokal. Jalankan ulang: `CORS_ORIGINS="https://domain-frontend" docker compose up -d backend`. |
| Tunnel tidak dapat URL | `journalctl -u cloudflared-quick -n 50 --no-pager`, biasanya jaringan/DNS mesin sedang bermasalah. |

## 9. Catatan keamanan

Konfigurasi ini adalah **lingkungan demo**, bukan produksi:

- `APP_ENV=development`, `SECRET_KEY` masih nilai contoh di `docker-compose.yml`.
- uvicorn berjalan dengan `--reload`.
- PostgreSQL terbuka di port `5432` host dengan password default `postgres`.
- URL quick tunnel bersifat sementara dan bisa diakses siapa pun yang tahu alamatnya.

Sebelum dipakai untuk data nyata: ganti `SECRET_KEY`, matikan `--reload`, jangan
publikasikan port `5432`, dan pakai named tunnel + domain sendiri.
