import { defineConfig } from "@playwright/test";

// Smoke tests load the unpacked build in bundled Chromium (branded Chrome ≥137 can't).
// Runs inside the builder container only: `make in-docker-smoke EXT=<slug>`.
export default defineConfig({ testDir: "tests/smoke", retries: 0, reporter: "list" });
