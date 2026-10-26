import { defineConfig } from "vite";
export default defineConfig({
  build: {
    outDir: "../agenticai/static",
    emptyOutDir: false,
    rollupOptions: {
      output: {
        manualChunks: {
          graph: ["@xyflow/react"],
          markdown: ["react-markdown"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/tutorial": "http://127.0.0.1:8765",
    },
  },
});
