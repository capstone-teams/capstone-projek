import { Alert } from '../../ui';
import { groupValidationIssues } from '../../../utils/coursePlan';

const issueText = (issue) => issue?.message || 'Temuan validasi tanpa keterangan.';

/**
 * Hasil validasi akademik course plan (CoursePlanValidationResult, BE-14.2): lolos/tidak beserta temuan tingkat
 * rencana dan temuan per minggu. `passed` false tanpa temuan berarti versi ini belum divalidasi.
 */
export default function CoursePlanValidation({ validation }) {
  const issues = validation?.issues ?? [];
  const passed = validation?.passed === true;
  const { general, byWeek } = groupValidationIssues(issues);

  if (passed && issues.length === 0) {
    return <Alert tone="success" title="Lolos validasi">Rencana memenuhi seluruh pemeriksaan akademik.</Alert>;
  }
  if (!passed && issues.length === 0) {
    return <Alert tone="warning" title="Rencana belum divalidasi">Rencana ini belum dapat disetujui sampai lolos validasi.</Alert>;
  }

  return (
    <Alert tone={passed ? 'info' : 'warning'} title={passed ? 'Lolos validasi dengan catatan' : 'Rencana belum lolos validasi'}>
      <div aria-label="Temuan validasi">
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
    </Alert>
  );
}
