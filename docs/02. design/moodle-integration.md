# Moodle Integration Design

## 1. Document Information

| Item                  | Value                                                  |
| --------------------- | ------------------------------------------------------ |
| Document              | Moodle Integration Design                              |
| Project               | Agentic AI untuk Mengisi Konten Moodle                 |
| Status                | Proposed                                               |
| Owner                 | Capstone Team                                          |
| Related Documents     | Project Charter, PRD, System Design, API Specification |
| External System       | Moodle LMS ITK                                         |
| Integration Mechanism | Moodle Web Service API                                 |

---

## 2. Purpose

Dokumen ini mendefinisikan bagaimana sistem Capstone berintegrasi dengan Moodle LMS ITK untuk menjalankan course plan dan konten yang telah disetujui oleh instructor.

Dokumen ini berfokus pada boundary antara sistem Capstone dan Moodle.

Integrasi mengikuti arsitektur:

```text
Agent
  ↓
Controlled Tool Layer
  ↓
Backend / Moodle Integration Layer
  ↓
Moodle Web Service API
  ↓
Moodle LMS ITK
```

Agent tidak berkomunikasi langsung dengan Moodle dan tidak menerima credential Moodle.

Moodle Web Service merupakan framework resmi Moodle untuk menyediakan fungsi yang dapat diakses oleh sistem eksternal. Moodle juga menyediakan daftar external functions yang dapat digunakan oleh web services.

---

## 3. Integration Principles

### 3.1 Moodle sebagai External System

Moodle diperlakukan sebagai external system.

Sistem Capstone tidak memodifikasi core Moodle dan tidak membuat "Moodle API ITK" baru.

Terminologi yang digunakan:

* **Application Backend API** = API milik sistem Capstone untuk komunikasi Frontend ↔ Backend.
* **Moodle Web Service API** = API/service mechanism resmi Moodle untuk komunikasi Backend ↔ Moodle.
* **Moodle Integration Layer** = adapter internal yang menerjemahkan operasi sistem Capstone menjadi operasi Moodle.

---

### 3.2 Backend sebagai Integration Boundary

Semua komunikasi ke Moodle harus melalui Backend.

```text
Frontend
   │
   ▼
Application Backend API
   │
   ▼
Backend
   │
   ├── Agent / Workflow
   │
   └── Moodle Integration Layer
           │
           ▼
      Moodle Web Service
           │
           ▼
        Moodle ITK
```

Frontend tidak memanggil Moodle secara langsung.

Agent juga tidak memanggil Moodle secara langsung.

---

### 3.3 Credential Isolation

Credential atau authentication token Moodle harus disimpan pada sisi Backend/integration layer.

Credential tidak boleh:

* diberikan kepada LLM;
* dimasukkan ke prompt;
* dimasukkan ke generated content;
* dikirim ke Frontend;
* disimpan sebagai bagian dari agent context.

Agent hanya mendapatkan tool abstraction seperti:

```text
create_course(...)
update_course(...)
get_course_contents(...)
create_activity(...)
verify_course(...)
```

Detail authentication ditangani oleh Moodle Integration Layer.

---

## 4. Moodle API Status

Moodle menyediakan Web Service API dan external functions yang dapat digunakan oleh aplikasi eksternal. Dokumentasi Moodle juga menyediakan API documentation pada Moodle instance yang sedang digunakan.

Status integrasi proyek:

| Item                                           | Status         |
| ---------------------------------------------- | -------------- |
| Moodle LMS ITK sebagai target                  | Confirmed      |
| Moodle Web Service sebagai mekanisme integrasi | Confirmed      |
| Custom ITK Moodle API                          | Not applicable |
| Application Backend API                        | Proposed       |
| Moodle Integration Layer                       | Proposed       |
| Exact Moodle functions                         | TBD            |
| Authentication mechanism                       | TBD            |
| Moodle service/token configuration             | TBD            |
| Required permissions/capabilities              | TBD            |
| Moodle version ITK                             | TBD            |

Dokumentasi resmi Moodle menunjukkan bahwa external functions memiliki parameter, return value, dan permission/capability yang harus diperhatikan ketika digunakan.

---

