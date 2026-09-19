import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  email: string;
  name: string;
  role: string;
  initials: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string, pass: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_EMAIL = "official@thermalx.gov.in";
const DEMO_PASSWORD = "ThermalX@123";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    const saved = localStorage.getItem('thermalx_auth');
    return saved === 'true';
  });

  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('thermalx_user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        return null;
      }
    }
    return null;
  });

  useEffect(() => {
    if (isAuthenticated && !user) {
      setUser({
        email: DEMO_EMAIL,
        name: 'Admin',
        role: 'Authorized Official',
        initials: 'AS'
      });
    }
  }, [isAuthenticated, user]);

  const login = async (email: string, pass: string): Promise<{ success: boolean; error?: string }> => {
    // Artificial brief delay for realistic government SSO response
    await new Promise((resolve) => setTimeout(resolve, 600));

    if (!email.trim() || !pass.trim()) {
      return { success: false, error: "Please enter both Official Email / User ID and Password." };
    }

    if (email.trim().toLowerCase() === DEMO_EMAIL.toLowerCase() && pass === DEMO_PASSWORD) {
      const userData: User = {
        email: DEMO_EMAIL,
        name: 'Admin',
        role: 'Authorized Official',
        initials: 'AS'
      };
      setIsAuthenticated(true);
      setUser(userData);
      localStorage.setItem('thermalx_auth', 'true');
      localStorage.setItem('thermalx_user', JSON.stringify(userData));
      return { success: true };
    }

    return { success: false, error: "Invalid credentials. Please try again." };
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem('thermalx_auth');
    localStorage.removeItem('thermalx_user');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
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
