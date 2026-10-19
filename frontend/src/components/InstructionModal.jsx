import { useState } from 'react';
import { ErrorAlert, Field, Modal } from './ui';

/** Modal berisi satu textarea wajib, mis. instruksi regenerasi atau alasan penolakan. */
export default function InstructionModal({ open, title, label, placeholder, submitLabel, danger, onSubmit, onClose }) {
  const [text, setText] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const close = () => {
    setText('');
    setError(null);
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setPending(true);
    setError(null);
    try {
      await onSubmit(text.trim());
      setText('');
      onClose();
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  };

  return (
    <Modal open={open} title={title} onClose={close}>
      <form className="form" onSubmit={submit}>
        <ErrorAlert error={error} />
        <Field label={label}>
          <textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder} required autoFocus />
        </Field>
        <div className="form__actions">
          <button type="button" className="btn btn--ghost" onClick={close}>
            Batal
          </button>
          <button type="submit" className={`btn ${danger ? 'btn--danger' : 'btn--primary'}`} disabled={pending || !text.trim()}>
            {pending ? 'Mengirim…' : submitLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
