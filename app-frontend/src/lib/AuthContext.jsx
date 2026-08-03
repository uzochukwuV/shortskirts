import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '@/services/authService';
import { sessionStorage } from '@/services/session';

const AuthContext = createContext(null);

const extractToken = (payload) =>
  payload?.access_token ??
  payload?.token ??
  payload?.data?.access_token ??
  payload?.data?.token ??
  null;

const extractUser = (payload) =>
  payload?.user ??
  payload?.data?.user ??
  payload?.profile ??
  payload?.data?.profile ??
  payload ??
  null;

const getStoredUser = () => sessionStorage.getUser();
const getStoredToken = () => sessionStorage.getToken();

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => getStoredUser());
  const [token, setToken] = useState(() => getStoredToken());
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getStoredToken()));
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState(null);

  const clearSession = useCallback(() => {
    sessionStorage.clear();
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const persistSession = useCallback((nextToken, nextUser) => {
    if (!nextToken) return;
    sessionStorage.set(nextToken, nextUser ?? undefined);
    setToken(nextToken);
    setUser(nextUser ?? null);
    setIsAuthenticated(true);
    setAuthError(null);
  }, []);

  const refreshAuth = useCallback(async () => {
    const storedToken = getStoredToken();

    if (!storedToken) {
      clearSession();
      setIsLoadingAuth(false);
      setAuthChecked(true);
      setAuthError(null);
      return null;
    }

    try {
      const currentUser = await authService.me();
      const nextUser = extractUser(currentUser) ?? getStoredUser();
      sessionStorage.set(storedToken, nextUser ?? undefined);
      setToken(storedToken);
      setUser(nextUser ?? null);
      setIsAuthenticated(true);
      setAuthError(null);
      return nextUser ?? null;
    } catch (error) {
      clearSession();
      setAuthError({
        type: 'auth_required',
        message: error?.message || 'Session expired. Please log in again.',
      });
      return null;
    } finally {
      setIsLoadingAuth(false);
      setAuthChecked(true);
    }
  }, [clearSession]);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  const login = useCallback(async ({ email, password }) => {
    const response = await authService.login({ email, password });
    const nextToken = extractToken(response);
    const nextUser = extractUser(response);

    if (nextToken) {
      persistSession(nextToken, nextUser);
      if (!nextUser) {
        await refreshAuth();
      }
      return getStoredUser();
    }

    await refreshAuth();
    return getStoredUser();
  }, [persistSession, refreshAuth]);

  const register = useCallback(async ({ email, password }) => {
    const response = await authService.register({ email, password });
    const nextToken = extractToken(response);
    const nextUser = extractUser(response);

    if (nextToken) {
      persistSession(nextToken, nextUser);
      if (!nextUser) {
        await refreshAuth();
      }
    }

    return response;
  }, [persistSession, refreshAuth]);

  const logout = useCallback(async (redirectTo = '/login') => {
    try {
      await authService.logout();
    } catch {
      // Ignore backend logout failures. Local session cleanup still happens.
    } finally {
      clearSession();
      setAuthChecked(true);
      setIsLoadingAuth(false);
      setAuthError(null);
      if (redirectTo) {
        navigate(redirectTo, { replace: true });
      }
    }
  }, [clearSession, navigate]);

  const navigateToLogin = useCallback((returnTo = '/') => {
    const target = returnTo && returnTo !== '/' ? `/login?returnTo=${encodeURIComponent(returnTo)}` : '/login';
    navigate(target, { replace: true });
  }, [navigate]);

  const value = useMemo(() => ({
    user,
    token,
    isAuthenticated,
    isLoadingAuth,
    authChecked,
    authError,
    refreshAuth,
    login,
    register,
    logout,
    navigateToLogin,
    clearSession,
  }), [
    user,
    token,
    isAuthenticated,
    isLoadingAuth,
    authChecked,
    authError,
    refreshAuth,
    login,
    register,
    logout,
    navigateToLogin,
    clearSession,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
