import type { Role } from "@/types/api";

/** Node colours by role. Separate from the status colours, which keep their own meaning (EX-9). */
export const ROLE_FILL: Record<Role, string> = {
  hub: "oklch(0.55 0.2 275)",
  subject: "oklch(0.55 0.2 275)",
  mule: "oklch(0.62 0.13 225)",
  source: "oklch(0.65 0.05 250)",
  sink: "oklch(0.45 0.05 250)",
  other: "oklch(0.7 0.01 260)",
};
