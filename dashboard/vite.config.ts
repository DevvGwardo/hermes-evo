import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api/stream': { target: 'http://localhost:18789', ws: false, headers: { 'Connection': '' } },
      '/api': 'http://localhost:18789',
    },
  },
});
