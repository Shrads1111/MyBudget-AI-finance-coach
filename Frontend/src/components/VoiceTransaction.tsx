/**
 * VoiceTransaction.tsx
 *
 * Refactored voice transaction component.
 * Exports: VoiceMicButton
 *
 * Flow:
 *   idle → listening (Web Speech API, continuous) → stop → parsing (POST /api/voice/parse)
 *   → confirm (multiple editable transactions, checkboxes) → onConfirm(payloads) → idle
 *   If parsing fails: transition to edit_transcript (manually edit speech transcript and retry analysis)
 *
 * Zero changes to existing transaction logic.
 * Parent only provides onConfirm(payloads) callback.
 */

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic,
  X,
  Check,
  AlertCircle,
  Loader2,
  Edit3,
  Volume2,
  Plus,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

type VoiceParsedTx = {
  amount?: number | null;
  type: "expense" | "income";
  category: string;
  date: string;
  note: string;
  merchant?: string | null;
  friend_name?: string | null;
  friend_owe_amount?: number | null;
};

type VoiceParsed = {
  transactions: VoiceParsedTx[];
  clarification_needed?: boolean;
  clarification_message?: string | null;
};

type TransactionPayload = {
  amount: number;
  category: string;
  description: string;
  date: string;
  type?: string;
  account_id?: string;
};

type VoiceMicButtonProps = {
  /** Called when user confirms the parsed transactions. Parent handles save + refresh. */
  onConfirm: (payloads: TransactionPayload[]) => Promise<void>;
};

type MicState = "idle" | "listening" | "parsing" | "edit_transcript" | "confirm" | "error";

type EditableTx = {
  id: string;
  amount: string;
  category: string;
  date: string;
  note: string;
  type: "expense" | "income";
  friend_name?: string;
  friend_owe_amount?: string;
  selected: boolean;
  account_id?: string;
};

// ─── Exported Component ───────────────────────────────────────────────────────