# 5. Integration Scope

MVP integration dibatasi pada operasi yang diperlukan untuk flow utama produk.

### In Scope

1. Mendapatkan informasi course.
2. Membuat atau memilih course target jika capability tersedia.
3. Mengelola struktur section/week.
4. Membuat learning material.
5. Membuat resource jika dibutuhkan.
6. Membuat assignment apabila diaktifkan instructor.
7. Membuat quiz apabila diaktifkan instructor dan capability tersedia.
8. Mengambil kembali struktur/content Moodle.
9. Melakukan verification.
10. Menangani error dan retry.
11. Mencatat status setiap operasi.
12. Mendukung student-side verification.

### Out of Scope

1. Modifikasi Moodle core.
2. Membuat custom Moodle API.
3. Pengelolaan seluruh fitur Moodle.
4. Pengelolaan akademik mahasiswa secara penuh.
5. Attendance/absensi.
6. Seluruh jenis Moodle activity.
7. Autonomous publishing tanpa instructor approval.
8. Pengelolaan credential dari sisi LLM.

---

# 6. Integration Flow

Flow utama:

```text
RPS
 ↓
RPS Processing
 ↓
RPS Analysis
 ↓
Course Planning
 ↓
Instructor Review
 ↓
Content Generation
 ↓
Content Validation
 ↓
Instructor Approval
 ↓
Moodle Execution
 ↓
Moodle Verification
 ↓
Student Verification
```

Moodle hanya digunakan setelah content melewati validation dan approval yang diperlukan.

---

# 7. Moodle Integration Lifecycle

## 7.1 Pre-Execution

Sebelum eksekusi ke Moodle:

1. Course plan tersedia.
2. Weekly content tersedia.
3. Required validation berhasil.
4. Instructor memberikan approval.
5. Moodle connection tersedia.
6. Credential valid.
7. Required Moodle functions tersedia.
8. Required permissions tersedia.

Jika salah satu dependency penting belum terpenuhi, execution tidak boleh dilanjutkan.

---

## 7.2 Execution

Execution dilakukan melalui controlled tools.

Contoh:

```text
Agent
  ↓
execute_moodle_operation
  ↓
Controlled Tool
  ↓
Moodle Integration Layer
  ↓
Moodle Web Service
```

Agent tidak menentukan credential atau raw HTTP request secara langsung.

---

## 7.3 Verification

Setelah execution:

```text
Moodle Execution
       ↓
Read Back Moodle
       ↓
Compare Expected vs Actual
       ↓
Verification Result
```

Verification digunakan untuk memastikan bahwa data yang diharapkan benar-benar tersedia pada Moodle.

---

# 8. Operation Mapping

Tabel berikut merupakan integration contract tingkat sistem.

**Function Moodle yang belum diverifikasi tidak boleh dianggap final.**

| Application Operation    | Moodle Target          | Required Operation | Moodle Function                                                | Status    |
| ------------------------ | ---------------------- | ------------------ | -------------------------------------------------------------- | --------- |
| Get course               | Course                 | Read               | `core_course_get_courses` / `core_course_get_courses_by_field` | Candidate |
| Create course            | Course                 | Create             | `core_course_create_courses`                                   | Candidate |
| Update course            | Course                 | Update             | `core_course_update_courses`                                   | Candidate |
| Read course content      | Course contents        | Read               | `core_course_get_contents`                                     | Candidate |
| Manage section           | Course section         | Create/Update      | TBD                                                            | TBD       |
| Create learning material | Resource/activity      | Create             | TBD                                                            | TBD       |
| Update learning material | Resource/activity      | Update             | TBD                                                            | TBD       |
| Create assignment        | Assignment             | Create             | TBD                                                            | TBD       |
| Update assignment        | Assignment             | Update             | TBD                                                            | TBD       |
| Create quiz              | Quiz                   | Create             | TBD                                                            | TBD       |
| Update quiz              | Quiz                   | Update             | TBD                                                            | TBD       |
| Read assignment          | Assignment             | Read               | `mod_assign_*`                                                 | Candidate |
| Read quiz                | Quiz                   | Read               | `mod_quiz_*`                                                   | Candidate |
| Upload file              | Moodle file storage    | Upload             | `core_files_upload` or dedicated upload endpoint               | Candidate |
| Verify course structure  | Course contents        | Read               | `core_course_get_contents`                                     | Candidate |
| Verify activity          | Activity/module        | Read               | TBD                                                            | TBD       |
| Verify student access    | Course/activity access | Read               | TBD                                                            | TBD       |

