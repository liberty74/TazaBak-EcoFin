import axios from 'axios';

export const getApiBaseUrl = (): string => {
  const configuredUrl = localStorage.getItem('apiBaseUrl') || import.meta.env.VITE_API_BASE_URL;
  if (configuredUrl) return configuredUrl;

  // When the UI is opened from a phone over Wi-Fi, 127.0.0.1 would point to
  // the phone itself. Reuse the page host so the same FastAPI instance on the
  // developer's laptop is addressed automatically.
  const host = window.location.hostname;
  const apiHost = host === 'localhost' || host === '127.0.0.1' ? '127.0.0.1' : host;
  return `http://${apiHost}:8000`;
};

export const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
});

function isDispatcherProtectedRequest(method: string, url: string): boolean {
  if (!url) return false;
  if (url.startsWith('/api/dispatcher/') || url.startsWith('/api/dispatch/') || url.startsWith('/api/alerts/')) {
    return true;
  }
  if (method.toLowerCase() === 'post' && url.match(/^\/api\/volunteer\/tasks\/\d+\/complete$/)) {
    return true;
  }
  return false;
}

apiClient.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  if (config.url && isDispatcherProtectedRequest(config.method || 'get', config.url)) {
    const key = sessionStorage.getItem('dispatcherKey');
    if (key) {
      config.headers['X-Dispatcher-Key'] = key;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      const config = error.config;
      if (config && config.url && isDispatcherProtectedRequest(config.method || 'get', config.url)) {
        sessionStorage.removeItem('dispatcherKey');
        window.dispatchEvent(new Event('dispatcher-auth-failed'));
      }
    }
    return Promise.reject(error);
  }
);

export function resolveMediaUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  // If it's an absolute path that starts with /static/, prepend the current API_BASE_URL
  const baseUrl = getApiBaseUrl();
  if (url.startsWith('/')) {
    return `${baseUrl}${url}`;
  }
  return `${baseUrl}/${url}`;
}

export * from './errors';
