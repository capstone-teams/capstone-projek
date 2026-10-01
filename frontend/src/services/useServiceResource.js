import { useCallback, useEffect, useState } from 'react'
import { mapRequestError } from './apiError.js'

/**
 * @template T
 * @typedef {{ status: 'loading', data: null, error: null } |
 *   { status: 'success', data: T, error: null } |
 *   { status: 'error', data: null, error: import('./apiError.js').ApiError }} ResourceState
 */

/** @template T @param {() => Promise<T>} load */
export function useServiceResource(load) {
  /** @type {[{ load: typeof load, attempt: number, state: ResourceState<T> } | null, Function]} */
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const retry = useCallback(() => setAttempt((current) => current + 1), [])
  /** @type {ResourceState<T>} */
  const state = result?.load === load && result.attempt === attempt
    ? result.state
    : { status: 'loading', data: null, error: null }

  useEffect(() => {
    let active = true
    load().then(
      (data) => {
        if (active) setResult({ load, attempt, state: { status: 'success', data, error: null } })
      },
      (error) => {
        if (active) setResult({ load, attempt, state: { status: 'error', data: null, error: mapRequestError(error) } })
      },
    )
    return () => { active = false }
  }, [load, attempt])

  return { ...state, retry }
}
