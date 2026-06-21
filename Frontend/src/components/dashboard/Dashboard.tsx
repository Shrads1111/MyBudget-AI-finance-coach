import { motion } from "framer-motion";
import { useEffect, useState, useCallback } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  CreditCard,
  Sparkles,
  Download,
  AlertCircle,
  Play
} from "lucide-react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { VoiceMicButton } from "@/components/VoiceTransaction";

type DashboardSummary = {
  summary: {
    total_expenses: number;
    monthly_expenses: number;
    active_goals_count: number;
    total_balance: number;
    total_income: number;
    friend_owe: number;
    friend_owe_you?: number;
    friend_you_owe?: number;
    friend_net?: number;
  };
  budget_utilization: Array<{
    category: string;
    limit: number;
    spent: number;
    remaining: number;
    utilization_percentage: number;
  }>;
  savings_progress: Array<{
    goal_id: string;
    goal_name: string;
    target_amount: number;
    current_amount: number;
    progress_percentage: number;
    deadline: string;
  }>;
  top_spending_categories: Array<{
    category: string;
    total_amount: number;
  }>;
  expense_by_category: Record<string, { amount: number; percentage: number }>;
  recent_transactions: Array<{
    expense_id: string;
    amount: number;
    category: string;
    description: string;
    date: string;
  }>;
};

type HealthScore = {
  score: number;
  grade: string;
  breakdown: {
    savings: number;
    budget: number;
    goals: number;
    stability: number;
    consistency: number;
  };
  recommendations: string[];
};

type SpendingPattern = {
  type: string;
  message: string;
};

type SimulationResult = {
  type: string;
  result: any;
  explanation: string;
};

const statusStyles: Record<string, string> = {
  Completed: "bg-success/10 text-success",
  Pending: "bg-warning/10 text-warning",
  "In Progress": "bg-primary/10 text-primary",
  Failed: "bg-destructive/10 text-destructive",
};

