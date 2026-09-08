# Development & Git Workflow Documentation

Dokumen ini menjelaskan struktur repository, aturan percabangan, konvensi commit, manajemen issue, Pull Request (PR), serta panduan branch protection yang digunakan oleh seluruh anggota tim dalam Capstone Project.

---

## 1. Repository Structure

Struktur repository proyek dibagi ke dalam beberapa direktori utama:

```text
capstone-projek/
├── backend/            # Source code dan konfigurasi service backend
│   └── README.md
├── frontend/           # Source code dan komponen UI frontend
│   └── README.md
├── docs/               # Dokumentasi proyek
│   ├── 01. project-charter/
│   ├── 02. design/
│   ├── 03. quality-plan/
│   └── 04. workflow/
│       └── development-workflow.md
├── .github/            # Template issue dan pull request
│   ├── ISSUE_TEMPLATE/
│   │   ├── feature_request.md
│   │   ├── bug_report.md
│   │   └── task.md
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore          # Konfigurasi file yang diabaikan oleh Git
├── .env.example        # Template variabel lingkungan / environment
├── aturan.md           # Aturan kolaborasi dan pengembangan utama
└── README.md           # Panduan dan deskripsi repository
```

---

## 2. Branching Strategy & Naming Conventions

### Branch Hierarchy

```text
main (Production/Stable)
└── develop (Integration Branch)
    ├── feature/*
    ├── fix/*
    ├── refactor/*
    ├── docs/*
    ├── test/*
    └── chore/*
```

### Branch Roles
- **`main`**: Menampung kode yang stabil, teruji, dan siap dipakai sebagai versi utama. Tidak diperbolehkan direct push.
- **`develop`**: Branch utama integrasi pengembangan harian. Semua fitur dan perbaikan harus masuk melalui Pull Request dari branch fitur/fix.

### Naming Format
Format branch: `<type>/<short-description>`

| Type | Penggunaan | Contoh |
| --- | --- | --- |
| `feature` | Penambahan fitur baru | `feature/login`, `feature/moodle-integration` |
| `fix` | Perbaikan bug / error | `fix/auth-validation`, `fix/db-connection` |
| `refactor` | Perubahan struktur kode tanpa mengubah behavior | `refactor/moodle-service` |
| `docs` | Pembaruan atau penambahan dokumentasi | `docs/api-guide` |
| `test` | Penambahan atau perbaikan unit/integration test | `test/prediction-service` |
| `chore` | Maintenance, dependency, konfigurasi teknis | `chore/update-deps` |

---

## 3. Branch Protection Rules

### Mandatory Protections for `main` & `develop`
1. **No Direct Push**: Direct push ke `main` dan `develop` dilarang.
2. **Require Pull Request**: Perubahan ke `main` atau `develop` wajib melalui Pull Request.
3. **Code Review**: PR membutuhkan minimal 1 persetujuan (approval) dari anggota tim/reviewer.
4. **Clean Merge Strategy**: Menggunakan **Squash and Merge** saat melakukan merge ke `develop` agar histori commit tetap bersih dan rapi.
5. **No Secret Leaks**: Dilarang meng-commit file credential/secret (`.env`, private key, token).

### Step-by-Step GitHub Setup Guide for Repository Admin
1. Buka repository di GitHub: `https://github.com/capstone-teams/capstone-projek`.
2. Masuk ke **Settings** -> **Branches** (atau **Rulesets**).
3. Klik **Add branch protection rule** (atau buat Ruleset baru):
   - **Branch pattern name**: `main` (dan `develop`)
   - Centang **Require a pull request before merging**:
     - Set **Require approvals**: `1`
     - Centang **Dismiss stale pull request approvals when new commits are pushed**.
   - Centang **Require status checks to pass before merging** (jika CI/CD aktif).
   - Centang **Restrict who can push to matching branches** / **Block force pushes**.
4. Simpan konfigurasi.

---

## 4. Commit Message Conventions

Proyek ini menggunakan standar **Conventional Commits**:

Format:
```text
<type>: <description>
```

### Commit Types:
- `feat`: Penambahan fitur baru (misal: `feat: add user authentication endpoint`)
- `fix`: Memperbaiki bug (misal: `fix: handle null sensor payload`)
- `refactor`: Refactoring kode (misal: `refactor: simplify moodle client API`)
- `docs`: Perubahan dokumentasi (misal: `docs: update deployment guide`)
- `test`: Penambahan/perbaikan testing (misal: `test: add auth controller test`)
- `chore`: Pekerjaan maintenance/konfigurasi (misal: `chore: update dependencies`)

---

## 5. Issue Management Workflow

Setiap pekerjaan teknis atau fitur dimulai dari **GitHub Issue**.

### Issue Title Format:
```text
[Type] Short description
```
Contoh: `[Feature] Add Moodle course sync API`, `[Bug] Token expired error on login`.

### Issue Lifecycle & Statuses:
- **TODO**: Pekerjaan terdaftar tetapi belum dimulai.
- **IN PROGRESS**: Pekerjaan sedang aktif dikerjakan oleh Assignee.
- **BLOCKED**: Pekerjaan terhambat oleh dependency atau kendala teknis lain.
- **IN REVIEW**: Pekerjaan selesai secara teknis dan PR sedang ditinjau.
- **DONE**: Pekerjaan selesai, PR di-merge, dan Acceptance Criteria terpenuhi.

---

## 6. Pull Request (PR) Workflow

1. Pastikan branch lokal telah disinkronkan dengan branch `develop` terbaru (`git pull origin develop`).
2. Push branch ke remote repository (`git push -u origin feature/<nama-fitur>`).
3. Buat Pull Request dari branch fitur ke branch `develop`.
4. Isi judul dan deskripsi PR sesuai template (`.github/PULL_REQUEST_TEMPLATE.md`), dan sertakan referensi Issue (`Closes #<issue_number>`).
5. Minta minimal 1 reviewer untuk memeriksa PR.
6. Lakukan penyesuaian jika reviewer memberikan feedback.
7. Setelah di-approve dan seluruh checks lolos, lakukan **Squash and Merge** ke branch `develop`.
8. Tutup Issue terkait.

---

## 7. Step-by-Step Development Flow

```text
1. Ambil/Pilih Issue pada Project Board & set Assignee
       ↓
2. Update local develop:
   git checkout develop && git pull origin develop
       ↓
3. Buat branch baru:
   git checkout -b feature/nama-fitur
       ↓
4. Kerjakan fitur & commit dengan Conventional Commit:
   git commit -m "feat: add feature X"
       ↓
5. Push branch ke remote:
   git push -u origin feature/nama-fitur
       ↓
6. Buat Pull Request ke branch `develop` (isi PR Template & referensi Issue)
       ↓
7. Code Review oleh minimal 1 anggota tim
       ↓
8. Squash and Merge ke `develop` setelah Approval
       ↓
9. Issue otomatis ditutup (Closes #ID) & update Task Board ke DONE
```
