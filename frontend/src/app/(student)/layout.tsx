"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shared/sidebar";
import { MobileHeader } from "@/components/shared/mobile-header";
import { ConsentModal } from "@/components/privacy/consent-modal";
import { useAuth } from "@/hooks/use-auth";
import { isAuthenticated } from "@/lib/auth";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, initialize, loading, consentPending, checkConsent, dismissConsentModal } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!loading && !isAuthenticated()) {
      router.replace("/login");
    }
  }, [loading, router]);

  useEffect(() => {
    if (user?.role === "student" && !loading) {
      checkConsent();
    }
  }, [user, loading, checkConsent]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center" role="status" aria-label="Đang tải">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground animate-pulse">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <MobileHeader onMenuToggle={() => setMobileMenuOpen(true)} />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto bg-muted/30 p-4 lg:p-8"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
      {consentPending && (
        <ConsentModal onComplete={dismissConsentModal} />
      )}
    </div>
  );
}
