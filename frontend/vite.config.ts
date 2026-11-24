import process from "node:process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local development, the backend normally runs on the same machine.
// In Docker Compose, override this with the backend service DNS name.
const apiProxyTarget =
  process.env.JARVIS_API_PROXY_TARGET || "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    // Raise warning threshold — Three.js vendor chunk is expected to be large
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          // Three.js and 3D rendering — large but cached across sessions
          "vendor-three": ["three"],
          // React core — very stable, long cache TTL
          "vendor-react": ["react", "react-dom"],
        },
      },
    },
  },
});
