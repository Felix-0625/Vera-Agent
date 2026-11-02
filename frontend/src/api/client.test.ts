import { afterEach, describe, expect, it, vi } from 'vitest';
import { request } from './client';

function mockFetch(response: { ok: boolean; status: number; body?: unknown; invalidJson?: boolean }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: response.invalidJson
      ? () => Promise.reject(new SyntaxError('bad json'))
      : () => Promise.resolve(response.body),
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('request', () => {
  it('sends JSON headers, keeps caller options, and returns the parsed body', async () => {
    const fetchMock = mockFetch({ ok: true, status: 200, body: { items: [1] } });

    await expect(request('/api/taskboard/tasks', { method: 'POST', headers: { 'X-Trace': '1' } })).resolves.toEqual({
      items: [1],
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/taskboard/tasks');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual({ 'Content-Type': 'application/json', 'X-Trace': '1' });
  });

  it('surfaces the backend `error` field as the thrown message', async () => {
    mockFetch({ ok: false, status: 409, body: { error: 'Work item changed; refresh and retry' } });
    await expect(request('/api/taskboard/tasks/x', { method: 'PATCH' })).rejects.toThrow(
      'Work item changed; refresh and retry',
    );
  });

  it('falls back to the HTTP status when the error body is not JSON', async () => {
    mockFetch({ ok: false, status: 502, invalidJson: true });
    await expect(request('/api/mcp/market')).rejects.toThrow('HTTP error 502');
  });
});
