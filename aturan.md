# Development & Collaboration Guidelines

Dokumen ini menjadi aturan kerja tim dalam pengembangan Capstone Project. Seluruh anggota tim wajib mengikuti aturan branch, commit, issue, pull request, code review, dan workflow yang ditetapkan di dokumen ini.

Tujuan aturan ini adalah menjaga repository tetap terstruktur, memudahkan kolaborasi, mengurangi konflik, mempermudah tracking pekerjaan, dan memastikan setiap perubahan dapat ditelusuri.

---

# 1. Repository Structure

Repository menggunakan struktur branch berikut:

```text
main
└── develop
    ├── feature/*
    ├── fix/*
    ├── refactor/*
    ├── docs/*
    ├── test/*
    └── chore/*
```

## Main Branch

`main` merupakan branch untuk kode yang dianggap stabil dan siap digunakan sebagai versi utama project.

Aturan:

* Tidak diperbolehkan melakukan direct push ke `main`.
* Semua perubahan harus melalui Pull Request.
* `main` hanya menerima perubahan dari `develop` atau release yang telah disetujui tim.
* Kode yang berada di `main` harus dalam kondisi dapat dijalankan.

## Develop Branch

`develop` merupakan branch utama untuk development.

Aturan:

* Development harian dilakukan melalui branch masing-masing anggota.
* Perubahan dari anggota masuk ke `develop` melalui Pull Request.
* Jangan melakukan direct push ke `develop`.
* `develop` harus selalu berada dalam kondisi yang relatif stabil dan dapat diintegrasikan.

---

# 2. Branch Naming Convention

Setiap pekerjaan harus menggunakan branch tersendiri.

Format:

```text
<type>/<short-description>
```

Jenis branch yang diperbolehkan:

| Type       | Penggunaan                                                           |
| ---------- | -------------------------------------------------------------------- |
| `feature`  | Menambahkan fitur baru                                               |
| `fix`      | Memperbaiki bug                                                      |
| `refactor` | Mengubah struktur kode tanpa mengubah fungsi utama                   |
| `docs`     | Dokumentasi                                                          |
| `test`     | Menambahkan atau memperbaiki testing                                 |
| `chore`    | Maintenance, configuration, dependency, dan pekerjaan teknis lainnya |

## Contoh

```text
feature/login
feature/prediction-api
feature/dashboard
feature/machine-management

fix/login-validation
fix/prediction-error
fix/database-connection

refactor/auth-service
refactor/ml-service

docs/api-documentation
docs/setup-guide

test/prediction-service

chore/update-dependencies
```

## Aturan Branch

1. Gunakan huruf kecil.
2. Gunakan `-` untuk memisahkan kata.
3. Gunakan nama yang singkat tetapi jelas.
4. Jangan menggunakan spasi.
5. Jangan menggunakan nama anggota sebagai nama branch.
6. Satu branch hanya digunakan untuk satu pekerjaan atau satu logical change.
7. Jangan membuat branch dengan nama tidak jelas seperti:

```text
test
coba
baru
fix
branch-baru
punya-noel
final
final-project
```

Gunakan:

```text
feature/user-authentication
fix/token-expiration
```

---

# 3. Membuat Branch

Sebelum membuat branch baru, pastikan local repository sudah diperbarui.

```bash
git checkout develop
git pull origin develop
```

Kemudian buat branch:

```bash
git checkout -b feature/login
```

Atau menggunakan command Git modern:

```bash
git switch develop
git pull origin develop
git switch -c feature/login
```

Setelah selesai membuat branch:

```bash
git push -u origin feature/login
```

---

# 4. Branch harus berasal dari Develop

Untuk pekerjaan development normal:

```text
develop
   │
   ├── feature/login
   ├── feature/dashboard
   ├── feature/prediction-api
   └── fix/login-error
```

Jangan membuat branch feature dari branch feature anggota lain kecuali memang terdapat dependency yang sudah disepakati.

Jika membutuhkan pekerjaan dari branch lain, komunikasikan terlebih dahulu kepada anggota terkait.

---

