import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      aria-hidden="true"
      {...props}
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6" aria-hidden="true">
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-11 w-11 rounded-lg" />
      </div>
    </div>
  );
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-lg border bg-card" aria-hidden="true">
      <div className="p-6 space-y-2">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-3 w-56" />
      </div>
      <div className="px-6 pb-6 space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </div>
    </div>
  );
}

export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 py-3 px-4" aria-hidden="true">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-4", i === 0 ? "w-32" : i === cols - 1 ? "w-16" : "flex-1")}
        />
      ))}
    </div>
  );
}

export function AlertCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6" aria-hidden="true">
      <div className="flex items-start gap-4">
        <Skeleton className="h-3 w-3 rounded-full mt-1 shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-8 w-20 rounded-md" />
            <Skeleton className="h-8 w-20 rounded-md" />
            <Skeleton className="h-8 w-20 rounded-md" />
          </div>
        </div>
        <Skeleton className="h-3 w-24 shrink-0" />
      </div>
    </div>
  );
}
