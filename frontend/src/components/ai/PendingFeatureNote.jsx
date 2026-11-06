/** Keterangan singkat untuk kontrol yang tampil tetapi belum dapat dipakai karena layanannya belum tersedia. */
export default function PendingFeatureNote({ children = 'Fitur ini belum tersedia.' }) {
  return (
    <p className="mt-2 text-sm text-muted" data-pending-feature>
      {children}
    </p>
  );
}
