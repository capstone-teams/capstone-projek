import { Badge, Card, ProgressBar } from '../ui';
import { CONTENT_KIND_LABELS } from '../../services/contentService';
import { CONTENT_STATE_META, contentGenerationProgress } from '../../utils/contentEvents';

/**
 * Progres GENERATING_CONTENT per minggu (FE-19.1) dari event AKTIVITAS_AGENT run terakhir: keadaan tiap jenis konten
 * (dibuat, diperbaiki, lolos/gagal validasi) dan ringkasan minggu yang selesai. Diperbarui real-time bersama event.
 */
export default function WorkflowContentProgress({ events = [] }) {
  const progress = contentGenerationProgress(events);
  if (!progress?.total) return null;

  return (
    <Card title="Progres pembuatan konten">
      <ProgressBar completed={progress.weeksDone} total={progress.total} label="Minggu selesai" />
      <ul className="mt-4 grid list-none gap-2 p-0" aria-label="Progres konten per minggu">
        {progress.weeks.map((week) => (
          <li key={week.week} className="flex flex-wrap items-center gap-2 rounded-md border border-line p-2.5 text-sm" aria-label={`Minggu ${week.week}`}>
            <span className="w-24 shrink-0 font-semibold">Minggu {week.week}</span>
            {week.items.map((item) => {
              const state = CONTENT_STATE_META[item.state];
              return (
                <span key={item.kind} className="flex items-center gap-1">
                  <span className="text-muted">{CONTENT_KIND_LABELS[item.kind]}:</span>
                  <Badge tone={state.tone}>{state.label}</Badge>
                </span>
              );
            })}
            {week.summary && (
              <span className="ml-auto text-xs text-muted">
                {week.summary.validated} lolos, {week.summary.failed} gagal
              </span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}
