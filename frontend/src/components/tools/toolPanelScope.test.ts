import { describe, expect, it } from 'vitest';
import { getActivePanelInstanceKey } from './toolPanelScope';

describe('getActivePanelInstanceKey', () => {
  it('scopes panel state by conversation and tab ID', () => {
    expect(getActivePanelInstanceKey('conversation:th_1', 'tab_2', 'terminal')).toBe('conversation:th_1:tab_2');
  });

  it('falls back to the tool type, then to an empty slot', () => {
    expect(getActivePanelInstanceKey('conversation:th_1', undefined, 'terminal')).toBe('conversation:th_1:terminal');
    expect(getActivePanelInstanceKey('conversation:th_1')).toBe('conversation:th_1:empty');
  });

  it('keeps the same tab in different conversations separate', () => {
    expect(getActivePanelInstanceKey('conversation:a', 'files')).not.toBe(
      getActivePanelInstanceKey('conversation:b', 'files'),
    );
  });
});
