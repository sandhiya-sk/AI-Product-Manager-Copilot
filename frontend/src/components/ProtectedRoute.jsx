import React, { useContext } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, loading } = useContext(AuthContext);
  const location = useLocation();

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Verifying authentication...</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    // Redirect to login but save the current location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Role not authorized, redirect to homepage or appropriate default page
    return <Navigate to={user.role === 'product_manager' ? '/dashboard' : '/upload/feedback'} replace />;
  }

  return children;
};

export default ProtectedRoute;
