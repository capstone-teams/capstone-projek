import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppStateContext } from '../context/appStateContext';
import {
  REGENERATION_SCOPE,
  listWorkflowContents,
  regenerateWorkflowContents,
} from '../services/contentService';
import { EXECUTION_SCOPE, getExecution, listExecutions } from '../services/executionService';
import { findWorkflowForCourse, getWorkflow } from '../services/workflowService';
import {
  canRegenerateWorkflowContent,
  findOperationForMoodleCm,
  resolveContentForOperation,
} from '../utils/activityRegeneration';
import { WORKFLOW_EVENT, isWorkflowBusy } from '../utils/workflowStatus';
import { useApi } from './useApi';
import { usePolling } from './usePolling';
import { useWorkflowEvents } from './useWorkflowEvents';

const MAX_FULL_EXECUTIONS_TO_SCAN = 5;

async function findActivityOrigin(course, cmid) {
  if (!course || !cmid) return null;
  const keys = [course.moodle_course_id, course.id, course.shortname].filter(Boolean);
  if (keys.length === 0) return null;

  const workflow = await findWorkflowForCourse(...keys).catch(() => null);
  if (!workflow?.id) return null;

  const executions = await listExecutions(workflow.id).catch(() => []);
  const fullExecutions = executions
    .filter((ex) => ex?.scope === EXECUTION_SCOPE.FULL)
    .slice(0, MAX_FULL_EXECUTIONS_TO_SCAN);

  let operation = null;
  for (const summary of fullExecutions) {
    const detail = await getExecution(workflow.id, summary.execution_id).catch(() => null);
    operation = findOperationForMoodleCm(detail ? [detail] : [], cmid);
    if (operation) break;
  }
  if (!operation) return null;

  const contents = await listWorkflowContents(workflow.id).catch(() => []);
  const content = resolveContentForOperation(contents, operation);
  return content?.id ? { workflow, operation, contents, content } : null;
}

/**
 * Hook penghubung halaman detail aktivitas Moodle (`/course/:courseId/mod/:cmid`) dengan
 * aksi regenerasi konten AI workflow (scope `ITEM`) untuk dosen pengampu.
 */
export function useActivityRegeneration(course, cmid) {
  const notify = useContext(AppStateContext)?.notify;
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState(null);
  const [synced, setSynced] = useState(null);

  const origin = useApi(
    () => findActivityOrigin(course, cmid),
    [course?.id, course?.moodle_course_id, course?.shortname, cmid],
  );
  const workflowId = origin.data?.workflow?.id ?? null;
  const syncKey = `${course?.id ?? ''}:${cmid ?? ''}:${workflowId ?? ''}`;

  const mountedRef = useRef(true);
  const activeKeyRef = useRef(syncKey);
  useEffect(() => {
    mountedRef.current = true;
    activeKeyRef.current = syncKey;
    return () => {
      mountedRef.current = false;
    };
  }, [syncKey]);

  const activeSynced = synced?.key === syncKey ? synced : null;
  const workflow = activeSynced?.workflow ?? origin.data?.workflow ?? null;
  const operation = origin.data?.operation ?? null;
  const contentsList = activeSynced?.contents ?? origin.data?.contents ?? null;
  const content = operation ? resolveContentForOperation(contentsList, operation) : null;

  const busy = isWorkflowBusy(workflow);
  const eligibility = canRegenerateWorkflowContent(workflow);

  const syncAll = useCallback(async () => {
    if (!workflowId) return;
    const targetKey = activeKeyRef.current;
    const [wf, list] = await Promise.all([
      getWorkflow(workflowId).catch(() => null),
      listWorkflowContents(workflowId).catch(() => null),
    ]);
    if (!mountedRef.current || activeKeyRef.current !== targetKey) return;
    setSynced((prev) => ({
      key: targetKey,
      workflow: wf ?? (prev?.key === targetKey ? prev.workflow : null),
      contents: list ?? (prev?.key === targetKey ? prev.contents : null),
    }));
  }, [workflowId]);

  useWorkflowEvents(
    workflowId ? [workflowId] : [],
    (event) => {
      if (
        event?.event === WORKFLOW_EVENT.WAITING_FOR_REVIEW
        || event?.event === WORKFLOW_EVENT.STAGE_COMPLETED
        || event?.event === WORKFLOW_EVENT.COMPLETED
        || event?.event === WORKFLOW_EVENT.FAILED
        || event?.event === WORKFLOW_EVENT.CONTENT_VALIDATED
      ) {
        syncAll();
      }
    },
  );

  usePolling(syncAll, 3000, Boolean(workflowId && busy));

  const submitRegenerate = async (notes) => {
    if (!workflowId || !content?.id) return null;
    const result = await regenerateWorkflowContents(workflowId, {
      scope: REGENERATION_SCOPE.ITEM,
      content_id: content.id,
      notes,
    });
    setNotice({ key: syncKey, message: result?.message || 'Regenerasi konten dijadwalkan.' });
    notify?.('Regenerasi konten dimulai.', { type: 'info' });
    void syncAll();
    return result;
  };

  return {
    supported: Boolean(workflowId && operation && content?.id),
    workflow,
    operation,
    content,
    busy,
    eligibility,
    modalOpen,
    startedNotice: notice?.key === syncKey ? notice.message : null,
    openModal: () => setModalOpen(true),
    closeModal: () => setModalOpen(false),
    clearNotice: () => setNotice(null),
    submitRegenerate,
  };
}
