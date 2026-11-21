import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === "true" },
    port: 5173,
    proxy: {
      "/api": process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
      "/health": process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
      "/docs": process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
      "/openapi.json": process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
