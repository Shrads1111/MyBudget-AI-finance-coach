import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { Dashboard } from "@/components/dashboard/Dashboard";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard · MyBudget" },
      { name: "description", content: "Your AI-powered financial dashboard — balance, spending, savings goals, and insights at a glance." },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
