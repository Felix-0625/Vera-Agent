/**
 * Shared fetch wrapper for the local VeraAgent API.
 *
 * Requests are same-origin: the backend serves the built UI, and the Vite dev server proxies `/api`.
 * Non-2xx responses throw `Error(body.error)`.
 */
export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMessage = `HTTP error ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody.error) errMessage = errBody.error;
    } catch {
      // ignore
    }
    throw new Error(errMessage);
  }

  return response.json() as Promise<T>;
}
