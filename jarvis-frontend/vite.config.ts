import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
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
