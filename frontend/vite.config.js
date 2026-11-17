import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // The app uses its own CSS and does not contain Tailwind directives. Avoid
  // loading Tailwind's native Oxide binary during local Vite startup/builds.
  plugins: [react()],
})
