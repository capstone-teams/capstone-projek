import { Fragment } from 'react';
import { Badge, Spinner } from '../../ui';
import {
  EXECUTION_SCOPE,
  OPERATION_STATUS,
  OPERATION_TYPE,
  OPERATION_TYPE_LABELS,
} from '../../../services/executionService';
import { groupExecutionOperationsByWeek } from '../../../utils/executionReadiness';

function OperationStatusBadge({ status }) {
  if (status === OPERATION_STATUS.SUCCESS) return <Badge tone="success">✓ Berhasil</Badge>;
  if (status === OPERATION_STATUS.RUNNING) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
        <Spinner size="sm" />
        <span>Memproses…</span>
      </span>
    );
  }
  if (status === OPERATION_STATUS.FAILED) return <Badge tone="danger">✕ Gagal</Badge>;
  if (status === OPERATION_STATUS.SKIPPED) return <Badge tone="neutral">Dilewati</Badge>;
  return <Badge tone="neutral">Menunggu</Badge>;
}

function OperationResultCell({ operation }) {
  const status = operation?.status || OPERATION_STATUS.PENDING;
  const moodleId = operation?.moodle_object_id;
  const errorMessage = operation?.error_message;
  const retryCount = operation?.retry_count || 0;

  if (status === OPERATION_STATUS.SUCCESS) {
    if (!moodleId) return <span className="text-success font-medium">Selesai diterapkan</span>;
    const prefix = operation?.operation_type === OPERATION_TYPE.SECTION ? 'Section' : 'Activity';
    return (
      <div className="flex items-center gap-1.5 font-mono text-success">
        <span className="font-semibold">{prefix} #{moodleId}</span>
      </div>
    );
  }

  if (status === OPERATION_STATUS.FAILED) {
    return (
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
    );
  }

  if (status === OPERATION_STATUS.SKIPPED) {
    return <span className="text-muted">{errorMessage || 'Operasi dilewati.'}</span>;
  }

  if (status === OPERATION_STATUS.RUNNING) {
    return <span className="text-muted">Menyimpan ke Moodle…</span>;
  }

  return <span className="text-muted">-</span>;
}

function OperationRow({ operation, fallbackTitle }) {
  const status = operation?.status || OPERATION_STATUS.PENDING;
  const opType = operation?.operation_type || OPERATION_TYPE.SECTION;
  const opLabel = OPERATION_TYPE_LABELS[opType] ?? opType;
  const itemTitle = operation?.title || fallbackTitle;

  return (
    <tr
      className={`hover:bg-surface-subtle/50 transition-colors ${
        status === OPERATION_STATUS.RUNNING ? 'bg-primary-light/10' : ''
      }`}
    >
      <td className="px-3.5 py-2.5 min-w-[220px]">
        <div className="font-medium text-ink">{itemTitle}</div>
      </td>
      <td className="px-3.5 py-2.5 text-center whitespace-nowrap">
        <Badge tone="neutral">{opLabel}</Badge>
      </td>
      <td className="px-3.5 py-2.5 text-center whitespace-nowrap">
        <OperationStatusBadge status={status} />
      </td>
      <td className="px-3.5 py-2.5 text-xs">
        <OperationResultCell operation={operation} />
      </td>
    </tr>
  );
}

/**
 * Tabel daftar operasi eksekusi Moodle per minggu (STRUCTURE maupun FULL, FE-13.2 & FE-18.1).
 */
