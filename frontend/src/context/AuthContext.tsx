import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface User {
  email: string;
  name: string;
  role: string;        // "ADMIN" | "VIEWER"
  initials: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string, pass: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Backend base URL — uses Vite proxy so this is just '/api'
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem('thermalx_auth') === 'true';
  });

  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('thermalx_user');
    if (saved) {
      try { return JSON.parse(saved); } catch { return null; }
    }
    return null;
  });

  // On mount: verify the HttpOnly cookie is still valid via /api/auth/me
  useEffect(() => {
    if (!isAuthenticated) return;
    fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          const userData: User = {
            email: data.email,
            name: data.name,
            role: data.role,
            initials: data.initials || '',
          };
          setUser(userData);
          localStorage.setItem('thermalx_user', JSON.stringify(userData));
        } else {
          // Cookie is gone / expired — clear local state
          setIsAuthenticated(false);
          setUser(null);
          localStorage.removeItem('thermalx_auth');
          localStorage.removeItem('thermalx_user');
        }
      })
      .catch(() => {
        // Network error — keep local state, will re-validate next mount
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // login
  // ---------------------------------------------------------------------------

  const login = useCallback(async (
    email: string,
    pass: string,
  ): Promise<{ success: boolean; error?: string }> => {
    if (!email.trim() || !pass.trim()) {
      return { success: false, error: 'Please enter both Official Email / User ID and Password.' };
    }

    try {
      const body = new URLSearchParams({ username: email.trim(), password: pass });
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
        credentials: 'include', // receive the HttpOnly cookie
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        return { success: false, error: err.detail || 'Invalid credentials. Please try again.' };
      }

      const data = await response.json();
      const userData: User = {
        email:    data.user.email,
        name:     data.user.name,
        role:     data.user.role,
        initials: data.user.initials || '',
      };

      setIsAuthenticated(true);
      setUser(userData);
      localStorage.setItem('thermalx_auth', 'true');
      localStorage.setItem('thermalx_user', JSON.stringify(userData));
      return { success: true };
    } catch {
      return { success: false, error: 'Login request failed. Please check your connection.' };
    }
  }, []);

  // ---------------------------------------------------------------------------
  // logout
  // ---------------------------------------------------------------------------

  const logout = useCallback(() => {
    // Tell backend to clear the cookie
    fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => {});
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem('thermalx_auth');
    localStorage.removeItem('thermalx_user');
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
