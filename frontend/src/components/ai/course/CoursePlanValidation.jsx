import { useState } from 'react';
import { Alert } from '../../ui';
import { groupValidationIssues } from '../../../utils/coursePlan';

const issueText = (issue) => issue?.message || 'Temuan validasi tanpa keterangan.';
const COLLAPSE_THRESHOLD = 3;

/**
 * Hasil validasi akademik course plan (CoursePlanValidationResult, BE-14.2): lolos/tidak beserta temuan tingkat
 * rencana dan temuan per minggu. `passed` false tanpa temuan berarti versi ini belum divalidasi.
 */
export default function CoursePlanValidation({ validation }) {
  const issues = validation?.issues ?? [];
  const passed = validation?.passed === true;
  const { general, byWeek } = groupValidationIssues(issues);
  const needsCollapse = issues.length > COLLAPSE_THRESHOLD;
  const [expanded, setExpanded] = useState(!needsCollapse);

  if (passed && issues.length === 0) {
    return <Alert tone="success" title="Lolos validasi">Rencana memenuhi seluruh pemeriksaan akademik.</Alert>;
  }
  if (!passed && issues.length === 0) {
    return <Alert tone="warning" title="Rencana belum divalidasi">Rencana ini belum dapat disetujui sampai lolos validasi.</Alert>;
  }

  return (
    <Alert tone={passed ? 'info' : 'warning'} title={passed ? 'Lolos validasi dengan catatan' : 'Rencana belum lolos validasi'}>
      <div aria-label="Temuan validasi">
        {needsCollapse && (
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span>
              Terdapat {issues.length} temuan validasi{byWeek.size > 0 ? ' (temuan per minggu juga tampil pada tabel di bawah)' : ''}.
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--xs font-semibold"
              aria-expanded={expanded}
              onClick={() => setExpanded((open) => !open)}
            >
              {expanded ? 'Sembunyikan temuan' : `Lihat detail (${issues.length} temuan)`}
            </button>
          </div>
        )}
        {(!needsCollapse || expanded) && (
          <div className={needsCollapse ? 'mt-2 max-h-48 overflow-y-auto pr-1' : ''}>
            {general.length > 0 && (
              <ul className="m-0 mt-1 list-disc pl-5">
                {general.map((issue, index) => <li key={index}>{issueText(issue)}</li>)}
              </ul>
            )}
            {byWeek.size > 0 && (
              <dl className="m-0 mt-2 grid gap-1.5">
                {[...byWeek].map(([week, items]) => (
                  <div key={week} className="flex flex-wrap gap-x-2">
                    <dt className="font-semibold">Minggu {week}:</dt>
                    <dd className="m-0 min-w-0">{items.map(issueText).join(' ')}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        )}
      </div>
    </Alert>
  );
}
