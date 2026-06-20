import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Wallet,
  Receipt,
  Sparkles,
  Target,
  Users,
  Bell,
  Search,
  Settings,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/budget", label: "AI Advisor", icon: Sparkles },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/groups", label: "Group Budget", icon: Users },
  { to: "/wallet", label: "Wallet", icon: Wallet },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(true);
  const [menu, setMenu] = useState(false);
  const { location } = useRouterState();
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    if (!loading && !user) navigate({ to: "/auth" });
  }, [loading, user, navigate]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-background grid place-items-center text-muted-foreground text-sm">
        Loading…
      </div>
    );
  }

  const initial = user.name?.[0]?.toUpperCase() ?? "U";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        <aside className="hidden lg:flex fixed inset-y-0 left-0 w-[260px] flex-col border-r border-border bg-sidebar px-5 py-6">
          <Link to="/" className="flex items-center gap-2 px-2 mb-8">
            <div className="h-9 w-9 rounded-xl bg-primary grid place-items-center text-primary-foreground font-bold">M</div>
            <div className="leading-tight">
              <div className="font-semibold tracking-tight">MyBudget</div>
              <div className="text-[11px] text-muted-foreground">Student Finance OS</div>
            </div>
          </Link>

          <nav className="flex-1 space-y-1">
            {navItems.map((item) => {
              const active = location.pathname === item.to;
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                    active ? "bg-sidebar-active text-primary font-medium" : "text-sidebar-foreground hover:bg-surface-hover hover:text-foreground"
                  }`}
                >
                  <Icon className="h-[18px] w-[18px]" strokeWidth={active ? 2.25 : 1.75} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-6 rounded-2xl border border-border p-4 bg-gradient-to-br from-accent to-transparent">
            <div className="flex items-center gap-2 text-xs font-medium text-primary mb-1">
              <Sparkles className="h-3.5 w-3.5" /> AI Pro
            </div>
            <p className="text-xs text-muted-foreground mb-3">Unlock deeper forecasts & weekly coach reports.</p>
            <button className="w-full rounded-lg bg-primary text-primary-foreground text-xs font-medium py-2 hover:bg-primary-hover transition">Upgrade</button>
          </div>

          <Link to="/settings" className="mt-4 flex items-center gap-3 px-3 py-2 text-sm text-sidebar-foreground hover:text-foreground">
            <Settings className="h-[18px] w-[18px]" strokeWidth={1.75} /> Settings
          </Link>
        </aside>

        <main className="flex-1 lg:ml-[260px] min-h-screen">
          <header className="sticky top-0 z-30 glass border-b border-border">
            <div className="flex items-center gap-4 px-6 lg:px-10 h-16">
              <div className="flex-1 max-w-md relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
                <input
                  placeholder="Search transactions, goals, friends…"
                  className="w-full h-10 rounded-xl bg-surface border border-border pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary transition"
                />
              </div>
              <button
                onClick={() => setDark((d) => !d)}
                className="h-10 w-10 grid place-items-center rounded-xl bg-surface border border-border hover:bg-surface-hover transition"
                aria-label="Toggle theme"
              >
                {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              <button className="relative h-10 w-10 grid place-items-center rounded-xl bg-surface border border-border hover:bg-surface-hover transition">
                <Bell className="h-4 w-4" />
                <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary" />
              </button>
              <div className="relative">
                <button onClick={() => setMenu((v) => !v)} className="flex items-center gap-3 pl-3 border-l border-border">
                  <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary to-primary-hover grid place-items-center text-primary-foreground text-sm font-semibold">{initial}</div>
                  <div className="hidden sm:block leading-tight text-left">
                    <div className="text-sm font-medium">{user.name}</div>
                    <div className="text-[11px] text-muted-foreground">Premium</div>
                  </div>
                </button>
                {menu && (
                  <div className="absolute right-0 top-12 w-52 rounded-xl border border-border bg-background shadow-lg overflow-hidden">
                    <Link to="/settings" onClick={() => setMenu(false)} className="flex items-center gap-2 px-4 py-3 text-sm hover:bg-surface-hover">
                      <Settings className="h-4 w-4" /> Settings
                    </Link>
                    <button onClick={() => { setMenu(false); logout(); navigate({ to: "/auth" }); }} className="w-full flex items-center gap-2 px-4 py-3 text-sm hover:bg-surface-hover text-destructive">
                      <LogOut className="h-4 w-4" /> Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          <div className="px-6 lg:px-10 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
