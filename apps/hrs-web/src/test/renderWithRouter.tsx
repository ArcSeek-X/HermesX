import { render, type RenderOptions } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';

/** Page tests use the same router context required by AppPage and navigation hooks. */
export function renderWithRouter(ui: ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: MemoryRouter, ...options });
}
