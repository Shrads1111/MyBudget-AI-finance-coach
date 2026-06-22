import { getAuth } from "firebase/auth";

const BASE_URL = import.meta.env.VITE_API_URL;

async function getHeaders(): Promise<HeadersInit> {
  const auth = getAuth();
  const user = auth.currentUser;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (user) {
    const token = await user.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  async get(endpoint: string) {
    const headers = await getHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, { headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || `Request failed with status ${res.status}`);
    }
    return res.json();
  },
  async post(endpoint: string, body?: any) {
    const headers = await getHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || `Request failed with status ${res.status}`);
    }
    return res.json();
  },
  async put(endpoint: string, body?: any) {
    const headers = await getHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "PUT",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || `Request failed with status ${res.status}`);
    }
    return res.json();
  },
  async delete(endpoint: string) {
    const headers = await getHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || `Request failed with status ${res.status}`);
    }
    return res.json();
  },
  async getPdf(endpoint: string) {
    const headers = await getHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, { headers });
    if (!res.ok) {
      throw new Error(`Failed to download report`);
    }
    return res.blob();
  }
};
