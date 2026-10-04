# Moodle Integration Guide

| Item | Value |
| :--- | :--- |
| **Issue** | #48 (BE-04) |
| **Status** | Draft — diuji pada Moodle lokal (Docker), belum diverifikasi di Moodle ITK |
| **Related Documents** | `moodle-integration.md` (design), `moodle-integration-contract.md` (hasil capability discovery) |

## 1. Tujuan
Panduan ini menjelaskan struktur integrasi backend dengan Moodle dan cara memakainya dari modul lain, termasuk workflow Agentic AI pada milestone berikutnya. Moodle diperlakukan sebagai external system: modul lain tidak boleh memanggil Moodle Web Service secara langsung, dan tidak boleh memegang URL maupun token Moodle.

## 2. Arsitektur

```
Application / workflow
        |
IMoodleIntegration  <-  TrackedMoodleIntegration (mencatat status eksekusi)
        |
MoodleAdapter   (mapping ID, retry, normalisasi error)
        |
MoodleClient    (HTTP, token, validasi response)
        |
Moodle Web Service API
```

Di samping jalur utama ada `MockMoodleIntegration` (pengganti Moodle untuk development dan test) dan `MoodleHealthChecker` (cek ketersediaan Moodle).

## 3. Komponen

Semua berada di `backend/src/services/` kecuali disebut lain.

| File | Tanggung jawab |
| :--- | :--- |
| `moodle_client.py`, `moodle_exceptions.py` | Client HTTP untuk Moodle Web Service: autentikasi token, timeout, validasi response, redaksi token pada pesan error dan log |
| `moodle_integration_interface.py` | Kontrak `IMoodleIntegration` dan DTO (`CourseDTO`, `SectionDTO`, `LearningMaterial`, `LearningMaterialDTO`) |
| `moodle_adapter.py` | Implementasi `IMoodleIntegration` di atas `MoodleClient` |
| `moodle_adapter_exceptions.py`, `moodle_error_normalizer.py` | Error application-level dan penerjemah error client |
| `moodle_retry.py` | `RetryPolicy` dan daftar function yang tidak boleh di-retry buta |
| `moodle_mapping.py`, `moodle_mapping_sql.py` | Pemetaan ID internal ke ID Moodle (in-memory dan database) |
| `moodle_execution.py`, `moodle_execution_sql.py` | Status eksekusi dan penyimpanannya |
| `moodle_tracked_integration.py` | Pembungkus yang mencatat setiap operasi yang mengubah Moodle |
| `moodle_mock.py` | `MockMoodleIntegration`, versi in-memory seluruh `IMoodleIntegration` |
| `moodle_health.py` | `MoodleHealthChecker` |
| `models/moodle_entity_mapping.py`, `models/moodle_execution_record.py` | Model tabel `moodle_entity_mappings` dan `moodle_executions` |

## 4. Konfigurasi
Konfigurasi dibaca dari environment (`backend/.env`, contoh di `backend/.env.example`):

| Variabel | Fungsi |
| :--- | :--- |
| `MOODLE_BASE_URL` | Alamat dasar Moodle, misalnya `http://localhost:8000` |
| `MOODLE_WEB_SERVICE_TOKEN` | Token web service untuk service `Capstone Integration` |

Token tidak boleh ditulis di source code, dokumen, log, maupun test. Client menyamarkan token pada pesan error dan log.

## 5. Merakit integrasi

```python
from src.config.settings import settings
from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_client import MoodleClient
from src.services.moodle_execution import MoodleExecutionTracker
from src.services.moodle_execution_sql import SqlMoodleExecutionRepository
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_tracked_integration import TrackedMoodleIntegration

client = MoodleClient.from_settings(settings)
tracker = MoodleExecutionTracker(SqlMoodleExecutionRepository(session))
adapter = MoodleAdapter(
    client,
    SqlMoodleMappingRepository(session),
    retry_observer=tracker.observe_retry,
)
integration = TrackedMoodleIntegration(adapter, tracker)
```

`session` adalah `AsyncSession` dari `src/config/database.py`. Tanpa `retry_observer`, retry tetap berjalan tetapi status `RETRYING` tidak tercatat. Untuk development tanpa Moodle, ganti seluruh rakitan dengan `MockMoodleIntegration()`.

## 6. Operasi

| Operasi | Status pada adapter |
| :--- | :--- |
| `get_course`, `find_course` (by shortname), `get_course_contents` | Tersedia |
| `create_course` | Tersedia, idempotent berdasarkan mapping |
| `update_course` | Tersedia |
| `get_weekly_sections`, `resolve_week_section` | Tersedia (section minggu N diasumsikan bernomor N; section 0 adalah General) |
| `create_section`, `update_section` | Belum tersedia: melapor `MoodleCapabilityUnavailableError`; tersedia pada mock |
| `create_learning_material`, `update_learning_material` | Belum tersedia: melapor `MoodleCapabilityUnavailableError`; tersedia pada mock |

