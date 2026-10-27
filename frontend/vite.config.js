import process from 'node:process';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// During development the React app calls "/api/..." and Vite forwards those
// requests (and "/media/..." recordings) to Django, so no CORS setup is needed.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  const proxy = {
    '/api': { target: backend, changeOrigin: false },
    '/media': { target: backend, changeOrigin: false },
  };

  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
  };
});
