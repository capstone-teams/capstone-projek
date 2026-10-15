/** Avatar user: foto dari Moodle bila ada, selain itu inisial. */
export function Avatar({ name = '', src, size = 'md' }) {
  const sizes = { sm: 'size-7 text-xs', md: 'size-9 text-sm', lg: 'size-20 text-2xl' };
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join('')
    .toUpperCase();
  // URL default Moodle (u/f1, u/f2) adalah gambar siluet; tampilkan inisial saja.
  const usable = src && !/\/u\/f\d/.test(src);
  return usable ? (
    <img src={src} alt="" className={`${sizes[size]} shrink-0 rounded-full object-cover`} />
  ) : (
    <span className={`${sizes[size]} grid shrink-0 place-items-center rounded-full bg-[#e3e7eb] font-bold text-muted`} aria-hidden="true">
      {initials || '?'}
    </span>
  );
}
