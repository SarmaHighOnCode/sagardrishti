import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    // Offline mode is a hard requirement — everything must be bundled.
    // No CDN references anywhere. See docs/OFFLINE_MODE.md
    assetsInlineLimit: 0,
    sourcemap: true,
  },
});
