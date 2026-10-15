import { Link } from 'react-router-dom';
import { listRps } from '../../services/rpsService';
import { useApi } from '../../hooks/useApi';
import { usePolling } from '../../hooks/usePolling';
import { Badge, Card, EmptyState, ErrorAlert, PageHeader, Spinner } from '../../components/ui';
import RpsUploadForm from '../../components/ai/RpsUploadForm';
import { RPS_STATUS_LABELS } from '../../utils/workflow';
import { formatDateTime, formatFileSize } from '../../utils/format';

const RPS_TONES = { processed: 'success', failed: 'danger', uploaded: 'neutral' };

export default function RpsPage() {
  const { data, error, loading, reload } = useApi(listRps);
  const items = data?.items ?? [];
  const processing = items.some((r) => ['uploaded', 'processing', 'analyzing'].includes(r.status));

  usePolling(() => reload({ silent: true }), 2000, processing);

  return (
    <>
      <PageHeader title="RPS" subtitle="RPS adalah sumber utama informasi akademik untuk agent." />
      <div className="grid grid--sidebar">
        <Card title="Unggah RPS baru">
          <RpsUploadForm onDone={() => reload({ silent: true })} />
        </Card>

        <Card title="Daftar RPS">
          <ErrorAlert error={error} />
          {loading && !data ? (
            <Spinner />
          ) : items.length === 0 ? (
            <EmptyState title="Belum ada RPS." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Ukuran</th>
                    <th>Diunggah</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id}>
                      <td>{r.filename}</td>
                      <td>{formatFileSize(r.size)}</td>
                      <td>{formatDateTime(r.created_at)}</td>
                      <td>
                        <Badge tone={RPS_TONES[r.status] ?? 'info'}>{RPS_STATUS_LABELS[r.status] ?? r.status}</Badge>
                      </td>
                      <td className="table__actions">
                        {r.status === 'processed' && (
                          <>
                            <Link to={`/ai/rps/${r.id}`} className="btn btn--ghost btn--sm">
                              Analisis
                            </Link>
                            <Link to={`/ai/courses/new?rps=${r.id}`} className="btn btn--sm">
                              Buat course
                            </Link>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
