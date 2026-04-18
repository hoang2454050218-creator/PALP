"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import { getStoredUser, setStoredUser, clearStoredUser } from "@/lib/auth";
import type { User, ConsentStatus } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  consentPending: boolean;
  consentLastCheckedAt: number;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  checkConsent: (force?: boolean) => Promise<void>;
  dismissConsentModal: () => void;
  initialize: () => void;
}

const CONSENT_CACHE_MS = 5 * 60 * 1000;

async function refreshConsent(set: (state: Partial<AuthState>) => void) {
  try {
    const statuses = await api.get<ConsentStatus[]>("/privacy/consent/");
    const list = Array.isArray(statuses) ? statuses : (statuses as any).results ?? [];
    const allGranted = list.length > 0 && list.every((s: ConsentStatus) => s.granted);
    set({ consentPending: !allGranted, consentLastCheckedAt: Date.now() });
  } catch {
    set({ consentPending: true, consentLastCheckedAt: Date.now() });
  }
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: true,
  consentPending: false,
  consentLastCheckedAt: 0,

  initialize: () => {
    const stored = getStoredUser();
    set({ user: stored, loading: false });
  },

  login: async (username: string, password: string) => {
    await api.login(username, password);
    const user = await api.get<User>("/auth/profile/");
    setStoredUser(user);
    set({ user, consentLastCheckedAt: 0 });
    if (user.role === "student") {
      await refreshConsent(set);
    }
  },

  logout: async () => {
    await api.logout();
    clearStoredUser();
    set({ user: null, consentPending: false, consentLastCheckedAt: 0 });
  },

  // Re-check is rate-limited: subsequent calls within 5 minutes hit cache
  // unless ``force=true``. Prevents the consent dialog from flashing on
  // every client-side navigation while still surfacing fresh decisions
  // shortly after the user updates them on the privacy page.
  checkConsent: async (force = false) => {
    const last = get().consentLastCheckedAt;
    if (!force && last && Date.now() - last < CONSENT_CACHE_MS) {
      return;
    }
    await refreshConsent(set);
  },

  dismissConsentModal: () => {
    set({ consentPending: false, consentLastCheckedAt: Date.now() });
  },

  fetchProfile: async () => {
    try {
      const user = await api.get<User>("/auth/profile/");
      setStoredUser(user);
      set({ user, loading: false });
    } catch {
      clearStoredUser();
      set({ user: null, loading: false });
    }
  },
}));