Moodle mendokumentasikan `core_course_create_courses`, `core_course_get_contents`, dan `core_course_update_courses` sebagai external functions.

Untuk file, Moodle menyediakan `core_files_upload()` dan `core_files_get_files()`, serta dedicated endpoints `/webservice/upload.php` dan `/webservice/pluginfile.php`. Dokumentasi Moodle menyarankan dedicated upload endpoint untuk kasus file besar karena base64 encoding pada web service function dapat membutuhkan memori lebih besar.

---

# 9. Course Operations

## 9.1 Course Selection

Sistem harus dapat menentukan course Moodle target.

Possible flow:

```text
Course Plan
   ↓
Search Existing Course
   ↓
Course Found?
 ┌───────┴───────┐
Yes              No
 │                │
Select           Create
 │                │
 └───────┬────────┘
         ↓
     Course Target
```

Course matching tidak boleh hanya berdasarkan nama jika terdapat identifier yang lebih reliable.

Candidate identifiers:

* Moodle course ID.
* Shortname.
* ID number.

Moodle menyediakan fungsi untuk mengambil course berdasarkan field tertentu seperti ID, shortname, ID number, atau category.

---

## 9.2 Course Creation

Jika course baru dibuat:

```text
Validated Course Plan
        ↓
Create Moodle Course
        ↓
Receive Moodle Course ID
        ↓
Persist Mapping
```

Sistem internal harus menyimpan mapping:

```text
Internal Course ID
        ↕
Moodle Course ID
```

`core_course_create_courses` tercantum pada dokumentasi Moodle sebagai fungsi untuk membuat course baru. Namun keberadaan fungsi pada dokumentasi tidak berarti token/service ITK otomatis memiliki akses untuk menggunakannya. Permission dan service configuration tetap harus diverifikasi.

---

# 10. Section / Weekly Structure

Course plan dapat memiliki struktur:

```text
Course
 ├── Week 1
 ├── Week 2
 ├── Week 3
 ├── ...
 └── Week N
```

Target umum proyek adalah hingga 16 minggu, tetapi jumlah aktual harus mengikuti RPS.

Sistem tidak boleh memaksakan 16 minggu jika RPS tidak menggunakan struktur tersebut.

### Requirement

Moodle Integration Layer harus menyediakan abstraction:

```text
create_section()
update_section()
get_sections()
```

Implementasi actual Moodle function masih `TBD`.

Dokumentasi Moodle yang diperiksa menyediakan `core_course_edit_section` untuk melakukan tindakan pada existing section, tetapi kebutuhan create-section harus diverifikasi terhadap versi dan konfigurasi Moodle ITK.

---

# 11. Learning Material

Learning material merupakan aktivitas utama MVP.

Contoh representasi internal:

```json
{
  "type": "learning_material",
  "title": "Pengantar Basis Data",
  "description": "...",
  "content": "...",
  "week": 1
}
```

Integration Layer bertanggung jawab menerjemahkan representasi internal tersebut menjadi resource/activity Moodle yang sesuai.

Possible Moodle representations:

* Page
* Resource/file
* Book
* Other supported resource

Jenis final harus dipilih berdasarkan kebutuhan MVP dan capability Moodle ITK.

Dokumentasi Moodle mencantumkan fungsi pembacaan untuk Page dan Resource, tetapi fungsi create/update yang diperlukan untuk automation harus diverifikasi pada environment target.

---

# 12. Assignment

Assignment bersifat optional.

Instructor menentukan apakah assignment perlu dibuat:

```json
{
  "learning_material": true,
  "assignment": true,
  "quiz": false
}
```

Jika:

```text
assignment = false
```

agent tidak boleh membuat assignment.

Jika:

```text
assignment = true
```

maka assignment harus:

