/**
 * ACCESSIBILITY FOCUS TRAP HOOK (src/lib/useFocusTrap.ts)
 * Traps Keyboard Tab focus within active modal/dialog overlays and restores focus
 * to triggering elements upon Escape key dismissals.
 */

// --- SECTION 1: Dependencies & Hook Options Schema ---
// Imports React effect and ref hooks and defines focus trap configuration options.
import { useEffect, useRef } from 'react'

interface UseFocusTrapOptions {
  isOpen: boolean
  onClose?: () => void
}

// --- SECTION 2: Focus Trap Hook Implementation ---
// Queries focusable DOM nodes, traps Tab/Shift-Tab navigation, and listens for Escape key presses.
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>({
  isOpen,
  onClose,
}: UseFocusTrapOptions) {
  const ref = useRef<T>(null)
  const previousActiveElement = useRef<Element | null>(null)

  useEffect(() => {
    if (!isOpen) return

    previousActiveElement.current = document.activeElement

    const container = ref.current
    if (!container) return

    const getFocusableElements = () => {
      return Array.from(
        container.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter(
        (el) =>
          !el.hasAttribute('disabled') &&
          el.getAttribute('aria-hidden') !== 'true' &&
          el.offsetWidth > 0 &&
          el.offsetHeight > 0
      )
    }

    // Move focus to first focusable element or the container itself
    const focusableElements = getFocusableElements()
    if (focusableElements.length > 0) {
      focusableElements[0].focus()
    } else {
      container.focus()
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) {
        e.preventDefault()
        e.stopPropagation()
        onClose()
        return
      }

      if (e.key === 'Tab') {
        const elements = getFocusableElements()
        if (elements.length === 0) {
          e.preventDefault()
          return
        }

        const firstElement = elements[0]
        const lastElement = elements[elements.length - 1]

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault()
            lastElement.focus()
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault()
            firstElement.focus()
          }
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown, true)

    return () => {
      window.removeEventListener('keydown', handleKeyDown, true)
      if (
        previousActiveElement.current &&
        'focus' in previousActiveElement.current &&
        typeof (previousActiveElement.current as HTMLElement).focus === 'function'
      ) {
        ;(previousActiveElement.current as HTMLElement).focus()
      }
    }
  }, [isOpen, onClose])

  return ref
}
