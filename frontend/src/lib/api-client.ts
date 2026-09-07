import { ApiError } from '../types';

const BASE_URL = '/api/v1';

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('usimamizi-access-token');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const cleanEndpoint = endpoint.startsWith('/api/v1') ? endpoint.slice(7) : endpoint;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${cleanEndpoint}`, {
      ...options,
      headers,
    });
  } catch {
    throw {
      code: 'NETWORK_ERROR',
      detail: 'Network error or server unreachable. Please check your connection.',
      field_errors: {},
    } as ApiError;
  }

  // Handle 401 Unauthorized by attempting a token refresh
  if (response.status === 401 && !cleanEndpoint.includes('/auth/login') && !cleanEndpoint.includes('/auth/refresh')) {
    const refreshToken = localStorage.getItem('usimamizi-refresh-token');
    if (refreshToken) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${BASE_URL}/accounts/auth/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
          });

          if (refreshRes.ok) {
            const refreshData = await refreshRes.json();
            if (refreshData.access) {
              localStorage.setItem('usimamizi-access-token', refreshData.access);
              if (refreshData.refresh) {
                localStorage.setItem('usimamizi-refresh-token', refreshData.refresh);
              }
              onTokenRefreshed(refreshData.access);

              // Retry original request with new token
              headers['Authorization'] = `Bearer ${refreshData.access}`;
              const retryResponse = await fetch(`${BASE_URL}${cleanEndpoint}`, {
                ...options,
                headers,
              });

              if (retryResponse.status === 204) {
                return {} as T;
              }

              const acceptHeader = options.headers ? (options.headers as Record<string, string>)['Accept'] : undefined;
              if (acceptHeader === 'application/octet-stream' || endpoint.includes('/export-')) {
                const blob = await retryResponse.blob();
                return blob as unknown as T;
              }

              let retryData: any = {};
              try {
                retryData = await retryResponse.json();
              } catch {
                retryData = {};
              }

              if (!retryResponse.ok) {
                throw {
                  code: retryData.code || 'API_ERROR',
                  detail: retryData.detail || 'An unexpected error occurred.',
                  field_errors: retryData.field_errors || {},
                } as ApiError;
              }

              return retryData as T;
            }
          } else {
            // Refresh token itself expired or invalid
            localStorage.removeItem('usimamizi-access-token');
            localStorage.removeItem('usimamizi-refresh-token');
            localStorage.removeItem('usimamizi-user');
            localStorage.removeItem('usimamizi-active-company');
            localStorage.removeItem('usimamizi-active-company-id');
          }
        } catch {
          // Network or parsing error during refresh
        } finally {
          isRefreshing = false;
        }
      } else {
        // Another request is already refreshing, wait for it
        return new Promise<T>((resolve, reject) => {
          subscribeTokenRefresh(async (newToken) => {
            try {
              headers['Authorization'] = `Bearer ${newToken}`;
              const retryResponse = await fetch(`${BASE_URL}${cleanEndpoint}`, {
                ...options,
                headers,
              });

              if (retryResponse.status === 204) {
                resolve({} as T);
                return;
              }

              const acceptHeader = options.headers ? (options.headers as Record<string, string>)['Accept'] : undefined;
              if (acceptHeader === 'application/octet-stream' || endpoint.includes('/export-')) {
                const blob = await retryResponse.blob();
                resolve(blob as unknown as T);
                return;
              }

              let retryData: any = {};
              try {
                retryData = await retryResponse.json();
              } catch {
                retryData = {};
              }

              if (!retryResponse.ok) {
                reject({
                  code: retryData.code || 'API_ERROR',
                  detail: retryData.detail || 'An unexpected error occurred.',
                  field_errors: retryData.field_errors || {},
                } as ApiError);
                return;
              }

              resolve(retryData as T);
            } catch (err) {
              reject(err);
            }
          });
        });
      }
    }
  }

  if (response.status === 204) {
    return {} as T;
  }

  const acceptHeader = options.headers ? (options.headers as Record<string, string>)['Accept'] : undefined;
  const isBlob = acceptHeader === 'application/octet-stream';
  if (isBlob || endpoint.includes('/export-')) {
    const blob = await response.blob();
    return blob as unknown as T;
  }

  let data: any = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const error: ApiError = {
      code: data.code || 'API_ERROR',
      detail: data.detail || 'An unexpected error occurred.',
      field_errors: data.field_errors || {},
    };
    throw error;
  }

  return data as T;
}

export interface RequestConfig {
  responseType?: 'blob';
  headers?: Record<string, string>;
}

export const apiClient = {
  get: async <T>(endpoint: string, config: RequestConfig = {}): Promise<{ data: T }> => {
    const isBlob = config.responseType === 'blob';
    const res = await apiFetch<T>(endpoint, {
      method: 'GET',
      headers: {
        ...(isBlob ? { 'Accept': 'application/octet-stream' } : {}),
        ...(config.headers || {}),
      },
    });
    return { data: res };
  },
  post: async <T>(endpoint: string, body?: unknown, config: RequestConfig = {}): Promise<{ data: T }> => {
    const res = await apiFetch<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body || {}),
      headers: config.headers || {},
    });
    return { data: res };
  },
  put: async <T>(endpoint: string, body?: unknown, config: RequestConfig = {}): Promise<{ data: T }> => {
    const res = await apiFetch<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body || {}),
      headers: config.headers || {},
    });
    return { data: res };
  },
  patch: async <T>(endpoint: string, body?: unknown, config: RequestConfig = {}): Promise<{ data: T }> => {
    const res = await apiFetch<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body || {}),
      headers: config.headers || {},
    });
    return { data: res };
  },
  delete: async <T>(endpoint: string, config: RequestConfig = {}): Promise<{ data: T }> => {
    const res = await apiFetch<T>(endpoint, {
      method: 'DELETE',
      headers: config.headers || {},
    });
    return { data: res };
  },
};
