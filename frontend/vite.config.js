import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
 
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxies /api/* calls to your Flask backend during development,
    // so fetch("/api/auth/login") works without CORS issues and
    // without hardcoding http://localhost:5000 everywhere in authApi.js.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
 