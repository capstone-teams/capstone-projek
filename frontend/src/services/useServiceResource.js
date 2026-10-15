import { useApi } from '../hooks/useApi';
import { mapRequestError } from './apiError.js';
export function useServiceResource(load) {
    const { data, error, loading, reload } = useApi(load, [load]);
    return {
        status: loading ? 'loading' : error ? 'error' : 'success',
        data,
        error: error ? mapRequestError(error) : null,
        retry: reload,
    };
}
