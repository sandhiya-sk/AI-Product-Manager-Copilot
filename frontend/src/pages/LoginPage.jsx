import React, { useState, useContext, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { login, isAuthenticated, user } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();

  // If already logged in, redirect based on role
  useEffect(() => {
    if (isAuthenticated && user) {
      const from = location.state?.from?.pathname || 
        (user.role === 'product_manager' ? '/dashboard' : '/upload/feedback');
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, user, navigate, location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/auth/login', { email, password });
      if (response.data.success) {
        const { access_token, user_id, role, project_id } = response.data.data;
        login(access_token, { user_id, email, role, project_id });
      } else {
        setError(response.data.error || "Login failed.");
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || "Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page-container">
      <div className="auth-card glass-panel">
        <div className="auth-header">
          <h2>Welcome Back</h2>
          <p>Sign in to continue to AI Product Manager Copilot</p>
        </div>

        <form onSubmit={handleSubmit} className="standard-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <button type="submit" className="action-btn auth-submit-btn" disabled={loading}>
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        {error && (
          <div className="alert-message error-alert auth-alert">
            {error}
          </div>
        )}

        <div className="auth-footer">
          <p>Don't have an account? <Link to="/register" className="auth-link">Register here</Link></p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
