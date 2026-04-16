"use client";

import { Menu, GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MobileHeaderProps {
  onMenuToggle: () => void;
}

export function MobileHeader({ onMenuToggle }: MobileHeaderProps) {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b bg-card px-4 lg:hidden">
      <Button
        variant="ghost"
        size="sm"
        onClick={onMenuToggle}
        aria-label="Mở menu điều hướng"
        className="p-2"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </Button>
      <div className="flex items-center gap-2">
        <GraduationCap className="h-6 w-6 text-primary" aria-hidden="true" />
        <span className="text-base font-bold text-primary">PALP</span>
      </div>
    </header>
  );
}
