import { Link } from 'react-router-dom';
import { useCourse } from '../../../hooks/useCourse';
import { useRpsLibrary } from '../../../hooks/useRpsLibrary';
import { RPS_DELETE_AVAILABLE } from '../../../services/config';
import { Card, ErrorAlert, Field, Spinner } from '../../ui';
import EventLog from '../EventLog';
import RpsList from '../RpsList';
import RpsUploadForm from '../RpsUploadForm';
import WorkflowStatusPanel from '../WorkflowStatusPanel';

/**
 * Ringkasan Generator AI untuk kursus tanpa project /courses (backend nyata, DL-011): RPS kursus ini beserta
 * workflow-nya, status dan tindakan berikutnya dengan tautan cepat ke tab terkait, serta aktivitas agent.
 */
export default function WorkflowCourseOverview() {
  const { course, workflow, events = [], selectRps } = useCourse();
  const library = useRpsLibrary();
  // Hanya RPS yang punya workflow yang dapat dipakai alur generator.
  const choices = library.items.filter((item) => item.workflow_id);

  return (
    <div className="grid grid--2">
      <div className="stack">
        <Card title="Langkah berikutnya">
          {workflow ? (
            // Halaman ini adalah indeks tab Generator AI, jadi tautan cepat menuju tab saudara ("./plan", dst.).
            <WorkflowStatusPanel workflow={workflow} events={events} linkBase="." />
          ) : (
            <p>
              Unggah RPS mata kuliah ini, lalu tunggu sampai selesai dianalisis. Setelah itu susun rencana di tab{' '}
              <Link to="plan">Rencana</Link>.
            </p>
          )}
        </Card>

        <Card title="RPS mata kuliah">
          <p className="mb-3 text-muted">RPS adalah sumber utama informasi akademik untuk agent.</p>
          <div className="stack">
            <RpsUploadForm
              onUploaded={(result) => {
                library.addUploaded(result);
                if (result?.rps?.id) selectRps?.(result.rps.id);
              }}
            />
            {choices.length > 0 && (
              <Field label="RPS untuk kursus ini" hint="Workflow RPS terpilih dipakai tab RPS, Course Target, Rencana, dan Publikasi.">
                <select value={course.rps_id ?? ''} onChange={(e) => selectRps?.(e.target.value || null)}>
                  {!course.rps_id && <option value="">Pilih RPS</option>}
                  {choices.map((item) => (
                    <option key={item.id} value={item.id}>{item.filename}</option>
                  ))}
                </select>
              </Field>
            )}
            <ErrorAlert error={library.error} />
            <ErrorAlert error={library.actionError} onClose={library.clearActionError} />
            {library.loading ? (
              <Spinner label="Memuat daftar RPS…" />
            ) : (
              !library.error && (
                <RpsList
                  items={library.items}
                  progress={library.progress}
                  highlightId={library.highlightId}
                  busyId={library.busyId}
                  onProcess={library.process}
                  onReanalyze={library.reanalyze}
                  onHide={RPS_DELETE_AVAILABLE ? library.hide : undefined}
                  analysisHref={(item) => `rps?rps=${item.id}`}
                  monitorHref={(item) => `workflows?workflow=${item.workflow_id}`}
                />
              )
            )}
          </div>
        </Card>
      </div>

      <div className="stack">
        <Card title="Aktivitas agent">
          <EventLog events={events} limit={15} />
        </Card>
      </div>
    </div>
  );
}
