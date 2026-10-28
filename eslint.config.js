import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'public/**', 'node_modules/**', 'python/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, __LOCAL_PYODIDE__: 'readonly' },
    },
    rules: {
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-self-closing': ['warn', { html: { void: 'always', normal: 'always', component: 'always' } }],
      'vue/require-default-prop': 'off',
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
  { files: ['scripts/**/*.mjs', 'vite.config.js', 'eslint.config.js'], languageOptions: { globals: globals.node } },
]
