import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useMemo } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { CreditCard, Plus, Wallet as WalletIcon, Banknote, Smartphone, AlertCircle, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

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

function WalletPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<ExpenseItem[]>([]);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  
  // Link Account dialog state
  const [open, setOpen] = useState(false);

  const fetchWalletData = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      const [expRes, accRes] = await Promise.all([
        api.get("/api/expenses?limit=1000"),
        api.get("/api/accounts")
      ]);
      setItems(expRes.expenses || []);
      setAccounts(accRes || []);
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

      // Classify payment method tags
      const isPaytm = desc.includes("paytm") || desc.includes("wallet") || desc.includes("recharge") || desc.includes("swiggy") || desc.includes("zomato") || desc.includes("uber") || desc.includes("ola");
      const isCard = desc.includes("card") || desc.includes("student") || desc.includes("amazon") || desc.includes("flipkart") || desc.includes("netflix") || desc.includes("spotify") || desc.includes("gym") || cat.includes("subscriptions") || cat.includes("entertainment");

      // Auto-route transaction to the most appropriate account
      let bestAccIndex = 0;
      let bestWeight = -1;

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
        if (accType === "bank" && !isPaytm && !isCard) weight += 0.5;

        if (weight > bestWeight) {
          bestWeight = weight;
          bestAccIndex = index;
        }
      });

      // Apply amount to the resolved best match account
      if (item.category === "Income") {
        calculated[bestAccIndex].balance += amt;
      } else {
        calculated[bestAccIndex].balance -= amt;
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

  // Dynamically aggregate recurring payments from Subscriptions category
  const recurringData = useMemo(() => {
    const subs = items.filter(
      (item) => item.category === "Subscriptions" || item.category === "Bills"
    );

    // Group by description (ignoring case/whitespace)
    const grouped: { [key: string]: ExpenseItem } = {};
    subs.forEach((item) => {
      const key = (item.description || item.category).trim().toLowerCase();
      if (!grouped[key] || new Date(item.date) > new Date(grouped[key].date)) {
        grouped[key] = item;
      }
    });

    // Convert to target structure and calculate next billing date (add 30 days)
    return Object.values(grouped)
      .map((item) => {
        const lastDate = new Date(item.date);
        const nextDate = new Date(lastDate);
        nextDate.setDate(lastDate.getDate() + 30);
        
        const formattedNext = nextDate.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });

        return {
          name: item.description || item.category,
          amount: parseFloat(item.amount as any) || 0,
          next: formattedNext,
          dateRaw: nextDate,
        };
      })
      .sort((a, b) => a.dateRaw.getTime() - b.dateRaw.getTime());
  }, [items]);

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

          <div className="rounded-2xl border border-border bg-surface">
            <div className="p-5 border-b border-border">
              <div className="font-semibold">Recurring payments</div>
              <div className="text-xs text-muted-foreground">Upcoming charges calculated from historical subscriptions and bills</div>
            </div>
            <div className="divide-y divide-border">
              {recurringData.map((r) => (
                <div key={r.name} className="flex items-center justify-between px-5 py-4 hover:bg-surface-hover transition-colors">
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">Next payment estimate: {r.next}</div>
                  </div>
                  <div className="text-sm font-semibold">₹{r.amount.toLocaleString()}</div>
                </div>
              ))}
              {recurringData.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No upcoming recurring subscriptions or bills found in transactions.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {open && <LinkAccountDialog onClose={() => setOpen(false)} onAdd={handleAddAccount} />}
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


