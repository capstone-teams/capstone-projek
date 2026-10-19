import { useEffect } from 'react';
import { subscribeCourseEvents } from '../services/monitoringSocket';
import { useLatest } from './useLatest';

/** Berlangganan event WebSocket course; `onEvent` dipanggil untuk tiap event. */
export function useCourseEvents(courseId, onEvent, enabled = true) {
  const ref = useLatest(onEvent);

  useEffect(() => {
    if (!courseId || !enabled) return undefined;
    return subscribeCourseEvents(courseId, (ev) => ref.current(ev));
  }, [ref, courseId, enabled]);
}
