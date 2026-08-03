const TOKEN_KEY = 'pipeline_access_token';
const USER_KEY = 'pipeline_user';

export const sessionStorage = {
  getToken() {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(TOKEN_KEY);
  },
  set(token, user) {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(TOKEN_KEY, token);
    if (user) {
      window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  },
  getUser() {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },
  clear() {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  },
};

export const SESSION_KEYS = {
  token: TOKEN_KEY,
  user: USER_KEY,
};