export function Dashboard() {
  const { user, token } = useAuth();
  
  // States for live API data
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [health, setHealth] = useState<HealthScore | null>(null);
  const [patterns, setPatterns] = useState<SpendingPattern[]>([]);
  
  // Simulator states
  const [simQuery, setSimQuery] = useState("");
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Lifted outside useEffect so voice save handler can call it too
  const fetchAllData = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);

      const [sumRes, healthRes, patternRes] = await Promise.all([
        api.get("/api/dashboard/summary"),
        api.get("/api/health-score"),
        api.get("/api/analytics/patterns")
      ]);

      setSummary(sumRes);
      setHealth(healthRes);
      setPatterns(patternRes);
    } catch (e: any) {
      console.error("Dashboard fetch error:", e);
      setErr(e.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Syncing details when auth token is present
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Report Download Trigger
  const downloadReport = async () => {
    try {
      const blob = await api.getPdf("/api/reports/monthly");
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `MyBudget_Statement_${new Date().toISOString().slice(0, 7)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (e: any) {
      alert("Error generating report: " + e.message);
    }
  };

  // Voice transaction save — posts to existing /api/expenses then refreshes dashboard
  const handleVoiceSave = async (payloads: Array<{ amount: number; category: string; description: string; date: string }>) => {
    await Promise.all(payloads.map(payload => api.post("/api/expenses", payload)));
    fetchAllData();
  };

  // Run AI Simulation
  const handleSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simQuery.trim()) return;
    try {
      setSimLoading(true);
      setSimError(null);
      const res = await api.post("/api/ai/simulate", { query: simQuery });
      setSimResult(res);
    } catch (err: any) {
      setSimError(err.message || "Failed to execute simulation");
    } finally {
      setSimLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-sm text-muted-foreground">Gathering your financial ledger...</p>
        </div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-6 text-center max-w-xl mx-auto my-12">
        <AlertCircle className="h-10 w-10 text-destructive mx-auto mb-3" />
        <h3 className="font-semibold text-lg">Failed to sync dashboard</h3>
        <p className="text-sm text-muted-foreground mt-2">{err}</p>
        <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary-hover transition">
          Retry Sync
        </button>
      </div>
    );
  }

  // Calculate live values
  const totalExpenses = summary?.summary.total_expenses || 0;
  const monthlyExpenses = summary?.summary.monthly_expenses || 0;
  const activeGoals = summary?.summary.active_goals_count || 0;
  const totalBalance = summary?.summary.total_balance ?? 0;
  const friendOwe = summary?.summary.friend_owe ?? 0;
  const friendOweYou = summary?.summary.friend_owe_you ?? 0;
  const friendYouOwe = summary?.summary.friend_you_owe ?? 0;
  const friendNet = summary?.summary.friend_net ?? 0;

  // Build pie chart data from expense_by_category
  const PIE_COLORS = [
    "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#3b82f6",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#84cc16",
    "#a855f7", "#06b6d4"
  ];
  const pieData = Object.entries(summary?.expense_by_category || {}).map(
    ([name, val]) => ({ name, value: val.amount, percentage: val.percentage })
  ).sort((a, b) => b.value - a.value);

  // Render recent activities
  const recentActivities = summary?.recent_transactions || [];




  return (
    <div className="max-w-[1400px] mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Good morning, {user?.name || "Student"}</h1>
          <p className="text-sm text-muted-foreground mt-1">Here is a real-time summary of your balances, budgets, and savings.</p>
        </div>
        <div className="flex items-center gap-2">
          <VoiceMicButton onConfirm={handleVoiceSave} />
          <button onClick={downloadReport} className="inline-flex items-center gap-2 h-10 px-4 rounded-xl border border-border bg-surface text-sm hover:bg-surface-hover transition">
            <Download className="h-4 w-4" /> Download Report
          </button>
        </div>
      </div>

      {/* KPI Row — 4 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Total Balance */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Total Balance</div>
          <div className="mt-4 flex items-end justify-between">
            <div className={`text-3xl font-semibold tracking-tight ${totalBalance >= 0 ? "" : "text-destructive"}`}>
              ₹{Math.abs(totalBalance).toLocaleString()}
            </div>
            <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${totalBalance >= 0 ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
              {totalBalance >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
              {totalBalance >= 0 ? "Surplus" : "Deficit"}
            </span>
          </div>
        </div>

        {/* Card 2: Total Spend */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Total Spend</div>
          <div className="mt-4 flex items-end justify-between">
            <div className="text-3xl font-semibold tracking-tight">₹{totalExpenses.toLocaleString()}</div>
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-primary/10 text-primary">
              All-Time
            </span>
          </div>
        </div>

        {/* Card 3: Friend Owe */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)] flex flex-col justify-between min-h-[120px]">
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Friend Owe</div>
          <div className="mt-3 space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">People Owe You:</span>
              <span className="font-semibold text-emerald-500">₹{friendOweYou.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">You Owe Others:</span>
              <span className="font-semibold text-rose-500">₹{friendYouOwe.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center text-sm pt-1.5 border-t border-border/50">
              <span className="font-medium text-foreground">Net:</span>
              <span className={`font-bold ${friendNet >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                {friendNet >= 0 ? "+" : ""}₹{friendNet.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Active Savings Targets */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-card)]">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Active Savings Targets</div>
          <div className="mt-4 flex items-end justify-between">
            <div className="text-3xl font-semibold tracking-tight">{activeGoals} Goals</div>
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-success/10 text-success">
              Active
            </span>
          </div>
        </div>
      </div>

      {/* Main Analysis Block (Health Score & Budgets) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        
        {/* Feature 1: Financial Health Score Card */}
        <div className="lg:col-span-1 rounded-2xl bg-card border border-border p-6 shadow-[var(--shadow-card)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-5">
              <div>
                <div className="text-sm font-medium">Financial Health Score</div>
                <div className="text-xs text-muted-foreground">Calculated mathematically</div>
              </div>
              <div className="h-8 w-8 rounded-full bg-primary/10 text-primary text-sm font-bold flex items-center justify-center">
                {health?.grade}
              </div>
            </div>
            
            <div className="flex flex-col items-center py-4">
              {/* Progress Ring */}
              <div className="relative h-28 w-28">
                <svg className="w-full h-full" viewBox="0 0 36 36">
                  <path
                    className="text-border"
                    strokeWidth="3"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="text-primary"
                    strokeDasharray={`${health?.score || 0}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold">{health?.score || 0}</span>
                  <span className="text-[9px] text-muted-foreground uppercase">Score</span>
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <div className="text-xs font-semibold uppercase text-muted-foreground">Recommendations:</div>
              <div className="space-y-1.5 max-h-[140px] overflow-y-auto">
                {health?.recommendations.map((rec, i) => (
                  <p key={i} className="text-xs text-foreground/80 leading-relaxed">&bull; {rec}</p>
                ))}
              </div>
            </div>
          </div>
          
          <div className="mt-4 grid grid-cols-5 gap-1 text-center border-t border-border pt-3">
            {[
              { label: "Save", val: health?.breakdown.savings },
              { label: "Bgt", val: health?.breakdown.budget },
              { label: "Goal", val: health?.breakdown.goals },
              { label: "Stab", val: health?.breakdown.stability },
              { label: "Cons", val: health?.breakdown.consistency }
            ].map((b, i) => (
              <div key={i}>
                <div className="text-[9px] text-muted-foreground truncate">{b.label}</div>
                <div className="text-xs font-semibold mt-0.5">{b.val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Daily Expense Breakdown — Pie Chart */}
        <div className="lg:col-span-2 rounded-2xl bg-card border border-border p-6 shadow-[var(--shadow-card)]">
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="text-sm font-medium">Daily Expense Breakdown</div>
              <div className="text-xs text-muted-foreground">Spending distribution across all categories</div>
            </div>
          </div>
          <div className="h-[260px]">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="40%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                    formatter={(value: any, name: any, props: any) => [
                      `₹${Number(value).toLocaleString()} (${props.payload.percentage}%)`,
                      name,
                    ]}
                  />
                  <Legend
                    layout="vertical"
                    align="right"
                    verticalAlign="middle"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => (
                      <span style={{ fontSize: 11, color: "var(--color-foreground)" }}>{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No expenses recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Feature 3: Smart Spending Insights & Anomaly Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="rounded-2xl bg-card border border-border p-6 shadow-[var(--shadow-card)] lg:col-span-1">
          <div className="font-semibold text-sm mb-4">Smart Spending Insights</div>
          <div className="space-y-3">
            {patterns.map((pat, idx) => (
              <div key={idx} className="rounded-xl border border-border p-3 bg-surface hover:bg-surface-hover transition">
                <div className="text-[10px] uppercase tracking-wider text-primary font-semibold mb-1">
                  {pat.type.replace('_', ' ')}
                </div>
                <div className="text-xs text-foreground leading-relaxed">{pat.message}</div>
              </div>
            ))}
            {patterns.length === 0 && (
              <div className="text-center text-xs text-muted-foreground py-8">
                No trends detected. Log more expenses to trigger insights.
              </div>
            )}
          </div>
        </div>

        {/* Feature 5: AI Financial Simulator Widget */}
        <div className="lg:col-span-2 relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-card)]">
          <div className="absolute inset-0 pointer-events-none opacity-60 bg-[radial-gradient(circle_at_top_right,var(--color-accent),transparent_60%)]" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <div className="inline-flex items-center gap-2 text-xs font-medium text-primary px-2.5 py-1 rounded-full bg-accent">
                <Sparkles className="h-3.5 w-3.5" /> AI Financial Simulator
              </div>
              <button 
                type="button" 
                onClick={() => {
                  setSimQuery("");
                  setSimResult(null);
                  setSimError(null);
                }} 
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            </div>
            
            <h3 className="text-lg font-semibold tracking-tight">
              Simulate Future Scenarios
            </h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-xl">
              Type or select a financial scenario to execute real-time mathematical calculations followed by natural language AI coaching.
            </p>

            <div className="mt-4 flex gap-2 flex-wrap">
              {[
                "If I save ₹5000 per month, when will I reach ₹1 lakh?",
                "If I reduce food spending by 20%, how much money will I save annually?",
                "If I increase my savings rate by 10%, what happens after one year?"
              ].map((q) => (
                <button 
                  key={q} 
                  type="button"
                  onClick={() => setSimQuery(q)} 
                  className="text-[11px] px-3 py-1.5 rounded-full border border-border bg-surface hover:bg-surface-hover text-foreground font-medium transition"
                >
                  {q}
                </button>
              ))}
            </div>

            <form onSubmit={handleSimulation} className="mt-4 flex gap-2">
              <input 
                value={simQuery} 
                onChange={(e) => setSimQuery(e.target.value)} 
                placeholder="Ask e.g. If I save ₹3000 monthly, when will I hit ₹50000?" 
                className="flex-1 h-10 rounded-xl bg-surface border border-border px-4 text-xs focus:outline-none focus:border-primary" 
              />
              <button 
                type="submit"
                disabled={simLoading || !simQuery.trim()}
                className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary-hover transition inline-flex items-center gap-1 disabled:opacity-60"
              >
                <Play className="h-3.5 w-3.5" /> Run
              </button>
            </form>

            {simLoading && (
              <div className="mt-4 text-center py-4">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary mx-auto"></div>
                <p className="text-[11px] text-muted-foreground mt-1">Calculating forecast...</p>
              </div>
            )}

            {simError && (
              <div className="mt-4 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-xl p-3">
                {simError}
              </div>
            )}

            {simResult && (
              <motion.div 
                initial={{ opacity: 0, y: 5 }} 
                animate={{ opacity: 1, y: 0 }} 
                className="mt-4 rounded-xl border border-border bg-surface p-4 space-y-3"
              >
                <div className="flex gap-4">
                  {simResult.type === "savings_target" && (
                    <>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Monthly Savings</div>
                        <div className="text-base font-bold">₹{simResult.result.monthly_savings.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Target Amount</div>
                        <div className="text-base font-bold">₹{simResult.result.target_amount.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Months Needed</div>
                        <div className="text-base font-bold text-primary">{simResult.result.months_required} Months</div>
                      </div>
                    </>
                  )}
                  {simResult.type === "expense_reduction" && (
                    <>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Category cut</div>
                        <div className="text-base font-bold">{simResult.result.category} ({simResult.result.reduction_percentage}%)</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Monthly Saving</div>
                        <div className="text-base font-bold">₹{simResult.result.monthly_savings.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Annual Saving</div>
                        <div className="text-base font-bold text-primary">₹{simResult.result.annual_savings.toLocaleString()}</div>
                      </div>
                    </>
                  )}
                  {simResult.type === "savings_rate_increase" && (
                    <>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Rate Increase</div>
                        <div className="text-base font-bold">{simResult.result.increase_percentage}%</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Monthly Extra</div>
                        <div className="text-base font-bold">₹{simResult.result.monthly_extra.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Projected 1-Yr Savings</div>
                        <div className="text-base font-bold text-primary">₹{simResult.result.projected_total_savings_1yr.toLocaleString()}</div>
                      </div>
                    </>
                  )}
                  {simResult.type === "general_projection" && (
                    <>
                      <div>
                        <div className="text-[10px] text-muted-foreground">Monthly Savings</div>
                        <div className="text-base font-bold">₹{simResult.result.current_monthly_savings.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">6-Month Forecast</div>
                        <div className="text-base font-bold text-primary">₹{simResult.result.projected_savings_6m.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-muted-foreground">1-Year Forecast</div>
                        <div className="text-base font-bold text-primary">₹{simResult.result.projected_savings_12m.toLocaleString()}</div>
                      </div>
                    </>
                  )}
                </div>
                <div className="text-xs text-foreground/80 leading-relaxed border-t border-border pt-2">
                  {simResult.explanation}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activities */}
      <div className="rounded-2xl bg-card border border-border shadow-[var(--shadow-card)] overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-6">
          <div>
            <div className="text-sm font-medium">Recent Activities</div>
            <div className="text-xs text-muted-foreground">Latest transactions across all wallets</div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-y border-border bg-surface">
                <th className="font-medium px-6 py-3">Category</th>
                <th className="font-medium px-6 py-3">Description</th>
                <th className="font-medium px-6 py-3">Price</th>
                <th className="font-medium px-6 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {recentActivities.map((a, idx) => (
                <tr key={a.expense_id} className="border-b border-border last:border-0 hover:bg-surface-hover transition">
                  <td className="px-6 py-4 font-medium">{a.category}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg grid place-items-center ${a.category === 'Income' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-primary/10 text-primary'}`}>
                        {a.category === 'Income' ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                      </div>
                      {a.description || a.category}
                    </div>
                  </td>
                  <td className="px-6 py-4 font-medium">
                    {a.category === 'Income' ? '+' : '-'}₹{floatAmount(a.amount).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">{a.date}</td>
                </tr>
              ))}
              {recentActivities.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-sm text-muted-foreground">
                    No transactions found. Go to Transactions page to record your first transaction!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function floatAmount(amt: any): number {
  try {
    return parseFloat(amt) || 0;
  } catch {
    return 0;
  }
}
