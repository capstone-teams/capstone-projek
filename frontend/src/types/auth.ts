export type UserRole = 'dosen' | 'mahasiswa'

export interface UserProfile {
  name: string
  identifier: string // NIP or NIM
  role: UserRole
  roleLabel: string
  prodi: string
  email: string
  avatarInitial: string
}

export const DOSEN_PROFILE: UserProfile = {
  name: 'Muchammad Chandra Cahyo Utomo, S. Kom., M. Kom.',
  identifier: '198503152010122001',
  role: 'dosen',
  roleLabel: 'Dosen Pengampu',
  prodi: 'Informatika · Jurusan Sains & Teknologi Informasi',
  email: 'chandra.cahyo@itk.ac.id',
  avatarInitial: 'MC',
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
