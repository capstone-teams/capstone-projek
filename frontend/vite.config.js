import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000';

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 3000,
      // Teruskan /api ke FastAPI backend agar tidak perlu CORS saat development.
      proxy: {
        '/api': { target: backendUrl, changeOrigin: true, ws: true },
      },
    },
    test: {
      environment: 'jsdom',
      include: ['tests/**/*.test.{js,jsx}'],
      // Tes UI memakai Moodle dummy agar tidak bergantung pada server Moodle.
      env: { VITE_MOODLE_MOCK: 'true', VITE_USE_MOCK: 'true' },
    },
  };
});