export default function ExecutionOperationsTable({
  operations = [],
  plan,
  scope = EXECUTION_SCOPE.STRUCTURE,
}) {
  const { weeks, unscheduledOperations } = groupExecutionOperationsByWeek(operations, plan);
  const hasContentOps = scope === EXECUTION_SCOPE.FULL
    || operations.some((op) => op?.operation_type && op.operation_type !== OPERATION_TYPE.SECTION);

  if (!hasContentOps) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-ink">
            Detail Operasi Section Mingguan ({weeks.length} Minggu)
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
              {weeks.map(({ weekNumber, title, operations: weekOps }) => {
                const operation = weekOps[0];
                const status = operation?.status || OPERATION_STATUS.PENDING;
                return (
                  <tr
                    key={weekNumber}
                    className={`hover:bg-surface-subtle/50 transition-colors ${
                      status === OPERATION_STATUS.RUNNING ? 'bg-primary-light/10' : ''
                    }`}
                  >
                    <td className="px-3.5 py-3 font-semibold text-ink whitespace-nowrap">
                      Minggu {weekNumber}
                    </td>
                    <td className="px-3.5 py-3 min-w-[200px]">
                      <div className="font-medium text-ink">
                        Minggu {weekNumber} - {title}
                      </div>
                    </td>
                    <td className="px-3.5 py-3 text-center whitespace-nowrap">
                      <Badge tone="neutral">
                        {operation?.operation_type || OPERATION_TYPE.SECTION}
                      </Badge>
                    </td>
                    <td className="px-3.5 py-3 text-center whitespace-nowrap">
                      <OperationStatusBadge status={status} />
                    </td>
                    <td className="px-3.5 py-3 text-xs">
                      <OperationResultCell operation={operation} />
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

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-ink">
          Daftar Operasi per Minggu dan per Konten ({weeks.length} Minggu)
        </h4>
        <span className="text-xs text-muted">
          Cakupan: Section &amp; Activity Konten (FULL)
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line bg-surface">
        <table className="min-w-full divide-y divide-line text-left text-sm">
          <thead className="bg-surface-subtle text-xs font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th scope="col" className="px-3.5 py-2.5">Operasi / Judul Konten</th>
              <th scope="col" className="px-3.5 py-2.5 w-32 text-center">Jenis</th>
              <th scope="col" className="px-3.5 py-2.5 w-32 text-center">Status</th>
              <th scope="col" className="px-3.5 py-2.5 w-56">Hasil Moodle / Keterangan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {weeks.map(({ weekNumber, title, operations: weekOps }) => (
              <Fragment key={weekNumber}>
                <tr className="bg-surface-subtle/60">
                  <th colSpan={4} scope="colgroup" className="px-3.5 py-2 text-xs font-semibold text-ink">
                    Minggu {weekNumber} — {title}
                  </th>
                </tr>
                {weekOps.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-3.5 py-2.5 text-xs text-muted">
                      Belum ada operasi tercatat untuk minggu ini.
                    </td>
                  </tr>
                ) : (
                  weekOps.map((operation, idx) => {
                    const opType = operation?.operation_type || OPERATION_TYPE.SECTION;
                    const opLabel = OPERATION_TYPE_LABELS[opType] ?? opType;
                    const fallbackTitle = opType === OPERATION_TYPE.SECTION
                      ? `Minggu ${weekNumber} - ${title}`
                      : `${opLabel} Minggu ${weekNumber}`;
                    return (
                      <OperationRow
                        key={operation?.operation_id ?? `${weekNumber}-${opType}-${idx}`}
                        operation={operation}
                        fallbackTitle={fallbackTitle}
                      />
                    );
                  })
                )}
              </Fragment>
            ))}

            {unscheduledOperations.length > 0 && (
              <Fragment key="unscheduled">
                <tr className="bg-surface-subtle/60">
                  <th colSpan={4} scope="colgroup" className="px-3.5 py-2 text-xs font-semibold text-ink">
                    Operasi Tambahan
                  </th>
                </tr>
                {unscheduledOperations.map((operation, idx) => {
                  const opType = operation?.operation_type || OPERATION_TYPE.SECTION;
                  const opLabel = OPERATION_TYPE_LABELS[opType] ?? opType;
                  return (
                    <OperationRow
                      key={operation?.operation_id ?? `extra-${idx}`}
                      operation={operation}
                      fallbackTitle={opLabel}
                    />
                  );
                })}
              </Fragment>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
