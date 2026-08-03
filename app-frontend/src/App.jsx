import React from 'react';
import { BrowserRouter as Router, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import ScrollToTop from './components/ScrollToTop';
import PageNotFound from './lib/PageNotFound';
import { safeReturnTo } from '@/lib/authReturnTo';
import ProtectedRoute from '@/components/ProtectedRoute';

import Home from '@/pages/Home';
import Dashboard from '@/pages/Dashboard';
import Workspace from '@/pages/Workspace';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';

const LoadingScreen = () => (
  <div className="fixed inset-0 flex items-center justify-center bg-[#0a0a0a]">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-[#dfff1e]/30 border-t-[#dfff1e] rounded-full animate-spin" />
      <span className="text-white/40 text-xs">Loading…</span>
    </div>
  </div>
);

const PublicOnlyRoute = () => {
  const { isAuthenticated, isLoadingAuth, authChecked } = useAuth();
  const location = useLocation();

  if (isLoadingAuth || !authChecked) return <LoadingScreen />;

  if (isAuthenticated) {
    const target = safeReturnTo();
    return <Navigate to={target && target !== '/' ? target : '/dashboard'} replace state={{ from: location }} />;
  }

  return <Outlet />;
};

const AuthenticatedApp = () => (
  <Routes>
    <Route path="/" element={<Home />} />
    <Route element={<PublicOnlyRoute />}>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
    </Route>
    <Route element={<ProtectedRoute />}>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/workspace" element={<Workspace />} />
      <Route path="/workspace/:storyId" element={<Workspace />} />
    </Route>
    <Route path="*" element={<PageNotFound />} />
  </Routes>
);

function App() {
  return (
    <QueryClientProvider client={queryClientInstance}>
      <Router>
        <AuthProvider>
          <ScrollToTop />
          <AuthenticatedApp />
          <Toaster />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
