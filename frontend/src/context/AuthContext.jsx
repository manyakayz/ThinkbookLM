import { createContext, useContext, useState, useEffect } from 'react';
import { getMeApi, loginApi, registerApi, logoutApi, setUnauthorizedHandler } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check initial authentication state
    async function restoreSession() {
      try {
        const data = await getMeApi();
        if (data && data.user) {
          setUser(data.user);
        } else {
          setUser(null);
        }
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    setUnauthorizedHandler(() => {
      setUser(null);
    });

    restoreSession();
  }, []);

  const login = async (email, password) => {
    const data = await loginApi(email, password);
    setUser(data.user);
    return data.user;
  };

  const register = async (fullName, email, password, confirmPassword) => {
    const data = await registerApi(fullName, email, password, confirmPassword);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await logoutApi();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
