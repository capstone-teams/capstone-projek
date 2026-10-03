import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        include: ['tests/**/*.test.{js,jsx}'],
        env: { VITE_USE_MOCK: 'true' },
    },
    server: {
        port: 3000,
        strictPort: true,
    },
    preview: {
        port: 3000,
        strictPort: true,
    },
});
