import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  base: '/ai-pulse/',
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        predictions: resolve(__dirname, 'predictions/index.html'),
        'dead-or-alive': resolve(__dirname, 'dead-or-alive/index.html'),
      },
    },
  },
})
