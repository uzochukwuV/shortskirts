import { pipelineApi, pipelineEndpoints } from './pipelineApi';

const TOKEN_KEY = 'pipeline_access_token';
const USER_KEY = 'pipeline_user';

export const authStorage = {
  getToken() {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(TOKEN_KEY);
  },
  setSession(token, user) {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(TOKEN_KEY, token);
    if (user) window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  },
  getUser() {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  },
};

export const authService = {
  register: (payload) => pipelineApi.post(pipelineEndpoints.auth.register, payload),
  login: (payload) => pipelineApi.post(pipelineEndpoints.auth.login, payload),
  me: () => pipelineApi.get(pipelineEndpoints.auth.me),
  logout: () => pipelineApi.post(pipelineEndpoints.auth.logout),
};
