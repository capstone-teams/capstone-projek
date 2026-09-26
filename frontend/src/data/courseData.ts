import type {
  SyllabusWeek,
  DosenCourse,
  MahasiswaCourse,
  RpsAnalysisData,
  MaterialDocument,
} from '../types/course'

export const WEEKS_DATA: SyllabusWeek[] = [
  { weekNumber: 1, title: 'Sistem Persamaan Linear dan Matriks', duration: '3 SKS · Minggu 01', status: 'moodle' },
  { weekNumber: 2, title: 'Operasi Matriks, Determinan, dan Invers', duration: '3 SKS · Minggu 02', status: 'moodle' },
  { weekNumber: 3, title: 'Determinan & Invers Matriks (OBE & Kofaktor)', duration: '3 SKS · Minggu 03', status: 'moodle' },
  { weekNumber: 4, title: 'Evaluasi Pembelajaran (Kuis 1)', duration: '3 SKS · Minggu 04', status: 'approved' },
  { weekNumber: 5, title: 'Vektor dan Operasi Vektor', duration: '3 SKS · Minggu 05', status: 'approved' },
  { weekNumber: 6, title: 'Spanning Set, Linear Independence, Transformasi Linier', duration: '3 SKS · Minggu 06', status: 'approved' },
  { weekNumber: 7, title: 'Transformasi Linier pada Vektor', duration: '3 SKS · Minggu 07', status: 'approved' },
  { weekNumber: 8, title: 'Ujian Tengah Semester (UTS)', duration: '3 SKS · Minggu 08', status: 'approved' },
  { weekNumber: 9, title: 'Ruang Vektor, Vektor Basis, Dimensi, Rank', duration: '3 SKS · Minggu 09', status: 'approved' },
  { weekNumber: 10, title: 'Basis, Dimensi, dan Rank Matriks', duration: '3 SKS · Minggu 10', status: 'approved' },
  { weekNumber: 11, title: 'Basis Ortogonal dan Basis Ortonormal', duration: '3 SKS · Minggu 11', status: 'approved' },
  { weekNumber: 12, title: 'Evaluasi Pembelajaran (Kuis 2)', duration: '3 SKS · Minggu 12', status: 'approved' },
  { weekNumber: 13, title: 'Nilai Eigen, Vektor Eigen, dan Diagonalisasi', duration: '3 SKS · Minggu 13', status: 'approved' },
  { weekNumber: 14, title: 'Diagonalisasi Matriks', duration: '3 SKS · Minggu 14', status: 'approved' },
  { weekNumber: 15, title: 'Pra Ujian Akhir Semester (Pra UAS)', duration: '3 SKS · Minggu 15', status: 'approved' },
  { weekNumber: 16, title: 'Ujian Akhir Semester (UAS)', duration: '3 SKS · Minggu 16', status: 'approved' },
]

export const DOSEN_COURSES: DosenCourse[] = [
  {
    code: 'IF201405',
    name: 'Aljabar Linear dan Geometri',
    sks: '3 SKS · 16 pertemuan',
    semester: 'Semester III (Tiga)',
    badge: 'Course Plan siap',
    badgeType: 'moodle',
    progress: '16 pertemuan terpetakan',
  },
  {
    code: 'IF302',
    name: 'Pemrograman Web',
    sks: '3 SKS · 16 pertemuan',
    semester: 'Semester Gasal 2026/2027',
    badge: 'Draft',
    badgeType: 'draft',
    progress: 'Siap disusun',
  },
  {
    code: 'IF201',
    name: 'Basis Data',
    sks: '3 SKS · 16 pertemuan',
    semester: 'Semester Gasal 2026/2027',
    badge: 'Disetujui',
    badgeType: 'approved',
    progress: 'Konten lengkap',
  },
]

