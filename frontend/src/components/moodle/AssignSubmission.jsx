import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { getSubmissionStatus } from '../../services/moodle/moodleApi';
import { withToken } from '../../services/moodle/moodleClient';
import { Badge, ErrorAlert, Spinner } from '../ui';
import MoodleHtml from './MoodleHtml';
import { submissionContent, submissionTypes } from '../../utils/assignSubmission';
import { formatFileSize, formatUnixDateTime } from '../../utils/format';

// String mod_assign (lang/en/assign.php) agar tampilan sama dengan halaman tugas Moodle.
const SUBMISSION_STATUS = {
  new: ['No submission', 'neutral'],
  draft: ['Draft (not submitted)', 'warning'],
  submitted: ['Submitted for grading', 'success'],
  reopened: ['Reopened', 'warning'],
};
const GRADING_STATUS = { notgraded: 'Not graded', graded: 'Graded', released: 'Graded' };

// Seperti format_time() Moodle: "8 days 23 hours".
function formatDuration(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const unit = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  return days ? `${unit(days, 'day')} ${unit(hours, 'hour')}` : unit(hours, 'hour');
}

/** Kotak "Opened/Due" dan deskripsi di atas halaman tugas (activity header Moodle). */
export function AssignIntro({ assign }) {
  const hasDates = assign.allowsubmissionsfromdate > 0 || assign.duedate > 0;
  return (
    <div className="mb-6 rounded-md bg-surface px-4 py-3 text-sm">
      {hasDates && (
        <div className="flex flex-col gap-0.5">
          {assign.allowsubmissionsfromdate > 0 && <span><strong>Opened:</strong> {formatUnixDateTime(assign.allowsubmissionsfromdate)}</span>}
          {assign.duedate > 0 && <span><strong>Due:</strong> {formatUnixDateTime(assign.duedate)}</span>}
        </div>
      )}
      {assign.intro && (
        <div className={hasDates ? 'mt-3 border-t border-line pt-3' : ''}>
          <MoodleHtml html={assign.intro} />
        </div>
      )}
    </div>
  );
}

export function SubmittedFiles({ files }) {
  return (
    <ul className="flex flex-col gap-1">
      {files.map((file) => (
        <li key={`${file.filepath ?? '/'}${file.filename}`}>
          {file.fileurl ? <a href={withToken(file.fileurl)} target="_blank" rel="noreferrer">{file.filename}</a> : file.filename}
          {file.filepath && file.filepath !== '/' && <span className="text-muted"> ({file.filepath.slice(1, -1)})</span>}
          <span className="text-muted"> · {formatFileSize(file.filesize)}</span>
        </li>
      ))}
    </ul>
  );
}

/** Halaman tugas untuk mahasiswa: tombol Add/Edit submission lalu tabel Submission status. */
export default function AssignSubmission({ assign, editPath }) {
  const [now] = useState(() => Math.floor(Date.now() / 1000));
  const { data, error, loading } = useApi(() => getSubmissionStatus(assign.id), [assign.id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  const types = submissionTypes(assign);
  const attempt = data.lastattempt ?? {};
  const submission = attempt.submission ?? attempt.teamsubmission;
  const status = submission?.status ?? 'new';
  const [statusLabel, statusTone] = SUBMISSION_STATUS[status] ?? [status, 'neutral'];
  const content = submissionContent(submission);
  const hasContent = !!content.text || content.files.length > 0;
  const opened = !assign.allowsubmissionsfromdate || assign.allowsubmissionsfromdate <= now;
  const canSubmit = (types.onlineText || types.files) && opened && attempt.canedit !== false;

  let remaining = '-';
  if (assign.duedate) {
    if (status === 'submitted') remaining = `Assignment was submitted ${formatDuration(Math.max(0, assign.duedate - submission.timemodified))} early`;
    else if (assign.duedate >= now) remaining = formatDuration(assign.duedate - now);
    else remaining = <span className="font-semibold text-danger">Assignment is overdue by: {formatDuration(now - assign.duedate)}</span>;
  }

  const rows = [
    ['Submission status', <Badge tone={statusTone}>{statusLabel}</Badge>],
    ['Grading status', GRADING_STATUS[attempt.gradingstatus] ?? attempt.gradingstatus ?? '-'],
    ['Time remaining', remaining],
    ['Last modified', submission?.timemodified ? formatUnixDateTime(submission.timemodified) : '-'],
  ];
  if (types.onlineText) rows.push(['Online text', content.text ? <MoodleHtml html={content.text} /> : '-']);
  if (types.files) rows.push(['File submissions', content.files.length ? <SubmittedFiles files={content.files} /> : '-']);
  if (data.feedback?.gradefordisplay) rows.push(['Grade', <MoodleHtml html={data.feedback.gradefordisplay} />]);

  return (
    <section aria-labelledby="submission-status-heading">
      {canSubmit && (
        <Link to={editPath} className="btn btn--primary mb-5">{hasContent ? 'Edit submission' : 'Add submission'}</Link>
      )}
      {!opened && (
        <p className="mb-4 text-sm text-muted">This assignment will accept submissions from {formatUnixDateTime(assign.allowsubmissionsfromdate)}.</p>
      )}
      <h3 id="submission-status-heading" className="mb-3 text-xl">Submission status</h3>
      <div className="table-wrap">
        <table className="table">
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <th className="w-1/3 bg-surface !font-normal">{label}</th>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
