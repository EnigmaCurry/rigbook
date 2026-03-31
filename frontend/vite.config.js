import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte({
    compilerOptions: {
      customElement: false,
    },
    onwarn(warning, handler) {
      if (warning.code === "custom-element" || (warning.message && warning.message.includes("hex-color-picker"))) return;
      handler(warning);
    },
  })],
  build: {
    outDir: "../src/rigbook/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8073",
    },
  },
});
