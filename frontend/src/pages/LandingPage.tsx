import React, { useState } from 'react';
import Navbar from '../components/landing/Navbar';
import HeroSection from '../components/landing/HeroSection';
import OfficialLogin from '../components/landing/OfficialLogin';
import ForgotPasswordModal from '../components/common/ForgotPasswordModal';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  // If already logged in, navigate straight to dashboard if desired
  React.useEffect(() => {
    if (isAuthenticated) {
      // Allow viewing landing page or navigate if requested
    }
  }, [isAuthenticated, navigate]);

  const scrollToLogin = () => {
    const el = document.getElementById('official-login-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleLearnMore = () => {
    scrollToLogin();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F4F7FB]">
      {/* Top Navigation matching Reference Image 1 */}
      <Navbar
        onOfficialLoginClick={scrollToLogin}
        onNavigateSection={(section) => {
          if (section === 'features' || section === 'about') {
            scrollToLogin();
          } else {
            scrollToLogin();
          }
        }}
      />

      {/* Main Content */}
      <main className="flex-1">
        {/* Hero Section matching Reference Image 1 */}
        <HeroSection
          onLoginClick={scrollToLogin}
          onLearnMoreClick={handleLearnMore}
          onSelectAnomaly={scrollToLogin}
        />

        {/* Official Login Section matching Reference Image 1 */}
        <OfficialLogin
          onForgotPasswordClick={() => setIsForgotModalOpen(true)}
        />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>© 2026 Thermal X — Smart India Hackathon (SIH 26162). Ministry of Environment, Forest and Climate Change & NIC.</p>
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">Security Standard: CERT-In Compliant</span>
            <span>•</span>
            <span className="text-slate-400">Satellite Sensor: INSAT-3DR / VIIRS / MODIS</span>
          </div>
        </div>
      </footer>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
      />
    </div>
  );
};
export default LandingPage;