1. berasal dari content plan;
2. lolos validation;
3. disetujui instructor;
4. dikirim melalui integration layer;
5. diverifikasi setelah execution.

Moodle mendokumentasikan sejumlah `mod_assign` functions, termasuk fungsi untuk membaca assignment dan submission-related information. Namun fungsi create/update yang diperlukan untuk automated creation harus dikonfirmasi pada Moodle ITK sebelum implementation dikunci.

---

# 13. Quiz

Quiz juga optional.

Jika instructor tidak mengaktifkan quiz:

```text
quiz = false
```

maka sistem tidak membuat quiz.

Jika quiz diaktifkan, sistem perlu mendukung minimal:

```text
Quiz
 ├── Title
 ├── Description
 ├── Questions
 ├── Question type
 ├── Answer options
 ├── Correct answer
 └── Basic grading configuration
```

Moodle menyediakan sejumlah `mod_quiz` web service functions, terutama untuk access information, quiz retrieval, attempts, dan review. Namun kemampuan create quiz dan question melalui Web Service harus diverifikasi pada instance ITK sebelum dijadikan implementation dependency.

Karena itu:

**Quiz creation = Dependency / TBD untuk MVP sampai capability Moodle ITK dikonfirmasi.**

---

# 14. File Handling

File dapat digunakan untuk:

* learning resources;
* generated supporting material;
* references jika diperlukan.

Moodle menyediakan web service functions untuk upload/fetch file dan dedicated file endpoints.

Abstraction internal:

```text
upload_file()
get_file()
```

Integration Layer memilih mekanisme aktual berdasarkan ukuran file dan kemampuan Moodle service.

Untuk MVP, file handling harus dibuat sederhana dan tidak menjadi dependency utama jika learning material dapat disimpan sebagai HTML/text content.

---

# 15. Student Verification

Student role digunakan untuk memastikan hasil yang dibuat sistem dapat dilihat dari perspektif learner.

Verification minimum:

```text
Course visible?
       ↓
Section visible?
       ↓
Learning material visible?
       ↓
Assignment visible if enabled?
       ↓
Quiz visible if enabled?
```

Verification tidak hanya memeriksa apakah Moodle mengembalikan HTTP success.

Verification harus membandingkan:

```text
Expected Structure
        vs
Actual Moodle Structure
```

Contoh:

```text
Expected:
Week 1
 ├── Material A
 └── Assignment A

Actual:
Week 1
 ├── Material A
 └── Assignment A

Result:
PASS
```

Jika berbeda:

```text
Result:
FAIL / PARTIAL
```

dan sistem harus mencatat discrepancy.

---

# 16. Verification Model

Verification result:

```json
{
  "status": "PASS",
  "course_id": "internal-course-id",
  "moodle_course_id": 123,
  "checks": [
    {
      "target": "course",
      "status": "PASS"
    },
    {
      "target": "week_1",
      "status": "PASS"
    },
    {
      "target": "material_1",
      "status": "PASS"
    }
  ]
}
```

Possible status:

* `PASS`
* `PARTIAL`
* `FAIL`
* `UNKNOWN`

`UNKNOWN` digunakan ketika sistem tidak memiliki kemampuan cukup untuk memverifikasi suatu property.

---

# 17. Error Handling

Moodle integration harus membedakan jenis error.

### Authentication Error

Contoh:

```text
Invalid token
Expired credential
Unauthorized service
```

Action:

```text
STOP
→ Record error
→ Notify instructor/admin
```

Tidak dilakukan blind retry.

---

### Permission Error

Contoh:

```text
Function unavailable for current user
Missing capability
```

Action:

```text
STOP operation
→ Record exact operation
→ Mark dependency issue
```

---

### Validation Error

Input tidak sesuai dengan requirement Moodle.

Action:

```text
Do not send request
→ Return validation error
```

---

### Transient Error

Contoh:

```text
Timeout
Temporary network failure
Temporary Moodle availability issue
```

Action:

```text
Retry with bounded retry policy
```

---

### Execution Error

Moodle menerima request tetapi operasi gagal.

Action:

```text
Record Moodle response
→ Determine whether retry is safe
→ Retry or escalate
```

---

# 18. Retry Policy

