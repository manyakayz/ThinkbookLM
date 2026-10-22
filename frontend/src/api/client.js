// Centralized API client for ThinkbookLM

let activeCsrfToken = '';
let onUnauthorizedCallback = null;

export function setCsrfToken(token) {
  activeCsrfToken = token || '';
}

export function getCsrfToken() {
  if (activeCsrfToken) return activeCsrfToken;
  // Try reading from thinkbook_csrf cookie
  const match = document.cookie.match(/(?:^|;\s*)thinkbook_csrf=([^;]+)/);
  if (match) {
    activeCsrfToken = decodeURIComponent(match[1]);
  }
  return activeCsrfToken;
}

export function setUnauthorizedHandler(callback) {
  onUnauthorizedCallback = callback;
}

export async function apiFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };

  // Attach CSRF token on state-changing requests
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const token = getCsrfToken();
    if (token && !headers['X-CSRF-Token']) {
      headers['X-CSRF-Token'] = token;
    }
  }

  // Ensure credentials are always included so HTTP-only cookies are sent
  const fetchOptions = {
    ...options,
    method,
    headers,
    credentials: 'include',
  };

  const response = await fetch(url, fetchOptions);

  if (response.status === 401) {
    if (onUnauthorizedCallback && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      onUnauthorizedCallback();
    }
  }

  return response;
}

// Global fetch wrapper to ensure credentials & CSRF are sent for all /api calls
const originalFetch = window.fetch;
window.fetch = async function (input, init = {}) {
  const url = typeof input === 'string' ? input : input.url;
  if (typeof url === 'string' && (url.startsWith('/api') || url.startsWith('/auth') || url.includes('/api/'))) {
    const method = (init.method || 'GET').toUpperCase();
    const headers = new Headers(init.headers || {});

    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      const token = getCsrfToken();
      if (token && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', token);
      }
    }

    const modifiedInit = {
      ...init,
      headers,
      credentials: init.credentials || 'include',
    };

    const res = await originalFetch(input, modifiedInit);
    if (res.status === 401 && onUnauthorizedCallback && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      onUnauthorizedCallback();
    }
    return res;
  }
  return originalFetch(input, init);
};

export async function loginApi(email, password) {
  const res = await apiFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Login failed.');
  }
  setCsrfToken(data.csrf_token);
  return data;
}

export async function registerApi(fullName, email, password, confirmPassword) {
  const res = await apiFetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
      confirm_password: confirmPassword,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Registration failed.');
  }
  setCsrfToken(data.csrf_token);
  return data;
}

export async function logoutApi() {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } finally {
    setCsrfToken('');
  }
}

export async function getMeApi() {
  const res = await apiFetch('/api/auth/me');
  if (!res.ok) {
    return null;
  }
  const data = await res.json();
  setCsrfToken(data.csrf_token);
  return data;
}

export async function chatRagApi({
  message,
  notebookId,
  documentIds = [],
  history = [],
  topK = 5,
  temperature = 0.3,
}) {
  const payload = {
    message,
    notebook_id: notebookId,
    document_ids: documentIds,
    history,
    top_k: topK,
    temperature,
  };

  const res = await apiFetch('/api/chat/rag', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail || `Server error (${res.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

