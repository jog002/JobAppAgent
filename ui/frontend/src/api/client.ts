// API base URL - use relative path in production, proxy in development
const API_BASE = '/api';

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

// GET request
export async function get<T>(endpoint: string): Promise<T> {
  return fetchAPI<T>(endpoint);
}

// PATCH request
export async function patch<T>(endpoint: string, data: unknown): Promise<T> {
  return fetchAPI<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// POST request
export async function post<T>(endpoint: string, data: unknown): Promise<T> {
  return fetchAPI<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export default { get, patch, post };
