/**
 * POSTCSS CONFIGURATION (postcss.config.mjs)
 * PostCSS plugin processing setup integrating TailwindCSS PostCSS plugin engine.
 */

// --- SECTION 1: Plugin Configuration ---
// Configures @tailwindcss/postcss plugin for stylesheet processing.
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

// --- SECTION 2: Config Export ---
// Exports the PostCSS configuration object for Next.js build pipeline.
export default config;

