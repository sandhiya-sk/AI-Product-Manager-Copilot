import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';

// Page Imports
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UploadCSVPage from './pages/UploadCSVPage';
import FeedbackFormPage from './pages/FeedbackFormPage';
import StatusPage from './pages/StatusPage';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app-shell">
          <Navbar />
          <main className="main-content-layout">
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Protected Product Manager Only Routes */}
              <Route 
                path="/dashboard" 
                element={
                  <ProtectedRoute allowedRoles={['product_manager']}>
                    <DashboardPage />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/upload/csv" 
                element={
                  <ProtectedRoute allowedRoles={['product_manager']}>
                    <UploadCSVPage />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/status" 
                element={
                  <ProtectedRoute allowedRoles={['product_manager']}>
                    <StatusPage />
                  </ProtectedRoute>
                } 
              />

              {/* Protected Combined Routes (PM & Customer) */}
              <Route 
                path="/upload/feedback" 
                element={
                  <ProtectedRoute allowedRoles={['product_manager', 'customer']}>
                    <FeedbackFormPage />
                  </ProtectedRoute>
                } 
              />

              {/* Root redirects to dashboard (PM) or form (Customer) inside login redirect logic */}
              <Route path="/" element={<Navigate to="/login" replace />} />
              
              {/* Fallback */}
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
