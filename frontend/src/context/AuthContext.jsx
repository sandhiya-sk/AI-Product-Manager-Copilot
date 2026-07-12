import React, { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext(null);

// Helper to decode JWT payload safely
const decodeToken = (token) => {
  if (!token) return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch (error) {
    console.error("Failed to decode token", error);
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      if (decoded) {
        // Check if token has expired
        const currentTime = Date.now() / 1000;
        if (decoded.exp && decoded.exp < currentTime) {
          console.warn("Token expired. Logging out.");
          logout();
        } else {
          setUser({
            user_id: decoded.sub,
            email: decoded.email,
            role: decoded.role,
            project_id: decoded.project_id,
            full_name: decoded.full_name
          });
        }
      } else {
        localStorage.removeItem('token');
        setToken(null);
      }
    } else {
      setUser(null);
    }
    setLoading(false);
  }, [token]);

  const login = (jwtToken, userData) => {
    localStorage.setItem('token', jwtToken);
    setToken(jwtToken);
    if (userData) {
      setUser(userData);
    } else {
      const decoded = decodeToken(jwtToken);
      if (decoded) {
        setUser({
          user_id: decoded.sub,
          email: decoded.email,
          role: decoded.role,
          project_id: decoded.project_id,
          full_name: decoded.full_name
        });
      }
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value = {
    token,
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!token && !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
