import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Serve Pyodide from public/pyodide when it has been fetched (scripts/fetch_pyodide.py),
// otherwise fall back to the jsDelivr CDN.
const localPyodide = existsSync(new URL('./public/pyodide/VERSION', import.meta.url)) // written last by the fetch script

// `base: './'` keeps all asset URLs relative so the build works on any GitHub Pages path.
export default defineConfig({
  base: './',
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  worker: { format: 'es' },
  define: { __LOCAL_PYODIDE__: JSON.stringify(localPyodide) },
  server: { host: true, port: 5173 },
})
