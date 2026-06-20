import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Send, Sparkles, Plus, X, AlertCircle } from "lucide-react";

export const Route = createFileRoute("/budget")({
  head: () => ({ meta: [{ title: "AI Advisor · MyBudget" }] }),
  component: () => (
    <AppShell>
      <BudgetPage />
    </AppShell>
  ),
});

const starterPrompts = [
  "How can I save ₹3,000 more this month?",
  "Where am I overspending?",
  "Build me a weekly budget for ₹2,500",
  "Should I cancel any subscriptions?",
];

type BudgetLimit = {
  budget_id: string;
  category: string;
  limit: number;
  spent: number;
  remaining: number;
  month: string;
};

type AIInsight = {
  tag: string;
  text: string;
};

function BudgetPage() {
  const { token } = useAuth();
  
  // Data States
  const [budgets, setBudgets] = useState<BudgetLimit[]>([]);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Chatbot State
  const [messages, setMessages] = useState<{ role: "ai" | "you"; text: string }[]>([
    { role: "ai", text: "Hey! I'm your Agentic AI Financial Advisor. Ask me anything about your pocket money, campus splits, or category budget caps." },
  ]);
  const [input, setInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  
  // Add budget state
  const [open, setOpen] = useState(false);

  // Fetch budgets and insights (Health Recommendations)
  const fetchData = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      const [bRes, healthRes] = await Promise.all([
        api.get("/api/budgets"),
        api.get("/api/health-score")
      ]);
      setBudgets(bRes || []);
      
      // Convert health score recommendations into AI Insights cards
      const recs = healthRes.recommendations || [];
      const tagList = ["Savings", "Budget", "Goals", "Stability", "Consistency"];
      const formattedInsights = recs.map((r: string, idx: number) => ({
        tag: tagList[idx % tagList.length],
        text: r
      }));
      setInsights(formattedInsights);
    } catch (e: any) {
      setErr(e.message || "Failed to load budget summaries.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const send = async (text: string) => {
    if (!text.trim() || chatBusy) return;
    
    // Add user message
    setMessages((m) => [...m, { role: "you", text }]);
    setInput("");
    setChatBusy(true);

    try {
      // Call orchestrated chat endpoint
      const res = await api.post("/api/ai/chat", { query: text });
      setMessages((m) => [...m, { role: "ai", text: res.response }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "ai", text: "Sorry, I couldn't reach the agent orchestrator. Please verify your connection: " + e.message }
      ]);
    } finally {
      setChatBusy(false);
    }
  };

  // Add Budget
  const handleAddBudget = async (payload: { category: string; limit: number; month: string }) => {
    try {
      await api.post("/api/budgets", payload);
      setOpen(false);
      fetchData();
    } catch (e: any) {
      alert("Failed to save budget: " + e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-medium text-primary mb-2">
            <Sparkles className="h-4 w-4" /> AI Financial Coach
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Your personal money advisor</h1>
          <p className="text-sm text-muted-foreground">Ask anything. Get tailored advice based on your real transactions.</p>
        </div>
        
        <button onClick={() => setOpen(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-medium inline-flex items-center gap-2">
          <Plus className="h-4 w-4" /> Set budget limit
        </button>
      </div>

      {err && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>{err}</span>
        </div>
      )}

      <div className="grid lg:grid-cols-[1fr_360px] gap-6">
        {/* Chat Window */}
        <div className="rounded-2xl border border-border bg-surface flex flex-col h-[640px]">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "you" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${m.role === "you" ? "bg-primary text-primary-foreground" : "bg-background border border-border"}`}>
                  {m.text}
                </div>
              </div>
            ))}
            {chatBusy && (
              <div className="flex justify-start">
                <div className="max-w-[78%] rounded-2xl px-4 py-3 text-sm bg-background border border-border flex items-center gap-2">
                  <div className="animate-pulse h-1.5 w-1.5 rounded-full bg-primary"></div>
                  <div className="animate-pulse h-1.5 w-1.5 rounded-full bg-primary delay-75"></div>
                  <div className="animate-pulse h-1.5 w-1.5 rounded-full bg-primary delay-150"></div>
                  <span className="text-xs text-muted-foreground ml-1">Orchestrator thinking...</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="border-t border-border p-4 space-y-3">
            <div className="flex gap-2 flex-wrap">
              {starterPrompts.map((p) => (
                <button key={p} onClick={() => send(p)} disabled={chatBusy} className="text-xs px-3 py-1.5 rounded-full border border-border bg-background hover:bg-surface-hover disabled:opacity-50">
                  {p}
                </button>
              ))}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)} disabled={chatBusy} placeholder="Ask your AI advisor…" className="flex-1 h-11 rounded-xl bg-background border border-border px-4 text-sm focus:outline-none focus:border-primary text-foreground disabled:opacity-50" />
              <button disabled={chatBusy || !input.trim()} className="h-11 px-4 rounded-xl bg-primary text-primary-foreground inline-flex items-center gap-2 font-medium hover:bg-primary-hover disabled:opacity-50">
                <Send className="h-4 w-4" /> Send
              </button>
            </form>
          </div>
        </div>

        {/* Sidebar budgets & insights */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="text-sm font-semibold mb-3">Budgets this month</div>
            
            {loading ? (
              <p className="text-xs text-muted-foreground">Syncing limits...</p>
            ) : (
              <div className="space-y-3">
                {budgets.map((b) => {
                  const limitVal = parseFloat(b.limit as any) || 0;
                  const spentVal = parseFloat(b.spent as any) || 0;
                  const pct = Math.min(100, limitVal > 0 ? (spentVal / limitVal) * 100 : 0);
                  const over = pct >= 100;
                  const warning = pct >= 80 && pct < 100;
                  
                  return (
                    <div key={b.budget_id}>
                      <div className="flex justify-between text-xs mb-1">
                        <span>{b.category}</span>
                        <span className="text-muted-foreground">₹{spentVal} / ₹{limitVal}</span>
                      </div>
                      <div className="h-2 rounded-full bg-background overflow-hidden">
                        <div 
                          className={`h-full ${over ? "bg-rose-500" : warning ? "bg-amber-500" : "bg-primary"}`} 
                          style={{ width: `${pct}%` }} 
                        />
                      </div>
                    </div>
                  );
                })}
                {budgets.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">No budget limits set.</p>
                )}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="text-sm font-semibold mb-3">AI Insights</div>
            
            {loading ? (
              <p className="text-xs text-muted-foreground">Syncing score recommendations...</p>
            ) : (
              <div className="space-y-3 max-h-[300px] overflow-y-auto">
                {insights.map((i, idx) => (
                  <div key={idx} className="rounded-xl border border-border p-3 bg-background">
                    <div className="text-[10px] uppercase tracking-wider text-primary font-semibold mb-1">{i.tag}</div>
                    <div className="text-xs text-foreground leading-relaxed">{i.text}</div>
                  </div>
                ))}
                {insights.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">Track expenses to get AI advices.</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {open && <AddBudgetDialog onClose={() => setOpen(false)} onAdd={handleAddBudget} />}
    </div>
  );
}

function AddBudgetDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (b: { category: string; limit: number; month: string }) => void }) {
  const [category, setCategory] = useState("Food");
  const [limit, setLimit] = useState("");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7)); // Format: YYYY-MM

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({ category, limit: Number(limit), month });
  };

  const categories = ["Food", "Transport", "Subscriptions", "Entertainment", "Education", "Bills", "Other"];

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Configure budget limit</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <div>
          <div className="text-xs text-muted-foreground mb-1">Category</div>
          <select 
            value={category} 
            onChange={(e) => setCategory(e.target.value)} 
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
          >
            {categories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Limit (₹)</div>
          <input value={limit} onChange={(e) => setLimit(e.target.value)} type="number" required className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Month</div>
          <input value={month} onChange={(e) => setMonth(e.target.value)} type="month" required className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Save</button>
      </form>
    </div>
  );
}
