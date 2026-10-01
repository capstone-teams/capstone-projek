import { useCallback, useEffect, useState } from 'react'
import { ApiError, mapRequestError } from './apiError.ts'

type ResourceState<T> =
  | { status: 'loading'; data: null; error: null }
  | { status: 'success'; data: T; error: null }
  | { status: 'error'; data: null; error: ApiError }

export function useServiceResource<T>(load: () => Promise<T>) {
  const [result, setResult] = useState<{
    load: typeof load
    attempt: number
    state: ResourceState<T>
  } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const retry = useCallback(() => setAttempt((current) => current + 1), [])
  const state: ResourceState<T> = result?.load === load && result.attempt === attempt
    ? result.state
    : { status: 'loading', data: null, error: null }

  useEffect(() => {
    let active = true
    load().then(
      (data) => {
        if (active) setResult({ load, attempt, state: { status: 'success', data, error: null } })
      },
      (error: unknown) => {
        if (active) setResult({ load, attempt, state: { status: 'error', data: null, error: mapRequestError(error) } })
      },
    )
    return () => { active = false }
  }, [load, attempt])

  return { ...state, retry }
}