export const MAHASISWA_COURSES: MahasiswaCourse[] = [
  {
    code: 'IF201405',
    name: 'Aljabar Linear dan Geometri',
    dosen: 'Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.',
    sks: '3 SKS',
    available: '3 pertemuan tersedia',
    badge: 'Tersedia di Moodle',
    badgeType: 'moodle',
  },
  {
    code: 'IF302',
    name: 'Pemrograman Web',
    dosen: 'Ahmad Fauzi, M.T.',
    sks: '3 SKS',
    available: '2 pertemuan tersedia',
    badge: 'Tersedia di Moodle',
    badgeType: 'moodle',
  },
  {
    code: 'IF201',
    name: 'Basis Data',
    dosen: 'Nurul Hidayah, M.Kom.',
    sks: '3 SKS',
    available: '1 pertemuan tersedia',
    badge: 'Tersedia',
    badgeType: 'approved',
  },
]

export const RPS_ANALYSIS_DATA: RpsAnalysisData = {
  courseCode: 'IF201405',
  courseName: 'Aljabar Linear dan Geometri',
  sks: 3,
  semester: 'Semester III (Tiga) · Tahun Ajaran 2020 - 2025',
  totalWeeks: 16,
  programStudi: 'S1 Informatika · Institut Teknologi Kalimantan',
  dosenPengampu: 'Ramadhan Paninggalih S.Si., M.Si., M.Sc.',
  koordinatorProdi: 'Nisa Rizqiya Fadhliana, S.Kom., M.T.',
  tanggalPenyusunan: '16 Juli 2023',
  deskripsiSingkat:
    'Pada mata kuliah ini, mahasiswa diharapkan mampu menerapkan konsep dasar dari Aljabar Linear dengan baik dan benar dalam kehidupan sehari-hari.',
  targetCpl: [
    'CPL 2. Mampu mengidentifikasi, merumuskan, menganalisa, menyelesaikan permasalahan kompleks, serta mengambil keputusan dengan mempertimbangkan dampaknya pada aspek hukum, ekonomi, lingkungan, sosial, politik, kesehatan, keselamatan, dan keberlanjutan serta memanfaatkan teknologi informasi dan potensi sumber daya nasional dalam perspektif global.',
    'CPL 5. Mampu menunjukkan kemampuan belajar sepanjang hayat dan menerapkan pengetahuan tersebut sesuai kebutuhan dengan strategi pembelajaran yang tepat.',
    'CPL 6. Mampu memahami konsep matematika, statistika, struktur diskrit, struktur data dan algoritma, dalam menyelesaikan berbagai masalah berkaitan dengan keteknikan dengan prinsip-prinsip komputasi secara efektif dan efisien.',
    'CPL 12. Mampu menerapkan etika profesional bidang ilmu komputer.',
  ],
  cpmkList: [
    '1. Mahasiswa mampu memahami konsep Sistem Persamaan Linear (SPL) dan konsep matriks',
    '2. Mahasiswa mampu menjelaskan konsep determinan dari suatu matriks dan karakteristiknya',
    '3. Mahasiswa mampu memahami konsep Ruang Vektor Euclid',
    '4. Mahasiswa mampu memahami dan menjelaskan konsep Ruang Vektor secara umum',
    '5. Mahasiswa mampu menjelaskan konsep mengenai Transformasi Linear dan mampu memberikan contoh sederhana dalam bidang informatika',
    '6. Mahasiswa mampu memahami konsep dari Aljabar Geometri, karakteristik serta operasi yang ada didalamnya',
    '7. Mahasiswa mampu menjelaskan konsep Pencerminan dan Rotasi',
    '8. Mahasiswa mampu menjelaskan aplikasi dari Aljabar Geometri dalam bidang Informatika',
  ],
  cpmkCount: 8,
  fileName: 'RPS_Aljabar_Linear_dan_Geometri.pdf',
  fileSize: '3.1 MB · Terverifikasi',
  extractedAt: '16 Juli 2023 (Dokumen No. 01 / Revisi 01)',
  weeklyPlans: [
    {
      weekNumber: 1,
      subCpmk:
        '1. Mahasiswa mampu menentukan solusi dari Sistem Persamaan Linear (SPL) melalui interpretasi matriks',
      bahanKajian: [
        'a. Sistem Persamaan Linier (SPL)',
        'b. Eliminasi Gauss dalam menyelesaikan SPL',
        'c. Eliminasi Gauss-Jordan dalam menyelesaikan SPL',
      ],
    },
    {
      weekNumber: 2,
      subCpmk:
        '2. Mahasiswa mampu melakukan operasi matriks, determinan, dan invers matriks.',
      bahanKajian: [
        'a. Operasi penjumlahan dan pengurangan pada matriks',
        'b. Operasi perkalian pada matriks',
      ],
    },
    {
      weekNumber: 3,
      subCpmk:
        'Mahasiswa mampu menentukan determinan dan invers matriks menggunakan Operasi Baris Elementer (OBE) dan kofaktor.',
      bahanKajian: [
        'a. Determinan matriks menggunakan Operasi Baris Elementer (OBE) dan kofaktor',
        'b. Invers matriks menggunakan Operasi Baris Elementer (OBE) dan kofaktor',
      ],
    },
    {
      weekNumber: 4,
      subCpmk: 'Evaluasi Pembelajaran (Kuis 1)',
      bahanKajian: [
        'Materi Minggu 1 s.d. 3 (Sistem Persamaan Linier, Operasi Matriks, Determinan, dan Invers Matriks)',
      ],
    },
    {
      weekNumber: 5,
      subCpmk: '3. Mahasiswa mampu melakukan operasi pada vektor.',
      bahanKajian: [
        'a. Vektor',
        'b. Norm, jarak, dot product, ortogonalitas, dan cross product',
      ],
    },
    {
      weekNumber: 6,
      subCpmk:
        '4. Mahasiswa mampu mengidentifikasi Spanning Set, Linear Independence dan transformasi linier pada vektor.',
      bahanKajian: [
        'a. Kombinasi Linier',
        'b. Spanning Set',
        'c. Linear Independence',
      ],
    },
    {
      weekNumber: 7,
      subCpmk: 'Mahasiswa mampu menentukan transformasi linier pada vektor.',
      bahanKajian: ['a. Transformasi linier'],
    },
    {
      weekNumber: 8,
      subCpmk: 'Evaluasi Tengah Semester: Ujian Tengah Semester (UTS)',
      bahanKajian: [
        'Evaluasi Capaian Pembelajaran Materi Perkuliahan Minggu 1 s.d. 7',
      ],
    },
    {
      weekNumber: 9,
      subCpmk:
        '5. Mahasiswa mampu menentukan ruang vektor, vektor basis, dimensi, dan rank pada matriks.',
      bahanKajian: ['a. Ruang Vektor', 'b. Sub Ruang Vektor'],
    },
    {
      weekNumber: 10,
      subCpmk:
        'Mahasiswa mampu menentukan basis, dimensi dan rank pada matriks.',
      bahanKajian: ['a. Basis', 'b. Dimensi', 'c. Rank matriks'],
    },
    {
      weekNumber: 11,
      subCpmk:
        '6. Mahasiswa mampu menentukan basis ortogonal dan basis ortonormal.',
      bahanKajian: [
        'a. Ruang hasil kali dalam',
        'b. Basis ortogonal',
        'c. Basis ortonormal',
      ],
    },
    {
      weekNumber: 12,
      subCpmk: 'Evaluasi Pembelajaran (Kuis 2)',
      bahanKajian: [
        'Materi Minggu 9 s.d. 11 (Ruang Vektor, Basis, Dimensi, Rank, Basis Ortogonal & Ortonormal)',
      ],
    },
    {
      weekNumber: 13,
      subCpmk:
        '7. Mahasiswa mampu menentukan nilai eigen, vektor eigen dan diagonalisasi pada suatu matriks.',
      bahanKajian: ['a. Nilai eigen', 'b. Vektor eigen'],
    },
    {
      weekNumber: 14,
      subCpmk: 'Mahasiswa mampu menentukan diagonalisasi matriks.',
      bahanKajian: ['a. Diagonalisasi matriks'],
    },
    {
      weekNumber: 15,
      subCpmk: 'Pra Ujian Akhir Semester (Pra UAS)',
      bahanKajian: [
        'Pembahasan studi kasus komprehensif dan latihan persiapan UAS',
      ],
    },
    {
      weekNumber: 16,
      subCpmk: 'Evaluasi Akhir Semester: Ujian Akhir Semester (UAS)',
      bahanKajian: [
        'Evaluasi Capaian Pembelajaran Semester (Materi Perkuliahan Minggu 9 s.d. 14)',
      ],
    },
  ],
}

