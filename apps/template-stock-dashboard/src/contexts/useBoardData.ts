import { useContext } from 'react';
import { BoardDataContext } from './boardDataValueContext';

export function useBoardData() {
  const context = useContext(BoardDataContext);
  if (!context) {
    throw new Error('useBoardData must be used within BoardDataProvider');
  }
  return context;
}
