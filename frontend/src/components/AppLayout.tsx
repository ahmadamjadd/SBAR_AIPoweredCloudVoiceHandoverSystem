import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, LayoutGrid, Mic, LogOut, Search, Bell } from "lucide-react";
import type { ReactNode } from "react";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/record", label: "New Handover", icon: Mic },
] as const;

export function AppLayout({
  title,
  subtitle,
  children,
  showSearch = true,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  showSearch?: boolean;
}) {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen bg-background">
      <div className="flex min-h-screen w-full">
        {/* Sidebar */}
        <aside className="hidden w-64 shrink-0 flex-col border-r border-border/60 bg-surface/60 px-5 py-6 md:flex">
          <div className="flex items-center gap-3 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-soft">
              <Activity className="h-5 w-5" strokeWidth={2.25} />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">SBAR Voice</div>
              <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Handover System
              </div>
            </div>
          </div>

          <div className="mt-10 px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Navigation
          </div>
          <nav className="mt-3 flex flex-col gap-1">
            {nav.map((item) => {
              const active = item.to === "/" ? path === "/" : path.startsWith(item.to);
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={
                    "group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-all " +
                    (active
                      ? "bg-primary text-primary-foreground shadow-soft"
                      : "text-foreground/70 hover:bg-surface-muted hover:text-foreground")
                  }
                >
                  <Icon className="h-[18px] w-[18px]" strokeWidth={2} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto flex items-center gap-3 rounded-2xl bg-card p-3 shadow-soft">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent font-semibold">
              DR
            </div>
            <div className="min-w-0 flex-1 leading-tight">
              <div className="truncate text-sm font-semibold">Dr. House Officer</div>
              <div className="truncate text-xs text-muted-foreground">Medicine Ward</div>
            </div>
            <button
              className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 px-6 py-6 pb-24 md:px-10 md:py-10 md:pb-10">
          <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
              {subtitle && (
                <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              {showSearch && (
                <div className="relative w-full sm:w-72">
                  <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="search"
                    placeholder="Search handovers…"
                    className="h-11 w-full rounded-full border border-border bg-card pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/10"
                  />
                </div>
              )}
              <button
                aria-label="Notifications"
                className="relative flex h-11 w-11 items-center justify-center rounded-full border border-border bg-card text-foreground/70 transition-colors hover:text-foreground hover:shadow-soft"
              >
                <Bell className="h-[18px] w-[18px]" />
                <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-destructive" />
              </button>
            </div>
          </header>

          <div className="mt-8 animate-fade-in">{children}</div>
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-border bg-background/80 px-2 py-3 backdrop-blur-md md:hidden">
        {nav.map((item) => {
          const active = item.to === "/" ? path === "/" : path.startsWith(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center gap-1 rounded-xl px-4 py-1 transition-colors ${
                active ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-5 w-5" strokeWidth={active ? 2.5 : 2} />
              <span className="text-[10px] font-semibold">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
