import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
// Read environment variables from the repository root .env rather than a
// separate frontend/.env, to keep configuration in one place — see
// ../.env.example and docs/GETTING_STARTED.md.
export default defineConfig({
    plugins: [react()],
    envDir: "../",
    server: {
        port: 5173,
        // Test setup and specs live in ../tests/frontend (outside this root); allow it.
        fs: { allow: [".."] },
    },
    test: {
        environment: "jsdom",
        globals: true,
        setupFiles: ["../tests/frontend/setup.ts"],
        include: ["src/**/*.test.{ts,tsx}", "../tests/frontend/*.test.{ts,tsx}"],
        exclude: ["**/node_modules/**", "**/dist/**"],
    },
});
