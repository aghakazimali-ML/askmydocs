import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built files are committed to src/motion/dist so Streamlit Cloud needs no Node build step.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "../src/motion/dist", emptyOutDir: true, chunkSizeWarningLimit: 800 },
});
