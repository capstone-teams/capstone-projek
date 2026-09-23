import type {
  SyllabusWeek,
  DosenCourse,
  MahasiswaCourse,
  RpsAnalysisData,
} from '../types/course'

export const WEEKS_DATA: SyllabusWeek[] = [
  { weekNumber: 1, title: 'Dasar-dasar Keamanan Siber', duration: '3 SKS · Minggu 01', status: 'moodle' },
  { weekNumber: 2, title: 'Ancaman dan Serangan', duration: '3 SKS · Minggu 02', status: 'moodle' },
  { weekNumber: 3, title: 'Rekognisi Jejak Digital', duration: '3 SKS · Minggu 03', status: 'moodle' },
  { weekNumber: 4, title: 'Pemindaian dan Enumerasi', duration: '3 SKS · Minggu 04', status: 'approved' },
  { weekNumber: 5, title: 'Eksploitasi Keamanan Web', duration: '3 SKS · Minggu 05', status: 'approved' },
  { weekNumber: 6, title: 'Malware dan Backdoor', duration: '3 SKS · Minggu 06', status: 'approved' },
  { weekNumber: 7, title: 'Autentikasi dan Kontrol Akses', duration: '3 SKS · Minggu 07', status: 'approved' },
  { weekNumber: 8, title: 'Ujian Tengah Semester', duration: '3 SKS · Minggu 08', status: 'approved' },
  { weekNumber: 9, title: 'Keamanan Fisik dan Rekayasa Sosial', duration: '3 SKS · Minggu 09', status: 'approved' },
  { weekNumber: 10, title: 'Kriptografi Dasar', duration: '3 SKS · Minggu 10', status: 'approved' },
  { weekNumber: 11, title: 'Keamanan Jaringan', duration: '3 SKS · Minggu 11', status: 'approved' },
  { weekNumber: 12, title: 'Keamanan Aplikasi', duration: '3 SKS · Minggu 12', status: 'approved' },
  { weekNumber: 13, title: 'Respons Insiden', duration: '3 SKS · Minggu 13', status: 'approved' },
  { weekNumber: 14, title: 'Analisis Kasus', duration: '3 SKS · Minggu 14', status: 'approved' },
  { weekNumber: 15, title: 'Presentasi Proyek', duration: '3 SKS · Minggu 15', status: 'approved' },
  { weekNumber: 16, title: 'Ujian Akhir Semester', duration: '3 SKS · Minggu 16', status: 'approved' },
]

export const DOSEN_COURSES: DosenCourse[] = [
  {
    code: 'IF403',
    name: 'Keamanan Siber',
    sks: '3 SKS · 16 pertemuan',
    semester: 'Semester Gasal 2026/2027',
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
    code: 'IF403',
    name: 'Keamanan Siber',
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
  courseCode: 'IF403',
  courseName: 'Keamanan Siber',
  sks: 3,
  semester: 'Semester Gasal 2026/2027',
  totalWeeks: 16,
  targetCpl: [
    'Mampu menganalisis ancaman dan kerentanan sistem informasi',
    'Mampu menerapkan mekanisme perlindungan data dan kriptografi dasar',
    'Mampu merancang arsitektur keamanan jaringan bertingkat',
  ],
  cpmkCount: 4,
  fileName: 'RPS_Keamanan_Siber.pdf',
  fileSize: '2.4 MB · Terverifikasi',
  extractedAt: '23 September 2026',
}
