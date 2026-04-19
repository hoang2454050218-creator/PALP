"use client";

import { useCallback, useEffect, useState } from "react";
import { Users2 } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { displayName } from "@/lib/utils";

import { BenchmarkPanel } from "@/components/peer/benchmark-panel";
import { BuddyPanel } from "@/components/peer/buddy-panel";
import { FrontierPanel } from "@/components/peer/frontier-panel";
import type {
  BenchmarkResult,
  BuddyMineResult,
  FrontierSnapshot,
  PeerConsentPayload,
  PeerMatch,
} from "@/components/peer/types";

const PEER_DISCLAIMER =
  "Trang này không có bảng xếp hạng, không có điểm thưởng, không hiện tên ai khi so sánh — theo nguyên tắc Self-Determination Theory và Marsh 1987 BFLPE để tránh việc bạn bị 'đè bẹp' bởi peer comparison ngược.";

export default function PeerPage() {
  const { user } = useAuth();
  const [consent, setConsent] = useState<PeerConsentPayload | null>(null);
  const [frontier, setFrontier] = useState<FrontierSnapshot | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [matches, setMatches] = useState<PeerMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadCore = useCallback(async () => {
    const [c, f] = await Promise.all([
      api.get<PeerConsentPayload>("/peer/consent/"),
      api.get<FrontierSnapshot>("/peer/frontier/"),
    ]);
    setConsent(c);
    setFrontier(f);
    return c;
  }, []);

  const loadBenchmark = useCallback(async (granted: boolean) => {
    if (!granted) {
      setBenchmark(null);
      return;
    }
    try {
      const b = await api.get<BenchmarkResult>("/peer/benchmark/");
      setBenchmark(b);
    } catch {
      setBenchmark({ available: false, reason: "" });
    }
  }, []);

  const loadBuddy = useCallback(async (granted: boolean) => {
    if (!granted) {
      setMatches([]);
      return;
    }
    try {
      const data = await api.get<BuddyMineResult>("/peer/buddy/me/");
      setMatches(data.matches);
    } catch {
      setMatches([]);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const c = await loadCore();
      await Promise.all([
        loadBenchmark(c.peer_comparison),
        loadBuddy(c.peer_teaching),
      ]);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [loadCore, loadBenchmark, loadBuddy]);

  useEffect(() => {
    if (user?.role === "student") {
      load();
    }
  }, [user?.role, load]);

  const greeting = user ? `Mạng lưới của ${displayName(user)}` : "Mạng lưới";
  const description =
    "Bạn so với chính bạn · Cohort cùng năng lực · Buddy dạy nhau";

  if (user && user.role !== "student") {
    return null;
  }

  if (error) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <ErrorState
          title="Không tải được dữ liệu peer"
          message="Hãy thử tải lại sau ít phút."
          onRetry={load}
        />
      </div>
    );
  }

  if (loading || !user || !consent) {
    return (
      <div>
        <PageHeader title={greeting} description={description} />
        <div className="grid gap-6 lg:grid-cols-3">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  async function patchConsent(payload: Partial<PeerConsentPayload>) {
    try {
      const updated = await api.patch<PeerConsentPayload>(
        "/peer/consent/",
        payload,
      );
      setConsent(updated);
      return updated;
    } catch {
      return null;
    }
  }

  async function handleToggleComparison(next: boolean) {
    const updated = await patchConsent({ peer_comparison: next });
    if (updated) {
      await loadBenchmark(updated.peer_comparison);
    }
  }

  async function handleToggleTeaching(next: boolean) {
    const updated = await patchConsent({ peer_teaching: next });
    if (updated) {
      await loadBuddy(updated.peer_teaching);
    }
  }

  async function handleFindMatch() {
    try {
      await api.post<{ match: PeerMatch | null }>("/peer/buddy/find/", {});
      const next = await api.get<BuddyMineResult>("/peer/buddy/me/");
      setMatches(next.matches);
    } catch {
      // surface as error in next loadBuddy
    }
  }

  async function handleRespond(
    matchId: number,
    action: "accept" | "decline" | "archive",
  ) {
    try {
      await api.post(`/peer/buddy/${matchId}/respond/`, { action });
      await loadBuddy(true);
    } catch {
      // ignore
    }
  }

  return (
    <div>
      <PageHeader title={greeting} description={description}>
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"
          aria-hidden="true"
        >
          <Users2 className="h-5 w-5" />
        </span>
      </PageHeader>

      <section
        aria-label="Ba góc peer: Frontier, Benchmark, Buddy"
        className="grid gap-6 lg:grid-cols-3 items-start"
      >
        <FrontierPanel data={frontier} loading={loading} />
        <BenchmarkPanel
          consent={consent}
          benchmark={benchmark}
          loading={loading}
          onToggleConsent={handleToggleComparison}
        />
        <BuddyPanel
          consent={consent}
          matches={matches}
          loading={loading}
          onToggleConsent={handleToggleTeaching}
          onFindMatch={handleFindMatch}
          onRespond={handleRespond}
        />
      </section>

      <footer className="mt-10 border-t pt-6">
        <p className="text-xs text-muted-foreground text-center max-w-2xl mx-auto leading-relaxed">
          {PEER_DISCLAIMER}
        </p>
      </footer>
    </div>
  );
}
