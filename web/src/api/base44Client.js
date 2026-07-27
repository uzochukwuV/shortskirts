const TOKEN_KEY = "dysentry_auth_token";

// Auth error event dispatcher
const AUTH_ERROR_EVENT = "dysentry:auth-error";

function emitAuthError(status) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(AUTH_ERROR_EVENT, { 
      detail: { status } 
    }));
  }
}

function onAuthError(callback) {
  if (typeof window !== 'undefined') {
    window.addEventListener(AUTH_ERROR_EVENT, (e) => callback(e.detail));
  }
  return () => {
    if (typeof window !== 'undefined') {
      window.removeEventListener(AUTH_ERROR_EVENT, callback);
    }
  };
}

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

export async function request(path, options = {}) {
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
    // Emit auth error for 401/403 so components can handle logout
    if (response.status === 401 || response.status === 403) {
      emitAuthError(response.status);
    }
    
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

function createEntityApi(entityType, basePath) {
  return {
    async filter(query = {}) {
      const qs = new URLSearchParams();
      Object.entries(query).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") qs.set(k, v);
      });
      const qsStr = qs.toString();
      return request(`${basePath}${qsStr ? `?${qsStr}` : ""}`);
    },
    async get(id) {
      return request(`${basePath}/${id}`);
    },
    async create(payload) {
      return request(basePath, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    async update(id, payload) {
      return request(`${basePath}/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    },
    async delete(id) {
      return request(`${basePath}/${id}`, {
        method: "DELETE",
      });
    },
  };
}

const entities = {
  series: createEntityApi("series", "/pipeline/stories"),
  episode: createEntityApi("episode", "/pipeline/episodes"),
  scene: createEntityApi("scene", "/pipeline/scenes"),
  character: createEntityApi("character", "/pipeline/characters"),
  job: createEntityApi("job", "/pipeline/jobs"),
  schedule: createEntityApi("schedule", "/pipeline/schedules"),
  publishTarget: createEntityApi("publishTarget", "/pipeline/publish-targets"),
  socialAccount: createEntityApi("socialAccount", "/pipeline/social/accounts"),
  bible: createEntityApi("bible", "/pipeline/bibles"),
  gallery: createEntityApi("gallery", "/pipeline/gallery"),
  checkpoint: createEntityApi("checkpoint", "/pipeline/checkpoints"),
  pipelineRun: createEntityApi("pipelineRun", "/pipeline/runs"),
  user: createEntityApi("user", "/pipeline/users"),
};

const integrations = {
  Core: {
    async UploadFile(file) {
      const formData = new FormData();
      formData.append("file", file);
      return request("/pipeline/uploads/image", {
        method: "POST",
        body: formData,
        headers: {},
      });
    },
  },
};

export const db = { auth, entities, integrations, onAuthError };
export const base44 = db;
export default db;
