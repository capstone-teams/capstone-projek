import { isWorkflowFinished } from '../../utils/workflowStatus';

const NOTES = {
  connected: 'Status diperbarui otomatis.',
  connecting: 'Menghubungkan pembaruan otomatis…',
  reconnecting: 'Koneksi terputus, menyambungkan ulang. Status tetap diperbarui berkala.',
  offline: 'Status diperbarui berkala.',
};

/** Keterangan singkat cara status diperbarui; tidak ditampilkan lagi setelah workflow berhenti. */
export default function WorkflowConnectionNote({ workflow, connection }) {
  if (!workflow || isWorkflowFinished(workflow)) return null;
  return (
    <p className="mb-3 text-sm text-muted" role="status" data-connection={connection}>
      {NOTES[connection] ?? NOTES.offline}
    </p>
  );
}
