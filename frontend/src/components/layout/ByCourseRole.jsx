import { useMoodleCourse } from '../../hooks/useMoodleCourse';

/**
 * Pilih halaman dosen atau mahasiswa untuk route kursus yang sama. Peran dihitung per kursus
 * (pengajar kursus ini atau admin = dosen), sehingga URL tetap sama bagi keduanya.
 */
export default function ByCourseRole({ dosen, mahasiswa }) {
  const { isTeacher } = useMoodleCourse();
  return isTeacher ? dosen : mahasiswa;
}
