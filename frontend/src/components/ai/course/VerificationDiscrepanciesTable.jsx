import { Fragment, useState } from 'react';
import { Alert, Badge, Card } from '../../ui';
import { DISCREPANCY_TYPE, VERIFICATION_STATUS } from '../../../services/verificationService';
import { DIFF_FILTER, groupVerificationDiffsByWeek } from '../../../utils/verificationResult';

function typeTone(type) {
  if (type === DISCREPANCY_TYPE.UNEXPECTED) return 'warning';
  return 'danger';
}

function ComparisonDetail({ item }) {
  const showCompare = item.expectedText && item.actualText && item.expectedText !== item.actualText;
  return (
    <div className="space-y-1">
      <div className="text-ink">{item.message}</div>
      {showCompare && (
        <div className="text-xs text-muted">
          Diharapkan: <strong className="text-ink">{item.expectedText}</strong> · Aktual di Moodle:{' '}
          <strong className="text-ink">{item.actualText}</strong>
        </div>
      )}
    </div>
  );
}

/**
 * Daftar perbedaan hasil verifikasi per minggu beserta jenis perbedaan dan status perbaikannya (FE-18.2).
 */
export default function VerificationDiscrepanciesTable({ verification }) {
  const [filter, setFilter] = useState(DIFF_FILTER.ALL);
  if (!verification) return null;

  const remainingCount = verification.discrepancies?.length ?? 0;
  const repairedCount = verification.repaired?.length ?? 0;
  const totalCount = remainingCount + repairedCount;
  const grouped = groupVerificationDiffsByWeek(verification, filter);

  const filterTabs = totalCount > 0 ? (
    <div className="inline-flex rounded-lg border border-line bg-surface p-0.5" role="tablist" aria-label="Filter perbedaan verifikasi">
      {[
        { key: DIFF_FILTER.ALL, label: `Semua (${totalCount})` },
        { key: DIFF_FILTER.REMAINING, label: `Masih berbeda (${remainingCount})` },
        { key: DIFF_FILTER.REPAIRED, label: `Diperbaiki (${repairedCount})` },
      ].map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={filter === tab.key}
          className={`btn btn--xs ${filter === tab.key ? 'btn--primary' : 'btn--ghost'}`}
          onClick={() => setFilter(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  ) : null;

  return (
    <Card title="Daftar Perbedaan per Minggu" actions={filterTabs}>
      {totalCount === 0 ? (
        verification.status === VERIFICATION_STATUS.UNKNOWN ? (
          <p className="text-sm text-muted">
            Daftar perbedaan tidak tersedia karena server Moodle gagal dibaca pada pemeriksaan ini.
          </p>
        ) : (
          <Alert tone="success">
            Tidak ditemukan perbedaan antara isi course Moodle dengan rencana pembelajaran dan konten yang disetujui.
          </Alert>
        )
      ) : grouped.length === 0 ? (
        <p className="text-sm text-muted">Tidak ada item perbedaan untuk kategori filter ini.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line bg-white">
          <table className="min-w-full divide-y divide-line text-left text-sm">
            <thead className="bg-surface text-xs font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th scope="col" className="px-3.5 py-2.5">Objek / Target</th>
                <th scope="col" className="px-3.5 py-2.5 w-44">Jenis Perbedaan</th>
                <th scope="col" className="px-3.5 py-2.5">Keterangan</th>
                <th scope="col" className="px-3.5 py-2.5 w-48">Status Perbaikan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {grouped.map(({ weekNumber, items }) => (
                <Fragment key={weekNumber ?? 'general'}>
                  <tr className="bg-surface">
                    <th colSpan={4} scope="colgroup" className="px-3.5 py-2 text-xs font-semibold text-ink">
                      {weekNumber != null ? `Minggu ${weekNumber}` : 'Umum / Tingkat Course'} ({items.length})
                    </th>
                  </tr>
                  {items.map((item) => (
                    <tr key={item.key} className="hover:bg-surface/60">
                      <td className="min-w-[200px] px-3.5 py-2.5 align-top">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge tone="neutral">{item.targetLabel}</Badge>
                          {item.moodle_object_id != null && (
                            <span className="font-mono text-xs text-muted">#{item.moodle_object_id}</span>
                          )}
                        </div>
                        {item.objectTitle && (
                          <div className="mt-1 font-medium text-ink">{item.objectTitle}</div>
                        )}
                      </td>
                      <td className="px-3.5 py-2.5 align-top whitespace-nowrap">
                        <Badge tone={typeTone(item.type)}>{item.typeLabel}</Badge>
                      </td>
                      <td className="min-w-[240px] px-3.5 py-2.5 align-top">
                        <ComparisonDetail item={item} />
                      </td>
                      <td className="px-3.5 py-2.5 align-top whitespace-nowrap">
                        <Badge tone={item.repairMeta.tone}>{item.repairMeta.label}</Badge>
                      </td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
