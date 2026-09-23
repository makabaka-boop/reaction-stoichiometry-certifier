import { defineConfig, devices } from "@playwright/test";

// The single E2E journey needs both services: uvicorn (exact API) and the
// Vite dev server (which proxies /api to it). In CI/Compose the same journey
// runs against the nginx-served build on http://localhost:8080.
const WEB_ORIGIN = process.env.E2E_WEB_ORIGIN ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: WEB_ORIGIN,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_WEB_ORIGIN
    ? undefined
    : [
        {
          command: "python3 -m uvicorn app.main:app --port 8000",
          cwd: "../backend",
          url: "http://localhost:8000/api/health",
          reuseExistingServer: true,
          timeout: 30_000,
        },
        {
          command: "npm run dev -- --port 5173",
          url: "http://localhost:5173",
          reuseExistingServer: true,
          timeout: 60_000,
        },
      ],
});
