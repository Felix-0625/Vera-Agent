const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
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
