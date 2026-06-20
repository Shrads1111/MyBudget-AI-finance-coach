import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Mail, Lock, User as UserIcon, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({ meta: [{ title: "Sign in · MyBudget" }] }),
  component: AuthPage,
});

function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { login, signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(name || email.split("@")[0], email, password);
      }
      navigate({ to: "/" });
    } catch (e: any) {
      setErr(e?.message ?? "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const handleGoogleLogin = async () => {
    setErr(null);
    setBusy(true);
    try {
      await loginWithGoogle();
      navigate({ to: "/" });
    } catch (e: any) {
      setErr(e?.message ?? "Google Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      <div className="hidden lg:flex flex-1 relative overflow-hidden bg-gradient-to-br from-primary/20 via-background to-background p-12 flex-col justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-primary grid place-items-center text-primary-foreground font-bold">M</div>
          <span className="font-semibold tracking-tight text-lg">MyBudget</span>
        </Link>
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-medium text-primary mb-4">
            <Sparkles className="h-4 w-4" /> AI Financial OS for Students
          </div>
          <h1 className="text-4xl xl:text-5xl font-bold tracking-tight leading-tight">
            Spend smart.<br />Save smarter.<br />
            <span className="text-primary">Stress less.</span>
          </h1>
          <p className="mt-4 text-muted-foreground max-w-md">
            Track expenses, hit savings goals, split bills with flatmates, and get personalized AI coaching — all in one place.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">© 2026 MyBudget</div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <h2 className="text-2xl font-semibold tracking-tight">{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {mode === "login" ? "Sign in to continue managing your money." : "Start your journey to financial freedom."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            {mode === "signup" && (
              <Field icon={<UserIcon className="h-4 w-4" />} label="Full name">
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Jane Student" className="input" />
              </Field>
            )}
            <Field icon={<Mail className="h-4 w-4" />} label="Email">
              <input value={email} onChange={(e) => setEmail(e.target.value)} required type="email" placeholder="you@university.edu" className="input" />
            </Field>
            <Field icon={<Lock className="h-4 w-4" />} label="Password">
              <input value={password} onChange={(e) => setPassword(e.target.value)} required type="password" minLength={4} placeholder="••••••••" className="input" />
            </Field>

            {err && <div className="text-sm text-destructive">{err}</div>}

            <button type="submit" disabled={busy} className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary-hover transition flex items-center justify-center gap-2 disabled:opacity-60">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
              {!busy && <ArrowRight className="h-4 w-4" />}
            </button>

            <div className="relative my-4 flex py-1 items-center">
              <div className="flex-grow border-t border-border"></div>
              <span className="flex-shrink mx-4 text-muted-foreground text-xs uppercase">Or</span>
              <div className="flex-grow border-t border-border"></div>
            </div>

            <button type="button" onClick={handleGoogleLogin} disabled={busy} className="w-full h-11 rounded-xl border border-border bg-surface hover:bg-surface-hover transition flex items-center justify-center gap-2 disabled:opacity-60 text-sm font-medium text-foreground">
              Continue with Google
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            {mode === "login" ? "New to MyBudget?" : "Already have an account?"}{" "}
            <button onClick={() => setMode(mode === "login" ? "signup" : "login")} className="text-primary font-medium hover:underline">
              {mode === "login" ? "Create account" : "Sign in"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs font-medium text-muted-foreground mb-1.5">{label}</div>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</div>
        <div className="[&_.input]:w-full [&_.input]:h-11 [&_.input]:rounded-xl [&_.input]:bg-surface [&_.input]:border [&_.input]:border-border [&_.input]:pl-9 [&_.input]:pr-3 [&_.input]:text-sm [&_.input]:placeholder:text-muted-foreground [&_.input]:focus:outline-none [&_.input]:focus:border-primary [&_.input]:transition">
          {children}
        </div>
      </div>
    </label>
  );
}
