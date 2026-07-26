import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import db from '@/api/base44Client';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [isLoadingPublicSettings, setIsLoadingPublicSettings] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [appPublicSettings, setAppPublicSettings] = useState(null);
  const isHandlingAuthError = useRef(false);

  // Handle auth errors from API calls
  const handleAuthError = useCallback((detail) => {
    // Prevent multiple simultaneous auth error handling
    if (isHandlingAuthError.current) return;
    isHandlingAuthError.current = true;

    // Only handle if we're authenticated and haven't already shown error
    if (isAuthenticated && authChecked) {
      console.warn('Auth error from API:', detail);
      db.auth.setToken(null);
      setAuthError({
        type: 'auth_required',
        message: 'Your session has expired. Please log in again.',
      });
      
      // Redirect after a short delay to let the user see the error
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
    }
    
    // Reset flag after a delay
    setTimeout(() => {
      isHandlingAuthError.current = false;
    }, 1000);
  }, [isAuthenticated, authChecked, authError]);

  useEffect(() => {
    // Subscribe to auth errors from API
    const unsubscribe = db.onAuthError(handleAuthError);
    return unsubscribe;
  }, [handleAuthError]);

  useEffect(() => {
    checkAppState();
  }, []);

  const checkAppState = async () => {
    try {
      setIsLoadingPublicSettings(false);
      setAuthError(null);

      setAppPublicSettings({ auth_required: true });
      if (db.auth.getToken()) {
        await checkUserAuth();
      } else {
        setUser(null);
        setIsLoadingAuth(false);
        setIsAuthenticated(false);
        setAuthChecked(true);
      }
    } catch (error) {
      console.error('Unexpected auth bootstrap error:', error);
      setAuthError({
        type: 'unknown',
        message: error.message || 'An unexpected error occurred',
      });
      setIsLoadingAuth(false);
      setAuthChecked(true);
    }
  };

  const checkUserAuth = async () => {
    try {
      setIsLoadingAuth(true);
      const currentUser = await db.auth.me();
      setUser(currentUser);
      setIsAuthenticated(true);
      setAuthError(null);
      setIsLoadingAuth(false);
      setAuthChecked(true);
    } catch (error) {
      console.error('User auth check failed:', error);
      setIsLoadingAuth(false);
      setIsAuthenticated(false);
      setUser(null);
      setAuthChecked(true);

      if (error.status === 401 || error.status === 403) {
        db.auth.setToken(null);
        setAuthError({
          type: 'auth_required',
          message: 'Authentication required',
        });
      } else {
        setAuthError({
          type: 'unknown',
          message: error.message || 'Authentication failed',
        });
      }
    }
  };

  const logout = (shouldRedirect = true) => {
    setUser(null);
    setIsAuthenticated(false);
    setAuthChecked(true);
    setAuthError(null);
    
    if (shouldRedirect) {
      db.auth.logout().finally(() => {
        window.location.href = "/login";
      });
    } else {
      db.auth.logout();
    }
  };

  const navigateToLogin = () => {
    db.auth.redirectToLogin();
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      isAuthenticated, 
      isLoadingAuth,
      isLoadingPublicSettings,
      authError,
      appPublicSettings,
      authChecked,
      logout,
      navigateToLogin,
      checkUserAuth,
      checkAppState
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
