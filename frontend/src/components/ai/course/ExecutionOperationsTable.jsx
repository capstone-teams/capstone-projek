import { Badge, Spinner } from '../../ui';

/**
 * Tabel atau daftar 16 operasi section mingguan ke Moodle (FE-13.2).
 * Menggabungkan judul topik dari course plan dengan data operasi eksekusi.
 */
export default function ExecutionOperationsTable({ operations = [], plan }) {
  // Buat mapping judul dari course plan berdasarkan week_number
  const planWeekTitles = new Map(
    (plan?.weeks ?? []).map((w) => [w.week_number, w.title])
  );

  // Jika operations belum memiliki 16 item (misal baru inisiasi), lengkapi placeholder 16 minggu
  const totalWeeks = Math.max(operations.length, plan?.weeks?.length || 16);
  const operationByWeek = new Map(
    operations.map((op) => [op.week_number, op])
  );

  const rows = Array.from({ length: totalWeeks }, (_, idx) => {
    const weekNumber = idx + 1;
    const op = operationByWeek.get(weekNumber);
    const title = planWeekTitles.get(weekNumber) || `Topik Perkuliahan Minggu ${weekNumber}`;
    return {
      weekNumber,
      title,
      operation: op,
    };
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-ink">
          Detail Operasi Section Mingguan (16 Minggu)
        </h4>
        <span className="text-xs text-muted">
          Cakupan: Section Kursus
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line bg-surface">
        <table className="min-w-full divide-y divide-line text-left text-sm">
          <thead className="bg-surface-subtle text-xs font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th scope="col" className="px-3.5 py-2.5 w-20">Minggu</th>
              <th scope="col" className="px-3.5 py-2.5">Nama Section / Topik</th>
              <th scope="col" className="px-3.5 py-2.5 w-28 text-center">Tipe</th>
              <th scope="col" className="px-3.5 py-2.5 w-32 text-center">Status</th>
              <th scope="col" className="px-3.5 py-2.5 w-44">Hasil Moodle / Keterangan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map(({ weekNumber, title, operation }) => {
              const status = operation?.status || 'PENDING';
              const moodleId = operation?.moodle_object_id;
              const errorMessage = operation?.error_message;
              const retryCount = operation?.retry_count || 0;

              return (
                <tr
                  key={weekNumber}
                  className={`hover:bg-surface-subtle/50 transition-colors ${
                    status === 'RUNNING' ? 'bg-primary-light/10' : ''
                  }`}
                >
                  {/* Nomor Minggu */}
                  <td className="px-3.5 py-3 font-semibold text-ink whitespace-nowrap">
                    Minggu {weekNumber}
                  </td>

                  {/* Judul Topik */}
                  <td className="px-3.5 py-3 min-w-[200px]">
                    <div className="font-medium text-ink">
                      Minggu {weekNumber} - {title}
                    </div>
                  </td>

                  {/* Tipe Operasi */}
                  <td className="px-3.5 py-3 text-center whitespace-nowrap">
                    <Badge tone="neutral">
                      {operation?.operation_type || 'SECTION'}
                    </Badge>
                  </td>

                  {/* Status Operasi */}
                  <td className="px-3.5 py-3 text-center whitespace-nowrap">
                    {status === 'SUCCESS' ? (
                      <Badge tone="success">✓ Berhasil</Badge>
                    ) : status === 'RUNNING' ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                        <Spinner size="sm" />
                        <span>Memproses…</span>
                      </span>
                    ) : status === 'FAILED' ? (
                      <Badge tone="danger">✕ Gagal</Badge>
                    ) : status === 'SKIPPED' ? (
                      <Badge tone="neutral">Dilewati</Badge>
                    ) : (
                      <Badge tone="neutral">Menunggu</Badge>
                    )}
                  </td>

                  {/* Hasil Moodle & Pesan Error */}
                  <td className="px-3.5 py-3 text-xs">
                    {status === 'SUCCESS' && moodleId ? (
                      <div className="flex items-center gap-1.5 font-mono text-success">
                        <span className="font-semibold">Section #{moodleId}</span>
                      </div>
                    ) : status === 'FAILED' ? (
                      <div className="space-y-1">
                        <span className="text-danger font-medium block">
                          {errorMessage || 'Operasi gagal diterapkan ke Moodle.'}
                        </span>
                        {retryCount > 0 && (
                          <span className="text-muted text-[11px] block">
                            (Dicoba ulang: {retryCount}x)
                          </span>
                        )}
                      </div>
                    ) : status === 'RUNNING' ? (
                      <span className="text-muted">Menyimpan ke Moodle…</span>
                    ) : (
                      <span className="text-muted">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
