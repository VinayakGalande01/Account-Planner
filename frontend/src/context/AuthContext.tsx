'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (name: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(async () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    try {
      await fetch('http://127.0.0.1:8002/auth/logout', { 
        method: 'POST',
        credentials: 'include'
      });
    } catch (err) {
      console.error('Failed to log out session on server:', err);
    }
  }, []);

  // Session refresh handler
  const refreshSession = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch('http://127.0.0.1:8002/auth/refresh', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include'
      });

      if (res.ok) {
        const data = await res.json();
        if (data.access_token) {
          setToken(data.access_token);
          localStorage.setItem('token', data.access_token);

          // Get current user using the new token
          const userRes = await fetch('http://127.0.0.1:8002/auth/me', {
            headers: {
              'Authorization': `Bearer ${data.access_token}`,
              'Accept': 'application/json',
            },
          });

          if (userRes.ok) {
            const userData = await userRes.json();
            setUser(userData);
            return data.access_token;
          }
        }
      }
    } catch (err) {
      console.error('Failed to silently refresh auth session:', err);
    }
    // If refresh fails, clear auth state
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    return null;
  }, []);

  // Initial load verification
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const res = await fetch('http://127.0.0.1:8002/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`,
              'Accept': 'application/json',
            },
          });
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
            setToken(storedToken);
            setLoading(false);
            return;
          }
        } catch (err) {
          console.error('Saved token verification failed, trying refresh token:', err);
        }
      }

      // If token verification fails or no token in storage, try refresh token cookie
      await refreshSession();
      setLoading(false);
    };

    initializeAuth();
  }, [refreshSession]);

  // Periodic Refresh Cycle (Runs every 14 minutes since tokens expire in 60 minutes)
  useEffect(() => {
    if (!token) return;

    const interval = setInterval(() => {
      refreshSession();
    }, 14 * 60 * 1000);

    return () => clearInterval(interval);
  }, [token, refreshSession]);

  const login = async (email: string, password: string): Promise<boolean> => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8002/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ email, password }),
        credentials: 'include' // Allow receiving HttpOnly refresh cookies
      });

      const data = await res.json();

      if (res.ok && data.access_token) {
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        
        // Fetch profile details
        const userRes = await fetch('http://127.0.0.1:8002/auth/me', {
          headers: {
            'Authorization': `Bearer ${data.access_token}`,
            'Accept': 'application/json',
          },
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          setUser(userData);
          return true;
        }
      }
      
      setError(data.detail || 'Invalid email or password');
      return false;
    } catch (err) {
      setError('Connection to auth server failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const signup = async (name: string, email: string, password: string): Promise<boolean> => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8002/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();

      if (res.ok) {
        // Automatically log in after successful signup
        return await login(email, password);
      } else {
        setError(data.detail || 'Registration failed');
        return false;
      }
    } catch (err) {
      setError('Connection to signup server failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const authFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
    const currentToken = token || localStorage.getItem('token');
    const headers = new Headers(options.headers || {});

    if (currentToken) {
      headers.set('Authorization', `Bearer ${currentToken}`);
    }

    return fetch(url, {
      ...options,
      headers,
    });
  }, [token]);

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      error,
      login,
      signup,
      logout,
      authFetch
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
