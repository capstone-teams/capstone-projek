import { Badge, Card } from '../../ui';
import { VERIFICATION_STATUS_META } from '../../../services/verificationService';
import { formatDateTime } from '../../../utils/format';

/**
 * Daftar riwayat hasil verifikasi Moodle workflow (FE-18.2), terbaru lebih dulu.
 */
export default function VerificationHistoryCard({
  verifications = [],
  activeVerificationId = null,
  onSelectVerification,
}) {
  if (!verifications || verifications.length === 0) return null;

  return (
    <Card title={`Riwayat Verifikasi (${verifications.length})`}>
      <p className="mb-4 text-sm text-muted">
        Daftar pemeriksaan kesesuaian course Moodle beserta perbaikan otomatis yang pernah dijalankan pada workflow ini.
      </p>

      <div className="divide-y divide-line rounded-lg border border-line bg-surface">
        {verifications.map((item, idx) => {
          const isSelected = item.verification_id === activeVerificationId;
          const meta = VERIFICATION_STATUS_META[item.status] ?? {
            label: item.status || '-',
            tone: 'neutral',
          };
          const remaining = item.discrepancies?.length ?? 0;
          const repairs = item.repair_count ?? 0;
          const summary = item.summary;

          return (
            <div
              key={item.verification_id}
              className={`flex flex-wrap items-center justify-between gap-3 p-3.5 transition-colors ${
                isSelected ? 'bg-primary-light/40' : 'hover:bg-white'
              }`}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-ink">
                    {item.verification_id}
                  </span>
                  {idx === 0 && <span className="text-xs text-muted">(terbaru)</span>}
                  <Badge tone={meta.tone}>{meta.label}</Badge>
                  {isSelected && (
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                      ● Sedang Ditinjau
                    </span>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted">
                  <span>Waktu: {formatDateTime(item.verified_at)}</span>
                  {summary && (
                    <>
                      <span>·</span>
                      <span>
                        Section <strong>{summary.actual_sections ?? 0}/{summary.expected_sections ?? 0}</strong> · Activity{' '}
                        <strong>{summary.found_activities ?? 0}/{summary.expected_activities ?? 0}</strong>
                      </span>
                    </>
                  )}
                  <span>·</span>
                  <span>
                    Perbaikan: <strong>{repairs}</strong> · Sisa perbedaan: <strong>{remaining}</strong>
                  </span>
                </div>
              </div>

              {!isSelected && onSelectVerification && (
                <button
                  type="button"
                  className="btn btn--secondary btn--xs"
                  onClick={() => onSelectVerification(item.verification_id)}
                >
                  Tinjau Detail
                </button>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