# 5. Commit Convention

Project menggunakan Conventional Commits.

Format:

```text
<type>: <description>
```

Contoh:

```text
feat: add login endpoint
fix: validate sensor payload
refactor: separate prediction service
docs: update API documentation
test: add prediction service tests
chore: update dependencies
```

## Commit Types

### `feat`

Digunakan ketika menambahkan fitur baru.

```text
feat: add user registration
feat: add machine monitoring
feat: add prediction endpoint
```

### `fix`

Digunakan ketika memperbaiki bug.

```text
fix: handle invalid login credentials
fix: prevent duplicate machine records
fix: handle null sensor values
```

### `refactor`

Digunakan untuk perubahan struktur kode tanpa mengubah behavior utama.

```text
refactor: separate authentication service
refactor: simplify prediction controller
```

### `docs`

Digunakan untuk perubahan dokumentasi.

```text
docs: add API documentation
docs: update installation guide
```

### `test`

Digunakan untuk testing.

```text
test: add login controller tests
test: add prediction service tests
```

### `chore`

Digunakan untuk pekerjaan maintenance.

```text
chore: update dependencies
chore: configure eslint
chore: update docker configuration
```

---

# 6. Aturan Commit

Commit harus memenuhi aturan berikut:

1. Satu commit harus merepresentasikan satu logical change.
2. Commit message harus menjelaskan perubahan.
3. Jangan menggunakan commit message yang terlalu umum.
4. Jangan menggabungkan perubahan yang tidak berkaitan dalam satu commit.
5. Jangan membuat commit hanya untuk memenuhi jumlah commit.
6. Commit harus dibuat setelah pekerjaan memiliki perubahan yang bermakna.

## Hindari

```text
update
fix
done
final
final fix
perbaikan
coba lagi
changes
```

## Gunakan

```text
feat: add machine registration endpoint
fix: validate sensor reading payload
refactor: simplify authentication middleware
docs: update database setup guide
```

---

# 7. Commit yang Terlalu Besar

Hindari commit seperti:

```text
feat: complete backend
```

yang berisi:

```text
- authentication
- machine API
- sensor API
- prediction API
- database migration
- documentation
```

Lebih baik dipisahkan:

```text
feat: add authentication middleware
feat: add machine API
feat: add sensor API
feat: add prediction API
docs: add backend API documentation
```

Tujuannya agar perubahan lebih mudah dibaca, direview, dan dikembalikan jika terjadi masalah.

---

# 8. Issue Management

Setiap pekerjaan yang membutuhkan perubahan pada project sebaiknya direpresentasikan sebagai Issue.

Issue digunakan untuk:

* Feature request
* Bug report
* Task development
* Documentation
* Technical debt
* Improvement
* Research atau investigation

Jangan menggunakan chat sebagai satu-satunya tempat untuk menyimpan pekerjaan.

Jika sebuah pekerjaan penting, buat Issue agar dapat dilacak.

---

# 9. Issue Title

Gunakan format:

```text
[type] short description
```

Contoh:

```text
[Feature] Add user authentication
[Feature] Add prediction endpoint
[Bug] Login fails with valid credentials
[Docs] Create API documentation
[Fix] Handle invalid sensor payload
[Research] Evaluate prediction model
```

Judul harus menjelaskan pekerjaan tanpa perlu membuka isi Issue.

Hindari:

```text
Login
Backend
Bug
Error
Tolong cek
Bikin API
```

---

# 10. Issue Description

Issue minimal harus menjelaskan:

```text
## Description

Jelaskan pekerjaan atau masalah.

## Objective

Apa yang ingin dicapai?

## Requirements

- Requirement 1
- Requirement 2
- Requirement 3

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Notes

Informasi tambahan jika diperlukan.
```

Untuk bug:

```text
## Bug Description

Jelaskan masalah.

## Steps to Reproduce

1. ...
2. ...
3. ...

## Expected Behavior

...

## Actual Behavior

...

## Environment

- OS:
- Browser:
- Backend:
- Database:

## Evidence

Screenshot / log / error message.
```

