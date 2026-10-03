import { useLayoutEffect, useRef } from 'react';

/** Ref yang selalu berisi nilai terbaru, untuk callback di effect/timer tanpa menambah dependency. */
export function useLatest(value) {
  const ref = useRef(value);
  useLayoutEffect(() => {
    ref.current = value;
  });
  return ref;
}
