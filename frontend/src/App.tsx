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
        <Routes>
          {/* Public Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Official Login Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes: ThermalProvider only mounts AFTER auth — BUG-15 */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <ThermalProvider>
                  <DashboardPage />
                </ThermalProvider>
              </ProtectedRoute>
            }
          />
          <Route
            path="/events"
            element={
              <ProtectedRoute>
                <ThermalProvider>
                  <DashboardPage />
                </ThermalProvider>
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ProtectedRoute>
                <ThermalProvider>
                  <DashboardPage />
                </ThermalProvider>
              </ProtectedRoute>
            }
          />
          <Route
            path="/attribution"
            element={
              <ProtectedRoute>
                <ThermalProvider>
                  <DashboardPage />
                </ThermalProvider>
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
};

export default App;