export function VoiceMicButton({ onConfirm }: VoiceMicButtonProps) {
  const [state, setState] = useState<MicState>("idle");
  const [transcript, setTranscript] = useState("");
  const [parsed, setParsed] = useState<VoiceParsed | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const recognitionRef = useRef<any>(null);
  const transcriptRef = useRef("");

  const isSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const reset = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {}
      recognitionRef.current = null;
    }
    setState("idle");
    setTranscript("");
    transcriptRef.current = "";
    setParsed(null);
    setErrorMsg("");
  };

  const showError = (msg: string) => {
    setErrorMsg(msg);
    setState("error");
  };

  const handleMicClick = () => {
    if (!isSupported) {
      showError(
        "Voice input is not supported in this browser. Please use Chrome or Edge."
      );
      return;
    }
    if (state === "listening") {
      handleStop();
    } else {
      startListening();
    }
  };

  const startListening = () => {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    const recognition = new SR();
    recognition.lang = "en-IN"; // handles English, Hindi, Hinglish
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setState("listening");
      setTranscript("");
      transcriptRef.current = "";
    };

    recognition.onresult = (event: any) => {
      let fullTranscript = "";
      for (let i = 0; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript + " ";
      }
      const trimmed = fullTranscript.trim();
      setTranscript(trimmed);
      transcriptRef.current = trimmed;
    };

    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed" || event.error === "permission-denied") {
        showError("Microphone access is required for voice transactions.");
      } else if (event.error === "no-speech") {
        // Do not fail immediately on no-speech in continuous mode
      } else if (event.error === "network") {
        showError("Network error during voice recognition. Please try again.");
      } else {
        showError("Voice recognition error. Please try again.");
      }
    };

    recognition.onend = () => {
      // If still in listening state and browser naturally ends, analyze transcript if present
      setState((prev) => {
        if (prev === "listening") {
          const currentTranscript = transcriptRef.current;
          if (currentTranscript.trim()) {
            triggerParse(currentTranscript);
            return "parsing";
          }
          return "idle";
        }
        return prev;
      });
    };

    try {
      recognition.start();
    } catch {
      showError("Could not start microphone. Please try again.");
    }
  };

  const handleStop = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    const currentTranscript = transcriptRef.current;
    if (currentTranscript.trim()) {
      triggerParse(currentTranscript);
    } else {
      reset();
    }
  };

  const triggerParse = async (textToParse: string) => {
    setState("parsing");
    try {
      const result: VoiceParsed = await api.post("/api/voice/parse", {
        transcript: textToParse,
      });

      if (result.clarification_needed || !result.transactions || result.transactions.length === 0) {
        setErrorMsg(result.clarification_message || "AI was unable to extract any transactions.");
        setState("edit_transcript");
      } else {
        setParsed(result);
        setState("confirm");
      }
    } catch {
      setErrorMsg("Failed to contact the server. Please try again.");
      setState("edit_transcript");
    }
  };

  const handleConfirm = async (payloads: TransactionPayload[]) => {
    await onConfirm(payloads);
    reset();
  };

  const handleReAnalyze = (newTranscript: string) => {
    setTranscript(newTranscript);
    triggerParse(newTranscript);
  };

  return (
    <>
      {/* ── Mic trigger button ── */}
      <button
        type="button"
        onClick={handleMicClick}
        title={
          isSupported
            ? "Add transaction by voice"
            : "Voice input not supported in this browser"
        }
        aria-label="Voice transaction"
        className={`h-10 w-10 rounded-xl border flex items-center justify-center transition-all duration-150
          ${
            state === "listening"
              ? "bg-rose-500 border-rose-500 text-white scale-110 animate-pulse"
              : "bg-surface border-border text-muted-foreground hover:bg-surface-hover hover:text-foreground"
          }`}
      >
        <Mic className="h-4 w-4" />
      </button>

      {/* ── Error toast ── */}
      <AnimatePresence>
        {state === "error" && (
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.95 }}
            className="fixed top-5 right-5 z-[200] max-w-sm rounded-2xl border border-destructive/30 bg-card shadow-xl p-4 flex items-start gap-3"
          >
            <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-destructive">
                Voice Error
              </div>
              <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                {errorMsg}
              </div>
            </div>
            <button
              onClick={reset}
              className="text-muted-foreground hover:text-foreground flex-shrink-0"
            >
              <X className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Listening overlay ── */}
      <AnimatePresence>
        {state === "listening" && (
          <VoiceListeningOverlay
            onCancel={reset}
            onStop={handleStop}
            transcript={transcript}
          />
        )}
      </AnimatePresence>

      {/* ── Parsing overlay ── */}
      <AnimatePresence>
        {state === "parsing" && (
          <VoiceParsingOverlay transcript={transcript} onCancel={reset} />
        )}
      </AnimatePresence>

      {/* ── Edit Transcript modal ── */}
      <AnimatePresence>
        {state === "edit_transcript" && (
          <VoiceEditTranscriptModal
            transcript={transcript}
            errorMsg={errorMsg}
            onAnalyze={handleReAnalyze}
            onCancel={reset}
          />
        )}
      </AnimatePresence>

      {/* ── Confirmation modal ── */}
      <AnimatePresence>
        {state === "confirm" && parsed && (
          <VoiceConfirmModal
            parsed={parsed}
            transcript={transcript}
            onConfirm={handleConfirm}
            onCancel={reset}
            onEditTranscript={() => setState("edit_transcript")}
          />
        )}
      </AnimatePresence>
    </>
  );
}

// ─── Listening Overlay ────────────────────────────────────────────────────────

