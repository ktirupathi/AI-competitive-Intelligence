"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "scoutai_onboarding_completed";

/**
 * Hook to detect first-time users and track onboarding completion.
 *
 * Checks `localStorage` for a completion flag. Returns `showOnboarding`
 * which is `true` on the user's first visit, and a `completeOnboarding`
 * callback that persists the flag.
 */
export function useOnboarding() {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Only run in browser
    if (typeof window === "undefined") return;
    const completed = localStorage.getItem(STORAGE_KEY);
    if (!completed) {
      setShowOnboarding(true);
    }
  }, []);

  const completeOnboarding = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    setShowOnboarding(false);
  }, []);

  return { showOnboarding, completeOnboarding };
}