Retry tidak boleh dilakukan secara membabi buta.

Operation harus diklasifikasikan:

| Operation              | Retry                                  |
| ---------------------- | -------------------------------------- |
| Read operation         | Generally safe                         |
| Create operation       | Only if idempotency can be established |
| Update operation       | Usually retryable with safeguards      |
| Delete operation       | Requires strong safeguards             |
| Authentication failure | No automatic retry                     |
| Permission failure     | No automatic retry                     |

---

# 19. Idempotency

Idempotency penting karena agent workflow dapat mengalami retry.

Contoh masalah:

```text
Agent
 ↓
Create Assignment
 ↓
Moodle creates assignment
 ↓
Network timeout
 ↓
Agent assumes failure
 ↓
Retry
 ↓
Duplicate Assignment
```

Sistem harus mencegah kondisi tersebut.

Internal mapping harus menyimpan:

```text
Internal Activity ID
        ↕
Moodle Module ID
```

Sebelum create:

```text
Does mapping already exist?
       ↓
Yes → Verify/update existing object
No  → Create
```

---

# 20. Execution State

Moodle execution menggunakan state terpisah dari agent state.

Contoh:

```text
PENDING
 ↓
RUNNING
 ↓
SUCCESS
```

Failure states:

```text
FAILED
RETRYING
BLOCKED
```

Conceptual model:

```json
{
  "execution_id": "...",
  "course_id": "...",
  "operation": "create_material",
  "target_id": "...",
  "status": "SUCCESS",
  "moodle_object_id": 123
}
```

---

# 21. Controlled Tool Contract

Agent hanya melihat high-level tools.

Contoh:

```text
moodle.get_course()
moodle.create_course()
moodle.update_course()
moodle.get_course_contents()
moodle.create_section()
moodle.create_learning_material()
moodle.create_assignment()
moodle.create_quiz()
moodle.verify_course()
```

Tool implementation:

```text
Agent Tool
    ↓
Input Validation
    ↓
Authorization Check
    ↓
Moodle Adapter
    ↓
Moodle Web Service
```

Agent tidak diperbolehkan:

```text
LLM → raw Moodle URL
LLM → Moodle token
LLM → arbitrary HTTP request
```

---

# 22. Authorization

Application authorization dan Moodle authorization merupakan dua layer berbeda.

```text
Application Authorization
        ↓
Can this user perform this operation?
        ↓
Moodle Integration
        ↓
Moodle Authorization
        ↓
Can Moodle token/user perform this function?
```

Sistem tidak boleh mengasumsikan bahwa user yang dapat melakukan suatu operasi pada aplikasi otomatis memiliki capability yang sama di Moodle.

Moodle external functions dapat memiliki capability requirements yang perlu diperiksa.

---

# 23. Moodle Configuration Dependency

Sebelum integration dianggap ready, tim harus memperoleh informasi dari administrator Moodle ITK:

1. Moodle version.
2. Web services enabled.
3. Protocol yang digunakan.
4. Service yang tersedia.
5. External functions yang tersedia.
6. Authentication/token mechanism.
7. User account yang digunakan integration.
8. Required capabilities.
9. Course creation permission.
10. Section modification permission.
11. Activity creation permission.
12. File upload permission.
13. Assignment capability.
14. Quiz capability.
15. Student test account.
16. Test course/sandbox.

Tanpa informasi tersebut, implementation Moodle tertentu harus dianggap `TBD`.

---

# 24. Moodle Integration Test Environment

Development sebaiknya tidak langsung bergantung pada production course.

Minimum environment:

```text
Capstone Backend
      ↓
Moodle Test/Sandbox
      ↓
Test Course
      ↓
Test Instructor
      ↓
Test Student
```

Test environment digunakan untuk:

* API discovery;
* authentication testing;
* permission testing;
* course creation testing;
* content creation testing;
* verification testing;
* retry testing.

---

# 25. Mock / Adapter Strategy

Jika Moodle ITK belum dapat digunakan, development tidak boleh berhenti.

Gunakan abstraction:

```text
IMoodleService
      │
      ├── MoodleService
      │
      └── MockMoodleService
```

Example:

