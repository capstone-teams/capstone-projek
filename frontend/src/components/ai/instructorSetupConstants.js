export const MAX_PROMPT_LENGTH = 1000;

export const DEFAULT_ACTIVITY_CONFIGURATION = {
  learning_material: true,
  learning_resource: false,
  assignment: false,
  quiz: false,
};

export const ACTIVITY_OPTIONS = [
  {
    key: 'learning_material',
    label: 'Materi Pembelajaran',
    hint: 'Halaman modul dan teks materi per minggu',
  },
  {
    key: 'learning_resource',
    label: 'Sumber Referensi',
    hint: 'Tautan bacaan, literatur, dan bahan rujukan',
  },
  {
    key: 'assignment',
    label: 'Tugas',
    hint: 'Tugas mingguan dan pengumpulan mahasiswa',
  },
  {
    key: 'quiz',
    label: 'Kuis',
    hint: 'Kuis berkala dan evaluasi pemahaman',
  },
];
