import { useContext, useMemo, useReducer } from 'react';
import { AppStateContext } from '../context/appStateContext';
import { appStateReducer, initialAppState, workflowActions } from '../state/appState';

/**
 * Pantauan workflow di state aplikasi (FE-03.1): { workflows, loadWorkflow, receiveWorkflowEvent,
 * setWorkflowConnection }. Tanpa <AppStateProvider> (mis. pada tes komponen) state-nya lokal ke pemanggil.
 */
export function useWorkflowStore() {
  const ctx = useContext(AppStateContext);
  const [local, dispatch] = useReducer(appStateReducer, initialAppState);
  const localActions = useMemo(() => workflowActions(dispatch), []);
  return ctx
    ? { workflows: ctx.workflows, loadWorkflow: ctx.loadWorkflow, receiveWorkflowEvent: ctx.receiveWorkflowEvent, setWorkflowConnection: ctx.setWorkflowConnection }
    : { workflows: local.workflows, ...localActions };
}
