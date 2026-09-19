import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThermalProvider } from './context/ThermalContext';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProtectedRoute from './components/common/ProtectedRoute';

export const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <ThermalProvider>
          <Routes>
            {/* Public Landing Page matching Reference Image 1 */}
            <Route path="/" element={<LandingPage />} />

            {/* Official Login Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Authenticated Dashboard Route matching Reference Image 2 */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />

            {/* Auxiliary shortcuts that map directly to the dashboard features */}
            <Route
              path="/events"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/attribution"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ThermalProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;
