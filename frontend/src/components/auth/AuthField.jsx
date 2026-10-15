import { AUTH_INPUT_CLASS } from './authStyles';
import AuthFieldGroup from './AuthFieldGroup';

/** Label + input untuk form auth. Prop lain diteruskan ke <input>. */
export default function AuthField({ id, label, ...inputProps }) {
  return (
    <AuthFieldGroup id={id} label={label}>
      <input id={id} className={AUTH_INPUT_CLASS} {...inputProps} />
    </AuthFieldGroup>
  );
}