export const WEEKLY_MATERIALS_DATA: Record<string, MaterialDocument> = {
  'doc-week2-pdf': {
    id: 'doc-week2-pdf',
    weekNumber: 2,
    title: 'Pengantar & Operasi Dasar Matriks.pdf',
    fileType: 'pdf',
    fileSize: '2.8 MB',
    uploadedDate: '18 Agu 2026',
    estimatedTime: '30 Menit Baca',
    description:
      'Modul materi ajar mengenai definisi matriks, ordo, operasi penjumlahan, perkalian skalar, dan perkalian antar matriks berordo m × n.',
    subCpmkRef:
      'Sub-CPMK 2: Mampu melakukan operasi dasar matriks dan memodelkan representasi sistem persamaan linear.',
    sections: [
      {
        heading: '1. Definisi dan Notasi Matriks',
        content:
          'Matriks adalah susunan bilangan, simbol, atau ekspresi dalam baris dan kolom persegi panjang. Ukuran atau ordo matriks dinyatakan m × n, di mana m adalah baris dan n adalah kolom.',
        formula: 'A = [a_{ij}] \\in \\mathbb{R}^{m \\times n}',
      },
      {
        heading: '2. Operasi Penjumlahan & Pengurangan',
        content:
          'Dua matriks dapat dijumlahkan atau dikurangkan jika dan hanya jika keduanya memiliki ordo yang sama. Operasi dilakukan pada setiap elemen seletak.',
        formula: 'C = A \\pm B \\iff c_{ij} = a_{ij} \\pm b_{ij}',
      },
      {
        heading: '3. Perkalian Skalar dan Perkalian Matriks',
        content:
          'Perkalian matriks A berordo m × k dengan B berordo k × n menghasilkan C berordo m × n. Syarat: jumlah kolom matriks pertama harus sama dengan jumlah baris matriks kedua.',
        formula: 'c_{ij} = \\sum_{r=1}^{k} a_{ir} b_{rj}',
      },
      {
        heading: '4. Matriks Transpose dan Sifat Aljabar',
        content:
          'Transpose matriks A (dinotasikan A^T) didapat dengan menukar baris menjadi kolom. Sifat penting: (A + B)^T = A^T + B^T dan (AB)^T = B^T A^T.',
        formula: '(AB)^T = B^T A^T',
      },
    ],
    exercisePrompt:
      'Diberikan matriks A berordo 2×3 dan B berordo 3×2. Hitunglah hasil perkalian matriks AB dan BA!',
  },
  'doc-week2-ppt': {
    id: 'doc-week2-ppt',
    weekNumber: 2,
    title: 'Slide Perkuliahan: Sistem Persamaan Linear.pptx',
    fileType: 'ppt',
    fileSize: '4.5 MB',
    uploadedDate: '18 Agu 2026',
    estimatedTime: '20 Slide Presentasi',
    description:
      'Slide presentasi perkuliahan bab Sistem Persamaan Linear (SPL), bentuk matriks teraugmentasi, dan pengantar eliminasi Gauss.',
    subCpmkRef:
      'Sub-CPMK 2: Mampu memodelkan SPL ke dalam bentuk matriks augmented.',
    sections: [
      {
        heading: '1. Representasi SPL dalam Bentuk Matriks',
        content:
          'Sistem Persamaan Linear dengan m persamaan dan n variabel dapat dituliskan ringkas dalam bentuk perkalian matriks Ax = b.',
        formula: 'A x = b',
      },
      {
        heading: '2. Matriks Teraugmentasi (Augmented Matrix)',
        content:
          'Matriks augmentasi menggabungkan koefisien variabel dan konstanta ruas kanan [A | b] untuk mempermudah eksekusi algoritma eliminasi.',
        formula: '[A \\mid b] = \\begin{bmatrix} a_{11} & a_{12} & \\dots & a_{1n} & | & b_1 \\\\ a_{21} & a_{22} & \\dots & a_{2n} & | & b_2 \\end{bmatrix}',
      },
      {
        heading: '3. Tiga Operasi Baris Elementer (OBE)',
        content:
          '1) Menukar posisi dua baris.\n2) Mengalikan baris dengan konstanta bukan nol.\n3) Menjumlahkan kelipatan satu baris ke baris lainnya.',
      },
    ],
  },
  'doc-week2-task': {
    id: 'doc-week2-task',
    weekNumber: 2,
    title: 'Latihan Mandiri 01: Eliminasi Gauss-Jordan.pdf',
    fileType: 'assignment',
    fileSize: '1.2 MB',
    uploadedDate: '19 Agu 2026',
    estimatedTime: 'Tenggat: Minggu Depan',
    description:
      'Lembar tugas latihan mandiri penyelesaian sistem persamaan linear 3 variabel menggunakan Operasi Baris Elementer Gauss-Jordan.',
    subCpmkRef:
      'Sub-CPMK 2: Mampu menyelesaikan SPL dengan metode eliminasi Gauss-Jordan.',
    sections: [
      {
        heading: 'Petunjuk Latihan Mandiri',
        content:
          'Selesaikan sistem persamaan linear berikut menggunakan eliminasi Gauss-Jordan hingga diperoleh bentuk eselon baris tereduksi (RREF). Tuliskan notasi operasi baris elementer pada tiap langkah.',
      },
      {
        heading: 'Soal SPL 3 Variabel',
        content:
          '1) 2x + y - z = 8\n2) -3x - y + 2z = -11\n3) -2x + y + 2z = -3\nTentukan solusi tunggal untuk x, y, dan z!',
      },
    ],
    exercisePrompt:
      'Kumpulkan berkas pengerjaan dalam format PDF melalui laman penugasan LMS ITK sebelum pertemuan Minggu 03 dimulai.',
  },
  'doc-week3-pdf': {
    id: 'doc-week3-pdf',
    weekNumber: 3,
    title: 'Modul Lengkap: Determinan & Invers Matriks.pdf',
    fileType: 'pdf',
    fileSize: '3.4 MB',
    uploadedDate: '25 Agu 2026',
    estimatedTime: '35 Menit Baca',
    description:
      'Modul komprehensif determinan matriks dengan metode reduksi baris, ekspansi kofaktor Laplace, matriks adjoin, dan pencarian invers non-singular.',
    subCpmkRef:
      'Sub-CPMK 2: Menghitung determinan dengan reduksi baris elementer dan ekspansi kofaktor, serta menentukan invers matriks non-singular.',
    sections: [
      {
        heading: '1. Konsep Determinan Matriks Persegi',
        content:
          'Determinan adalah nilai skalar unik yang dihitung dari elemen-elemen matriks persegi. Nilai determinan menentukan apakah suatu matriks memiliki invers (non-singular, det != 0) atau tidak (singular, det = 0).',
        formula: '\\det(A) = |A|',
      },
      {
        heading: '2. Metode Ekspansi Kofaktor Laplace',
        content:
          'Determinan matriks berordo n × n dapat dihitung dengan menjumlahkan hasil kali elemen-elemen dari sembarang baris atau kolom dengan kofaktor-kofaktor yang bersesuaian.',
        formula: '\\det(A) = \\sum_{j=1}^{n} a_{ij} C_{ij}, \\quad C_{ij} = (-1)^{i+j} M_{ij}',
      },
      {
        heading: '3. Menentukan Invers dengan Matriks Adjoin',
        content:
          'Matriks adjoin adalah transpose dari matriks kofaktor C. Invers matriks A non-singular dapat dihitung langsung menggunakan rumus determinan dan adjoin.',
        formula: 'A^{-1} = \\frac{1}{\\det(A)} \\operatorname{Adj}(A)',
      },
      {
        heading: '4. Algoritma Invers dengan Operasi Baris Elementer (OBE)',
        content:
          'Metode Gauss-Jordan menyusun matriks berdampingan [A | I]. Dengan menerapkan serangkaian OBE hingga sisi kiri menjadi matriks identitas I, maka sisi kanan otomatis menjadi A^-1.',
        formula: '[A \\mid I] \\xrightarrow{\\text{OBE}} [I \\mid A^{-1}]',
      },
    ],
    exercisePrompt:
      'Hitunglah invers dari matriks A = [[1, 2, 3], [2, 5, 3], [1, 0, 8]] menggunakan metode adjoin dan verifikasi dengan OBE [A | I]!',
  },
  'doc-week3-ppt': {
    id: 'doc-week3-ppt',
    weekNumber: 3,
    title: 'Slide Perkuliahan: Reduksi Baris & Kofaktor.pptx',
    fileType: 'ppt',
    fileSize: '5.1 MB',
    uploadedDate: '25 Agu 2026',
    estimatedTime: '24 Slide Presentasi',
    description:
      'Slide presentasi visual teknik ekspansi kofaktor, sifat-sifat determinan, dan algoritma invers matriks berordo 3x3 dan 4x4.',
    subCpmkRef:
      'Sub-CPMK 2: Mampu menerapkan sifat-sifat determinan untuk penyederhanaan komputasi.',
    sections: [
      {
        heading: '1. Sifat-sifat Utama Determinan',
        content:
          '1) det(AB) = det(A) · det(B)\n2) det(A^T) = det(A)\n3) det(A^-1) = 1 / det(A)\n4) Jika suatu baris dikalikan k, maka determinan menjadi k · det(A).',
        formula: '\\det(AB) = \\det(A) \\cdot \\det(B)',
      },
      {
        heading: '2. Strategi Ekspansi Baris / Kolom Kofaktor',
        content:
          'Pilihlah baris atau kolom dengan angka 0 paling banyak untuk meminimalkan komputasi sub-matriks minor.',
      },
    ],
  },
  'doc-week3-task': {
    id: 'doc-week3-task',
    weekNumber: 3,
    title: 'Tugas 02: Perhitungan Invers Matriks Menggunakan OBE.pdf',
    fileType: 'assignment',
    fileSize: '1.5 MB',
    uploadedDate: '26 Agu 2026',
    estimatedTime: 'Tenggat: 2 September 2026',
    description:
      'Penugasan analisis dan perhitungan invers matriks non-singular ordo 3x3 menggunakan transformasi OBE [A | I] -> [I | A^-1].',
    subCpmkRef:
      'Sub-CPMK 2: Mampu menentukan invers matriks non-singular secara tepat.',
    sections: [
      {
        heading: 'Deskripsi Penugasan',
        content:
          'Lakukan analisis invertibilitas pada matriks yang diberikan, kemudian hitung invers matriks menggunakan eliminasi Gauss-Jordan [A | I].',
      },
      {
        heading: 'Soal Matriks 3×3',
        content:
          'Diberikan matriks A = [[2, 1, 1], [3, 2, 1], [2, 1, 2]].\n1) Hitunglah determinan matriks A untuk memastikan invertibilitas!\n2) Tentukan matriks invers A^-1 menggunakan OBE!\n3) Buktikan bahwa perkalian A · A^-1 menghasilkan matriks identitas I_3.',
        formula: 'A \\cdot A^{-1} = I_3',
      },
    ],
  },
}
