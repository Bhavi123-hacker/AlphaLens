import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import hooks from 'eslint-plugin-react-hooks'
import refresh from 'eslint-plugin-react-refresh'
export default tseslint.config(
  { ignores: ['node_modules/**', 'dist/**', 'src/api/generated.ts', 'playwright-report/**', 'test-results/**'] },
  js.configs.recommended, ...tseslint.configs.recommended,
  { files: ['scripts/*.mjs'], languageOptions: { globals: { console: 'readonly', process: 'readonly' } } },
  { files: ['**/*.{ts,tsx}'], plugins: { 'react-hooks': hooks, 'react-refresh': refresh },
    languageOptions: { globals: { console: 'readonly', process: 'readonly', URL: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly', AbortController: 'readonly', DOMException: 'readonly', fetch: 'readonly', window: 'readonly', document: 'readonly', localStorage: 'readonly', ResizeObserver: 'readonly' } },
    rules: { ...hooks.configs.recommended.rules, 'react-refresh/only-export-components': ['warn', { allowConstantExport: true }] } },
)
