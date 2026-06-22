import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { initializeApp } from "firebase/app";
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  GoogleAuthProvider,
  signInWithPopup,
  onAuthStateChanged,
  updateProfile,
  type User as FirebaseUser
} from "firebase/auth";

// Firebase configuration from workspace
const firebaseConfig = {
  apiKey: "AIzaSyChWFaVleUIpHUpOzN7hFepM7u2qkBtczU",
  authDomain: "mybudget-15057.firebaseapp.com",
  projectId: "mybudget-15057",
  storageBucket: "mybudget-15057.firebasestorage.app",
  messagingSenderId: "1005166417839",
  appId: "1:1005166417839:web:a60cde0947690a2215c15a",
  measurementId: "G-JBH0T5FHJY"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

type UserProfile = { name: string; email: string; uid: string };
type AuthCtx = {
  user: UserProfile | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  loading: boolean;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Sync user profile to backend
  const syncUserToBackend = async (idToken: string) => {
    try {
      const res = await fetch(
  `${import.meta.env.VITE_API_URL}/api/users/sync`,
  {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${idToken}`
    }
  }
);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Failed to sync user profile with backend:", e);
    }
    return null;
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const idToken = await firebaseUser.getIdToken();
          setToken(idToken);
          
          const fallbackName = firebaseUser.displayName || firebaseUser.email?.split("@")[0] || "User";
          setUser({
            name: fallbackName,
            email: firebaseUser.email || "",
            uid: firebaseUser.uid
          });

          // Sync profile to database and use Firestore display_name if exists
          const dbProfile = await syncUserToBackend(idToken);
          if (dbProfile && dbProfile.display_name) {
            setUser({
              name: dbProfile.display_name,
              email: dbProfile.email || firebaseUser.email || "",
              uid: dbProfile.uid || firebaseUser.uid
            });
          }
        } catch (e) {
          console.error("Error retrieving Firebase ID token:", e);
          setToken(null);
          setUser(null);
        }
      } else {
        setToken(null);
        setUser(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  };

  const signup = async (name: string, email: string, password: string) => {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    if (cred.user) {
      await updateProfile(cred.user, { displayName: name });
    }
  };

  const loginWithGoogle = async () => {
    await signInWithPopup(auth, googleProvider);
  };

  const logout = async () => {
    await signOut(auth);
  };

  return (
    <Ctx.Provider value={{ user, token, login, signup, loginWithGoogle, logout, loading }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used within AuthProvider");
  return v;
}
