// @vitest-environment node
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { describe, expect, it, vi } from 'vitest';

const html = readFileSync(resolve(__dirname, '..', 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
if (!script) throw new Error('Missing pre-render theme bootstrap');

describe('index.html theme bootstrap', () => {
  it.each([
    ['light', false, 'light'],
    ['dark', false, 'dark'],
    ['system', true, 'dark'],
    ['system', false, 'light'],
    ['invalid', true, 'dark'],
  ])('resolves stored %s with system dark=%s', (mode, systemDark, expected) => {
    const root = { classList: { remove: vi.fn(), add: vi.fn() }, style: { colorScheme: '' } };
    runInNewContext(script, {
      document: { documentElement: root },
      localStorage: { getItem: (key: string) => key === 'hrs-pref-theme'
        ? JSON.stringify({ themeMode: mode }) : null },
      window: { matchMedia: () => ({ matches: systemDark }) },
    });
    expect(root.classList.remove).toHaveBeenCalledWith('light', 'dark');
    expect(root.classList.add).toHaveBeenCalledWith(expected);
    expect(root.style.colorScheme).toBe(expected);
  });

  it.each(['legacy', 'malformed', 'unavailable', 'missing'])('handles %s storage', (scenario) => {
    const root = { classList: { remove: vi.fn(), add: vi.fn() }, style: { colorScheme: '' } };
    runInNewContext(script, {
      document: { documentElement: root },
      localStorage: { getItem: (key: string) => {
        if (scenario === 'unavailable') throw new Error('Storage denied');
        if (scenario === 'malformed') return '{';
        return scenario === 'legacy' && key.endsWith('.themeMode') ? 'light' : null;
      } },
      window: { matchMedia: () => ({ matches: true }) },
    });
    expect(root.style.colorScheme).toBe(scenario === 'legacy' ? 'light' : 'dark');
  });
});
