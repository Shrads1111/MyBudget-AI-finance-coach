import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useMemo } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { 
  CreditCard, 
  Plus, 
  Wallet as WalletIcon, 
  Banknote, 
  Smartphone, 
  AlertCircle, 
  Trash2, 
  X,
  Search,
  Filter,
  Calendar,
  TrendingUp,
  CheckCircle,
  Edit
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isIncome } from "@/lib/utils";

export const Route = createFileRoute("/wallet")({
  head: () => ({ meta: [{ title: "Wallet · MyBudget" }] }),
  component: () => (
    <AppShell>
      <WalletPage />
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

type AccountItem = {
  account_id: string;
  name: string;
  type: string;
  initial_balance: number;
  last_details: string;
};

type RecurringItem = {
  recurring_id: string;
  title: string;
  amount: number;
  category: string;
  frequency: string;
  start_date: string;
  next_due_date: string;
  notes?: string;
};

function WalletPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<ExpenseItem[]>([]);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [recurringPayments, setRecurringPayments] = useState<RecurringItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  
  // Dialog state
  const [open, setOpen] = useState(false); // Link Account dialog
  const [recOpen, setRecOpen] = useState(false); // Add/Edit Recurring Dialog
  const [editingPayment, setEditingPayment] = useState<RecurringItem | null>(null); // Recurring item currently edited

  // Search/Filters/Sort state
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("All");
  const [filterFrequency, setFilterFrequency] = useState("All");
  const [sortBy, setSortBy] = useState<"date-asc" | "date-desc">("date-asc");

  const fetchWalletData = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      const [expRes, accRes, recRes] = await Promise.all([
        api.get("/api/expenses?limit=1000"),
        api.get("/api/accounts"),
        api.get("/api/recurring")
      ]);
      setItems(expRes.expenses || []);
      setAccounts(accRes || []);
      setRecurringPayments(recRes || []);
    } catch (e: any) {
      setErr(e.message || "Failed to load wallet metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWalletData();
  }, [token]);

  // Dynamically calculate account balances based on transactions and auto-routing weight
  const accountsData = useMemo(() => {
    // Clone accounts list to track balances locally
    const calculated = accounts.map(acc => ({
      ...acc,
      balance: parseFloat(acc.initial_balance as any) || 0
    }));

    if (calculated.length === 0) return [];

    items.forEach((item) => {
      const amt = parseFloat(item.amount as any) || 0;
      const desc = (item.description || "").toLowerCase();
      const cat = (item.category || "").toLowerCase();
      const accountId = (item as any).account_id;

      let bestAccIndex = -1;

      if (accountId) {
        bestAccIndex = calculated.findIndex((acc) => acc.account_id === accountId);
      } else {
        // Auto-route transaction to the most appropriate account
        let bestWeight = 0;

        // Classify payment method tags
        const isPaytm = desc.includes("paytm") || desc.includes("wallet") || desc.includes("recharge") || desc.includes("swiggy") || desc.includes("zomato") || desc.includes("uber") || desc.includes("ola");
        const isCard = desc.includes("card") || desc.includes("student") || desc.includes("amazon") || desc.includes("flipkart") || desc.includes("netflix") || desc.includes("spotify") || desc.includes("gym") || cat.includes("subscriptions") || cat.includes("entertainment");

        calculated.forEach((acc, index) => {
          const accName = acc.name.toLowerCase();
          const accType = acc.type.toLowerCase();
          let weight = 0;

          // Name match gives highest priority
          if (desc.includes(accName) || accName.includes(desc)) {
            weight += 10;
          }
          
          // Match name keywords
          const keywords = accName.split(/\s+/);
          keywords.forEach(kw => {
            if (kw.length > 2 && desc.includes(kw)) {
              weight += 5;
            }
          });

          // Match type indicators
          if (accType === "wallet" && isPaytm) weight += 1;
          if (accType === "card" && isCard) weight += 1;

          if (weight > bestWeight) {
            bestWeight = weight;
            bestAccIndex = index;
          }
        });
      }

      // Apply amount to the resolved best match account
      if (bestAccIndex !== -1) {
        if (isIncome(item.category)) {
          calculated[bestAccIndex].balance += amt;
        } else {
          calculated[bestAccIndex].balance -= amt;
        }
      }
    });

    return calculated.map(acc => {
      // Pick dynamic icon based on account type
      let icon = WalletIcon;
      if (acc.type === "Bank") icon = Banknote;
      else if (acc.type === "Wallet") icon = Smartphone;
      else if (acc.type === "Card") icon = CreditCard;

      return {
        ...acc,
        icon
      };
    });
  }, [items, accounts]);

  const total = useMemo(() => {
    return accountsData.reduce((s, a) => s + a.balance, 0);
  }, [accountsData]);

  // Dynamically compute monthly recurring commitment summary totals
  const recurringTotals = useMemo(() => {
    let totalSIP = 0;
    let totalSub = 0;
    let totalBill = 0;
    let totalAll = 0;

    recurringPayments.forEach((rp) => {
      const amt = parseFloat(rp.amount as any) || 0;
      const freq = (rp.frequency || "Monthly").toLowerCase();
      let monthlyEquiv = amt;

      if (freq === "daily") monthlyEquiv = amt * 30;
      else if (freq === "weekly") monthlyEquiv = amt * 4.33;
      else if (freq === "monthly") monthlyEquiv = amt;
      else if (freq === "quarterly") monthlyEquiv = amt / 3;
      else if (freq === "half-yearly") monthlyEquiv = amt / 6;
      else if (freq === "yearly") monthlyEquiv = amt / 12;

      totalAll += monthlyEquiv;

      const cat = rp.category;
      if (["SIP", "Mutual Fund", "PPF", "RD"].includes(cat)) {
        totalSIP += monthlyEquiv;
      } else if (cat === "Subscription") {
        totalSub += monthlyEquiv;
      } else {
        totalBill += monthlyEquiv;
      }
    });

    return {
      sip: totalSIP,
      subscription: totalSub,
      bill: totalBill,
      total: totalAll
    };
  }, [recurringPayments]);

  // Search/Filters/Sort logic
  const filteredPayments = useMemo(() => {
    let list = [...recurringPayments];

    if (searchTerm.trim() !== "") {
      const term = searchTerm.toLowerCase();
      list = list.filter(
        (rp) =>
          rp.title.toLowerCase().includes(term) ||
          (rp.notes || "").toLowerCase().includes(term) ||
          rp.category.toLowerCase().includes(term)
      );
    }

    if (filterCategory !== "All") {
      list = list.filter((rp) => rp.category === filterCategory);
    }

    if (filterFrequency !== "All") {
      list = list.filter((rp) => rp.frequency === filterFrequency);
    }

    list.sort((a, b) => {
      const dateA = new Date(a.next_due_date).getTime();
      const dateB = new Date(b.next_due_date).getTime();
      return sortBy === "date-asc" ? dateA - dateB : dateB - dateA;
    });

    return list;
  }, [recurringPayments, searchTerm, filterCategory, filterFrequency, sortBy]);

  // Get status badge metadata
  const getStatusBadge = (dueDateStr: string) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const due = new Date(dueDateStr);
    due.setHours(0, 0, 0, 0);

    const diffTime = due.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      return {
        label: "Overdue",
        className: "bg-destructive/10 text-destructive border border-destructive/20"
      };
    } else if (diffDays === 0) {
      return {
        label: "Due Today",
        className: "bg-warning/10 text-warning border border-warning/20"
      };
    } else if (diffDays === 1) {
      return {
        label: "Due Tomorrow",
        className: "bg-primary/10 text-primary border border-primary/20"
      };
    } else {
      return {
        label: "Upcoming",
        className: "bg-success/10 text-success border border-success/20"
      };
    }
  };

  // Handle adding linked account
  const handleAddAccount = async (payload: { name: string; type: string; initial_balance: number; last_details: string }) => {
    try {
      await api.post("/api/accounts", payload);
      setOpen(false);
      fetchWalletData();
    } catch (e: any) {
      alert("Failed to link account: " + e.message);
    }
  };

  // Handle deleting linked account
  const handleDeleteAccount = async (accountId: string) => {
    if (!confirm("Are you sure you want to delete this linked account?")) return;
    try {
      await api.delete(`/api/accounts/${accountId}`);
      fetchWalletData();
    } catch (e: any) {
      alert("Failed to delete account: " + e.message);
    }
  };

  // Handle saving recurring commitment
  const handleSaveRecurring = async (payload: Omit<RecurringItem, "recurring_id"> & { recurring_id?: string }) => {
    try {
      if (payload.recurring_id) {
        await api.put(`/api/recurring/${payload.recurring_id}`, payload);
      } else {
        await api.post("/api/recurring", payload);
      }
      setRecOpen(false);
      setEditingPayment(null);
      fetchWalletData();
    } catch (e: any) {
      alert("Failed to save recurring commitment: " + e.message);
    }
  };

  // Handle deleting recurring commitment
  const handleDeleteRecurring = async (recurringId: string) => {
    if (!confirm("Are you sure you want to delete this recurring commitment?")) return;
    try {
      await api.delete(`/api/recurring/${recurringId}`);
      fetchWalletData();
    } catch (e: any) {
      alert("Failed to delete recurring commitment: " + e.message);
    }
  };

  // Handle marking recurring payment as paid
  const handleMarkAsPaid = async (recurringId: string) => {
    try {
      await api.post(`/api/recurring/${recurringId}/pay`, {});
      fetchWalletData();
    } catch (e: any) {
      alert("Failed to record payment: " + e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Wallet</h1>
          <p className="text-sm text-muted-foreground">All your accounts, cards, and recurring bills in one place.</p>
        </div>
        <button onClick={() => setOpen(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-medium inline-flex items-center gap-2">
          <Plus className="h-4 w-4" /> Link account
        </button>
      </div>

      {err && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">
          Calculating wallet balances...
        </div>
      ) : (
        <>
          <div className="rounded-2xl p-6 bg-gradient-to-br from-primary to-primary-hover text-primary-foreground shadow-lg">
            <div className="flex items-center gap-2 text-xs opacity-80"><WalletIcon className="h-4 w-4" /> Total balance</div>
            <div className="text-4xl font-bold mt-2">₹{total.toLocaleString()}</div>
            <div className="text-xs opacity-80 mt-1">Across {accountsData.length} accounts</div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {accountsData.map((a) => (
              <div key={a.account_id} className="rounded-2xl border border-border bg-surface p-5 hover:border-primary/30 transition-all relative group">
                <button 
                  onClick={() => handleDeleteAccount(a.account_id)}
                  className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-background opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Delete account"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 rounded-xl bg-background border border-border grid place-items-center text-primary">
                    <a.icon className="h-5 w-5" />
                  </div>
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground pr-8">{a.type}</span>
                </div>
                <div className="mt-4 font-semibold text-foreground truncate">{a.name}</div>
                <div className="text-xs text-muted-foreground">{a.last_details}</div>
                <div className="mt-3 text-2xl font-semibold">₹{a.balance.toLocaleString()}</div>
              </div>
            ))}
            {accountsData.length === 0 && (
              <div className="sm:col-span-2 lg:col-span-3 text-center py-8 text-sm text-muted-foreground border border-dashed border-border rounded-2xl">
                No linked accounts. Click 'Link account' to configure your wallets.
              </div>
            )}
          </div>

          {/* Recurring commitments Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">Recurring commitments</h2>
                <p className="text-xs text-muted-foreground">Manage your subscriptions, SIPs, EMIs, and bills</p>
              </div>
              <button 
                onClick={() => {
                  setEditingPayment(null);
                  setRecOpen(true);
                }} 
                className="h-9 px-3 rounded-lg bg-surface border border-border hover:bg-surface-hover text-xs font-medium inline-flex items-center gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" /> Add commitment
              </button>
            </div>

            {/* Commitments Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-2xl border border-border bg-surface p-4">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Total Monthly SIPs</div>
                <div className="text-lg font-bold mt-1">₹{recurringTotals.sip.toLocaleString()}</div>
              </div>
              <div className="rounded-2xl border border-border bg-surface p-4">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Subscriptions</div>
                <div className="text-lg font-bold mt-1">₹{recurringTotals.subscription.toLocaleString()}</div>
              </div>
              <div className="rounded-2xl border border-border bg-surface p-4">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Monthly Bills</div>
                <div className="text-lg font-bold mt-1">₹{recurringTotals.bill.toLocaleString()}</div>
              </div>
              <div className="rounded-2xl border border-border bg-surface p-4 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
                <div className="text-[10px] uppercase tracking-wider text-primary font-medium">Total commitments</div>
                <div className="text-lg font-bold mt-1 text-primary">₹{recurringTotals.total.toLocaleString()}/mo</div>
              </div>
            </div>

            {/* List Controls */}
            <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search commitments..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-xl bg-surface border border-border text-xs focus:outline-none focus:border-primary text-foreground"
                />
              </div>
              <div className="flex gap-2.5 items-center flex-wrap">
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                >
                  <option value="All">All Categories</option>
                  <option value="SIP">SIP</option>
                  <option value="Mutual Fund">Mutual Fund</option>
                  <option value="PPF">PPF</option>
                  <option value="RD">RD</option>
                  <option value="Subscription">Subscription</option>
                  <option value="Rent">Rent</option>
                  <option value="EMI">EMI</option>
                  <option value="Insurance">Insurance</option>
                  <option value="Internet">Internet</option>
                  <option value="Mobile Recharge">Mobile Recharge</option>
                  <option value="Electricity">Electricity</option>
                  <option value="Custom">Custom</option>
                </select>

                <select
                  value={filterFrequency}
                  onChange={(e) => setFilterFrequency(e.target.value)}
                  className="h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                >
                  <option value="All">All Frequencies</option>
                  <option value="Daily">Daily</option>
                  <option value="Weekly">Weekly</option>
                  <option value="Monthly">Monthly</option>
                  <option value="Quarterly">Quarterly</option>
                  <option value="Half-Yearly">Half-Yearly</option>
                  <option value="Yearly">Yearly</option>
                </select>

                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                >
                  <option value="date-asc">Due Date (Soonest)</option>
                  <option value="date-desc">Due Date (Furthest)</option>
                </select>
              </div>
            </div>

            {/* Commitments List */}
            <div className="rounded-2xl border border-border bg-surface overflow-hidden">
              <div className="divide-y divide-border">
                {filteredPayments.map((rp) => {
                  const badge = getStatusBadge(rp.next_due_date);
                  
                  // Pick appropriate icon
                  let CatIcon = Calendar;
                  if (["SIP", "Mutual Fund", "PPF", "RD"].includes(rp.category)) {
                    CatIcon = TrendingUp;
                  } else if (rp.category === "Subscription") {
                    CatIcon = CreditCard;
                  } else if (["Rent", "EMI"].includes(rp.category)) {
                    CatIcon = Banknote;
                  } else if (["Internet", "Mobile Recharge", "Electricity"].includes(rp.category)) {
                    CatIcon = Smartphone;
                  }

                  return (
                    <div key={rp.recurring_id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-surface-hover transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="h-9 w-9 rounded-lg bg-background border border-border grid place-items-center text-primary flex-shrink-0 mt-0.5">
                          <CatIcon className="h-4.5 w-4.5" />
                        </div>
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold">{rp.title}</span>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${badge.className}`}>
                              {badge.label}
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground flex items-center gap-2 flex-wrap">
                            <span>{rp.category}</span>
                            <span>•</span>
                            <span>{rp.frequency}</span>
                            <span>•</span>
                            <span>Next: {new Date(rp.next_due_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
                          </div>
                          {rp.notes && <div className="text-xs text-muted-foreground italic font-light">{rp.notes}</div>}
                        </div>
                      </div>

                      <div className="flex items-center justify-between sm:justify-end gap-4">
                        <div className="text-right flex-shrink-0">
                          <div className="text-base font-bold">₹{rp.amount.toLocaleString()}</div>
                          <div className="text-[10px] text-muted-foreground">started {new Date(rp.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleMarkAsPaid(rp.recurring_id)}
                            title="Mark as paid"
                            className="p-2 rounded-lg text-success hover:bg-success/10 transition-colors"
                          >
                            <CheckCircle className="h-4.5 w-4.5" />
                          </button>
                          <button
                            onClick={() => {
                              setEditingPayment(rp);
                              setRecOpen(true);
                            }}
                            title="Edit"
                            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-background transition-colors"
                          >
                            <Edit className="h-4.5 w-4.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteRecurring(rp.recurring_id)}
                            title="Delete"
                            className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {filteredPayments.length === 0 && (
                  <div className="p-10 text-center text-sm text-muted-foreground space-y-1">
                    <p>No active commitments found.</p>
                    <p className="text-xs opacity-75">Click 'Add commitment' to create a recurring SIP, bill, or subscription.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {open && <LinkAccountDialog onClose={() => setOpen(false)} onAdd={handleAddAccount} />}
      {recOpen && (
        <RecurringPaymentDialog 
          onClose={() => {
            setRecOpen(false);
            setEditingPayment(null);
          }} 
          onSave={handleSaveRecurring} 
          editingItem={editingPayment} 
        />
      )}
    </div>
  );
}

function LinkAccountDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (a: { name: string; type: string; initial_balance: number; last_details: string }) => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("Bank");
  const [balance, setBalance] = useState("");
  const [details, setDetails] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      name,
      type,
      initial_balance: Number(balance),
      last_details: details
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Link account</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Account name</div>
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="SBI Savings or Paytm Wallet" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <div>
          <div className="text-xs text-muted-foreground mb-1">Account Type</div>
          <select 
            value={type} 
            onChange={(e) => setType(e.target.value)}
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
          >
            <option value="Bank">Bank</option>
            <option value="Wallet">Wallet</option>
            <option value="Card">Card</option>
          </select>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Starting balance (₹)</div>
          <input value={balance} onChange={(e) => setBalance(e.target.value)} type="number" required placeholder="5000" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Last details (e.g. Card number or handle)</div>
          <input value={details} onChange={(e) => setDetails(e.target.value)} placeholder="•••• 1234 or @handle" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Save</button>
      </form>
    </div>
  );
}

function RecurringPaymentDialog({
  onClose,
  onSave,
  editingItem
}: {
  onClose: () => void;
  onSave: (p: any) => void;
  editingItem?: RecurringItem | null;
}) {
  const [title, setTitle] = useState(editingItem?.title || "");
  const [amount, setAmount] = useState(editingItem?.amount?.toString() || "");
  const [category, setCategory] = useState(editingItem?.category || "Subscription");
  const [frequency, setFrequency] = useState(editingItem?.frequency || "Monthly");
  const [startDate, setStartDate] = useState(editingItem?.start_date || new Date().toISOString().split("T")[0]);
  const [nextDueDate, setNextDueDate] = useState(editingItem?.next_due_date || new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState(editingItem?.notes || "");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      recurring_id: editingItem?.recurring_id,
      title,
      amount: Number(amount),
      category,
      frequency,
      start_date: startDate,
      next_due_date: nextDueDate,
      notes
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{editingItem ? "Edit Recurring Commitment" : "Add Recurring Commitment"}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Commitment Title</div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Netflix, House Rent, SIP..." className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <div className="text-xs text-muted-foreground mb-1">Amount (₹)</div>
            <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" required placeholder="500" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
          </label>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Frequency</div>
            <select 
              value={frequency} 
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
            >
              <option value="Daily">Daily</option>
              <option value="Weekly">Weekly</option>
              <option value="Monthly">Monthly</option>
              <option value="Quarterly">Quarterly</option>
              <option value="Half-Yearly">Half-Yearly</option>
              <option value="Yearly">Yearly</option>
            </select>
          </div>
        </div>

        <div>
          <div className="text-xs text-muted-foreground mb-1">Category</div>
          <select 
            value={category} 
            onChange={(e) => setCategory(e.target.value)}
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
          >
            <option value="SIP">SIP</option>
            <option value="Mutual Fund">Mutual Fund</option>
            <option value="PPF">PPF</option>
            <option value="RD">RD</option>
            <option value="Subscription">Subscription</option>
            <option value="Rent">Rent</option>
            <option value="EMI">EMI</option>
            <option value="Insurance">Insurance</option>
            <option value="Internet">Internet</option>
            <option value="Mobile Recharge">Mobile Recharge</option>
            <option value="Electricity">Electricity</option>
            <option value="Custom">Custom</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <div className="text-xs text-muted-foreground mb-1">Start Date</div>
            <input value={startDate} onChange={(e) => setStartDate(e.target.value)} type="date" required className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
          </label>

          <label className="block">
            <div className="text-xs text-muted-foreground mb-1">Next Due Date</div>
            <input value={nextDueDate} onChange={(e) => setNextDueDate(e.target.value)} type="date" required className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
          </label>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Optional Notes</div>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Auto-debit configured, quarterly premium, etc." className="w-full min-h-[60px] rounded-xl bg-surface border border-border p-3 text-sm focus:outline-none focus:border-primary text-foreground resize-none" />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Save</button>
      </form>
    </div>
  );
}
