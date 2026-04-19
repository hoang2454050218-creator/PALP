# Frontend Standards

Applies to: `frontend/**/*.{ts,tsx}`

## Stack

- Next.js 14 with App Router (`src/app/`)
- TypeScript 5.5 strict mode
- Tailwind CSS 3.4 + `tailwindcss-animate`
- Radix UI primitives for accessible components
- `class-variance-authority` (cva) for variant-based styling
- `clsx` + `tailwind-merge` for className composition
- Zustand for global state
- Recharts for data visualization
- Lucide React for icons

## Route Structure

```
src/app/
  (auth)/login/        Public login page
  (student)/...        Student-only routes
  (lecturer)/...       Lecturer-only routes
  layout.tsx           Root layout
  page.tsx             Home/landing
```

Route groups `(auth)`, `(student)`, `(lecturer)` separate concerns without affecting URL paths.

## Components

- Functional components only, no class components
- Extract reusable logic into custom hooks (`src/hooks/`)
- Use Radix UI primitives, wrap with cva for project-specific variants
- Compose classNames with `cn()` helper (clsx + tailwind-merge)

```tsx
import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border p-4", className)} {...props} />;
}
```

## State Management

- **Local state**: `useState`, `useReducer` for component-scoped state
- **Global state**: Zustand stores in `src/stores/`
- **Server state**: fetch in Server Components or use `fetch` with Next.js caching

## API Communication

- API calls proxy through Next.js rewrites: `/api/*` -> backend
- Base URL from `NEXT_PUBLIC_API_URL` env var
- JWT tokens managed via httpOnly cookies (set by backend)
- Handle 401 (redirect to login), 403 (show forbidden), network errors gracefully

## Styling

- Tailwind utility-first, avoid custom CSS files
- Use `tailwindcss-animate` for transitions
- Responsive: mobile-first breakpoints (`sm:`, `md:`, `lg:`)
- Dark mode support via Tailwind `dark:` variant if needed

## TypeScript

- Strict mode, no `any` types
- Define API response types matching backend serializers
- Use `interface` for object shapes, `type` for unions/intersections
- Export types from colocated `types.ts` files

## Testing

- Unit: Vitest + Testing Library (`*.test.ts(x)`)
- E2E: Playwright (`e2e/` directory)
- Mock API with MSW (Mock Service Worker)
- Test user interactions, not implementation details

## Security Headers

Already configured in `next.config.js`: CSP, X-Frame-Options DENY, HSTS, nosniff, XSS protection, strict referrer policy.
