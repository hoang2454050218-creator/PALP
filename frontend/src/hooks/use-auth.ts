"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import { getStoredUser, setStoredUser, clearStoredUser } from "@/lib/auth";
import type { User, ConsentStatus } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  consentPending: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  checkConsent: () => Promise<void>;
  dismissConsentModal: () => void;
  initialize: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  consentPending: false,

  initialize: () => {
    const stored = getStoredUser();
    set({ user: stored, loading: false });
  },

  login: async (username: string, password: string) => {
    await api.login(username, password);
    const user = await api.get<User>("/auth/profile/");
    setStoredUser(user);
    set({ user });

    if (user.role === "student") {
      try {
        const statuses = await api.get<ConsentStatus[]>("/privacy/consent/");
        const list = Array.isArray(statuses) ? statuses : (statuses as any).results ?? [];
        const allGranted = list.length > 0 && list.every((s: ConsentStatus) => s.granted);
        set({ consentPending: !allGranted });
      } catch {
        set({ consentPending: true });
      }
    }
  },

  logout: async () => {
    await api.logout();
    clearStoredUser();
    set({ user: null, consentPending: false });
  },

  checkConsent: async () => {
    try {
      const statuses = await api.get<ConsentStatus[]>("/privacy/consent/");
      const list = Array.isArray(statuses) ? statuses : (statuses as any).results ?? [];
      const allGranted = list.length > 0 && list.every((s: ConsentStatus) => s.granted);
      set({ consentPending: !allGranted });
    } catch {
      set({ consentPending: false });
    }
  },

  dismissConsentModal: () => {
    set({ consentPending: false });
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
