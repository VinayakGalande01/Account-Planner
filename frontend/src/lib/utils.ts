/**
 * CLASSNAME MERGE UTILITY (src/lib/utils.ts)
 * Merges conditional CSS class names using clsx and resolves Tailwind CSS class conflicts using tailwind-merge.
 */

// --- SECTION 1: Dependencies & Imports ---
// Imports clsx class formatting types and tailwind-merge conflict resolution engines.
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// --- SECTION 2: Class Value Merger (cn) ---
// Merges input ClassValue arguments into clean, conflict-free HTML className strings.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

