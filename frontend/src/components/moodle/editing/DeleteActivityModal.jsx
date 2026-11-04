import { useState } from 'react';
import { Modal } from '../../ui';

/** Konfirmasi sebelum aktivitas dihapus dari kursus. */
export default function DeleteActivityModal({ open, activity, onClose, onConfirm }) {
  const [pending, setPending] = useState(false);

  const confirm = async () => {
    setPending(true);
    const ok = await onConfirm();
    setPending(false);
    if (ok) onClose();
  };

  return (
    <Modal
      open={open}
      title="Hapus aktivitas?"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn--ghost" onClick={onClose}>Batal</button>
          <button type="button" className="btn btn--danger" disabled={pending} onClick={confirm}>
            {pending ? 'Menghapus…' : 'Hapus'}
          </button>
        </>
      }
    >
      <p>
        <strong>{activity.name}</strong> beserta seluruh isinya (pengumpulan, nilai, dan diskusi) akan dihapus dari kursus.
      </p>
    </Modal>
  );
}
