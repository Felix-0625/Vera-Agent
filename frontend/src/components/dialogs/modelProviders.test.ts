import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { MODEL_PROVIDERS, getProviderBaseUrl } from './modelProviders';

/** Provider IDs accepted by `_validate_model` in vera-agent/src/vera_agent/server/routes/settings.py. */
function backendProviderIds(): string[] {
  const settingsPath = fileURLToPath(new URL('../../../../vera-agent/src/vera_agent/server/routes/settings.py', import.meta.url));
  const source = readFileSync(settingsPath, 'utf-8');
  const block = source.match(/model\.get\("provider", "deepseek"\) not in \{([^}]*)\}/);
  if (!block) throw new Error('Provider allow-list not found in settings.py');
  return [...block[1].matchAll(/"([a-z]+)"/g)].map((match) => match[1]);
}

describe('MODEL_PROVIDERS', () => {
  it('matches the provider allow-list enforced by the backend', () => {
    expect(MODEL_PROVIDERS.map((provider) => provider.id).sort()).toEqual(backendProviderIds().sort());
  });

  it('has unique IDs and absolute HTTP(S) default URLs except for custom', () => {
    const ids = MODEL_PROVIDERS.map((provider) => provider.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const provider of MODEL_PROVIDERS) {
      if (provider.id === 'custom') expect(provider.baseUrl).toBe('');
      else expect(provider.baseUrl).toMatch(/^https?:\/\/[^/]+/);
    }
  });

  it('resolves default base URLs by provider ID', () => {
    expect(getProviderBaseUrl('deepseek')).toBe('https://api.deepseek.com');
    expect(getProviderBaseUrl('custom')).toBe('');
  });
});
