---
name: frontend-component
description: Build accessible, themed React components using Radix UI primitives + class-variance-authority + Tailwind. Use when creating any new component under frontend/src/components/.
---

# Frontend Component — Radix + cva + Tailwind Pattern

## When to use

- Creating a new component in `frontend/src/components/ui/` (primitives) or `frontend/src/components/<feature>/` (composites)
- Wrapping a Radix UI primitive with project-specific variants
- Adding a new variant (size, color, intent) to an existing component

## Stack contract

- **Functional component only**, no class components
- **Radix UI** for behavior (focus management, ARIA, portals)
- **`class-variance-authority` (cva)** for variant -> className mapping
- **`clsx` + `tailwind-merge`** via `cn()` helper for className composition
- **TypeScript strict** — no `any`, props typed via `React.ComponentPropsWithoutRef<typeof RadixPrimitive>`
- **Forward refs** for any component a parent might attach a ref to

## Canonical primitive template

`frontend/src/components/ui/button.tsx`:

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
export { buttonVariants };
```

## Composite (feature) component template

`frontend/src/components/dashboard/MasteryCard.tsx`:

```tsx
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

interface MasteryCardProps {
  conceptName: string;
  mastery: number;
  className?: string;
}

export function MasteryCard({ conceptName, mastery, className }: MasteryCardProps) {
  const percent = Math.round(mastery * 100);
  return (
    <Card className={cn("p-4", className)}>
      <h3 className="text-sm font-medium">{conceptName}</h3>
      <p className="text-2xl font-bold tabular-nums">{percent}%</p>
    </Card>
  );
}
```

## Hard rules

- **No inline styles** (`style={{...}}`) unless dynamic value can't be Tailwind (rare).
- **No custom CSS files** — use Tailwind utilities + `tailwindcss-animate`.
- **No `getByTestId`** in tests — use `getByRole`, `getByText`, `getByLabelText` (a11y-first).
- **Keyboard accessible** — every interactive element reachable by Tab, action by Enter/Space.
- **Loading + empty + error + success** states for any data-driven component (D7 in DoD).
- **Use existing `cn()` helper** from `frontend/src/lib/utils.ts` — never re-implement clsx/tailwind-merge composition.

## A11y checklist (per component)

- [ ] Semantic HTML (`button`, not `div onClick`)
- [ ] Visible focus ring (`focus-visible:ring-2`)
- [ ] Color contrast >= AA (4.5:1 for body text, 3:1 for large/UI)
- [ ] No information conveyed by color alone (icon + label, not just red)
- [ ] If interactive, has accessible name (`aria-label` or visible text)
- [ ] Form inputs paired with `<label htmlFor>` or `aria-labelledby`
- [ ] Dialog/popover uses Radix primitive (focus trap + portal handled)
- [ ] Animations respect `prefers-reduced-motion` (use `tailwindcss-animate`'s `motion-safe:` modifier)

## Tests

Co-locate `<Component>.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./button";

describe("Button", () => {
  it("renders default variant", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button", { name: "Click" })).toBeInTheDocument();
  });

  it("calls onClick when activated", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("respects disabled", () => {
    render(<Button disabled>Save</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

## Common pitfalls

- Forgetting `displayName` on `forwardRef` -> ugly DevTools display.
- Using `cn(...)` but passing the result to `style` prop instead of `className`.
- Hardcoding colors (`bg-blue-500`) instead of theme tokens (`bg-primary`).
- Building variants with conditional `className` strings instead of `cva` -> hard to test, no autocomplete.