```text
Agent
 ↓
Moodle Tool
 ↓
IMoodleService
 ↓
 ┌─────────────────┐
 │                 │
MoodleService   MockMoodleService
 │                 │
Moodle ITK       Local Test
```

Mock harus mengikuti contract yang sama dengan implementation sebenarnya.

Tujuannya bukan membuat fake Moodle yang lengkap, tetapi memungkinkan:

* agent development;
* workflow development;
* state management;
* validation;
* monitoring;
* retry;
* frontend development;

tetap berjalan sebelum Moodle dependency tersedia.

---

# 26. Data Mapping

Minimal mapping yang perlu disimpan:

| Internal Entity      | Moodle Entity                    |
| -------------------- | -------------------------------- |
| Course               | Course                           |
| Course Plan Week     | Section                          |
| Content              | Course Module / Resource         |
| Assignment           | Assignment Module                |
| Quiz                 | Quiz Module                      |
| Resource File        | Moodle File                      |
| Student Verification | Moodle User/Course/Module access |

Mapping actual ID harus disimpan pada database.

Contoh:

```text
course.id
moodle_course_id

content.id
moodle_cmid

activity.id
moodle_instance_id
```

---

# 27. Observability

Setiap Moodle operation harus menghasilkan event.

Contoh:

```json
{
  "event": "MOODLE_OPERATION_COMPLETED",
  "operation": "create_learning_material",
  "course_id": "...",
  "target_id": "...",
  "status": "SUCCESS",
  "timestamp": "..."
}
```

Event digunakan oleh monitoring UI.

Monitoring UI tidak membaca state langsung dari Moodle atau LLM.

Architecture:

```text
Moodle Integration
       ↓
Execution Event
       ↓
Backend Event Store
       ↓
WebSocket / Realtime Channel
       ↓
Monitoring UI
```

---

# 28. Security Requirements

### Credential

Credential Moodle:

* encrypted/protected at rest;
* tidak masuk database sebagai plain text jika dapat dihindari;
* tidak masuk log;
* tidak masuk WebSocket event;
* tidak masuk LLM context.

### Logging

Log harus menghindari:

```text
Moodle token
Password
Authorization header
Sensitive user information
```

### LLM Isolation

LLM hanya mendapatkan data yang diperlukan untuk reasoning dan generation.

LLM tidak menerima:

```text
Moodle token
Moodle password
Raw authentication header
```

---

# 29. Integration Sequence

## 29.1 Course Execution

```text
Instructor Approves
       ↓
Backend starts execution
       ↓
Find/Create Moodle Course
       ↓
Store Moodle Course ID
       ↓
Create/Update Sections
       ↓
Create Learning Materials
       ↓
Create Optional Activities
       ↓
Read Back Moodle
       ↓
Verify
       ↓
Complete / Retry / Fail
```

---

## 29.2 Single Content Retry

Retry tidak harus mengulang seluruh course.

Contoh:

```text
Week 5
 ├── Material A ✓
 ├── Material B ✗
 └── Assignment C ✓
```

Jika Material B gagal:

```text
Retry Material B
```

bukan:

```text
Regenerate entire course
```

Hal ini mengurangi execution cost dan risiko duplicate content.

---

# 30. Failure Boundary

Integration boundary:

```text
Agent Failure
      │
      ▼
Backend Workflow
      │
      ▼
Moodle Integration Failure
      │
      ▼
Moodle Web Service Failure
      │
      ▼
Moodle LMS
```

Setiap layer harus memiliki error representation sendiri.

Agent tidak boleh menerima raw low-level error sebagai satu-satunya context.

Contoh:

```text
Raw:
HTTP 403

Normalized:
MOODLE_PERMISSION_DENIED

Meaning:
The configured Moodle service/user does not have
permission to perform this operation.
```

---

# 31. MVP Integration Boundary

MVP tidak perlu mendukung seluruh Moodle.

Prioritas:

### Must Have

* Connect to Moodle.
* Authenticate.
* Identify target course.
* Read course.
* Read course contents.
* Manage required weekly structure.
* Create learning material.
* Execute approved content.
* Verify generated content.
* Error handling.
* Execution status.
* Student-side verification.