---

# 11. Issue Assignment

Setiap Issue yang sedang dikerjakan harus memiliki assignee.

Contoh:

```text
Issue #24
[Feature] Add Prediction API

Assignee:
@username
```

Jika pekerjaan dilakukan oleh dua orang atau lebih, tentukan satu orang sebagai primary owner dan anggota lainnya sebagai collaborator.

Jangan mengambil Issue yang sedang dikerjakan anggota lain tanpa komunikasi terlebih dahulu.

---

# 12. Issue Status

Gunakan status:

```text
TODO
IN PROGRESS
BLOCKED
IN REVIEW
DONE
```

Makna:

### TODO

Pekerjaan belum dimulai.

### IN PROGRESS

Pekerjaan sedang dikerjakan.

### BLOCKED

Pekerjaan tidak dapat dilanjutkan karena dependency atau masalah tertentu.

Contoh:

```text
BLOCKED:
Menunggu endpoint dari backend.
```

### IN REVIEW

Pekerjaan telah selesai secara teknis dan sedang menunggu review melalui Pull Request.

### DONE

Pekerjaan telah selesai, direview, diintegrasikan, dan memenuhi Acceptance Criteria.

---

# 13. Issue dan Branch Harus Terhubung

Satu pekerjaan sebaiknya memiliki hubungan:

```text
Issue
   ↓
Branch
   ↓
Commit
   ↓
Pull Request
   ↓
Review
   ↓
Merge
   ↓
Issue Closed
```

Contoh:

```text
Issue #24
[Feature] Add Prediction API

        ↓

feature/prediction-api

        ↓

feat: add prediction endpoint

        ↓

PR #31
feat: add prediction API

        ↓

Review

        ↓

Merge

        ↓

Issue #24 CLOSED
```

Jika memungkinkan, gunakan GitHub keyword seperti:

```text
Closes #24
```

di Pull Request agar Issue otomatis ditutup ketika PR di-merge.

---

# 14. Pull Request

Semua perubahan yang akan masuk ke `develop` harus melalui Pull Request.

Format PR title mengikuti Conventional Commit:

```text
feat: add prediction API
fix: handle invalid sensor data
refactor: simplify authentication service
docs: update API documentation
```

PR harus menjelaskan:

```text
## Description

Jelaskan perubahan yang dilakukan.

## Changes

- Change 1
- Change 2
- Change 3

## Testing

Jelaskan bagaimana perubahan telah diuji.

## Related Issue

Closes #24
```

---

# 15. Pull Request Rules

Setiap Pull Request harus memenuhi:

* Tidak langsung merge ke branch tujuan tanpa review.
* Minimal satu anggota melakukan review.
* Tidak memiliki konflik yang belum diselesaikan.
* Testing yang diperlukan sudah dilakukan.
* Tidak memasukkan file yang tidak diperlukan.
* Tidak memasukkan secret atau credential.
* PR memiliki deskripsi yang jelas.
* PR hanya mencakup satu logical change atau satu Issue utama.
* Semua feedback reviewer yang relevan harus ditangani.

---

# 16. Ukuran Pull Request

Hindari Pull Request yang terlalu besar.

Buruk:

```text
PR #50
"Complete entire backend"
```

dengan perubahan puluhan file dan ribuan baris.

Lebih baik:

```text
PR #31
feat: add authentication

PR #32
feat: add machine API

PR #33
feat: add sensor API

PR #34
feat: add prediction API
```

PR yang kecil lebih mudah direview dan lebih kecil kemungkinan menyembunyikan bug.

---

# 17. Code Review

Reviewer tidak hanya memeriksa apakah program dapat dijalankan.

Reviewer harus memperhatikan:

```text
[ ] Apakah perubahan sesuai dengan Issue?
[ ] Apakah logic benar?
[ ] Apakah terdapat bug?
[ ] Apakah terdapat error handling?
[ ] Apakah naming jelas?
[ ] Apakah struktur kode sesuai project?
[ ] Apakah terdapat duplikasi kode?
[ ] Apakah terdapat security issue?
[ ] Apakah testing sudah dilakukan?
[ ] Apakah perubahan merusak bagian lain?
```

