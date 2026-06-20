import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useMemo } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ArrowDownRight, ArrowUpRight, Filter, Mic, Plus, Search, Trash2, X, AlertCircle } from "lucide-react";

export const Route = createFileRoute("/transactions")({
  head: () => ({ meta: [{ title: "Transactions · MyBudget" }] }),
  component: () => (
    <AppShell>
      <TransactionsPage />
    </AppShell>
  ),
});

type ExpenseItem = {
  expense_id: string;
  amount: number;
  category: string;
  description: string;
  date: string;
};

function TransactionsPage() {
  const { token } = useAuth();
  
  // Data State
  const [items, setItems] = useState<ExpenseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  
  // Filters & Search
  const [q, setQ] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedMonth, setSelectedMonth] = useState<string>(""); // Format: YYYY-MM
  const [selectedYear, setSelectedYear] = useState<string>(""); // Format: YYYY
  
  const [sortField, setSortField] = useState<string>("date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  
  const [open, setOpen] = useState(false);

  // Fetch expenses from backend
  const fetchExpenses = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      
      // Build query string params
      const params = new URLSearchParams();
      // Fetch maximum items for in-app client filter and aggregation
      params.append("limit", "1000");
      params.append("sort_by", sortField);
      params.append("sort_order", sortOrder);
      
      const res = await api.get(`/api/expenses?${params.toString()}`);
      setItems(res.expenses || []);
    } catch (e: any) {
      setErr(e.message || "Failed to load transactions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExpenses();
  }, [token, sortField, sortOrder]);

  // Client-side filtering & searching for smooth user experience
  const filtered = useMemo(() => {
    return items.filter((t) => {
      const matchesSearch =
        q === "" ||
        t.description.toLowerCase().includes(q.toLowerCase()) ||
        t.category.toLowerCase().includes(q.toLowerCase());
        
      const matchesCategory =
        selectedCategory === "all" ||
        (selectedCategory === "income" && t.category === "Income") ||
        (selectedCategory === "expense" && t.category !== "Income") ||
        t.category.toLowerCase() === selectedCategory.toLowerCase();

      const matchesMonth = selectedMonth === "" || t.date.startsWith(selectedMonth);
      const matchesYear = selectedYear === "" || t.date.startsWith(selectedYear);

      return matchesSearch && matchesCategory && matchesMonth && matchesYear;
    });
  }, [items, q, selectedCategory, selectedMonth, selectedYear]);

  // Tally Calculations
  const totals = useMemo(() => {
    let income = 0;
    let expense = 0;
    filtered.forEach((t) => {
      const amt = parseFloat(t.amount as any) || 0;
      if (t.category === "Income") {
        income += amt;
      } else {
        expense += amt;
      }
    });
    return { income, expense, net: income - expense };
  }, [filtered]);

  // Delete transaction
  const handleRemove = async (expenseId: string) => {
    if (!confirm("Are you sure you want to delete this transaction?")) return;
    try {
      await api.delete(`/api/expenses/${expenseId}`);
      // Refresh list
      fetchExpenses();
    } catch (e: any) {
      alert("Failed to delete transaction: " + e.message);
    }
  };

  // Add transaction
  const handleAdd = async (payload: { amount: number; category: string; description: string; date: string }) => {
    try {
      await api.post("/api/expenses", payload);
      setOpen(false);
      fetchExpenses();
    } catch (e: any) {
      alert("Failed to save transaction: " + e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
          <p className="text-sm text-muted-foreground">Track income, stipends, and expenses completely on Firestore.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setOpen(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-medium inline-flex items-center gap-2">
            <Plus className="h-4 w-4" /> Add transaction
          </button>
        </div>
      </div>

      {err && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">
          Syncing transaction records...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Stat label="Income" value={`₹${totals.income.toLocaleString()}`} up />
            <Stat label="Expense" value={`₹${totals.expense.toLocaleString()}`} />
            <Stat label="Net Balance" value={`₹${totals.net.toLocaleString()}`} up={totals.net >= 0} />
          </div>

          <div className="rounded-2xl border border-border bg-surface">
            {/* Filter controls */}
            <div className="flex items-center gap-3 p-4 border-b border-border flex-wrap">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search description or category…" className="w-full h-10 rounded-xl bg-background border border-border pl-9 pr-3 text-sm focus:outline-none focus:border-primary" />
              </div>
              
              <div className="flex gap-1 rounded-xl bg-background border border-border p-1">
                {[
                  { key: "all", label: "All" },
                  { key: "income", label: "Income" },
                  { key: "expense", label: "Expenses" }
                ].map((k) => (
                  <button key={k.key} onClick={() => setSelectedCategory(k.key)} className={`px-3 h-8 rounded-lg text-xs font-medium capitalize ${selectedCategory === k.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                    {k.label}
                  </button>
                ))}
              </div>

              {/* Month filter input */}
              <input 
                type="month" 
                value={selectedMonth} 
                onChange={(e) => setSelectedMonth(e.target.value)} 
                className="h-10 px-3 rounded-xl border border-border bg-background text-sm text-foreground focus:outline-none" 
              />
              
              {selectedMonth && (
                <button onClick={() => setSelectedMonth("")} className="text-xs text-primary hover:underline">Clear month</button>
              )}

              {/* Sorting triggers */}
              <button 
                onClick={() => {
                  setSortOrder(sortOrder === "asc" ? "desc" : "asc");
                }} 
                className="h-10 px-3 rounded-xl border border-border bg-background hover:bg-surface-hover text-sm inline-flex items-center gap-1.5"
              >
                Sort: {sortField} ({sortOrder})
              </button>
            </div>

            <div className="divide-y divide-border">
              {filtered.map((t) => (
                <div key={t.expense_id} className="flex items-center gap-4 px-4 py-3 hover:bg-surface-hover">
                  <div className={`h-10 w-10 rounded-xl grid place-items-center ${t.category === "Income" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>
                    {t.category === "Income" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{t.description || t.category}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.category} · {t.date}
                    </div>
                  </div>
                  <div className={`text-sm font-semibold ${t.category === "Income" ? "text-emerald-500" : "text-foreground"}`}>
                    {t.category === "Income" ? "+" : "-"}₹{parseFloat(t.amount as any).toLocaleString()}
                  </div>
                  <button onClick={() => handleRemove(t.expense_id)} className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-surface" aria-label="Delete">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {filtered.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No transaction records match filters.</div>}
            </div>
          </div>
        </>
      )}

      {open && <AddDialog onClose={() => setOpen(false)} onAdd={handleAdd} />}
    </div>
  );
}

function Stat({ label, value, up }: { label: string; value: string; up?: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${up === undefined ? "" : up ? "text-emerald-500" : "text-rose-500"}`}>{value}</div>
    </div>
  );
}

function AddDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (t: { amount: number; category: string; description: string; date: string }) => void }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Food");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({ description: title, amount: Number(amount), category, date });
  };

  const categories = ["Food", "Transport", "Subscriptions", "Entertainment", "Education", "Bills", "Income", "Other"];

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Add transaction</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <Input label="Description" value={title} onChange={setTitle} required />
        <Input label="Amount (₹)" value={amount} onChange={setAmount} type="number" required />
        
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

        <Input label="Date" value={date} onChange={setDate} type="date" required />
        
        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Save</button>
      </form>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", required }: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  return (
    <label className="block">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <input value={value} onChange={(e) => onChange(e.target.value)} type={type} required={required} className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
    </label>
  );
}
