import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy /api to the FastAPI server. Prod: FastAPI serves the built files from the same origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
