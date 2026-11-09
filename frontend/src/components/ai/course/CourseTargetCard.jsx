import { Badge } from '../../ui';

/**
 * Kartu pilihan kursus Moodle sebagai target sinkronisasi generator AI (FE-09.1).
 *
 * @param {Object} props
 * @param {Object} props.course - Data kursus dari Moodle (id, fullname, shortname, category, summary).
 * @param {boolean} props.isSelected - Apakah kursus ini sedang menjadi target yang dipilih.
 * @param {Function} props.onSelect - Callback saat tombol 'Pilih Course Target' diklik.
 * @param {boolean} [props.disabled] - Nonaktifkan tombol pemilihan.
 */
export default function CourseTargetCard({
  course,
  isSelected = false,
  onSelect,
  disabled = false,
}) {
  // Bersihkan tag HTML sederhana jika summary mengandung tag seperti <p>...</p>
  const cleanSummary = course.summary
    ? course.summary.replace(/<[^>]+>/g, '').trim()
    : 'Tidak ada deskripsi kursus.';

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border p-5 transition-all duration-150 ${
        isSelected
          ? 'border-primary bg-blue-50/30 ring-2 ring-primary/20 shadow-sm'
          : 'border-line bg-surface hover:border-line-focus hover:shadow-xs'
      }`}
      aria-label={`Target kursus ${course.shortname}`}
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge tone="info">{course.shortname}</Badge>
            <span className="text-xs font-mono text-muted">ID: {course.id}</span>
          </div>
          {course.category && (
            <span className="text-xs font-medium text-muted">{course.category}</span>
          )}
        </div>

        <div>
          <h3 className="text-base font-bold text-ink leading-snug">
            {course.fullname}
          </h3>
          <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted">
            {cleanSummary}
          </p>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-line-subtle pt-3">
        {isSelected ? (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>Target Terpilih</span>
          </div>
        ) : (
          <span className="text-xs text-muted">Tersedia di Moodle</span>
        )}

        <button
          type="button"
          onClick={() => onSelect(course)}
          disabled={disabled || isSelected}
          className={`btn btn--sm ${
            isSelected
              ? 'btn--primary cursor-default opacity-90'
              : 'btn--outline hover:btn--primary'
          }`}
          aria-label={isSelected ? `Kursus ${course.shortname} sudah dipilih` : `Pilih ${course.shortname} sebagai target`}
        >
          {isSelected ? 'Terpilih' : 'Pilih Course Target'}
        </button>
      </div>
    </div>
  );
}
