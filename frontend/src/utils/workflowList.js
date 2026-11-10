// Daftar workflow dosen (FE-10.1).

/**
 * Satu workflow per mata kuliah: workflow dengan RPS yang sama (RPS diunggah ulang) diwakili workflow terbarunya
 * (created_at), sehingga workflow baru langsung menggantikan yang lama di daftar. Workflow lama tetap ada di server.
 */
export function latestWorkflowPerRps(items = []) {
  const time = (workflow) => Date.parse(workflow.created_at ?? '') || 0;
  const latest = new Map();
  items.forEach((workflow) => {
    const key = workflow.rps_id ?? workflow.id;
    if (!latest.has(key) || time(workflow) > time(latest.get(key))) latest.set(key, workflow);
  });
  return [...latest.values()].sort((a, b) => time(b) - time(a));
}
