import { useMemo, useState } from 'react';
import { useCourse } from '../../../hooks/useCourse';
import { getMoodleCourses, getMoodleStatus } from '../../../services/moodleIntegrationService';
import { useApi } from '../../../hooks/useApi';
import { Alert, Card, EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import MoodleConnectionBanner from '../../../components/moodle/MoodleConnectionBanner';
import CourseTargetCard from '../../../components/ai/course/CourseTargetCard';

/**
 * Halaman Pemilihan Target Course Moodle (FE-09.1).
 * Memungkinkan dosen pengampu memilih kursus di Moodle LMS yang menjadi target
 * pengiriman materi, aktivitas, dan struktur mingguan yang dihasilkan AI.
 */
export default function CourseTargetSelectionPage() {
  const { course } = useCourse();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCourseId, setSelectedCourseId] = useState(
    course?.moodle_course_id ? String(course.moodle_course_id) : ''
  );
  const [successMessage, setSuccessMessage] = useState(null);

  // Ambil status koneksi Moodle dan daftar kursus dari Backend Integration Gateway
  const {
    data: statusData,
    loading: statusLoading,
    error: statusError,
    reload: reloadStatus,
  } = useApi(getMoodleStatus, []);

  const {
    data: coursesData,
    loading: coursesLoading,
    error: coursesError,
    reload: reloadCourses,
  } = useApi(getMoodleCourses, []);

  const handleRetryAll = () => {
    reloadStatus();
    reloadCourses();
  };

  const courses = useMemo(() => coursesData?.courses ?? [], [coursesData]);

  // Filter kursus berdasarkan fullname atau shortname
  const filteredCourses = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return courses;
    return courses.filter(
      (c) =>
        (c.fullname && c.fullname.toLowerCase().includes(query)) ||
        (c.shortname && c.shortname.toLowerCase().includes(query)) ||
        (c.category && c.category.toLowerCase().includes(query))
    );
  }, [courses, searchQuery]);

  const handleSelectCourse = (targetCourse) => {
    setSelectedCourseId(String(targetCourse.id));
    setSuccessMessage(
      `Kursus "${targetCourse.shortname} — ${targetCourse.fullname}" (ID: ${targetCourse.id}) dipilih sebagai target sinkronisasi Moodle.`
    );
  };

  return (
    <div className="stack">
      <Card title="Pilih Target Course Moodle">
        <p className="mb-4 text-sm text-muted">
          Pilih kursus di Moodle LMS ITK yang menjadi tujuan publikasi konten dan aktivitas pembelajaran.
          Hasil rancangan generator AI akan disinkronisasikan ke kursus target ini.
        </p>

        {/* Banner Status Koneksi Moodle */}
        <MoodleConnectionBanner
          status={statusData?.status}
          moodleUrl={statusData?.moodle_url}
          message={statusData?.message}
          loading={statusLoading}
          error={statusError}
          onRetry={handleRetryAll}
        />

        {successMessage && (
          <Alert tone="success" onClose={() => setSuccessMessage(null)}>
            {successMessage}
          </Alert>
        )}

        <ErrorAlert error={coursesError} onClose={reloadCourses} />

        {/* Input Pencarian */}
        <div className="mb-4 mt-2 flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari berdasarkan nama, kode (mis. IF2105), atau jurusan…"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              aria-label="Cari kursus target Moodle"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted hover:text-ink"
                aria-label="Bersihkan pencarian"
              >
                ✕
              </button>
            )}
          </div>
          <span className="text-xs text-muted">
            Menampilkan {filteredCourses.length} dari {courses.length} kursus
          </span>
        </div>

        {/* Grid Kursus */}
        {coursesLoading ? (
          <Spinner label="Memuat daftar kursus dari Moodle…" />
        ) : courses.length === 0 ? (
          <EmptyState
            title="Tidak ada kursus Moodle ditemukan."
            action={
              <button type="button" className="btn btn--outline" onClick={handleRetryAll}>
                Muat Ulang
              </button>
            }
          >
            Pastikan instance Moodle memiliki kursus aktif dan koneksi backend terhubung dengan benar.
          </EmptyState>
        ) : filteredCourses.length === 0 ? (
          <EmptyState
            title="Kursus tidak ditemukan."
            action={
              <button
                type="button"
                className="btn btn--outline"
                onClick={() => setSearchQuery('')}
              >
                Reset Pencarian
              </button>
            }
          >
            Tidak ada kursus yang cocok dengan kata kunci &quot;{searchQuery}&quot;. Coba gunakan kata kunci lain.
          </EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {filteredCourses.map((c) => (
              <CourseTargetCard
                key={c.id}
                course={c}
                isSelected={String(c.id) === String(selectedCourseId)}
                onSelect={handleSelectCourse}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
