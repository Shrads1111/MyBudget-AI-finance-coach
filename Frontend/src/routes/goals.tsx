import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, Trash2, X, AlertCircle, Sparkles, CheckCircle, Pencil } from "lucide-react";

export const Route = createFileRoute("/goals")({
  head: () => ({ meta: [{ title: "Goals · MyBudget" }] }),
  component: () => (
    <AppShell>
      <GoalsPage />
    </AppShell>
  ),
});

type SavingsGoal = {
  goal_id: string;
  goal_name: string;
  target_amount: number;
  current_amount: number;
  progress_percentage: number;
  remaining_amount: number;
  deadline: string;
};

type GoalPlan = {
  goal_id: string;
  goal_name: string;
  monthly_target: number;
  weekly_target: number;
  daily_target: number;
  completion_probability: number;
  estimated_completion_date: string;
  ai_advice?: string;
};

function GoalsPage() {
  const { token } = useAuth();
  
  // Data States
  const [goals, setGoals] = useState<SavingsGoal[]>([]);
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);
  const [goalPlan, setGoalPlan] = useState<GoalPlan | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [planLoading, setPlanLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Dialog State
  const [open, setOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<SavingsGoal | null>(null);
  const [contributeTargetGoal, setContributeTargetGoal] = useState<SavingsGoal | null>(null);

  // Fetch Goals
  const fetchGoals = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      const res = await api.get("/api/goals");
      setGoals(res || []);
      
      // Auto-select first goal if none selected
      if (res && res.length > 0) {
        // If selectedGoal is currently set, preserve selection from new list, else select first
        const found = res.find((g: SavingsGoal) => g.goal_id === selectedGoal?.goal_id);
        setSelectedGoal(found || res[0]);
      } else {
        setSelectedGoal(null);
        setGoalPlan(null);
      }
    } catch (e: any) {
      setErr(e.message || "Failed to load savings goals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGoals();
  }, [token]);

  // Fetch Planner recommendations when selected goal changes
  useEffect(() => {
    if (!token || !selectedGoal) return;
    
    const fetchPlan = async () => {
      try {
        setPlanLoading(true);
        const res = await api.get(`/api/goals/${selectedGoal.goal_id}/planner`);
        setGoalPlan(res);
      } catch (e) {
        console.error("Error loading planner recommendation:", e);
        setGoalPlan(null);
      } finally {
        setPlanLoading(false);
      }
    };

    fetchPlan();
  }, [token, selectedGoal]);

  // Add goal
  const handleAddGoal = async (payload: { goal_name: string; target_amount: number; current_amount: number; deadline: string }) => {
    try {
      await api.post("/api/goals", payload);
      setOpen(false);
      fetchGoals();
    } catch (e: any) {
      alert("Failed to create savings goal: " + e.message);
    }
  };

  // Edit goal
  const handleEditGoal = async (goalId: string, payload: { goal_name: string; target_amount: number; current_amount: number; deadline: string }) => {
    try {
      await api.put(`/api/goals/${goalId}`, payload);
      setOpen(false);
      setEditingGoal(null);
      fetchGoals();
    } catch (e: any) {
      alert("Failed to update savings goal: " + e.message);
    }
  };

  // Delete goal
  const handleDeleteGoal = async (goalId: string) => {
    if (!confirm("Are you sure you want to delete this savings goal?")) return;
    try {
      await api.delete(`/api/goals/${goalId}`);
      if (selectedGoal?.goal_id === goalId) {
        setSelectedGoal(null);
        setGoalPlan(null);
      }
      fetchGoals();
    } catch (e: any) {
      alert("Failed to delete goal: " + e.message);
    }
  };

  // Contrib tool
  const handleContribute = async (goalId: string, amount: number) => {
    try {
      const gObj = goals.find(x => x.goal_id === goalId);
      if (!gObj) return;
      const newAmt = (parseFloat(gObj.current_amount as any) || 0) + amount;
      
      await api.put(`/api/goals/${goalId}`, { current_amount: newAmt });
      
      // Refresh
      fetchGoals();
    } catch (e: any) {
      alert("Failed to save contribution: " + e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Savings Goals</h1>
          <p className="text-sm text-muted-foreground">Plan and fund your future milestones with live Firestore tracking.</p>
        </div>
        
        <button onClick={() => setOpen(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-medium inline-flex items-center gap-2">
          <Plus className="h-4 w-4" /> New savings goal
        </button>
      </div>

      {err && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>{err}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">
          Syncing savings ledger...
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Active Goals Grid */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase text-muted-foreground tracking-wider">Active Goals</h2>
            <div className="space-y-3">
              {goals.map((g) => {
                const target = parseFloat(g.target_amount as any) || 0;
                const current = parseFloat(g.current_amount as any) || 0;
                const pct = Math.min(100, target > 0 ? (current / target) * 100 : 0);
                const isSelected = selectedGoal?.goal_id === g.goal_id;

                return (
                  <div 
                    key={g.goal_id} 
                    onClick={() => setSelectedGoal(g)}
                    className={`rounded-2xl border p-5 cursor-pointer transition-all hover:translate-x-1 ${
                      isSelected ? "border-primary bg-primary/5 shadow-glow" : "border-border bg-surface hover:bg-surface-hover"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-semibold text-lg flex items-center gap-1.5">
                          {g.goal_name}
                          {pct >= 100 && <CheckCircle className="h-4 w-4 text-emerald-500 fill-emerald-500/10" />}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">Deadline: {g.deadline}</div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button 
                          onClick={(e) => { 
                            e.stopPropagation(); 
                            setEditingGoal(g); 
                            setOpen(true); 
                          }} 
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface transition cursor-pointer" 
                          aria-label="Edit"
                        >
                          <Pencil className="h-4.5 w-4.5" />
                        </button>
                        <button 
                          onClick={(e) => { 
                            e.stopPropagation(); 
                            handleDeleteGoal(g.goal_id); 
                          }} 
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-surface transition cursor-pointer" 
                          aria-label="Delete"
                        >
                          <Trash2 className="h-4.5 w-4.5" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="font-medium">₹{current.toLocaleString()} saved</span>
                        <span className="text-muted-foreground">₹{target.toLocaleString()} target</span>
                      </div>
                      <div className="h-2 rounded-full bg-background overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="flex justify-between items-center mt-3">
                        <span className="text-xs text-primary font-semibold">{pct.toFixed(0)}% Complete</span>
                        <div className="flex gap-2">
                          <button onClick={(e) => { e.stopPropagation(); handleContribute(g.goal_id, 500); }} className="text-[10px] px-2 py-1 rounded border border-border bg-background hover:bg-surface-hover cursor-pointer">+₹500</button>
                          <button onClick={(e) => { e.stopPropagation(); handleContribute(g.goal_id, 2000); }} className="text-[10px] px-2 py-1 rounded border border-border bg-background hover:bg-surface-hover cursor-pointer">+₹2k</button>
                          <button 
                            onClick={(e) => { 
                              e.stopPropagation(); 
                              setContributeTargetGoal(g); 
                            }} 
                            className="text-[10px] px-2 py-1 rounded border border-primary text-primary bg-primary/5 hover:bg-primary/10 transition cursor-pointer font-medium"
                          >
                            + Custom
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              {goals.length === 0 && (
                <div className="text-center py-12 border border-dashed border-border rounded-2xl bg-surface text-muted-foreground text-sm">
                  No savings goals created. Add your first goal to plan target forecasts!
                </div>
              )}
            </div>
          </div>

          {/* Goal Planner Details Card */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase text-muted-foreground tracking-wider">Smart Planner</h2>
            {selectedGoal ? (
              <div className="rounded-2xl border border-border bg-surface p-6 shadow-[var(--shadow-card)] space-y-6">
                <div>
                  <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary px-2.5 py-1 rounded-full bg-accent mb-3">
                    <Sparkles className="h-3.5 w-3.5" /> Actionable Saving Breakdown
                  </div>
                  <h3 className="text-2xl font-bold tracking-tight">{selectedGoal.goal_name}</h3>
                  <p className="text-xs text-muted-foreground mt-1">Estimations computed based on your historical cash flow rate.</p>
                </div>

                {planLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                    <p className="text-xs text-muted-foreground mt-2">Computing targets...</p>
                  </div>
                ) : goalPlan ? (
                  <div className="space-y-5">
                    {/* Probability Ring */}
                    <div className="rounded-xl bg-background border border-border p-4 flex items-center justify-between">
                      <div>
                        <div className="text-xs text-muted-foreground">Completion Probability</div>
                        <div className="text-lg font-bold mt-1 text-primary">{goalPlan.completion_probability}% Likelihood</div>
                      </div>
                      <div className="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary flex items-center justify-center font-bold text-sm">
                        {goalPlan.completion_probability}%
                      </div>
                    </div>

                    {/* Target Cards grid */}
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div className="rounded-xl border border-border bg-background p-3">
                        <div className="text-[10px] text-muted-foreground">Daily Target</div>
                        <div className="text-lg font-bold mt-1">₹{goalPlan.daily_target}</div>
                      </div>
                      <div className="rounded-xl border border-border bg-background p-3">
                        <div className="text-[10px] text-muted-foreground">Weekly Target</div>
                        <div className="text-lg font-bold mt-1">₹{goalPlan.weekly_target}</div>
                      </div>
                      <div className="rounded-xl border border-border bg-background p-3">
                        <div className="text-[10px] text-muted-foreground">Monthly Target</div>
                        <div className="text-lg font-bold mt-1 text-primary">₹{goalPlan.monthly_target}</div>
                      </div>
                    </div>

                    <div className="text-xs text-muted-foreground leading-relaxed bg-background p-3 rounded-xl border border-border">
                      To reach your target of ₹{selectedGoal.target_amount.toLocaleString()} for {selectedGoal.goal_name} by {goalPlan.estimated_completion_date}, you must contribute ₹{goalPlan.monthly_target.toLocaleString()} monthly. At your current transaction rate, we estimate a {goalPlan.completion_probability}% probability of achieving this on schedule.
                    </div>

                    {goalPlan.ai_advice && (
                      <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                          <Sparkles className="h-3.5 w-3.5" /> AI Coach Advice
                        </div>
                        <p className="text-xs text-foreground leading-relaxed">
                          {goalPlan.ai_advice}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-xs text-muted-foreground">
                    Unable to load planner recommendations.
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground bg-surface">
                Select a goal to view planner recommendations.
              </div>
            )}
          </div>
        </div>
      )}

      {open && (
        <AddGoalDialog 
          onClose={() => {
            setOpen(false);
            setEditingGoal(null);
          }} 
          onAdd={async (payload) => {
            if (editingGoal) {
              await handleEditGoal(editingGoal.goal_id, payload);
            } else {
              await handleAddGoal(payload);
            }
          }} 
          goalToEdit={editingGoal}
        />
      )}

      {contributeTargetGoal && (
        <ContributeDialog
          onClose={() => setContributeTargetGoal(null)}
          onContribute={async (amount) => {
            await handleContribute(contributeTargetGoal.goal_id, amount);
            setContributeTargetGoal(null);
          }}
        />
      )}
    </div>
  );
}

function AddGoalDialog({ 
  onClose, 
  onAdd, 
  goalToEdit 
}: { 
  onClose: () => void; 
  onAdd: (g: { goal_name: string; target_amount: number; current_amount: number; deadline: string }) => void;
  goalToEdit?: SavingsGoal | null;
}) {
  const [name, setName] = useState(goalToEdit?.goal_name || "");
  const [target, setTarget] = useState(goalToEdit?.target_amount?.toString() || "");
  const [current, setCurrent] = useState(goalToEdit?.current_amount?.toString() || "0");
  const [deadline, setDeadline] = useState(goalToEdit?.deadline || "");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({ goal_name: name, target_amount: Number(target), current_amount: Number(current), deadline });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{goalToEdit ? "Edit savings target" : "New savings target"}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <Input label="Goal Name" value={name} onChange={setName} required />
        <Input label="Target Amount (₹)" value={target} onChange={setTarget} type="number" required />
        <Input label="Initial Saved (₹)" value={current} onChange={setCurrent} type="number" required />
        <Input label="Deadline" value={deadline} onChange={setDeadline} type="date" required />

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover shadow-md">
          {goalToEdit ? "Save Changes" : "Save"}
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

function ContributeDialog({ 
  onClose, 
  onContribute 
}: { 
  onClose: () => void; 
  onContribute: (amount: number) => void;
}) {
  const [amount, setAmount] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const num = parseFloat(amount);
    if (!isNaN(num) && num > 0) {
      onContribute(num);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-border bg-background p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Add Saved Amount</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Enter Amount to Add (₹)</div>
          <input 
            value={amount} 
            onChange={(e) => setAmount(e.target.value)} 
            type="number" 
            required 
            placeholder="e.g. 1500" 
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" 
          />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover shadow-md">Add to Savings</button>
      </form>
    </div>
  );
}