Reviewer boleh meminta perubahan apabila terdapat masalah.

Gunakan komentar yang spesifik.

Buruk:

```text
Ini salah.
```

Lebih baik:

```text
Sebaiknya validation dilakukan sebelum query database agar
payload invalid tidak diteruskan ke layer berikutnya.
```

---

# 18. Resolving Review Comments

Jika reviewer meminta perubahan:

```text
Reviewer
   ↓
Request Changes
   ↓
Developer melakukan perubahan
   ↓
Push commit baru
   ↓
Reviewer melakukan review ulang
   ↓
Approve
```

Jangan menghapus komentar reviewer hanya karena tidak setuju.

Jika terdapat perbedaan pendapat, diskusikan terlebih dahulu.

Keputusan akhir harus berdasarkan alasan teknis, bukan berdasarkan siapa yang lebih senior atau lebih keras berargumen.

---

# 19. Merge Rules

Pull Request dapat di-merge apabila:

```text
[ ] Issue sesuai
[ ] Requirement terpenuhi
[ ] Testing berhasil
[ ] Code review selesai
[ ] Reviewer approve
[ ] Tidak ada conflict
[ ] Tidak ada blocking comment
```

Jangan merge Pull Request yang masih memiliki masalah yang diketahui hanya karena deadline semakin dekat.

Jika deadline sangat dekat, keputusan tersebut harus dibahas bersama PM dan dicatat sebagai project decision.

---

# 20. Merge Strategy

Untuk project ini gunakan:

```text
Squash and Merge
```

untuk menggabungkan Pull Request ke `develop`, terutama jika branch memiliki banyak commit kecil seperti:

```text
fix
fix again
try again
final
final fix
```

Dengan squash, history `develop` tetap bersih.

Contoh:

```text
feature/login

commit 1
commit 2
commit 3
commit 4

        ↓ Squash

develop

feat: add user authentication
```

---

# 21. Jangan Push Secret

Dilarang melakukan commit terhadap:

```text
.env
.env.local
.env.production
API keys
Database passwords
JWT secrets
Private keys
Cloud credentials
Service account credentials
```

Gunakan `.gitignore`.

Contoh:

```gitignore
.env
.env.*
!.env.example

node_modules/
dist/
build/
__pycache__/
*.pyc
```

Sediakan:

```text
.env.example
```

sebagai template.

Contoh:

```env
DATABASE_URL=
JWT_SECRET=
API_KEY=
```

Jangan memasukkan nilai credential sebenarnya.

---

# 22. Jangan Commit File yang Tidak Diperlukan

Jangan commit:

```text
node_modules/
__pycache__/
dist/
build/
temporary files
logs
IDE configuration yang tidak diperlukan
database dump pribadi
credential
```

Repository harus hanya berisi file yang memang dibutuhkan project.

---

# 23. Update Branch Sebelum Membuat Pull Request

Sebelum membuat PR, pastikan branch sudah mendapatkan perubahan terbaru dari `develop`.

Contoh:

```bash
git checkout develop
git pull origin develop

git checkout feature/login
git merge develop
```

Atau menggunakan rebase jika tim sudah sepakat menggunakannya:

```bash
git checkout feature/login
git rebase develop
```

Untuk anggota yang belum terbiasa dengan rebase, gunakan `merge` agar risiko kesalahan lebih kecil.

---

# 24. Conflict Resolution

Jika terjadi conflict:

```text
Jangan langsung menghapus perubahan anggota lain.
```

Langkah:

```text
1. Identifikasi file yang conflict.
2. Pahami perubahan kedua sisi.
3. Tentukan perubahan yang benar.
4. Resolve conflict.
5. Jalankan aplikasi.
6. Jalankan testing.
7. Commit hasil resolution.
8. Push kembali ke branch.
```

Jika conflict menyangkut keputusan arsitektur atau behavior sistem, konsultasikan dengan anggota terkait dan PM.

---

# 25. Direct Push Rules

