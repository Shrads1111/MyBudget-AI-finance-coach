import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { 
  Plus, 
  Users, 
  Send, 
  DollarSign, 
  X, 
  AlertCircle, 
  Check, 
  CheckCircle2, 
  Clock, 
  Smartphone, 
  Lock, 
  Info,
  Utensils,
  Home,
  Car,
  ShoppingBag,
  Film,
  User,
  ChevronRight,
  Bell,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Pencil,
  Trash2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const Route = createFileRoute("/groups")({
  head: () => ({ meta: [{ title: "Groups · MyBudget" }] }),
  component: () => (
    <AppShell>
      <GroupsPage />
    </AppShell>
  ),
});

type GroupItem = {
  group_id: string;
  group_name: string;
  created_by: string;
  members: string[];
};

type GroupSummary = {
  group_id: string;
  group_name: string;
  total_spending: number;
  total_expenses?: number;
  member_count?: number;
  per_person_share?: number;
  members: string[];
  balances: Record<string, number>;
  suggested_settlements: Array<{
    from: string;
    to: string;
    amount: number;
  }>;
};

// Category mapping helper
const CATEGORY_MAP = {
  "Food": { icon: Utensils, color: "bg-orange-500/10 text-orange-500 border-orange-500/20" },
  "Utilities": { icon: Home, color: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  "Travel": { icon: Car, color: "bg-indigo-500/10 text-indigo-500 border-indigo-500/20" },
  "Shopping": { icon: ShoppingBag, color: "bg-rose-500/10 text-rose-500 border-rose-500/20" },
  "Entertainment": { icon: Film, color: "bg-amber-500/10 text-amber-500 border-amber-500/20" },
  "Other": { icon: DollarSign, color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" }
};

// Play audio clicks and chimes using Web Audio API
const playBeep = (freq = 600, duration = 0.05) => {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    // Ignore audio restrictions
  }
};

const playSuccessSound = () => {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const now = ctx.currentTime;
    
    const playNote = (freq: number, start: number, duration: number) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, now + start);
      gain.gain.setValueAtTime(0, now + start);
      gain.gain.linearRampToValueAtTime(0.06, now + start + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.00001, now + start + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + start);
      osc.stop(now + start + duration);
    };
    
    // Play a Google Pay style C-major ascending arpeggio
    playNote(523.25, 0, 0.25); // C5
    playNote(659.25, 0.08, 0.25); // E5
    playNote(783.99, 0.16, 0.25); // G5
    playNote(1046.50, 0.24, 0.5); // C6
  } catch (e) {
    // Ignore
  }
};