Alasan operasi yang belum tersedia dicatat di `moodle-integration-contract.md`. Assignment, quiz, dan upload file belum dikerjakan.

## 7. Mapping ID
Setiap objek Moodle dipetakan ke ID internal pada tabel `moodle_entity_mappings` dengan `entity_type` berikut:

| `entity_type` | ID Moodle |
| :--- | :--- |
| `course` | ID course |
| `course_plan_week` | ID section Moodle (bukan nomor urutnya, karena nomor bisa berubah) |

Dua unique constraint menjaga pemetaan satu-ke-satu: `(entity_type, internal_id)` dan `(entity_type, moodle_id)`. Karena itu operasi yang diulang tidak membuat objek ganda: `create_course` memeriksa mapping sebelum memanggil Moodle.

## 8. Error
Error Moodle diterjemahkan menjadi error application-level. Semuanya turunan `MoodleOperationFailedError`, dengan atribut `category`, `retryable`, `original_error`, dan method `to_dict()`.

| Error | Kategori | Retry |
| :--- | :--- | :--- |
| `MoodleAuthenticationFailedError` | `authentication` | Tidak |
| `MoodlePermissionDeniedError` | `permission` | Tidak |
| `MoodleValidationFailedError` | `validation` | Tidak |
| `MoodleTransientError` | `transient` (timeout, jaringan, HTTP 429/502/503/504) | Ya |
| `MoodleOperationFailedError` | `execution` (lainnya) | Tidak |

Dua error lain berdiri sendiri: `MoodleEntityNotFoundError` (course atau section tidak ditemukan) dan `MoodleCapabilityUnavailableError` (operasi belum tersedia pada Moodle).

## 9. Retry
`RetryPolicy` default: maksimal 3 percobaan dengan jeda 0,5 detik lalu 1 detik (batas 5 detik), hanya untuk error `transient`. Pembacaan dan `update_course` aman diulang. `create_course` tidak di-retry buta: setelah error transient, adapter mencari course dengan shortname yang sama. Kalau sudah ada, course itu dipakai dan mapping disimpan, jadi tidak terbentuk course ganda. Kalau belum ada, create diulang sesuai batas percobaan.

## 10. Status eksekusi
Setiap operasi yang mengubah Moodle dicatat di tabel `moodle_executions` (operation, entity type, ID internal, ID Moodle, status, jumlah percobaan, kategori dan pesan error). Pesan error dipotong 500 karakter.

```
PENDING -> RUNNING -> SUCCESS
PENDING -> RUNNING -> RETRYING -> FAILED
```

Status ini terpisah dari state agent: kegagalan Moodle tidak menghilangkan catatan eksekusi. Operasi baca dan `resolve_week_section` tidak dicatat.

## 11. Health check

```python
health = await MoodleHealthChecker(client).check()
health.to_dict()
```

`check()` tidak pernah melempar error Moodle dan tidak melakukan retry. Hasilnya `available`, `release` (versi Moodle), `latency_ms`, serta `error_category` dan `message` bila gagal.

## 12. Pengujian
- `pytest` biasa: test unit memakai Moodle tiruan (`httpx.MockTransport`) dan SQLite in-memory, dan tidak membutuhkan Moodle.
- `tests/test_moodle_contract.py` menjalankan skenario yang sama pada mock dan adapter asli, dan memastikan semua implementasi memiliki seluruh `IMoodleIntegration`.
- `tests/test_moodle_live.py` diuji terhadap Moodle sungguhan dan dilewati secara default. Jalankan dengan Moodle menyala:

```
set MOODLE_LIVE_TESTS=1
pytest tests\test_moodle_live.py -v
```

Catatan: Moodle Docker lokal bisa lambat pada permintaan pertama, sehingga test live memakai timeout 60 detik. Setiap run meninggalkan satu course uji, karena service tidak memiliki function hapus course.

## 13. Aturan untuk modul lain
- Gunakan `IMoodleIntegration`. Jangan mengimpor `MoodleClient` atau membuat request HTTP ke Moodle di luar `services/moodle_*`.
- Agent tidak boleh menerima URL maupun token Moodle. Yang diterima hanya DTO dan error yang sudah dinormalisasi.
- Tangani `MoodleOperationFailedError` (menurut `category`), `MoodleEntityNotFoundError`, dan `MoodleCapabilityUnavailableError`.
- ID internal berupa string. ID Moodle dibaca dari DTO, bukan disimpan sendiri.

## 14. Batasan
- Semua hasil bersifat local-verified. Versi Moodle, mekanisme autentikasi, dan permission akun integrasi ITK masih harus diverifikasi.
- Daftar kode error validasi (`invalidparameter`, `shortnametaken`, dan lainnya) adalah kode standar Moodle yang belum diverifikasi ke Moodle ITK.
- Create dan update section serta learning material belum memiliki function pada Moodle; keputusan penggunaan plugin atau mock ada di Decision Log.
- Pelacak eksekusi belum disambungkan ke aplikasi, karena lapisan workflow belum ada.