function VoiceListeningOverlay({
  onCancel,
  onStop,
  transcript,
}: {
  onCancel: () => void;
  onStop: () => void;
  transcript: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-sm rounded-3xl bg-card border border-border p-8 flex flex-col items-center gap-6 shadow-2xl"
      >
        {/* Waveform */}
        <div className="flex items-end gap-1 h-10">
          {[0, 1, 2, 3, 4, 3, 2, 1, 0].map((base, i) => (
            <motion.div
              key={i}
              className="w-1.5 bg-primary rounded-full"
              animate={{
                height: [
                  `${8 + base * 4}px`,
                  `${24 + base * 4}px`,
                  `${8 + base * 4}px`,
                ],
              }}
              transition={{
                duration: 0.9,
                repeat: Infinity,
                delay: i * 0.08,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>

        {/* Pulsing mic */}
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="h-16 w-16 rounded-full bg-rose-500/15 border-2 border-rose-500 flex items-center justify-center"
        >
          <Mic className="h-7 w-7 text-rose-500" />
        </motion.div>

        <div className="text-center space-y-1 w-full">
          <div className="text-base font-semibold">Listening…</div>
          <div className="text-xs text-muted-foreground text-center">
            Speak freely. Tap Stop when finished.
          </div>
          <div className="text-[10px] text-muted-foreground italic">
            Supports multi-transactions, Hindi/English mix
          </div>
        </div>

        {/* Live Transcript bubble */}
        <div className="w-full min-h-[60px] max-h-[120px] overflow-y-auto rounded-2xl bg-surface border border-border px-4 py-3 text-xs italic text-foreground/85 text-center leading-relaxed">
          {transcript ? `"${transcript}"` : "Say something (e.g. spent 200 on food and received 1000)"}
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 w-full">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 h-10 rounded-xl border border-border bg-surface hover:bg-surface-hover text-xs font-medium transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex-1 h-10 rounded-xl bg-rose-500 text-white text-xs font-semibold hover:bg-rose-600 transition inline-flex items-center justify-center gap-1.5"
          >
            <Check className="h-3.5 w-3.5" /> Stop &amp; Analyze
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Parsing Overlay ──────────────────────────────────────────────────────────

function VoiceParsingOverlay({
  transcript,
  onCancel,
}: {
  transcript: string;
  onCancel: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-xs rounded-3xl bg-card border border-border p-8 flex flex-col items-center gap-5 shadow-2xl"
      >
        <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
          <Volume2 className="h-6 w-6 text-primary" />
        </div>

        <div className="w-full rounded-2xl bg-surface border border-border px-4 py-3 text-xs text-center italic text-foreground/80 max-h-[100px] overflow-y-auto">
          "{transcript}"
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Analyzing with Gemini AI…
        </div>

        <button
          type="button"
          onClick={onCancel}
          className="text-xs text-muted-foreground hover:text-foreground transition"
        >
          Cancel
        </button>
      </motion.div>
    </motion.div>
  );
}

// ─── Edit Transcript Modal ──────────────────────────────────────────────────

function VoiceEditTranscriptModal({
  transcript,
  errorMsg,
  onAnalyze,
  onCancel,
}: {
  transcript: string;
  errorMsg: string;
  onAnalyze: (newTranscript: string) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(transcript);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.92, opacity: 0, y: 10 }}
        className="w-full max-w-md rounded-3xl bg-card border border-border shadow-2xl overflow-hidden p-6 space-y-4"
      >
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <div className="text-sm font-semibold">Edit Voice Transcript</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">
              Review and edit the spoken text to run AI analysis again.
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 rounded-lg hover:bg-surface text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {errorMsg && (
          <div className="rounded-xl border border-warning/20 bg-warning/5 px-3 py-2.5 text-xs text-warning flex items-start gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-[11px] leading-relaxed">
              <span className="font-semibold">Notice:</span> {errorMsg}
            </div>
          </div>
        )}

        <div>
          <label className="text-[11px] text-muted-foreground block mb-1">
            Speech Transcript
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full rounded-xl bg-surface border border-border p-3 text-xs focus:outline-none focus:border-primary text-foreground resize-none"
            placeholder="Describe your transactions (e.g. spent 100 on books yesterday)"
          />
        </div>

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 h-11 rounded-xl border border-border bg-surface hover:bg-surface-hover text-sm font-medium transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onAnalyze(text)}
            disabled={!text.trim()}
            className="flex-1 h-11 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-hover disabled:opacity-60 transition inline-flex items-center justify-center gap-2"
          >
            <Sparkles className="h-4 w-4" /> Analyze with AI
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Confirmation Modal ───────────────────────────────────────────────────────

function VoiceConfirmModal({
  parsed,
  transcript,
  onConfirm,
  onCancel,
  onEditTranscript,
}: {
  parsed: VoiceParsed;
  transcript: string;
  onConfirm: (payloads: TransactionPayload[]) => Promise<void>;
  onCancel: () => void;
  onEditTranscript: () => void;
}) {
  const [txList, setTxList] = useState<EditableTx[]>(() => {
    return (parsed.transactions || []).map((tx, idx) => ({
      id: `tx-${idx}-${Date.now()}`,
      amount: tx.amount != null ? String(tx.amount) : "",
      category: tx.category || "Others",
      date: tx.date || new Date().toISOString().slice(0, 10),
      note: tx.note || "",
      type: tx.type || "expense",
      friend_name: tx.friend_name || "",
      friend_owe_amount: tx.friend_owe_amount != null ? String(tx.friend_owe_amount) : "",
      selected: true,
      account_id: "",
    }));
  });

  const [categories, setCategories] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<Array<{ account_id: string; name: string }>>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/api/categories")
      .then((res: any) => {
        const list: string[] = Array.isArray(res) ? res : [];
        setCategories(list);
      })
      .catch(() => {
        setCategories([
          "Food", "Travel", "Shopping", "Bills", "Health",
          "Entertainment", "Education", "Investment", "Others",
          "Salary", "Freelancing", "Refund", "Interest", "Bonus", "Other Income"
        ]);
      });

    api
      .get("/api/accounts")
      .then((res: any) => {
        setAccounts(res || []);
      })
      .catch((e) => {
        console.error("Failed to load accounts in voice confirmation modal:", e);
      });
  }, []);

  const updateField = (id: string, field: keyof EditableTx, value: any) => {
    setTxList((prev) =>
      prev.map((tx) => {
        if (tx.id === id) {
          return { ...tx, [field]: value };
        }
        return tx;
      })
    );
  };

  const deleteTx = (id: string) => {
    setTxList((prev) => prev.filter((tx) => tx.id !== id));
  };

  const addTx = () => {
    setTxList((prev) => [
      ...prev,
      {
        id: `tx-${Date.now()}`,
        amount: "",
        category: "Others",
        date: new Date().toISOString().slice(0, 10),
        note: "",
        type: "expense",
        selected: true,
      },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const toSave = txList.filter((tx) => tx.selected);
    if (toSave.length === 0) {
      alert("Please select at least one transaction to save.");
      return;
    }

    const invalid = toSave.some((tx) => !tx.amount || parseFloat(tx.amount) <= 0);
    if (invalid) {
      alert("Please enter a valid amount for all selected transactions.");
      return;
    }

    setSaving(true);
    try {
      const payloads = toSave.map((tx) => {
        let finalDescription = tx.note.trim() || tx.category;
        if (tx.friend_name && tx.friend_owe_amount) {
          finalDescription += ` – ${tx.friend_name} owes ₹${tx.friend_owe_amount}`;
        }
        return {
          amount: parseFloat(tx.amount),
          category: tx.category,
          description: finalDescription,
          date: tx.date,
          type: tx.type,
          account_id: tx.account_id || undefined,
        };
      });
      await onConfirm(payloads);
    } catch (err: any) {
      alert("Failed to save transactions: " + (err.message || String(err)));
    } finally {
      setSaving(false);
    }
  };

  const selectedCount = txList.filter((tx) => tx.selected).length;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[150] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.92, opacity: 0, y: 10 }}
        className="w-full max-w-2xl rounded-3xl bg-card border border-border shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface">
          <div>
            <div className="text-sm font-semibold">Review Extracted Transactions</div>
            <div className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1.5">
              <Edit3 className="h-3 w-3" />
              Verify and edit the details extracted by AI
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 rounded-lg hover:bg-surface-hover text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Transcript block */}
        <div className="px-6 pt-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-muted-foreground">Original Transcript:</span>
            <button
              type="button"
              onClick={onEditTranscript}
              className="text-[11px] text-primary font-medium hover:underline flex items-center gap-1"
            >
              <Edit3 className="h-3 w-3" /> Edit Transcript &amp; Re-Analyze
            </button>
          </div>
          <div className="rounded-xl bg-surface border border-border px-3 py-2 text-xs italic text-muted-foreground max-h-[80px] overflow-y-auto">
            "{transcript}"
          </div>
        </div>

        {/* List container */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-hidden flex flex-col mt-4">
          <div className="flex-1 overflow-y-auto space-y-4 px-6 pb-4">
            {txList.length === 0 ? (
              <div className="text-center py-12 text-sm text-muted-foreground">
                No transactions extracted. Click "Add Transaction" below to create one manually.
              </div>
            ) : (
              txList.map((tx, idx) => (
                <div key={tx.id} className="p-4 rounded-2xl border border-border bg-surface/40 space-y-3 relative transition hover:border-border/80">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={tx.selected}
                        onChange={(e) => updateField(tx.id, "selected", e.target.checked)}
                        className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                      />
                      <span className="text-xs font-semibold text-foreground">
                        Transaction #{idx + 1}
                      </span>
                    </label>
                    <button
                      type="button"
                      onClick={() => deleteTx(tx.id)}
                      className="p-1 rounded-lg text-muted-foreground hover:text-destructive hover:bg-surface transition"
                      title="Remove transaction"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Amount (₹)</label>
                      <input
                        type="number"
                        value={tx.amount}
                        onChange={(e) => updateField(tx.id, "amount", e.target.value)}
                        required
                        min="0.01"
                        step="0.01"
                        placeholder="e.g. 250"
                        className={`w-full h-9 rounded-xl bg-surface border px-3 text-xs focus:outline-none focus:border-primary text-foreground ${
                          !tx.amount ? "border-warning/60 bg-warning/5" : "border-border"
                        }`}
                      />
                      {!tx.amount && (
                        <span className="text-[9px] text-warning flex items-center gap-1 mt-1">
                          <AlertCircle className="h-2.5 w-2.5" /> Amount is required
                        </span>
                      )}
                    </div>

                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Type</label>
                      <select
                        value={tx.type}
                        onChange={(e) => {
                          const newType = e.target.value as "expense" | "income";
                          updateField(tx.id, "type", newType);
                          updateField(tx.id, "category", newType === "income" ? "Salary" : "Food");
                        }}
                        className="w-full h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      >
                        <option value="expense">Expense</option>
                        <option value="income">Income</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Category</label>
                      <select
                        value={tx.category}
                        onChange={(e) => updateField(tx.id, "category", e.target.value)}
                        className="w-full h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      >
                        {tx.type === "income" ? (
                          <>
                            <option value="Salary">Salary</option>
                            <option value="Freelancing">Freelancing</option>
                            <option value="Refund">Refund</option>
                            <option value="Interest">Interest</option>
                            <option value="Bonus">Bonus</option>
                            <option value="Other Income">Other Income</option>
                            <option value="Income">Income</option>
                          </>
                        ) : (
                          <>
                            <option value="Food">Food</option>
                            <option value="Travel">Travel</option>
                            <option value="Shopping">Shopping</option>
                            <option value="Bills">Bills</option>
                            <option value="Health">Health</option>
                            <option value="Entertainment">Entertainment</option>
                            <option value="Education">Education</option>
                            <option value="Investment">Investment</option>
                            <option value="Others">Others</option>
                          </>
                        )}
                        {categories
                          .filter(
                            (c) =>
                              ![
                                "Salary",
                                "Freelancing",
                                "Refund",
                                "Interest",
                                "Bonus",
                                "Other Income",
                                "Income",
                                "Food",
                                "Travel",
                                "Shopping",
                                "Bills",
                                "Health",
                                "Entertainment",
                                "Education",
                                "Investment",
                                "Others",
                              ].includes(c)
                          )
                          .map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Description / Note</label>
                      <input
                        value={tx.note}
                        onChange={(e) => updateField(tx.id, "note", e.target.value)}
                        placeholder="What was this for?"
                        className="w-full h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      />
                    </div>

                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Date</label>
                      <input
                        type="date"
                        value={tx.date}
                        onChange={(e) => updateField(tx.id, "date", e.target.value)}
                        required
                        className="w-full h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      />
                    </div>

                    <div>
                      <label className="text-[10px] text-muted-foreground block mb-1">Account</label>
                      <select
                        value={tx.account_id || ""}
                        onChange={(e) => updateField(tx.id, "account_id", e.target.value)}
                        className="w-full h-9 rounded-xl bg-surface border border-border px-3 text-xs focus:outline-none focus:border-primary text-foreground"
                      >
                        <option value="">Auto-Route</option>
                        {accounts.map((acc) => (
                          <option key={acc.account_id} value={acc.account_id}>
                            {acc.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {tx.friend_name && tx.friend_owe_amount && (
                    <div className="rounded-xl border border-success/30 bg-success/5 px-3 py-2 text-xs text-foreground/80 flex items-center justify-between">
                      <span>
                        Friend Split: <strong className="text-success">{tx.friend_name}</strong> owes you ₹{tx.friend_owe_amount}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Add manual transaction */}
            <button
              type="button"
              onClick={addTx}
              className="w-full py-2.5 rounded-xl border border-dashed border-border hover:border-primary hover:text-primary text-muted-foreground text-xs font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Plus className="h-4 w-4" /> Add Transaction Manually
            </button>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 h-10 rounded-xl border border-border bg-surface hover:bg-surface-hover text-sm font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || selectedCount === 0}
              className="px-6 h-10 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary-hover disabled:opacity-60 transition flex items-center gap-2 shadow-lg shadow-primary/20"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Saving…
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" /> Save {selectedCount} Transaction{selectedCount !== 1 ? "s" : ""}
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
