export type UserRole = 'dosen' | 'mahasiswa'

export interface UserProfile {
  name: string
  identifier: string // NIP or NIM
  role: UserRole
  roleLabel: string
  prodi: string
  email: string
  avatarInitial: string
  teachingApproach?: string
  aiInstructions?: string
}

export const DOSEN_PROFILE: UserProfile = {
  name: 'Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.',
  identifier: '198503152010122001',
  role: 'dosen',
  roleLabel: 'Dosen Pengampu',
  prodi: 'Informatika · Jurusan Sains & Teknologi Informasi',
  email: 'chandra.cahyo@itk.ac.id',
  avatarInitial: 'MC',
  teachingApproach: 'Berbasis proyek dan studi kasus bertahap.',
  aiInstructions:
    'Gunakan contoh nyata penerapan aljabar linear pada komputasi dan grafika, sertakan latihan bertingkat, dan hindari kuis mendadak.',
}

export const MAHASISWA_PROFILE: UserProfile = {
  name: 'Noel Sipayung',
  identifier: '11211045',
  role: 'mahasiswa',
  roleLabel: 'Mahasiswa',
  prodi: 'Informatika 2021 · Semester 7',
  email: '11211045@student.itk.ac.id',
  avatarInitial: 'NS',
}
