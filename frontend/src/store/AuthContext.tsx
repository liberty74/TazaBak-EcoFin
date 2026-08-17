import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Role = 'user' | 'volunteer' | 'dispatcher';

const VALID_ROLES: Role[] = ['user', 'volunteer', 'dispatcher'];

interface AuthUser {
  id: string;
  username: string;
  role: Role;
}

interface AuthContextType {
  user: AuthUser | null;
  setRole: (role: Role, username: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Load from local storage on mount
    const rawRole = localStorage.getItem('demoRole');
    const savedRole: Role | null = rawRole && VALID_ROLES.includes(rawRole as Role)
      ? rawRole as Role
      : null;
    const savedUsername = localStorage.getItem('demoUsername');
    
    if (savedRole && savedUsername) {
      setUser({ id: savedUsername, username: savedUsername, role: savedRole });
    } else {
      // Clear corrupt/invalid storage
      localStorage.removeItem('demoRole');
      localStorage.removeItem('demoUsername');
    }
    setIsLoading(false);
  }, []);

  const setRole = (role: Role, username: string) => {
    if (!VALID_ROLES.includes(role)) return;
    localStorage.setItem('demoRole', role);
    localStorage.setItem('demoUsername', username);
    setUser({ id: username, username, role });
  };

  const logout = () => {
    localStorage.removeItem('demoRole');
    localStorage.removeItem('demoUsername');
    sessionStorage.removeItem('dispatcherKey');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setRole, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
