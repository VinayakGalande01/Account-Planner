// Skeleton primitive: pulsing placeholder block used while content loads
// (widgets, tables, cards). Renders a single styled div and forwards props.
//
// --- SECTION: Types/Imports ---
// Uses cn() for class merging; accepts standard div attributes.
//
// --- SECTION: Component ---
// Skeleton renders the animated placeholder div below.
import { cn } from "@/lib/utils"

// --- SECTION: Component ---
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-secondary/50", className)}
      {...props}
    />
  )
}

export { Skeleton }
