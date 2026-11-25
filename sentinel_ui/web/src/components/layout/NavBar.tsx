import { Activity, BarChart3, Flag, Moon, MonitorPlay, Radio, Shield, Sun, Wind } from "lucide-react";
import { NavLink } from "react-router";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";
import { usePrefs } from "@/stores/prefs";
import { useLive } from "@/stores/live";

function Tab({ to, icon, children, badge }: { to: string; icon: React.ReactNode; children: string; badge?: number }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "relative inline-flex h-9 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-muted hover:bg-surface-2 hover:text-text [&_svg]:size-4",
          isActive && "bg-surface-2 text-text",
        )
      }
    >
      {icon}
      {children}
      {badge !== undefined && badge > 0 && (
        <span
          className="ml-0.5 rounded-full bg-flagged px-1.5 py-px text-[11px] font-semibold text-white tabular-nums"
          aria-label={`${badge} open flagged items`}
        >
          {badge}
        </span>
      )}
    </NavLink>
  );
}

export function NavBar() {
  const openFlags = useLive((s) => Object.values(s.cases).filter((c) => c.status === "new" || c.status === "awaiting_analyst").length);
  const working = useLive((s) => s.counters?.under_review ?? 0);
  const connection = useLive((s) => s.connection);
  const { theme, toggleTheme, reducedMotion, setReducedMotion, presenter, togglePresenter } = usePrefs();

  return (
    <header className="flex h-12 items-center gap-2 border-b border-border bg-surface px-3">
      <div className="mr-3 flex items-center gap-2">
        <Shield className="size-5 text-accent" aria-hidden />
        <span className="font-semibold tracking-tight">Sentinel</span>
        <span className="hidden text-xs text-muted sm:inline">AML analyst workspace</span>
      </div>
      <nav className="flex items-center gap-1" aria-label="Main">
        <Tab to="/stream" icon={<Radio />}>Live Stream</Tab>
        <Tab to="/queue" icon={<Flag />} badge={openFlags}>Flagged</Tab>
        <Tab to="/results" icon={<BarChart3 />}>Results</Tab>
      </nav>
      <div className="ml-auto flex items-center gap-1">
        {working > 0 && (
          <span className="mr-2 inline-flex items-center gap-1 text-xs text-review">
            <Activity className="size-3.5 animate-pulse" aria-hidden /> {working} under review
          </span>
        )}
        <span
          className={cn("mr-1 size-2 rounded-full", connection === "open" ? "bg-cleared" : connection === "lost" ? "bg-flagged" : "bg-review")}
          role="status"
          aria-label={`Connection ${connection}`}
          title={`Connection ${connection}`}
        />
        <Tooltip content={reducedMotion ? "Motion off" : "Motion on"}>
          <button className="rounded-md p-2 text-muted hover:bg-surface-2" onClick={() => setReducedMotion(!reducedMotion)} aria-pressed={!reducedMotion} aria-label="Toggle motion">
            <Wind className={cn("size-4", reducedMotion && "opacity-40")} />
          </button>
        </Tooltip>
        <Tooltip content="Presenter mode (P)">
          <button className="rounded-md p-2 text-muted hover:bg-surface-2" onClick={togglePresenter} aria-pressed={presenter} aria-label="Presenter mode">
            <MonitorPlay className={cn("size-4", presenter && "text-accent")} />
          </button>
        </Tooltip>
        <Tooltip content={theme === "dark" ? "Light theme" : "Dark theme"}>
          <button className="rounded-md p-2 text-muted hover:bg-surface-2" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </Tooltip>
      </div>
    </header>
  );
}
