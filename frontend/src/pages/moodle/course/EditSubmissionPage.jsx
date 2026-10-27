import { useContext, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AppStateContext } from '../../../context/appStateContext';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useApi } from '../../../hooks/useApi';
import { getAssignments, getSubmissionStatus, saveSubmission } from '../../../services/moodle/moodleApi';
import { EmptyState, ErrorAlert, Spinner } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import { AssignIntro } from '../../../components/moodle/AssignSubmission';
import MoodleEditor from '../../../components/moodle/submission/MoodleEditor';
import FileManager from '../../../components/moodle/submission/FileManager';
import { countWords, formatLimit, submissionContent, submissionTypes } from '../../../utils/assignSubmission';

// File yang sudah dikumpulkan menjadi isi awal file manager; folder diturunkan dari filepath.
function initialFiles(files) {
  const entries = files.map((file, index) => ({ key: `saved-${index}`, ...file, filepath: file.filepath ?? '/' }));
  const folders = new Set();
  entries.forEach(({ filepath }) => {
    const parts = filepath.split('/').filter(Boolean);
    parts.forEach((_, i) => folders.add(`/${parts.slice(0, i + 1).join('/')}/`));
  });
  return { entries, folders: [...folders] };
}

/** Formulir "Add submission" (Moodle: mod/assign/view.php?action=editsubmission). */
function SubmissionForm({ assign, types, content, onDone }) {
  const notify = useContext(AppStateContext)?.notify;
  const [open, setOpen] = useState(true);
  const [text, setText] = useState(content.text);
  const [files, setFiles] = useState(() => initialFiles(content.files));
  const [filesChanged, setFilesChanged] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const words = countWords(text);
  const overLimit = types.wordLimit > 0 && words > types.wordLimit;

  const submit = async (event) => {
    event.preventDefault();
    setSubmitted(true);
    if (overLimit) return;
    setPending(true);
    setError(null);
    try {
      // Tanpa perubahan file, files_filemanager tidak dikirim sehingga file di Moodle tetap.
      await saveSubmission(assign.id, {
        onlineText: types.onlineText ? text : null,
        files: types.files && filesChanged ? files.entries : null,
      });
      notify?.('Changes saved', { type: 'success' });
      onDone();
    } catch (e) {
      setError(e);
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <ErrorAlert error={error} onClose={() => setError(null)} />
      <h3 className="mb-4">
        <button type="button" aria-expanded={open} aria-controls="add-submission-fields" className="flex cursor-pointer items-center gap-2 text-xl text-primary" onClick={() => setOpen(!open)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true" className={open ? '' : '-rotate-90'}>
            <path d="m6 9 6 6 6-6" />
          </svg>
          Add submission
        </button>
      </h3>
      <div id="add-submission-fields" hidden={!open} className="grid gap-x-6 gap-y-6 md:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
        {types.onlineText && (
          <>
            <span id="onlinetext-label" className="text-sm md:pt-2">Online text</span>
            <div>
              <MoodleEditor
                id="onlinetext-editor"
                labelId="onlinetext-label"
                initialValue={content.text}
                onChange={setText}
                invalid={submitted && overLimit}
                describedBy={submitted && overLimit ? 'onlinetext-error' : undefined}
              />
              {submitted && overLimit && (
                <p id="onlinetext-error" role="alert" className="mt-1 text-sm text-danger">
                  The word limit for this assignment is {types.wordLimit} words and you are attempting to submit {words} words. Please review your submission and try again.
                </p>
              )}
              {types.wordLimit > 0 && <p className="mt-1 text-xs text-muted">Word limit: {types.wordLimit}</p>}
            </div>
          </>
        )}
        {types.files && (
          <>
            <span id="files-label" className="text-sm md:pt-7">File submissions</span>
            <div className="min-w-0">
              <p className="mb-1 text-right text-sm text-ink-subtle">
                Maximum file size: {formatLimit(types.maxBytes)}, maximum number of files: {types.maxFiles}
              </p>
              <FileManager
                labelId="files-label"
                value={files}
                maxFiles={types.maxFiles}
                maxBytes={types.maxBytes}
                onChange={(next) => { setFiles(next); setFilesChanged(true); }}
              />
            </div>
          </>
        )}
      </div>
      <div className="mt-6 grid gap-x-6 border-t border-line pt-4 md:grid-cols-[minmax(0,1fr)_minmax(0,3fr)]">
        <div className="flex flex-wrap gap-2 md:col-start-2">
          <button type="submit" className="btn btn--primary" disabled={pending}>{pending ? 'Saving…' : 'Save changes'}</button>
          <button type="button" className="btn btn--secondary" onClick={onDone}>Cancel</button>
        </div>
      </div>
    </form>
  );
}

export default function EditSubmissionPage() {
  const { cmid } = useParams();
  const navigate = useNavigate();
  const [now] = useState(() => Math.floor(Date.now() / 1000));
  const { course, sections, isTeacher } = useMoodleCourse();
  const section = sections.find((s) => s.modules.some((m) => m.id === Number(cmid)));
  const mod = section?.modules.find((m) => m.id === Number(cmid));
  const { data, error, loading } = useApi(async () => {
    const assign = (await getAssignments([course.id])).find((a) => a.cmid === Number(cmid));
    return { assign, status: assign ? await getSubmissionStatus(assign.id) : null };
  }, [course.id, cmid]);

  const activityPath = `/course/${course.id}/mod/${cmid}`;
  if (!mod || mod.modname !== 'assign') {
    return <EmptyState title="Tugas tidak ditemukan." action={<Link to={`/course/${course.id}`}>Kembali ke kursus</Link>} />;
  }

  let body;
  if (loading && !data) body = <Spinner />;
  else if (error) body = <ErrorAlert error={error} />;
  else if (!data.assign) body = <EmptyState title="Tugas tidak ditemukan." />;
  else {
    const types = submissionTypes(data.assign);
    const attempt = data.status?.lastattempt ?? {};
    const opened = !data.assign.allowsubmissionsfromdate || data.assign.allowsubmissionsfromdate <= now;
    body = (
      <>
        <AssignIntro assign={data.assign} />
        {isTeacher || !opened || attempt.canedit === false || !(types.onlineText || types.files) ? (
          <EmptyState title="You cannot edit this submission." action={<Link to={activityPath}>Kembali ke tugas</Link>} />
        ) : (
          <SubmissionForm
            assign={data.assign}
            types={types}
            content={submissionContent(attempt.submission ?? attempt.teamsubmission)}
            onDone={() => navigate(activityPath)}
          />
        )}
      </>
    );
  }

  return (
    <div>
      <nav className="mb-3 text-sm text-muted" aria-label="Breadcrumb aktivitas">
        <Link to={`/course/${course.id}#section-${section.section}`}>{section.name}</Link>
        {' / '}
        <Link to={activityPath}>{mod.name}</Link>
        {' / '}
        <span aria-current="page">Edit submission</span>
      </nav>
      <div className="mb-4 flex items-center gap-3">
        <ActivityIcon modname={mod.modname} src={mod.modicon} />
        <h2 className="text-2xl">{mod.name}</h2>
      </div>
      {body}
    </div>
  );
}
