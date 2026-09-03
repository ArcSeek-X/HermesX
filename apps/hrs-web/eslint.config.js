import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores([
    'dist',
    'playwright-report',
    'test-results',
    // FullCalendar Breezy 主题参考 demo（FullCalendar 7.x Themes API），与仓库锁定的
    // 6.1.21 不兼容，仅作视觉对照，不参与 lint。见 tsconfig.app.json 同目录 exclude。
    'src/components/common/LiveCalendarGrid/demo/**',
  ]),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
