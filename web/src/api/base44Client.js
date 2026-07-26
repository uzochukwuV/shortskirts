const TOKEN_KEY = "dysentry_auth_token";

function getApiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL || "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function getToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (!token) {
    window.localStorage.removeItem(TOKEN_KEY);
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, token);
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    data = text ? { detail: text } : null;
  }

  if (!response.ok) {
    const error = new Error(data?.detail || `Request failed with status ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

const auth = {
  getToken,
  setToken,
  async isAuthenticated() {
    if (!getToken()) return false;
    try {
      await auth.me();
      return true;
    } catch {
      return false;
    }
  },
  async me() {
    return request("/pipeline/auth/me");
  },
  async loginViaEmailPassword(email, password) {
    const data = await request("/pipeline/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data?.token) setToken(data.token);
    return data;
  },
  async register({ email, password }) {
    const data = await request("/pipeline/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data?.token) setToken(data.token);
    return data;
  },
  async logout() {
    try {
      await request("/pipeline/auth/logout", { method: "POST" });
    } finally {
      setToken(null);
    }
  },
  redirectToLogin() {
    setToken(null);
    window.location.href = "/login";
  },
  loginWithProvider() {
    throw new Error("Google sign-in is not configured yet");
  },
  async verifyOtp() {
    throw new Error("Email verification is not configured for this backend");
  },
  async resendOtp() {
    throw new Error("Email verification is not configured for this backend");
  },
  async resetPasswordRequest() {
    throw new Error("Password reset is not configured yet");
  },
  async resetPassword() {
    throw new Error("Password reset is not configured yet");
  },
  async updateMe() {
    throw new Error("Profile updates are not wired yet");
  },
};

export const db = {
  auth,
  entities: new Proxy(
    {},
    {
      get: () => ({
        filter: async () => [],
        get: async () => null,
        create: async () => ({}),
        update: async () => ({}),
        delete: async () => ({}),
      }),
    },
  ),
  integrations: {
    Core: {
      UploadFile: async () => {
        throw new Error("File upload is not wired yet");
      },
    },
  },
};

export const base44 = db;
export default db;
