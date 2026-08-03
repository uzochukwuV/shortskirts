import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { X, ChevronDown, Loader2, Mail, Lock } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

export default function AuthModal({ open, onClose }) {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setError('');

    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login({ email, password });
      } else {
        await register({ email, password });
        await login({ email, password });
      }
      onClose?.();
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err?.message || (mode === 'login' ? 'Login failed' : 'Registration failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-[#0c0c0c] rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl border border-white/5">
        <button onClick={onClose} className="absolute top-4 right-4 z-10 text-white/40 hover:text-white transition">
          <X size={20} />
        </button>

        <div className="p-8 lg:p-10">
          <div className="w-10 h-10 mb-6 bg-[#dfff1e] rounded-md grid grid-cols-4 gap-0.5 p-1.5">
            {[...Array(16)].map((_, i) => (
              <div key={i} className={`rounded-[1px] ${[0, 2, 4, 7, 8, 11, 13, 14, 15].includes(i) ? 'bg-black' : 'bg-transparent'}`} />
            ))}
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">
            Welcome to <span className="text-[#dfff1e]">SonicVision</span>
          </h2>
          <p className="text-white/50 text-sm mb-6">{mode === 'login' ? 'Log in to continue' : 'Create your account'}</p>

          <div className="flex items-center gap-2 mb-6 bg-white/5 p-1 rounded-full w-fit">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${mode === 'login' ? 'bg-[#dfff1e] text-black' : 'text-white/60 hover:text-white'}`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${mode === 'register' ? 'bg-[#dfff1e] text-black' : 'text-white/60 hover:text-white'}`}
            >
              Sign up
            </button>
          </div>

          {error && <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">{error}</div>}

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="block text-xs text-white/50 mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pl-10 text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[#dfff1e]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-white/50 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pl-10 text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[#dfff1e]"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-xs text-white/50 mb-2">Confirm password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 pl-10 text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[#dfff1e]"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#dfff1e] text-black py-3 rounded-xl text-sm font-semibold hover:bg-[#c5e01a] transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? (mode === 'login' ? 'Logging in...' : 'Creating account...') : (mode === 'login' ? 'Log in' : 'Create account')}
            </button>
          </form>

          <div className="flex items-center justify-between mt-6 text-xs text-white/40">
            <button type="button" onClick={onClose} className="hover:text-white transition">
              Close
            </button>
            <div className="flex items-center gap-3">
              <Link to="/login" className="hover:text-white transition">
                Full login page
              </Link>
              <ChevronDown size={12} className="opacity-60" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
