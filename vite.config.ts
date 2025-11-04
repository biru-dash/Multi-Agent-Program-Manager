import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    watch: {
      // Exclude directories that shouldn't trigger reloads
      ignored: [
        '**/node_modules/**',
        '**/backend/**',
        '**/venv/**',
        '**/.git/**',
        '**/dist/**',
        '**/build/**',
        '**/*.py',
        '**/__pycache__/**',
        '**/models_cache/**',
        '**/uploads/**',
        '**/outputs/**',
      ],
    },
    // Improve HMR performance
    hmr: {
      overlay: true,
    },
  },
  // Optimize dependency pre-bundling
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
    ],
    exclude: ['@lovable/tagger'],
  },
  // Exclude from build and dev processing
  publicDir: 'public',
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Improve build performance
  build: {
    target: 'esnext',
    sourcemap: false, // Disable sourcemaps in dev for faster rebuilds
  },
}));