Dilarang melakukan direct push ke:

```text
main
develop
```

kecuali keadaan darurat yang telah disepakati oleh PM dan anggota terkait.

Workflow normal:

```text
Local Branch
     ↓
Push
     ↓
Pull Request
     ↓
Review
     ↓
Merge
```

---

# 26. Definition of Done

Sebuah task tidak dianggap `DONE` hanya karena coding telah selesai.

Task dianggap selesai apabila:

```text
[ ] Requirement telah terpenuhi
[ ] Code telah selesai
[ ] Testing telah dilakukan
[ ] Error handling telah diperiksa
[ ] Dokumentasi diperbarui jika diperlukan
[ ] Pull Request telah dibuat
[ ] Code review selesai
[ ] PR telah di-merge
[ ] Tidak terdapat known blocking issue
[ ] Issue telah ditutup
```

---

# 27. Dependency Management

Jika pekerjaan membutuhkan pekerjaan anggota lain, dependency harus dicatat.

Contoh:

```text
Frontend Dashboard
       ↓
membutuhkan
       ↓
Backend Sensor API
       ↓
membutuhkan
       ↓
Database Schema
```

Jangan menunggu secara diam-diam.

Jika terhambat:

```text
Status: BLOCKED

Reason:
Menunggu endpoint GET /api/sensors dari backend.

Required by:
Frontend Dashboard

Needed by:
5 September 2026
```

PM harus mengetahui blocker yang dapat mempengaruhi timeline.

---

# 28. Communication Rules

Gunakan platform sesuai kebutuhan.

```text
GitHub Issues
→ Task, bug, feature, technical discussion

GitHub Pull Request
→ Code review

GitHub Repository
→ Source code

Documentation
→ Dokumentasi project

Group Chat
→ Komunikasi cepat dan koordinasi

Meeting
→ Keputusan yang membutuhkan diskusi bersama
```

Jangan menyimpan keputusan penting hanya di chat.

Jika keputusan penting dibuat melalui chat atau meeting, dokumentasikan hasilnya pada Issue atau Decision Log.

---

# 29. Decision Log

Keputusan penting project harus dapat dilacak.

Format:

```text
## Decision

Date:
YYYY-MM-DD

Decision:
Apa keputusan yang dibuat?

Reason:
Mengapa keputusan tersebut diambil?

Alternatives:
Alternatif yang dipertimbangkan.

Impact:
Apa dampaknya terhadap project?

Decision Maker:
Siapa yang terlibat dalam keputusan?
```

Contoh:

```text
## Decision

Date:
2026-09-01

Decision:
Menggunakan PostgreSQL sebagai database utama.

Reason:
Mendukung kebutuhan relational data dan integrasi vector
database yang dibutuhkan oleh sistem.

Alternatives:
MySQL

Impact:
Backend menggunakan PostgreSQL sebagai database utama.
```

---

# 30. Project Manager Rules

PM bertanggung jawab terhadap koordinasi project, bukan mengambil alih pekerjaan seluruh anggota.

PM harus memantau:

```text
Scope
Schedule
Task
Dependency
Risk
Resource
Quality
Communication
Integration
```

PM harus mengetahui:

```text
Apa yang sedang dikerjakan?
Siapa yang mengerjakan?
Kapan selesai?
Apa dependency-nya?
Apa blocker-nya?
Apa risikonya?
Apa keputusan terakhir?
```

PM tidak perlu mengontrol setiap baris kode, tetapi harus memastikan pekerjaan teknis menghasilkan output sesuai requirement dan timeline.

---

# 31. Daily / Periodic Update

Setiap anggota memberikan update secara berkala.

Format:

```text
Yesterday:
- Apa yang telah dikerjakan?

Today:
- Apa yang akan dikerjakan?

Blocker:
- Apa yang menghambat?
```

Contoh:

```text
Yesterday:
- Membuat endpoint machine.

Today:
- Membuat endpoint sensor.

Blocker:
- Tidak ada.
```

Jika ada blocker, jangan menunggu sampai deadline untuk melaporkannya.

---

