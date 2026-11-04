import { useId, useState } from 'react';
import { ErrorAlert, Field, Modal } from '../ui';

/** Modal berisi satu textarea wajib, mis. instruksi regenerasi atau alasan penolakan. */
export default function InstructionModal({ open, title, label, hint, placeholder, submitLabel, danger, onSubmit, onClose }) {
  const [text, setText] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const [fieldError, setFieldError] = useState(null);
  const errorId = useId();

  const close = () => {
    setText('');
    setError(null);
    setFieldError(null);
    onClose();
  };

  const change = (e) => {
    setText(e.target.value);
    if (fieldError && e.target.value.trim()) setFieldError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) {
      setFieldError(`${label} wajib diisi.`);
      return;
    }
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
      <form className="form" onSubmit={submit} noValidate>
        <ErrorAlert error={error} />
        <Field label={label} hint={hint} required error={fieldError} errorId={errorId}>
          <textarea
            rows={4}
            value={text}
            onChange={change}
            placeholder={placeholder}
            aria-required="true"
            aria-invalid={fieldError ? 'true' : undefined}
            aria-describedby={fieldError ? errorId : undefined}
            className={fieldError ? 'border-danger focus:border-danger focus:ring-danger/20' : undefined}
            autoFocus
          />
        </Field>
        <div className="form__actions">
          <button type="button" className="btn btn--ghost" onClick={close}>
            Batal
          </button>
          <button type="submit" className={`btn ${danger ? 'btn--danger' : 'btn--primary'}`} disabled={pending}>
            {pending ? 'Mengirim…' : submitLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
