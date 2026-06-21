import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useMemo } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isIncome } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight, Filter, Mic, Plus, Search, Trash2, X, AlertCircle, FileText, Upload, AlertTriangle, Loader2, Calendar as CalendarIcon } from "lucide-react";
import { getAuth } from "firebase/auth";
import { VoiceMicButton } from "@/components/VoiceTransaction";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";

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
  const [importOpen, setImportOpen] = useState(false);

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
        (selectedCategory === "income" && isIncome(t.category)) ||
        (selectedCategory === "expense" && !isIncome(t.category)) ||
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
      if (isIncome(t.category)) {
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

  // Add transaction (manual)
  const handleAdd = async (payload: { amount: number; category: string; description: string; date: string }) => {
    try {
      await api.post("/api/expenses", payload);
      setOpen(false);
      fetchExpenses();
    } catch (e: any) {
      alert("Failed to save transaction: " + e.message);
    }
  };

  // Add transaction (voice) — same API, no dialog to close
  const handleVoiceAdd = async (payloads: Array<{ amount: number; category: string; description: string; date: string }>) => {
    await Promise.all(payloads.map(payload => api.post("/api/expenses", payload)));
    fetchExpenses();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
          <p className="text-sm text-muted-foreground">Track income, stipends, and expenses completely on Firestore.</p>
        </div>
        <div className="flex gap-2">
          <VoiceMicButton onConfirm={handleVoiceAdd} />
          <button onClick={() => setImportOpen(true)} className="h-10 px-4 rounded-xl border border-border bg-surface text-muted-foreground hover:text-foreground hover:bg-surface-hover text-sm font-medium inline-flex items-center gap-2">
            <FileText className="h-4 w-4" /> Import PDF Statement
          </button>
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
                  <div className={`h-10 w-10 rounded-xl grid place-items-center ${isIncome(t.category) ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>
                    {isIncome(t.category) ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{t.description || t.category}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.category} · {t.date}
                    </div>
                  </div>
                  <div className={`text-sm font-semibold ${isIncome(t.category) ? "text-emerald-500" : "text-foreground"}`}>
                    {isIncome(t.category) ? "+" : "-"}₹{parseFloat(t.amount as any).toLocaleString()}
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
      {importOpen && <ImportDialog onClose={() => setImportOpen(false)} onImportComplete={() => { setImportOpen(false); fetchExpenses(); }} />}
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
  const [customCategoryName, setCustomCategoryName] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [categories, setCategories] = useState<string[]>([]);
  const [loadingCats, setLoadingCats] = useState(true);
  const [saving, setSaving] = useState(false);

  // Fetch categories (default + user custom) from backend on dialog open
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setLoadingCats(true);
        const res = await api.get("/api/categories");
        // res is a plain array of strings
        const list: string[] = Array.isArray(res) ? res : [];
        setCategories(list);
        // Set default selection to first non-Other item
        if (list.length > 0) {
          setCategory(list[0]);
        }
      } catch {
        // Fallback to hardcoded defaults if API fails
        const defaults = ["Food", "Transport", "Subscriptions", "Entertainment", "Education", "Bills", "Income", "Other"];
        setCategories(defaults);
      } finally {
        setLoadingCats(false);
      }
    };
    fetchCategories();
  }, []);

  const isCustom = category === "Other";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      let finalCategory = category;

      // If user chose "Other" and typed a custom name, save it first
      if (isCustom && customCategoryName.trim()) {
        finalCategory = customCategoryName.trim();
        try {
          await api.post("/api/categories", { name: finalCategory });
        } catch {
          // Non-fatal — category save failure doesn't block transaction
        }
      }

      onAdd({ description: title, amount: Number(amount), category: finalCategory, date });
    } finally {
      setSaving(false);
    }
  };

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
          {loadingCats ? (
            <div className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm flex items-center text-muted-foreground">
              Loading categories...
            </div>
          ) : (
            <select 
              value={category} 
              onChange={(e) => { setCategory(e.target.value); setCustomCategoryName(""); }} 
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
            >
              {categories.map(c => (
                <option key={c} value={c}>{c === "Other" ? "Other (Custom)" : c}</option>
              ))}
            </select>
          )}
        </div>

        {/* Custom category input — shown only when "Other" is selected */}
        {isCustom && (
          <div>
            <div className="text-xs text-muted-foreground mb-1">Custom Category Name</div>
            <input
              value={customCategoryName}
              onChange={(e) => setCustomCategoryName(e.target.value)}
              placeholder="e.g. Gym, Pets, Medicine, Books…"
              required
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              This category will be saved and available in future transactions.
            </p>
          </div>
        )}

        <div>
          <div className="text-xs text-muted-foreground mb-1">Date</div>
          <Popover>
            <PopoverTrigger asChild>
              <button
                type="button"
                className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground flex items-center justify-between text-left cursor-pointer"
              >
                <span className="truncate">
                  {date 
                    ? new Date(date + "T00:00:00").toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) 
                    : "Pick a date"}
                </span>
                <CalendarIcon className="h-4 w-4 text-muted-foreground shrink-0" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={date ? new Date(date + "T00:00:00") : undefined}
                onSelect={(selectedDate) => {
                  if (selectedDate) {
                    const year = selectedDate.getFullYear();
                    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
                    const day = String(selectedDate.getDate()).padStart(2, '0');
                    setDate(`${year}-${month}-${day}`);
                  }
                }}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>
        
        <button 
          type="submit" 
          disabled={saving || (isCustom && !customCategoryName.trim())}
          className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover disabled:opacity-60 transition"
        >
          {saving ? "Saving…" : "Save"}
        </button>
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

type ParsedTx = {
  date: string;
  description: string;
  amount: number;
  type: "expense" | "income";
  category: string;
  is_possible_duplicate?: boolean;
  selected?: boolean;
};

function ImportDialog({ onClose, onImportComplete }: { onClose: () => void; onImportComplete: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"upload" | "progress" | "review">("upload");
  const [progressStep, setProgressStep] = useState<number>(1);
  const [progressMsg, setProgressMsg] = useState<string>("");
  const [parsedList, setParsedList] = useState<ParsedTx[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 20 * 1024 * 1024) {
        setErrorMsg("File size exceeds 20 MB limit");
        return;
      }
      setFile(selected);
      setErrorMsg(null);
    }
  };

  const uploadAndAnalyze = async () => {
    if (!file) return;
    setStep("progress");
    setProgressStep(1);
    setProgressMsg("Uploading PDF statement...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      // Simulate a small transition to Step 2
      const step2Timeout = setTimeout(() => {
        setProgressStep(2);
        setProgressMsg("Extracting PDF text content...");
      }, 1000);

      // Simulate a small transition to Step 3
      const step3Timeout = setTimeout(() => {
        setProgressStep(3);
        setProgressMsg("Analyzing transactions with AI...");
      }, 2500);

      const auth = getAuth();
      const user = auth.currentUser;
      const headers: HeadersInit = {};
      if (user) {
        const token = await user.getIdToken();
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const response = await fetch("http://localhost:5000/api/transactions/import-pdf", {
        method: "POST",
        headers,
        body: formData
      });

      clearTimeout(step2Timeout);
      clearTimeout(step3Timeout);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Upload failed with status ${response.status}`);
      }

      const res = await response.json();
      const txs: ParsedTx[] = (res.transactions || []).map((t: any) => ({
        ...t,
        selected: true // default to import
      }));

      if (txs.length === 0) {
        setStep("upload");
        setErrorMsg("No transactions found.");
      } else {
        setParsedList(txs);
        setProgressStep(4);
        setProgressMsg("Reviewing Transactions...");
        setTimeout(() => {
          setStep("review");
        }, 500);
      }
    } catch (e: any) {
      setStep("upload");
      setErrorMsg(e.message || "Unable to extract transaction data from this PDF.");
    }
  };

  const handleUpdateField = (index: number, field: keyof ParsedTx, value: any) => {
    setParsedList(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      
      // Keep category in sync when type is updated
      if (field === "type") {
        copy[index].category = value === "income" ? "Salary" : "Food";
      }
      return copy;
    });
  };

  const handleRemoveRow = (index: number) => {
    setParsedList(prev => prev.filter((_, i) => i !== index));
  };

  const handleImportSubmit = async () => {
    const toImport = parsedList.filter(t => t.selected);
    if (toImport.length === 0) {
      alert("Please select at least one transaction to import.");
      return;
    }

    setImporting(true);
    try {
      for (const t of toImport) {
        let finalCategory = t.category;
        let finalDescription = t.description;

        if (t.type === "income") {
          finalCategory = "Income";
          // Prepend subcategory to description
          finalDescription = `${t.category}: ${t.description}`;
        }

        await api.post("/api/expenses", {
          amount: t.amount,
          category: finalCategory,
          description: finalDescription,
          date: t.date
        });
      }
      onImportComplete();
    } catch (e: any) {
      alert("Error importing transactions: " + e.message);
    } finally {
      setImporting(false);
    }
  };

  const expenseCategories = ["Food", "Travel", "Shopping", "Bills", "Health", "Entertainment", "Education", "Investment", "Others"];
  const incomeCategories = ["Salary", "Freelancing", "Refund", "Interest", "Bonus", "Other Income"];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm grid place-items-center p-4">
      <div className="w-full max-w-4xl max-h-[90vh] rounded-2xl border border-border bg-background flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2 text-foreground">
              <FileText className="h-5 w-5 text-primary" /> Import PDF Statement
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">Upload a bank statement, credit card statement or report to auto-extract transactions.</p>
          </div>
          <button type="button" onClick={onClose} disabled={importing} className="p-1.5 rounded-lg hover:bg-surface text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 min-h-[300px] flex flex-col justify-center">
          
          {step === "upload" && (
            <div className="space-y-4 max-w-lg mx-auto w-full">
              {errorMsg && (
                <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="border-2 border-dashed border-border rounded-2xl p-8 text-center hover:border-primary transition cursor-pointer bg-surface/50 group relative">
                <input 
                  type="file" 
                  accept=".pdf" 
                  onChange={handleFileChange}
                  className="absolute inset-0 opacity-0 cursor-pointer" 
                />
                <Upload className="h-10 w-10 text-muted-foreground group-hover:text-primary mx-auto transition-transform group-hover:-translate-y-1" />
                <div className="mt-4 text-sm font-medium text-foreground">
                  {file ? file.name : "Select or drag statement PDF"}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  PDF up to 20 MB. Digital &amp; scanned formats supported.
                </div>
              </div>

              {file && (
                <button
                  onClick={uploadAndAnalyze}
                  className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover transition shadow-lg shadow-primary/20"
                >
                  Analyze Statement
                </button>
              )}
            </div>
          )}

          {step === "progress" && (
            <div className="max-w-md mx-auto w-full space-y-6 py-6">
              <div className="text-center space-y-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
                <div className="text-sm font-medium text-foreground">{progressMsg}</div>
              </div>

              {/* Progress Timeline */}
              <div className="space-y-4 border-l-2 border-border ml-4 pl-6 relative">
                {[
                  { num: 1, label: "Uploading PDF" },
                  { num: 2, label: "Extracting Text" },
                  { num: 3, label: "AI Analysis" },
                  { num: 4, label: "Review Transactions" }
                ].map((s) => {
                  const isActive = progressStep === s.num;
                  const isDone = progressStep > s.num;
                  return (
                    <div key={s.num} className="relative">
                      {/* Node Bullet */}
                      <div className={`absolute -left-[35px] top-0.5 h-4 w-4 rounded-full border-2 flex items-center justify-center transition-colors
                        ${isDone ? "bg-primary border-primary text-primary-foreground" : isActive ? "bg-background border-primary" : "bg-background border-border"}`}
                      >
                        {isDone && <div className="h-1.5 w-1.5 rounded-full bg-background" />}
                        {isActive && <div className="h-1.5 w-1.5 rounded-full bg-primary animate-ping" />}
                      </div>
                      
                      <div className={`text-xs font-semibold ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
                        Step {s.num}: {s.label}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {step === "review" && (
            <div className="space-y-4 h-full flex flex-col justify-start">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>Extracted {parsedList.length} transactions from PDF</span>
                <span className="font-semibold text-primary">Uncheck rows you want to skip</span>
              </div>

              <div className="overflow-x-auto border border-border rounded-xl">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="bg-surface border-b border-border text-muted-foreground font-semibold">
                      <th className="p-3 w-10 text-center">Import</th>
                      <th className="p-3 w-36">Date</th>
                      <th className="p-3">Description</th>
                      <th className="p-3 w-28">Amount (₹)</th>
                      <th className="p-3 w-28">Type</th>
                      <th className="p-3 w-36">Category</th>
                      <th className="p-3 w-10">Remove</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {parsedList.map((tx, idx) => (
                      <tr key={idx} className={`hover:bg-surface-hover/30 transition-colors ${tx.is_possible_duplicate ? "bg-warning/5" : ""}`}>
                        {/* Checkbox */}
                        <td className="p-3 text-center">
                          <input 
                            type="checkbox"
                            checked={tx.selected}
                            onChange={(e) => handleUpdateField(idx, "selected", e.target.checked)}
                            className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                          />
                        </td>
                        
                        {/* Date */}
                        <td className="p-2">
                          <input 
                            type="date"
                            value={tx.date}
                            onChange={(e) => handleUpdateField(idx, "date", e.target.value)}
                            className="w-full h-8 rounded-lg bg-surface border border-border px-2 text-xs focus:outline-none focus:border-primary text-foreground"
                          />
                        </td>

                        {/* Description */}
                        <td className="p-2">
                          <div className="space-y-1">
                            <input 
                              type="text"
                              value={tx.description}
                              onChange={(e) => handleUpdateField(idx, "description", e.target.value)}
                              className="w-full h-8 rounded-lg bg-surface border border-border px-2 text-xs focus:outline-none focus:border-primary text-foreground"
                            />
                            {tx.is_possible_duplicate && (
                              <div className="text-[10px] text-amber-500 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                                Possible duplicate transaction detected.
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Amount */}
                        <td className="p-2">
                          <input 
                            type="number"
                            value={tx.amount}
                            min="0.01"
                            step="0.01"
                            onChange={(e) => handleUpdateField(idx, "amount", parseFloat(e.target.value) || 0)}
                            className="w-full h-8 rounded-lg bg-surface border border-border px-2 text-xs focus:outline-none focus:border-primary text-foreground font-medium"
                          />
                        </td>

                        {/* Type */}
                        <td className="p-2">
                          <select 
                            value={tx.type}
                            onChange={(e) => handleUpdateField(idx, "type", e.target.value)}
                            className="w-full h-8 rounded-lg bg-surface border border-border px-1 text-xs focus:outline-none focus:border-primary text-foreground"
                          >
                            <option value="expense">Expense</option>
                            <option value="income">Income</option>
                          </select>
                        </td>

                        {/* Category */}
                        <td className="p-2">
                          <select 
                            value={tx.category}
                            onChange={(e) => handleUpdateField(idx, "category", e.target.value)}
                            className="w-full h-8 rounded-lg bg-surface border border-border px-1 text-xs focus:outline-none focus:border-primary text-foreground"
                          >
                            {tx.type === "income" 
                              ? incomeCategories.map(c => <option key={c} value={c}>{c}</option>)
                              : expenseCategories.map(c => <option key={c} value={c}>{c}</option>)
                            }
                          </select>
                        </td>

                        {/* Delete Row Button */}
                        <td className="p-2 text-center">
                          <button
                            type="button"
                            onClick={() => handleRemoveRow(idx)}
                            className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-surface"
                            aria-label="Remove row"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        {step === "review" && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface">
            <button 
              type="button" 
              onClick={onClose}
              disabled={importing}
              className="px-4 h-10 rounded-xl border border-border hover:bg-surface text-sm font-medium transition"
            >
              Cancel
            </button>
            <button 
              type="button" 
              onClick={handleImportSubmit}
              disabled={importing || parsedList.filter(t => t.selected).length === 0}
              className="px-6 h-10 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover transition flex items-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-60"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Importing…
                </>
              ) : (
                <>
                  Import {parsedList.filter(t => t.selected).length} Transactions
                </>
              )}
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
