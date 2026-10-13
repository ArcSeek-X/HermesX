import { createContext } from 'react';
import type { AppSettings } from '@/types';

export interface AppSettingsContextValue {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  replaceSettings: (next: AppSettings) => void;
  getRefreshInterval: (key: keyof AppSettings['refreshInterval']) => number;
}

export const AppSettingsContext = createContext<AppSettingsContextValue | null>(null);
