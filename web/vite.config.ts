import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the browser calls /api/* and Vite proxies it to the api
// service; in production nginx performs the same reverse proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
