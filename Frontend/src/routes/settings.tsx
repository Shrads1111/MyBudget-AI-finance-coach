import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { LogOut, User as UserIcon, Bell, Shield, Palette } from "lucide-react";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings · MyBudget" }] }),
  component: () => (
    <AppShell>
      <SettingsPage />
    </AppShell>
  ),
});

function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notif, setNotif] = useState(true);
  const [weekly, setWeekly] = useState(true);
  const [aiTips, setAiTips] = useState(true);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your profile, preferences, and security.</p>
      </div>

      <Section icon={<UserIcon className="h-4 w-4" />} title="Profile">
        <Row label="Name" value={user?.name ?? "—"} />
        <Row label="Email" value={user?.email ?? "—"} />
        <Row label="Plan" value="Premium (Trial)" />
      </Section>

      <Section icon={<Bell className="h-4 w-4" />} title="Notifications">
        <Toggle label="Push notifications" value={notif} onChange={setNotif} />
        <Toggle label="Weekly AI coach report" value={weekly} onChange={setWeekly} />
        <Toggle label="Smart spending tips" value={aiTips} onChange={setAiTips} />
      </Section>

      <Section icon={<Palette className="h-4 w-4" />} title="Appearance">
        <Row label="Theme" value="System (toggle from top bar)" />
        <Row label="Currency" value="INR ₹" />
      </Section>

      <Section icon={<Shield className="h-4 w-4" />} title="Security">
        <Row label="Two-factor auth" value="Not enabled" />
        <Row label="Active sessions" value="1 device" />
      </Section>

      <button
        onClick={() => { logout(); navigate({ to: "/auth" }); }}
        className="h-11 px-5 rounded-xl border border-destructive/40 text-destructive hover:bg-destructive/10 text-sm font-medium inline-flex items-center gap-2"
      >
        <LogOut className="h-4 w-4" /> Sign out
      </button>
    </div>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-surface">
      <div className="p-5 border-b border-border flex items-center gap-2">
        <span className="text-primary">{icon}</span>
        <div className="font-semibold text-sm">{title}</div>
      </div>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center px-5 py-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex justify-between items-center px-5 py-4 text-sm">
      <span>{label}</span>
      <button
        onClick={() => onChange(!value)}
        className={`relative h-6 w-11 rounded-full transition ${value ? "bg-primary" : "bg-border"}`}
      >
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${value ? "left-[22px]" : "left-0.5"}`} />
      </button>
    </div>
  );
}
