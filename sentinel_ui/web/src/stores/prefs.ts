import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Per-viewer conveniences, remembered in this browser only. */
interface Prefs {
  theme: "light" | "dark";
  reducedMotion: boolean;
  presenter: boolean;
  autoplayReplay: boolean;
  edgeLabels: boolean;
  openedCases: Record<string, number>;
  toggleTheme: () => void;
  setReducedMotion: (v: boolean) => void;
  togglePresenter: () => void;
  setAutoplayReplay: (v: boolean) => void;
  setEdgeLabels: (v: boolean) => void;
  markOpened: (caseId: string, seq: number) => void;
}

const prefersDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
const prefersReduced =
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export const usePrefs = create<Prefs>()(
  persist(
    (set) => ({
      theme: prefersDark ? "dark" : "light",
      reducedMotion: Boolean(prefersReduced),
      presenter: false,
      autoplayReplay: true,
      edgeLabels: true,
      openedCases: {},
      toggleTheme: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
      setReducedMotion: (reducedMotion) => set({ reducedMotion }),
      togglePresenter: () => set((s) => ({ presenter: !s.presenter })),
      setAutoplayReplay: (autoplayReplay) => set({ autoplayReplay }),
      setEdgeLabels: (edgeLabels) => set({ edgeLabels }),
      markOpened: (caseId, seq) => set((s) => ({ openedCases: { ...s.openedCases, [caseId]: seq } })),
    }),
    { name: "sentinel-prefs", partialize: ({ openedCases: _omit, ...rest }) => rest },
  ),
);
