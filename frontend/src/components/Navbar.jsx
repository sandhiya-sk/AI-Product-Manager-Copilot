import React, { useContext } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout, isAuthenticated } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated || !user) {
    return null; // Don't render navigation for unauthenticated flows
  }

  const isActive = (path) => location.pathname === path ? 'active-link' : '';

  return (
    <nav className="navbar-container">
      <div className="navbar-brand">
        <Link to="/" className="navbar-logo-link">
          <span className="logo-icon">🚀</span>
          <span className="logo-text">PM Copilot</span>
        </Link>
      </div>

      <div className="navbar-links">
        {user.role === 'product_manager' && (
          <>
            <Link to="/dashboard" className={`navbar-link-item ${isActive('/dashboard')}`}>
              📊 Dashboard
            </Link>
            <Link to="/upload/csv" className={`navbar-link-item ${isActive('/upload/csv')}`}>
              📂 Upload CSV
            </Link>
            <Link to="/status" className={`navbar-link-item ${isActive('/status')}`}>
              🕵️ Processed Status
            </Link>
          </>
        )}
        <Link to="/upload/feedback" className={`navbar-link-item ${isActive('/upload/feedback')}`}>
          ✍️ Submit Feedback
        </Link>
      </div>

      <div className="navbar-user-profile">
        <div className="user-details">
          <span className="user-name">{user.full_name || user.email}</span>
          <span className="user-role-badge">
            {user.role === 'product_manager' ? 'Product Manager' : 'Customer'}
          </span>
        </div>
        <button onClick={handleLogout} className="logout-btn" aria-label="Sign out">
          Sign Out
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