# 32. Meeting Rules

Setiap meeting harus memiliki:

```text
Agenda
Discussion
Decision
Action Item
Deadline
```

Meeting tidak boleh berakhir tanpa mengetahui:

```text
Apa yang diputuskan?
Siapa mengerjakan apa?
Kapan harus selesai?
```

Format action item:

| Action                | Owner    | Deadline | Status      |
| --------------------- | -------- | -------- | ----------- |
| Create prediction API | Member A | 05 Sep   | In Progress |
| Create dashboard      | Member B | 07 Sep   | TODO        |
| Setup database        | Member C | 03 Sep   | Done        |

---

# 33. Scope Change

Penambahan fitur baru tidak otomatis menjadi pekerjaan yang harus dikerjakan.

Setiap perubahan scope harus mempertimbangkan:

```text
Value
Effort
Risk
Time
Dependency
Impact terhadap existing system
```

Pertanyaan yang harus dijawab:

```text
Mengapa fitur ini diperlukan?
Apakah termasuk scope awal?
Berapa effort yang dibutuhkan?
Apa dampaknya terhadap deadline?
Apa pekerjaan lain yang harus ditunda?
```

Jika fitur tidak penting terhadap MVP, masukkan sebagai:

```text
Future Improvement
```

bukan langsung dimasukkan ke development.

---

# 34. Emergency Fix

Jika ditemukan bug kritis pada `main` yang membutuhkan perbaikan segera, buat branch:

```text
fix/<description>
```

atau jika tim telah menetapkan workflow hotfix:

```text
hotfix/<description>
```

Contoh:

```text
hotfix/authentication-error
```

Perubahan tetap harus melalui Pull Request dan review apabila kondisi memungkinkan.

---

# 35. Recommended Workflow

Workflow standar anggota:

```text
1. Pilih Issue
       ↓
2. Assign Issue
       ↓
3. Update branch develop
       ↓
4. Buat feature/fix branch
       ↓
5. Develop
       ↓
6. Commit dengan Conventional Commit
       ↓
7. Push branch
       ↓
8. Update / rebase dari develop jika diperlukan
       ↓
9. Testing
       ↓
10. Create Pull Request
       ↓
11. Code Review
       ↓
12. Fix review comments
       ↓
13. Approval
       ↓
14. Squash and Merge
       ↓
15. Issue Closed
       ↓
16. Update Task Board
```

---

# 36. Quick Reference

## Branch

```text
feature/login
fix/login-error
refactor/auth-service
docs/api-documentation
test/login
chore/update-dependencies
```

## Commit

```text
feat: add login endpoint
fix: handle invalid credentials
refactor: simplify auth service
docs: update API documentation
test: add login tests
chore: update dependencies
```

## Issue

```text
[Feature] Add login
[Bug] Login fails with valid credentials
[Docs] Add API documentation
[Research] Evaluate ML model
```

## Pull Request

```text
feat: add login endpoint
```

dengan:

```text
Description
Changes
Testing
Related Issue
```

## Branch Flow

```text
main
 ↑
develop
 ↑
feature/fix branch
```

## Rule utama

```text
NO DIRECT PUSH TO MAIN
NO DIRECT PUSH TO DEVELOP
NO SECRET IN REPOSITORY
ONE TASK → ONE BRANCH
ONE LOGICAL CHANGE → ONE COMMIT
ONE FEATURE/FIX → ONE PR
PR → REVIEW → MERGE
```

---

# 37. Prinsip Utama Tim

Aturan ini dibuat untuk membantu tim bekerja, bukan untuk membuat proses menjadi rumit.

Prinsip yang harus dijaga:

> **Small changes, clear history, reviewed code, traceable work.**

Setiap perubahan harus dapat menjawab empat pertanyaan:

```text
Apa yang berubah?
Mengapa berubah?
Siapa yang mengubah?
Melalui pekerjaan/Issue apa perubahan tersebut dilakukan?
```

Jika empat pertanyaan tersebut dapat dijawab dengan mudah melalui GitHub, maka workflow development tim berjalan dengan baik.
