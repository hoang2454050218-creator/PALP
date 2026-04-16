import { StatCardSkeleton, CardSkeleton } from "@/components/ui/skeleton";

export default function LecturerLoading() {
  return (
    <div className="p-4 lg:p-8" aria-busy="true" aria-label="Đang tải trang">
      <div className="space-y-2 mb-8">
        <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
        <div className="h-4 w-64 animate-pulse rounded-md bg-muted" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <CardSkeleton lines={5} />
        <CardSkeleton lines={4} />
      </div>
    </div>
  );
}
