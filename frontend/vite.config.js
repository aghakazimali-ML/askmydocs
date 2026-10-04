import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Built files are committed to src/motion/dist so Streamlit Cloud needs no Node build step.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  build: { outDir: "../src/motion/dist", emptyOutDir: true, chunkSizeWarningLimit: 800 },
});