function GroupsPage() {
  const { user, token } = useAuth();
  
  // Data States
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<GroupItem | null>(null);
  const [groupSummary, setGroupSummary] = useState<GroupSummary | null>(null);
  const [groupDetails, setGroupDetails] = useState<any | null>(null);
  const [userProfiles, setUserProfiles] = useState<Record<string, { uid: string; email: string; display_name: string }>>({});
  
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Form states
  const [openCreate, setOpenCreate] = useState(false);
  const [openExpense, setOpenExpense] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);



  // Fetch groups list
  const fetchGroups = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErr(null);
      const res = await api.get("/api/groups");
      setGroups(res || []);
      
      if (res && res.length > 0) {
        // Retain selection if exists
        const found = res.find((g: GroupItem) => g.group_id === selectedGroup?.group_id);
        setSelectedGroup(found || res[0]);
      } else {
        setSelectedGroup(null);
        setGroupSummary(null);
        setGroupDetails(null);
      }
    } catch (e: any) {
      setErr(e.message || "Failed to load groups list.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, [token]);

  // Fetch summary and details for selected group
  const fetchSelectedGroupData = async () => {
    if (!token || !selectedGroup) return;
    try {
      setSummaryLoading(true);
      const [sumRes, detailRes] = await Promise.all([
        api.get(`/api/groups/${selectedGroup.group_id}/summary`),
        api.get(`/api/groups/${selectedGroup.group_id}`)
      ]);
      setGroupSummary(sumRes);
      setGroupDetails(detailRes);
    } catch (e) {
      console.error("Failed to load group details:", e);
      setGroupSummary(null);
      setGroupDetails(null);
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => {
    fetchSelectedGroupData();
  }, [token, selectedGroup]);

  // User Profile Resolver
  const fetchUserProfiles = async (uids: string[]) => {
    if (!token || uids.length === 0) return;
    try {
      const neededUids = uids.filter(uid => !userProfiles[uid]);
      if (neededUids.length === 0) return;
      const res = await api.post("/api/users/lookup", { uids: neededUids });
      setUserProfiles(prev => ({ ...prev, ...res }));
    } catch (e) {
      console.error("Failed to lookup user profiles:", e);
    }
  };

  useEffect(() => {
    if (!selectedGroup) return;
    const uids = new Set<string>();
    selectedGroup.members.forEach(m => uids.add(m));
    if (groupDetails?.expenses) {
      groupDetails.expenses.forEach((exp: any) => {
        uids.add(exp.paid_by);
        if (exp.splits) {
          exp.splits.forEach((s: any) => uids.add(s.member));
        }
      });
    }
    fetchUserProfiles(Array.from(uids));
  }, [token, selectedGroup, groupDetails]);

  const resolveMemberName = (uid: string) => {
    if (uid === user?.uid) return "You";
    const profile = userProfiles[uid];
    if (profile) {
      return profile.display_name || profile.email.split("@")[0] || uid.slice(0, 10);
    }
    return uid.slice(0, 10);
  };

  // Create Group
  const handleCreateGroup = async (payload: { group_name: string; members: string[] }) => {
    try {
      await api.post("/api/groups", payload);
      setOpenCreate(false);
      fetchGroups();
    } catch (e: any) {
      alert("Failed to create group: " + e.message);
    }
  };

  // Invite Member
  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroup || !inviteEmail.trim() || inviteBusy) return;
    try {
      setInviteBusy(true);
      await api.post("/api/groups/invite", {
        group_id: selectedGroup.group_id,
        member: inviteEmail.trim()
      });
      setInviteEmail("");
      fetchSelectedGroupData();
    } catch (e: any) {
      alert(e.message || "Failed to invite member.");
    } finally {
      setInviteBusy(false);
    }
  };

  // Add Group Expense
  const handleAddExpense = async (payload: any) => {
    if (!selectedGroup) return;
    try {
      await api.post("/api/groups/expense", {
        group_id: selectedGroup.group_id,
        expense: payload
      });
      setOpenExpense(false);
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Failed to add group bill: " + e.message);
    }
  };

  // Edit Group Expense
  const [editingExpense, setEditingExpense] = useState<any | null>(null);

  const handleEditExpense = async (expenseId: string, payload: any) => {
    if (!selectedGroup) return;
    try {
      await api.put(`/api/groups/${selectedGroup.group_id}/expense/${expenseId}`, {
        expense: payload
      });
      setOpenExpense(false);
      setEditingExpense(null);
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Failed to edit group bill: " + e.message);
    }
  };

  // Delete Group Expense
  const handleDeleteExpense = async (expenseId: string) => {
    if (!selectedGroup) return;
    if (!window.confirm("Are you sure you want to delete this bill split? This will also remove the payer's linked transaction and recalculate all roommate balances.")) {
      return;
    }
    try {
      await api.delete(`/api/groups/${selectedGroup.group_id}/expense/${expenseId}`);
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Failed to delete group bill: " + e.message);
    }
  };

  // Handle pay share directly without UPI
  const handlePayExpenseShare = async (expenseId: string) => {
    if (!selectedGroup) return;
    try {
      await api.post(`/api/groups/${selectedGroup.group_id}/expense/${expenseId}/pay`);
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Settle share failed: " + e.message);
    }
  };

  // Mark Paid Manually (Payer only)
  const handleMarkPaid = async (expenseId: string, memberUid: string) => {
    if (!selectedGroup) return;
    try {
      await api.post(`/api/groups/${selectedGroup.group_id}/expense/${expenseId}/mark-paid`, {
        member_uid: memberUid
      });
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Failed to mark as paid: " + e.message);
    }
  };

  // Remind Member (Payer only)
  const handleRemind = async (expenseId: string, memberUid: string) => {
    if (!selectedGroup) return;
    try {
      await api.post(`/api/groups/${selectedGroup.group_id}/expense/${expenseId}/remind`, {
        member_uid: memberUid
      });
      alert("Reminder notification sent successfully!");
    } catch (e: any) {
      alert("Failed to send reminder: " + e.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground/90 to-muted-foreground bg-clip-text text-transparent">Split Roommates</h1>
          <p className="text-sm text-muted-foreground mt-1">Split rent, dining, utilities, and shopping in Google Pay transaction style.</p>
        </div>
        
        <button onClick={() => setOpenCreate(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-semibold transition-all duration-200 shadow-md hover:shadow-lg flex items-center gap-2">
          <Plus className="h-4.5 w-4.5" /> Create split group
        </button>
      </div>

      {err && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2 animate-shake">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="h-10 w-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">Loading room lists...</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[280px_1fr] gap-6 items-start">
          {/* Groups List */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground/80 px-1">Your Rooms</div>
            <div className="space-y-2">
              {groups.map((g) => {
                const isSelected = selectedGroup?.group_id === g.group_id;
                return (
                  <button 
                    key={g.group_id} 
                    onClick={() => setSelectedGroup(g)}
                    className={`w-full text-left rounded-xl p-4 cursor-pointer transition-all duration-200 flex items-center gap-3 border ${
                      isSelected 
                        ? "border-primary bg-primary/5 text-foreground font-semibold shadow-sm" 
                        : "border-border/50 bg-surface hover:bg-surface-hover/80 text-muted-foreground hover:text-foreground hover:shadow-sm"
                    }`}
                  >
                    <div className={`p-2.5 rounded-lg ${isSelected ? 'bg-primary/10 text-primary' : 'bg-muted/50 text-muted-foreground'}`}>
                      <Users className="h-4 w-4" />
                    </div>
                    <span className="text-sm font-medium truncate flex-1">{g.group_name}</span>
                    {isSelected && <div className="h-1.5 w-1.5 rounded-full bg-primary" />}
                  </button>
                );
              })}
              {groups.length === 0 && (
                <div className="text-center text-xs text-muted-foreground/70 py-10 border border-dashed rounded-2xl bg-surface/50">No groups configured.</div>
              )}
            </div>
          </div>

          {/* Group details & spend feed */}
          <div>
            {selectedGroup ? (
              <div className="grid lg:grid-cols-[1fr_320px] gap-6 items-start">
                
                {/* Left side: balances & suggested steps & transactional feed */}
                <div className="space-y-6">
                  {/* Summary card */}
                  <div className="rounded-2xl border border-border bg-surface p-6 shadow-elegant relative overflow-hidden">
                    <div className="absolute top-0 right-0 h-24 w-24 bg-primary/5 rounded-bl-full pointer-events-none" />
                    
                    <div className="flex justify-between items-start flex-wrap gap-4 mb-6">
                      <div>
                        <h3 className="text-2xl font-bold tracking-tight text-foreground">{selectedGroup.group_name}</h3>
                        <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1.5">
                          <User className="h-3 w-3" />
                          <span>Owner: {resolveMemberName(selectedGroup.created_by)}</span>
                        </div>
                      </div>
                      <button onClick={() => setOpenExpense(true)} className="h-9 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-sm hover:shadow">
                        <Plus className="h-3.5 w-3.5" /> Split a new bill
                      </button>
                    </div>

                    {summaryLoading ? (
                      <div className="h-12 flex items-center text-xs text-muted-foreground">Calculating split balances...</div>
                    ) : groupSummary ? (
                      <div className="grid sm:grid-cols-2 gap-6 border-t border-border/60 pt-5">
                        <div className="bg-muted/30 rounded-xl p-3 border border-border/30">
                          <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Total Tally Spent</div>
                          <div className="text-2xl font-extrabold mt-1 text-foreground">₹{groupSummary.total_spending.toLocaleString()}</div>
                        </div>
                        <div className="bg-muted/30 rounded-xl p-3 border border-border/30">
                          <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Your Balance</div>
                          {(() => {
                            const bal = groupSummary.balances[user?.uid || ""] || 0;
                            return (
                              <div className={`text-2xl font-extrabold mt-1 ${bal > 0 ? 'text-emerald-500' : bal < 0 ? 'text-rose-500' : 'text-foreground'}`}>
                                {bal > 0 ? '+' : ''}₹{bal.toLocaleString()}
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">Unable to fetch balance summaries.</p>
                    )}
                  </div>

                  {/* Transaction Feed (Google Pay Chat/Feed Style) */}
                  <div className="space-y-4">
                    <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground/80 px-1">Activity Feed</div>
                    <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
                      {groupDetails?.expenses && groupDetails.expenses.length > 0 ? (
                        [...groupDetails.expenses].reverse().map((exp: any) => {
                          const config = CATEGORY_MAP[exp.category as keyof typeof CATEGORY_MAP] || CATEGORY_MAP["Other"];
                          const IconComponent = config.icon;
                          
                          // Determine user's split status
                          const userSplit = exp.splits?.find((s: any) => s.member === user?.uid);
                          const isPayer = exp.paid_by === user?.uid;
                          
                          // Calculate progress
                          const totalSplits = exp.splits?.length || 0;
                          const paidSplits = exp.splits?.filter((s: any) => s.paid).length || 0;
                          const pctPaid = totalSplits > 0 ? Math.round((paidSplits / totalSplits) * 100) : 100;
                          const allSettled = paidSplits === totalSplits;

                          return (
                            <div key={exp.expense_id} className="rounded-2xl border border-border/60 bg-surface p-5 shadow-elegant hover:shadow-card transition-all duration-200">
                              <div className="flex items-start gap-4">
                                {/* Category Icon */}
                                <div className={`p-3 rounded-2xl border ${config.color} shrink-0`}>
                                  <IconComponent className="h-5 w-5" />
                                </div>

                                {/* Body */}
                                <div className="flex-1 min-w-0 space-y-1">
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <h4 className="font-semibold text-sm text-foreground truncate">{exp.description}</h4>
                                      <div className="flex items-center gap-1 shrink-0">
                                        <button
                                          type="button"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setEditingExpense(exp);
                                            setOpenExpense(true);
                                          }}
                                          title="Edit Bill Split"
                                          className="p-1 rounded hover:bg-muted text-muted-foreground/60 hover:text-foreground transition cursor-pointer"
                                        >
                                          <Pencil className="h-3.5 w-3.5" />
                                        </button>
                                        <button
                                          type="button"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteExpense(exp.expense_id);
                                          }}
                                          title="Delete Bill Split"
                                          className="p-1 rounded hover:bg-destructive/10 text-muted-foreground/60 hover:text-destructive transition cursor-pointer"
                                        >
                                          <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                      </div>
                                    </div>
                                    <div className="text-lg font-bold text-foreground font-mono">₹{exp.amount.toLocaleString()}</div>
                                  </div>
                                  
                                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                                    <div>
                                      Paid by <span className="font-semibold text-foreground/80">{resolveMemberName(exp.paid_by)}</span>
                                    </div>
                                    <div>{exp.date}</div>
                                  </div>

                                  {/* Progress bar */}
                                  <div className="space-y-1.5 pt-3">
                                    <div className="flex items-center justify-between text-[11px]">
                                      <span className="font-medium text-muted-foreground">
                                        {paidSplits} of {totalSplits} settled
                                      </span>
                                      <span className={`font-bold ${allSettled ? 'text-emerald-500' : 'text-primary'}`}>
                                        {pctPaid}%
                                      </span>
                                    </div>
                                    <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full transition-all duration-300 ${allSettled ? 'bg-emerald-500' : 'bg-primary'}`} 
                                        style={{ width: `${pctPaid}%` }} 
                                      />
                                    </div>
                                  </div>

                                  {/* Split detail list for creator/details */}
                                  {exp.splits && (
                                    <div className="mt-4 pt-3 border-t border-border/50 space-y-2">
                                      <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground/70">Split Breakdown</div>
                                      <div className="grid gap-2 sm:grid-cols-2">
                                        {exp.splits.map((s: any) => {
                                          const memberName = resolveMemberName(s.member);
                                          const isMemberPayer = s.member === exp.paid_by;
                                          return (
                                            <div key={s.member} className="flex items-center justify-between p-2 rounded-xl bg-muted/20 border border-border/20 text-xs">
                                              <span className="font-medium truncate max-w-[120px]">{memberName}</span>
                                              <div className="flex items-center gap-1.5 shrink-0">
                                                <span className="font-bold text-foreground/80">₹{s.amount}</span>
                                                {s.paid ? (
                                                  <span className="text-emerald-500 font-medium flex items-center gap-0.5"><Check className="h-3.5 w-3.5" /> Paid</span>
                                                ) : isPayer ? (
                                                  // Payer view: can Remind or Mark as Paid
                                                  <div className="flex items-center gap-1">
                                                    <button 
                                                      onClick={() => handleRemind(exp.expense_id, s.member)}
                                                      title="Send Notification Reminder"
                                                      className="p-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 transition"
                                                    >
                                                      <Bell className="h-3 w-3" />
                                                    </button>
                                                    <button 
                                                      onClick={() => handleMarkPaid(exp.expense_id, s.member)}
                                                      title="Mark as Paid"
                                                      className="px-1.5 py-0.5 rounded bg-emerald-500 text-white hover:bg-emerald-600 font-semibold text-[10px] transition"
                                                    >
                                                      Settle
                                                    </button>
                                                  </div>
                                                ) : (
                                                  <span className="text-amber-500 font-medium flex items-center gap-0.5"><Clock className="h-3 w-3" /> Unpaid</span>
                                                )}
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  )}

                                  {/* Settle button for this item */}
                                  {!isPayer && userSplit && !userSplit.paid && (
                                    <div className="pt-4 flex justify-end">
                                      <button 
                                        onClick={() => {
                                          playBeep(440, 0.05);
                                          handlePayExpenseShare(exp.expense_id);
                                        }}
                                        className="h-9 px-5 rounded-xl bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary-hover transition shadow-sm flex items-center gap-1.5 cursor-pointer"
                                      >
                                        <Check className="h-3.5 w-3.5" /> Settle Share (₹{userSplit.amount})
                                      </button>
                                    </div>
                                  )}

                                  {!isPayer && userSplit && userSplit.paid && (
                                    <div className="pt-3 flex justify-end items-center gap-1 text-xs text-emerald-500 font-bold">
                                      <CheckCircle2 className="h-4 w-4" /> You paid ₹{userSplit.amount}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-center text-xs text-muted-foreground/70 py-12 border border-dashed rounded-2xl bg-surface/50">
                          No bills split in this room yet. Tap "Split a new bill" below to start.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right side: Member directory and suggested settlements */}
                <div className="space-y-6">
                  {/* Suggested settlements */}
                  <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-elegant">
                    <h4 className="font-semibold text-sm text-foreground">Suggested Settlements</h4>
                    
                    {groupSummary && (
                      <div className="grid grid-cols-3 gap-2 p-3 bg-muted/20 border border-border/30 rounded-xl text-center text-[11px]">
                        <div>
                          <div className="text-[9px] text-muted-foreground font-semibold uppercase tracking-wider">Trip Total</div>
                          <div className="font-bold text-foreground mt-0.5">₹{(groupSummary.total_expenses ?? groupSummary.total_spending ?? 0).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-[9px] text-muted-foreground font-semibold uppercase tracking-wider">Members</div>
                          <div className="font-bold text-foreground mt-0.5">{groupSummary.member_count ?? groupSummary.members?.length ?? 0}</div>
                        </div>
                        <div>
                          <div className="text-[9px] text-muted-foreground font-semibold uppercase tracking-wider">Per Share</div>
                          <div className="font-bold text-foreground mt-0.5">₹{(groupSummary.per_person_share ?? 0).toLocaleString()}</div>
                        </div>
                      </div>
                    )}

                    <div className="space-y-2">
                      {groupSummary?.suggested_settlements.map((s, idx) => (
                        <div key={idx} className="rounded-xl border border-border/85 p-3.5 bg-muted/10 flex items-center justify-between text-xs transition hover:bg-muted/20">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5 font-medium">
                              <span className="font-bold text-foreground">{resolveMemberName(s.from)}</span>
                              <ArrowRight className="h-3 w-3 text-muted-foreground" />
                              <span className="font-bold text-foreground">{resolveMemberName(s.to)}</span>
                            </div>
                            <div className="text-[10px] text-muted-foreground">Settles remaining debts</div>
                          </div>
                          <span className="font-extrabold text-primary text-sm">₹{s.amount.toLocaleString()}</span>
                        </div>
                      ))}
                      {groupSummary?.suggested_settlements.length === 0 && (
                        <div className="text-center py-6">
                          <div className="inline-flex p-3 rounded-full bg-emerald-500/10 text-emerald-500 mb-2">
                            <CheckCircle2 className="h-6 w-6 animate-pulse" />
                          </div>
                          <p className="text-xs font-medium text-foreground">All settled up!</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">No roommate debts pending in this room.</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Member Directory */}
                  <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-elegant">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-sm text-foreground">Roommates ({selectedGroup.members.length})</h4>
                    </div>
                    
                    <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
                      {selectedGroup.members.map((m) => (
                        <div key={m} className="flex items-center gap-2 text-xs py-2 border-b border-border/40 last:border-0 truncate font-medium">
                          <div className="h-6 w-6 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-[10px]">
                            {resolveMemberName(m).slice(0, 2).toUpperCase()}
                          </div>
                          <span className="truncate flex-1">{resolveMemberName(m)}</span>
                          {m === selectedGroup.created_by && (
                            <span className="text-[9px] bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.5 rounded font-semibold shrink-0">Admin</span>
                          )}
                        </div>
                      ))}
                    </div>
                    
                    <form onSubmit={handleInvite} className="flex gap-2 border-t border-border/50 pt-3">
                      <input 
                        value={inviteEmail} 
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="Add member email or UID"
                        className="flex-1 h-9 rounded-lg bg-background border border-border/80 px-3 text-xs focus:outline-none focus:border-primary text-foreground placeholder:text-muted-foreground/60 transition"
                      />
                      <button 
                        type="submit"
                        disabled={inviteBusy || !inviteEmail.trim()}
                        className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-hover disabled:opacity-60 transition flex items-center justify-center shrink-0"
                      >
                        {inviteBusy ? "..." : "Add"}
                      </button>
                    </form>
                  </div>
                </div>

              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border/80 p-16 text-center bg-surface/50 shadow-sm flex flex-col items-center justify-center">
                <div className="p-4 bg-muted/50 text-muted-foreground rounded-full mb-4 animate-bounce">
                  <Users className="h-8 w-8" />
                </div>
                <h3 className="font-bold text-lg text-foreground">Select a split room</h3>
                <p className="text-xs text-muted-foreground/80 mt-1 max-w-sm">Create or select a room from the sidebar to divide flat utilities, rent, and dining bills with your roommates.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {openCreate && <CreateGroupDialog onClose={() => setOpenCreate(false)} onAdd={handleCreateGroup} />}
      {openExpense && selectedGroup && (
        <AddGroupExpenseDialog 
          onClose={() => {
            setOpenExpense(false);
            setEditingExpense(null);
          }} 
          onAdd={(payload) => {
            if (editingExpense) {
              handleEditExpense(editingExpense.expense_id, payload);
            } else {
              handleAddExpense(payload);
            }
          }}
          expenseToEdit={editingExpense}
          currentUid={user?.uid || ""} 
          members={selectedGroup.members} 
          resolveMemberName={resolveMemberName}
          groupId={selectedGroup.group_id}
        />
      )}


    </div>
  );
}

// Create Group Dialog Component
function CreateGroupDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (g: { group_name: string; members: string[] }) => void }) {
  const [name, setName] = useState("");
  const [emails, setEmails] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const membersList = emails.split(',').map(m => m.trim()).filter(Boolean);
    onAdd({ group_name: name, members: membersList });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">Create Split Room</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted/55 transition"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs font-semibold text-muted-foreground mb-1.5">Room Name</div>
          <input 
            value={name} 
            onChange={(e) => setName(e.target.value)} 
            required 
            placeholder="e.g. Flat 304 Utilities or Dinner Splitting" 
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" 
          />
        </label>

        <label className="block">
          <div className="text-xs font-semibold text-muted-foreground mb-1">Invite Members (UIDs / Emails)</div>
          <p className="text-[10px] text-muted-foreground/70 mb-1.5">Enter registered emails or user IDs, comma separated.</p>
          <textarea 
            value={emails} 
            onChange={(e) => setEmails(e.target.value)} 
            placeholder="aman@example.com, bob@example.com" 
            className="w-full h-20 rounded-xl bg-surface border border-border p-3 text-sm focus:outline-none focus:border-primary text-foreground resize-none" 
          />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover transition shadow-md">Create Room</button>
      </form>
    </div>
  );
}

// Add Group Expense Dialog Component (Supporting Equally & Unequally custom splits)
function AddGroupExpenseDialog({ 
  onClose, 
  onAdd, 
  expenseToEdit,
  currentUid, 
  members,
  resolveMemberName,
  groupId
}: { 
  onClose: () => void; 
  onAdd: (e: any) => void; 
  expenseToEdit?: any;
  currentUid: string; 
  members: string[];
  resolveMemberName: (uid: string) => string;
  groupId: string;
}) {
  const [description, setDescription] = useState(expenseToEdit?.description || "");
  const [amount, setAmount] = useState(expenseToEdit?.amount?.toString() || "");
  const [category, setCategory] = useState(expenseToEdit?.category || "Other");
  const [paidBy, setPaidBy] = useState(expenseToEdit?.paid_by || currentUid);
  
  // Splitting mode: "equal" or "custom"
  const [splitType, setSplitType] = useState<"equal" | "custom">(expenseToEdit?.split_type || "equal");

  const [aiInput, setAiInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiWarning, setShowAiWarning] = useState(false);

  const handleAiParse = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!aiInput.trim()) return;
    try {
      setAiLoading(true);
      setShowAiWarning(false);
      const res = await api.post(`/api/groups/${groupId}/parse-expense`, { query: aiInput.trim() });
      if (res) {
        if (res.description) setDescription(res.description);
        if (res.amount) setAmount(res.amount.toString());
        if (res.category) setCategory(res.category);
        if (res.payer) setPaidBy(res.payer);
        if (res.participants && res.participants.length > 0) {
          const newChecked: Record<string, boolean> = {};
          members.forEach(m => {
            newChecked[m] = res.participants.includes(m);
          });
          setCheckedMembers(newChecked);
        }
        setShowAiWarning(res.needs_confirmation || false);
        playSuccessSound();
      }
    } catch (err: any) {
      alert(err.message || "Failed to parse expense using AI.");
    } finally {
      setAiLoading(false);
    }
  };
  
  // Checklist states: maps member uid to whether they are checked
  const [checkedMembers, setCheckedMembers] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    if (expenseToEdit) {
      members.forEach(m => {
        init[m] = expenseToEdit.splits?.some((s: any) => s.member === m) || expenseToEdit.participants?.includes(m) || false;
      });
    } else {
      members.forEach(m => { init[m] = true; });
    }
    return init;
  });

  // Custom Split Amounts state: maps member uid to their manually specified split amount
  const [customShares, setCustomShares] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    if (expenseToEdit && expenseToEdit.split_type === "custom") {
      expenseToEdit.splits?.forEach((s: any) => {
        init[s.member] = s.amount?.toString() || "0";
      });
    }
    return init;
  });

  // Auto initialize custom shares when changing split type
  useEffect(() => {
    if (splitType === "custom" && Number(amount) > 0 && Object.keys(customShares).length === 0) {
      const activeCount = Object.values(checkedMembers).filter(Boolean).length;
      if (activeCount > 0) {
        const equalShare = (Number(amount) / activeCount).toFixed(2);
        const newShares: Record<string, string> = {};
        members.forEach(m => {
          if (checkedMembers[m]) {
            newShares[m] = equalShare;
          } else {
            newShares[m] = "0";
          }
        });
        setCustomShares(newShares);
      }
    }
  }, [splitType, amount]);

  // Calculate sum of custom shares
  const sumCustomShares = () => {
    let sum = 0;
    members.forEach(m => {
      if (checkedMembers[m]) {
        sum += Number(customShares[m] || 0);
      }
    });
    return Number(sum.toFixed(2));
  };

  const handleCheckboxChange = (m: string) => {
    setCheckedMembers(prev => {
      const updated = { ...prev, [m]: !prev[m] };
      // Also adjust custom shares if in custom mode
      if (splitType === "custom") {
        setCustomShares(shares => ({
          ...shares,
          [m]: updated[m] ? (Number(amount) / Object.values(updated).filter(Boolean).length).toFixed(2) : "0"
        }));
      }
      return updated;
    });
  };

  const handleShareAmountChange = (m: string, value: string) => {
    setCustomShares(prev => ({ ...prev, [m]: value }));
  };

  const distributeRemainderEqually = () => {
    const numAmt = Number(amount);
    if (isNaN(numAmt) || numAmt <= 0) return;
    
    const activeMembers = members.filter(m => checkedMembers[m]);
    if (activeMembers.length === 0) return;
    
    const equalShare = (numAmt / activeMembers.length).toFixed(2);
    const newShares: Record<string, string> = {};
    
    // Equal distribution
    activeMembers.forEach(m => {
      newShares[m] = equalShare;
    });
    
    // Handle rounding remainder
    const sum = Number(equalShare) * activeMembers.length;
    const diff = Number((numAmt - sum).toFixed(2));
    if (diff !== 0 && activeMembers.length > 0) {
      const lastMem = activeMembers[activeMembers.length - 1];
      newShares[lastMem] = (Number(newShares[lastMem]) + diff).toFixed(2);
    }
    
    setCustomShares(newShares);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const numAmt = Number(amount);
    const splitWith = members.filter(m => checkedMembers[m]);

    if (splitWith.length === 0) {
      alert("Please select at least one member to split with.");
      return;
    }

    if (splitType === "equal") {
      onAdd({
        amount: numAmt,
        description,
        category,
        paid_by: paidBy,
        split_type: "equal",
        split_with: splitWith
      });
    } else {
      // Validate sum matches amount
      const sharesSum = sumCustomShares();
      if (Math.abs(sharesSum - numAmt) > 0.05) {
        alert(`Sum of shares (₹${sharesSum}) does not match the total amount (₹${numAmt}). Please adjust.`);
        return;
      }

      const splitsPayload = splitWith.map(m => ({
        member: m,
        amount: Number(customShares[m] || 0)
      }));

      onAdd({
        amount: numAmt,
        description,
        category,
        paid_by: paidBy,
        split_type: "custom",
        splits: splitsPayload
      });
    }
  };

  const customSum = sumCustomShares();
  const amtNum = Number(amount) || 0;
  const isCustomBalanced = splitType === "equal" || Math.abs(customSum - amtNum) <= 0.05;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-lg rounded-2xl border border-border bg-background p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">{expenseToEdit ? "Edit split bill" : "Post split bill"}</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted/50 transition"><X className="h-4 w-4" /></button>
        </div>

        {/* Quick Add with AI */}
        <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 space-y-2.5 relative overflow-hidden">
          <div className="flex items-center gap-1.5 text-xs font-bold text-primary uppercase tracking-wider">
            <Sparkles className="h-4 w-4" />
            <span>AI Quick Fill</span>
          </div>
          <div className="flex gap-2">
            <input 
              value={aiInput} 
              onChange={(e) => setAiInput(e.target.value)} 
              placeholder="e.g. Sai paid 1000 for petrol with Om" 
              className="flex-1 h-9 rounded-lg bg-background border border-border/80 px-3 text-xs focus:outline-none focus:border-primary text-foreground placeholder:text-muted-foreground/60 transition"
            />
            <button 
              type="button" 
              disabled={aiLoading || !aiInput.trim()}
              onClick={handleAiParse}
              className="h-9 px-4 rounded-lg bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary-hover disabled:opacity-60 transition flex items-center justify-center shrink-0"
            >
              {aiLoading ? (
                <div className="h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                "Fill Form"
              )}
            </button>
          </div>
          {showAiWarning && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-2.5 text-[10px] text-amber-600 flex items-start gap-1.5 font-medium animate-pulse">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>We parsed this expense with lower confidence or missing values. Please review the populated fields below!</span>
            </div>
          )}
          <p className="text-[10px] text-muted-foreground/75">
            Describe the expense. We will fill the payer, description, amount, category, and split checklist.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Description</div>
            <input 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
              required 
              placeholder="e.g. WiFi Bill or Dinner" 
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" 
            />
          </label>

          <label className="block">
            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Amount (₹)</div>
            <input 
              value={amount} 
              onChange={(e) => setAmount(e.target.value)} 
              type="number" 
              required 
              placeholder="300" 
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" 
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Category</div>
            <select 
              value={category} 
              onChange={(e) => setCategory(e.target.value)}
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
            >
              <option value="Food">Food & Drink</option>
              <option value="Utilities">Rent & Utilities</option>
              <option value="Travel">Travel & Transport</option>
              <option value="Shopping">Shopping</option>
              <option value="Entertainment">Entertainment</option>
              <option value="Other">Other</option>
            </select>
          </label>

          <label className="block">
            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Paid By</div>
            <select 
              value={paidBy} 
              onChange={(e) => setPaidBy(e.target.value)}
              className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
            >
              {members.map(m => (
                <option key={m} value={m}>{resolveMemberName(m)}</option>
              ))}
            </select>
          </label>
        </div>

        {/* Tab Selector for Split Method */}
        <div className="space-y-1.5">
          <div className="text-xs font-semibold text-muted-foreground">Split Method</div>
          <div className="grid grid-cols-2 p-1 bg-muted/40 rounded-xl border border-border/40">
            <button 
              type="button" 
              onClick={() => setSplitType("equal")}
              className={`py-1.5 rounded-lg text-xs font-semibold transition ${splitType === "equal" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground"}`}
            >
              Split Equally
            </button>
            <button 
              type="button" 
              onClick={() => setSplitType("custom")}
              className={`py-1.5 rounded-lg text-xs font-semibold transition ${splitType === "custom" ? "bg-background shadow-sm text-foreground" : "text-muted-foreground"}`}
            >
              Split Custom (Unequally)
            </button>
          </div>
        </div>

        {/* Member breakdown checklist */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-muted-foreground">Split With</div>
            {splitType === "custom" && (
              <button 
                type="button" 
                onClick={distributeRemainderEqually}
                className="text-[10px] font-bold text-primary hover:underline"
              >
                Distribute Remainder Equally
              </button>
            )}
          </div>
          <div className="space-y-2 border border-border/50 rounded-xl p-3 bg-surface/50 max-h-[220px] overflow-y-auto">
            {members.map(m => {
              const name = resolveMemberName(m);
              const isChecked = checkedMembers[m] || false;
              
              return (
                <div key={m} className="flex items-center justify-between text-xs py-1 border-b border-border/30 last:border-0 last:pb-0">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input 
                      type="checkbox" 
                      checked={isChecked}
                      onChange={() => handleCheckboxChange(m)}
                      className="rounded border-border text-primary focus:ring-primary h-4.5 w-4.5"
                    />
                    <span className="font-medium text-foreground">{name}</span>
                  </label>
                  
                  {isChecked && (
                    <div>
                      {splitType === "equal" ? (
                        <span className="font-bold text-muted-foreground/90 bg-muted/60 px-2 py-0.5 rounded-md">
                          ₹{(Number(amount || 0) / Object.values(checkedMembers).filter(Boolean).length || 0).toFixed(2)}
                        </span>
                      ) : (
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-muted-foreground">₹</span>
                          <input 
                            type="number"
                            value={customShares[m] || ""}
                            onChange={(e) => handleShareAmountChange(m, e.target.value)}
                            placeholder="0"
                            className="w-16 h-7 rounded border border-border px-2 text-xs text-right focus:outline-none focus:border-primary bg-background text-foreground"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Custom split verification warning */}
        {splitType === "custom" && (
          <div className={`p-3 rounded-xl border text-xs flex justify-between items-center ${
            isCustomBalanced ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
          }`}>
            <span className="font-medium">Total Assigned: ₹{customSum} of ₹{amtNum}</span>
            <span className="font-bold text-[10px] uppercase">
              {isCustomBalanced ? "Balanced ✓" : `₹${(amtNum - customSum).toFixed(2)} remaining`}
            </span>
          </div>
        )}

        <button 
          type="submit" 
          disabled={splitType === "custom" && !isCustomBalanced}
          className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover transition shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {expenseToEdit ? "Save Changes" : "Post Bill Split"}
        </button>
      </form>
    </div>
  );
}


