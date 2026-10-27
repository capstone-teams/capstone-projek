import { getInstructorSetup } from '../../services/instructorService';
import { useApi } from '../../hooks/useApi';
import { Card, ErrorAlert, Spinner } from '../ui';
import InstructorSetupForm from './InstructorSetupForm';
import { formatDateTime } from '../../utils/format';

/** Preferensi mengajar dosen yang dipakai agent saat menyusun rencana dan konten di semua kursus. */
export default function TeachingPreferencesCard() {
  const { data, error, loading, setData } = useApi(getInstructorSetup);
  return (
    <Card title="Preferensi mengajar">
      <p className="mb-3 text-sm text-muted">
        Dipakai agent saat menyusun rencana dan konten untuk semua kursus Anda.
        {data?.updated_at && ` Diperbarui ${formatDateTime(data.updated_at)}.`}
      </p>
      <ErrorAlert error={error} />
      {loading && !data ? <Spinner /> : data && <InstructorSetupForm initial={data} onSaved={setData} />}
    </Card>
  );
}
