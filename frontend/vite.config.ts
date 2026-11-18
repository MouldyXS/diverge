import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The backend's CORS policy allows exactly these origins, so the port is fixed (strictPort) for both the
// development server and `vite preview` (whose default port, 4173, is not allowed).
const local = { host: "127.0.0.1", port: 5173, strictPort: true };

export default defineConfig({
  plugins: [react()],
  server: local,
  preview: local,
  test: {
    projects: [
      {
        extends: true,
        // Test runner only (not the dev server): lets a test compare the P0 notice with its source document.
        server: { fs: { strict: false } },
        test: {
          name: "unit",
          environment: "jsdom",
          include: ["src/**/*.test.{ts,tsx}"],
          exclude: ["src/**/*.integration.test.ts"],
          setupFiles: ["./src/test/setup.ts"],
          // Keep the design tokens readable (Vitest empties CSS by default) so their contrast can be tested.
          css: { include: [/tokens\.css/] },
        },
      },
      {
        extends: true,
        test: {
          name: "integration",
          environment: "node",
          include: ["src/**/*.integration.test.ts"],
        },
      },
    ],
  },
});
