import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: 'frontend',
  plugins: [react()],
  build: { rollupOptions: { input: 'vite.html' } },
  server: { port: 5173 },
});
