/**
 * ESLINT CONFIGURATION (eslint.config.mjs)
 * Configures Next.js Core Web Vitals and TypeScript linting rules with global ignore patterns.
 */

// --- SECTION 1: Module Imports & Core Rule Sets ---
// Imports ESLint defineConfig utility and Next.js recommended web-vitals / typescript configs.
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// --- SECTION 2: Config Definition & Global Ignores ---
// Combines linting rulesets and defines build folder exclusions (.next, out, build).
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;

