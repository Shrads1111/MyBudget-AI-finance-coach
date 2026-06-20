import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, Users, Send, DollarSign, X, AlertCircle } from "lucide-react";

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
  members: string[];
  balances: Record<string, number>;
  suggested_settlements: Array<{
    from: string;
    to: string;
    amount: number;
  }>;
};

function GroupsPage() {
  const { user, token } = useAuth();
  
  // Data States
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<GroupItem | null>(null);
  const [groupSummary, setGroupSummary] = useState<GroupSummary | null>(null);
  const [groupDetails, setGroupDetails] = useState<any | null>(null);
  
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
        member: inviteEmail
      });
      setInviteEmail("");
      fetchSelectedGroupData();
    } catch (e: any) {
      alert("Failed to invite member: " + e.message);
    } finally {
      setInviteBusy(false);
    }
  };

  // Add Group Expense
  const handleAddExpense = async (payload: { amount: number; description: string; paid_by: string }) => {
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Group Bills</h1>
          <p className="text-sm text-muted-foreground">Split internet, rent, and canteens with flatmates. Equal contributions mapped.</p>
        </div>
        
        <button onClick={() => setOpenCreate(true)} className="h-10 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-sm font-medium inline-flex items-center gap-2">
          <Plus className="h-4 w-4" /> Create group
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
          Syncing share rooms...
        </div>
      ) : (
        <div className="grid lg:grid-cols-[280px_1fr] gap-6">
          {/* Groups List */}
          <div className="space-y-3">
            <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">Your Rooms</div>
            <div className="space-y-2">
              {groups.map((g) => {
                const isSelected = selectedGroup?.group_id === g.group_id;
                return (
                  <div 
                    key={g.group_id} 
                    onClick={() => setSelectedGroup(g)}
                    className={`rounded-xl p-4 cursor-pointer transition flex items-center gap-3 border ${
                      isSelected ? "border-primary bg-primary/5 text-foreground font-semibold" : "border-border bg-surface hover:bg-surface-hover text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Users className="h-4 w-4 text-primary" />
                    <span className="text-sm truncate">{g.group_name}</span>
                  </div>
                );
              })}
              {groups.length === 0 && (
                <div className="text-center text-xs text-muted-foreground py-6">No share rooms configured.</div>
              )}
            </div>
          </div>

          {/* Group details & settlement page */}
          <div>
            {selectedGroup ? (
              <div className="grid lg:grid-cols-[1fr_320px] gap-6">
                
                {/* Left side: balances & suggested steps */}
                <div className="space-y-6">
                  {/* Summary card */}
                  <div className="rounded-2xl border border-border bg-surface p-6">
                    <div className="flex justify-between items-center flex-wrap gap-2 mb-4">
                      <div>
                        <h3 className="text-xl font-bold">{selectedGroup.group_name}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Created by: {selectedGroup.created_by.slice(0, 12)}...</p>
                      </div>
                      <button onClick={() => setOpenExpense(true)} className="h-9 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary-hover text-xs font-semibold inline-flex items-center gap-1.5">
                        <DollarSign className="h-3.5 w-3.5" /> Post split bill
                      </button>
                    </div>

                    {summaryLoading ? (
                      <p className="text-xs text-muted-foreground">Calculating split balances...</p>
                    ) : groupSummary ? (
                      <div className="grid sm:grid-cols-2 gap-4 border-t border-border pt-4">
                        <div>
                          <div className="text-xs text-muted-foreground">Total Group Tally Spending</div>
                          <div className="text-2xl font-bold mt-1">₹{groupSummary.total_spending.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Your Balance</div>
                          {(() => {
                            const bal = groupSummary.balances[user?.uid || ""] || 0;
                            return (
                              <div className={`text-2xl font-bold mt-1 ${bal > 0 ? 'text-emerald-500' : bal < 0 ? 'text-rose-500' : 'text-foreground'}`}>
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

                  {/* Roommate balances */}
                  <div className="rounded-2xl border border-border bg-surface p-6 space-y-4">
                    <h4 className="font-semibold text-sm">Roommate Balances</h4>
                    <div className="divide-y divide-border">
                      {groupSummary && Object.entries(groupSummary.balances).map(([mem, bal]) => (
                        <div key={mem} className="flex justify-between items-center py-3 first:pt-0 last:pb-0">
                          <span className="text-xs font-medium">{mem === user?.uid ? "You" : mem.slice(0, 15)}</span>
                          <span className={`text-xs font-bold ${bal > 0 ? 'text-emerald-500' : bal < 0 ? 'text-rose-500' : 'text-foreground'}`}>
                            {bal > 0 ? 'Owed' : bal < 0 ? 'Owes' : 'Settled'} {bal !== 0 ? `₹${Math.abs(bal).toLocaleString()}` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Suggested settlements */}
                  <div className="rounded-2xl border border-border bg-surface p-6 space-y-4">
                    <h4 className="font-semibold text-sm">Suggested Settlements</h4>
                    <div className="space-y-2">
                      {groupSummary?.suggested_settlements.map((s, idx) => (
                        <div key={idx} className="rounded-xl border border-border p-3 bg-background flex items-center justify-between text-xs">
                          <span>
                            <b>{s.from === user?.uid ? "You" : s.from.slice(0, 10)}</b> owe <b>{s.to === user?.uid ? "You" : s.to.slice(0, 10)}</b>
                          </span>
                          <span className="font-bold text-primary">₹{s.amount.toLocaleString()}</span>
                        </div>
                      ))}
                      {groupSummary?.suggested_settlements.length === 0 && (
                        <p className="text-xs text-muted-foreground text-center py-4">All roommate accounts are fully settled!</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right side: Member directory and transaction history */}
                <div className="space-y-6">
                  {/* Invite/Members */}
                  <div className="rounded-2xl border border-border bg-surface p-5 space-y-4">
                    <h4 className="font-semibold text-sm">Members Directory</h4>
                    <div className="space-y-2 max-h-[140px] overflow-y-auto">
                      {selectedGroup.members.map((m) => (
                        <div key={m} className="text-xs py-1 border-b border-border last:border-0 truncate font-medium">
                          {m === user?.uid ? "You (Owner)" : m}
                        </div>
                      ))}
                    </div>
                    
                    <form onSubmit={handleInvite} className="flex gap-2 border-t border-border pt-3">
                      <input 
                        value={inviteEmail} 
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="Add member email or UID"
                        className="flex-1 h-9 rounded-lg bg-background border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      />
                      <button 
                        type="submit"
                        disabled={inviteBusy || !inviteEmail.trim()}
                        className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary-hover disabled:opacity-60 flex items-center justify-center"
                      >
                        Add
                      </button>
                    </form>
                  </div>

                  {/* Transaction log */}
                  <div className="rounded-2xl border border-border bg-surface p-5 space-y-4">
                    <h4 className="font-semibold text-sm">Group Spend Feed</h4>
                    <div className="space-y-3 max-h-[220px] overflow-y-auto">
                      {groupDetails?.expenses.map((exp: any) => (
                        <div key={exp.expense_id} className="rounded-xl border border-border p-3 bg-background flex justify-between items-start text-xs">
                          <div>
                            <div className="font-semibold">{exp.description}</div>
                            <div className="text-[10px] text-muted-foreground mt-0.5">Paid by: {exp.paid_by === user?.uid ? "You" : exp.paid_by.slice(0, 10)}</div>
                          </div>
                          <div className="font-bold text-foreground">₹{exp.amount}</div>
                        </div>
                      ))}
                      {(!groupDetails?.expenses || groupDetails.expenses.length === 0) && (
                        <p className="text-xs text-muted-foreground text-center py-6">No bills split in this room yet.</p>
                      )}
                    </div>
                  </div>
                </div>

              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted-foreground bg-surface">
                Create or select a share room from the sidebar to split expenses.
              </div>
            )}
          </div>
        </div>
      )}

      {openCreate && <CreateGroupDialog onClose={() => setOpenCreate(false)} onAdd={handleCreateGroup} />}
      {openExpense && selectedGroup && <AddGroupExpenseDialog onClose={() => setOpenExpense(false)} onAdd={handleAddExpense} currentUid={user?.uid || ""} members={selectedGroup.members} />}
    </div>
  );
}

function CreateGroupDialog({ onClose, onAdd }: { onClose: () => void; onAdd: (g: { group_name: string; members: string[] }) => void }) {
  const [name, setName] = useState("");
  const [emails, setEmails] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const membersList = emails.split(',').map(m => m.trim()).filter(Boolean);
    onAdd({ group_name: name, members: membersList });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Create bill split room</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Room Name</div>
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Flat 304 Utilities" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Invite member UIDs / Emails (comma separated)</div>
          <textarea value={emails} onChange={(e) => setEmails(e.target.value)} placeholder="aman@student.edu, riya@student.edu" className="w-full h-20 rounded-xl bg-surface border border-border p-3 text-sm focus:outline-none focus:border-primary text-foreground resize-none" />
        </label>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Create</button>
      </form>
    </div>
  );
}

function AddGroupExpenseDialog({ onClose, onAdd, currentUid, members }: { onClose: () => void; onAdd: (e: { amount: number; description: string; paid_by: string }) => void; currentUid: string; members: string[] }) {
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState(currentUid);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({ amount: Number(amount), description, paid_by: paidBy });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-border bg-background p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Post group bill</h2>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-surface"><X className="h-4 w-4" /></button>
        </div>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Description</div>
          <input value={description} onChange={(e) => setDescription(e.target.value)} required placeholder="WiFi or Electricity" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <label className="block">
          <div className="text-xs text-muted-foreground mb-1">Amount (₹)</div>
          <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" required placeholder="300" className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground" />
        </label>

        <div>
          <div className="text-xs text-muted-foreground mb-1">Paid By</div>
          <select 
            value={paidBy} 
            onChange={(e) => setPaidBy(e.target.value)}
            className="w-full h-10 rounded-xl bg-surface border border-border px-3 text-sm focus:outline-none focus:border-primary text-foreground"
          >
            {members.map(m => (
              <option key={m} value={m}>{m === currentUid ? "You" : m.slice(0, 15)}</option>
            ))}
          </select>
        </div>

        <button type="submit" className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover">Split Bill Equally</button>
      </form>
    </div>
  );
}