### Should Have

* Assignment creation.
* Quiz creation.
* File resources.
* Partial retry.
* Update existing content.

### Could Have

* More Moodle activity types.
* Advanced grading configuration.
* Complex question bank operations.
* Advanced course configuration.

### Won't Have

* Attendance.
* Full Moodle administration.
* Full student management.
* Moodle core modification.
* Autonomous uncontrolled publishing.

---

# 32. Open Technical Decisions

| Decision                          | Status    |
| --------------------------------- | --------- |
| Moodle version ITK                | TBD       |
| Web Service protocol              | TBD       |
| Authentication mechanism          | TBD       |
| Token/service configuration       | TBD       |
| Required Moodle capabilities      | TBD       |
| Course creation capability        | TBD       |
| Section creation capability       | TBD       |
| Learning material creation method | TBD       |
| Assignment creation method        | TBD       |
| Quiz creation method              | TBD       |
| Question creation method          | TBD       |
| File upload strategy              | Candidate |
| Student verification mechanism    | TBD       |
| Moodle test environment           | TBD       |

---

# 33. Required Action Before Implementation

Tim integration harus melakukan API discovery terhadap Moodle ITK.

Checklist:

```text
[ ] Moodle version obtained
[ ] Web services enabled
[ ] Protocol confirmed
[ ] Authentication confirmed
[ ] Test integration account obtained
[ ] API documentation accessed
[ ] Available functions exported/recorded
[ ] Required capabilities mapped
[ ] Course creation tested
[ ] Section operation tested
[ ] Material creation tested
[ ] Assignment creation tested
[ ] Quiz creation tested
[ ] File upload tested
[ ] Student access tested
[ ] Verification tested
```

Moodle menyediakan API documentation pada live Moodle site melalui area administrasi Web Services, sehingga daftar fungsi dari instance ITK sebaiknya dijadikan source of truth untuk implementasi final, bukan hanya daftar fungsi generik pada dokumentasi.

---

# 34. Definition of Integration Ready

Moodle integration dianggap **Ready for MVP Implementation** apabila:

1. Moodle version diketahui.
2. Web Service aktif.
3. Authentication berhasil.
4. Test account tersedia.
5. Required functions teridentifikasi.
6. Required capabilities teridentifikasi.
7. Course read berhasil.
8. Required write operations berhasil.
9. Student verification berhasil.
10. Error handling telah diuji.
11. Mapping internal ID ↔ Moodle ID telah ditentukan.
12. Mock implementation tersedia untuk operasi yang belum dapat diuji.

---

# 35. Architecture Summary

Final integration architecture:

```text
┌───────────────────────────────┐
│          Web App              │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│    Application Backend API    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Backend / Agent Orchestrator  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     Controlled Tool Layer     │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│   Moodle Integration Layer    │
│                               │
│ - Auth                        │
│ - Validation                  │
│ - Mapping                     │
│ - Retry                       │
│ - Idempotency                 │
│ - Error Normalization         │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│    Moodle Web Service API     │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│         Moodle LMS ITK        │
└───────────────────────────────┘
```

---

# 36. Design Decision

The project will **not assume that every Moodle operation required by the product is directly available through the standard Web Service functions**.

The integration layer therefore remains an abstraction boundary.

If an operation is unavailable:

```text
Moodle capability unavailable
          ↓
Do not bypass security
Do not let LLM access Moodle directly
Do not invent an API
          ↓
Use supported alternative / mock / defer feature
```

This keeps the core agent architecture independent from uncertain Moodle capabilities.

---

# 37. Related Documents

* `project-charter.md`
* `prd.md`
* `system-design.md`
* `api-specification.md`
* `data-model.md` — next
* `agent-design.md`
* `content-schema.md`
* `testing-quality.md`

---

# 38. Document Status

**Status: Proposed**

The architecture and integration boundary are established.

The following remain dependent on direct Moodle ITK verification:

* exact Moodle functions;
* authentication;
* service configuration;
* permissions;
* activity creation mechanisms;
* quiz/question creation;
* student verification mechanism.

These items must not be converted from `TBD` to `Confirmed` until verified against the Moodle ITK environment.
