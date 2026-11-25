import { useEffect } from "react";
import { Outlet } from "react-router";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ModeBanner } from "@/components/layout/ModeBanner";
import { NavBar } from "@/components/layout/NavBar";
import { SummaryBar } from "@/components/layout/SummaryBar";
import { AlertStack } from "@/features/alerts/AlertStack";
import { cn } from "@/lib/cn";
import { useLiveConnection } from "@/lib/useLiveConnection";
import { usePrefs } from "@/stores/prefs";

export function AppShell() {
  useLiveConnection();
  const { theme, presenter, togglePresenter } = usePrefs();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
      if (!typing && e.key.toLowerCase() === "p" && !e.metaKey && !e.ctrlKey) togglePresenter();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [togglePresenter]);

  return (
    <div className={cn("flex h-full flex-col", presenter && "presenter")}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-2">Skip to content</a>
      <NavBar />
      <ModeBanner />
      <SummaryBar />
      <main id="main" className="min-h-0 flex-1">
        <Outlet />
      </main>
      <Disclaimer />
      <AlertStack />
    </div>
  );
}
