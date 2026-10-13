import { useContext } from 'react';
import { AppSettingsContext } from './appSettingsContext';

export function useAppSettings() {
  const context = useContext(AppSettingsContext);
  if (!context) {
    throw new Error('useAppSettings must be used within AppSettingsProvider');
  }
  return context;
}
