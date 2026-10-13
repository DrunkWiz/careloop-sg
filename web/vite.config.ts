import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// One build, two front doors: /senior and /care.
export default defineConfig({
  plugins: [react()],
  server: { host: true },
});
