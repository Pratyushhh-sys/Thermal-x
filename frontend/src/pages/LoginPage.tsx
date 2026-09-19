import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import OfficialLogin from '../components/landing/OfficialLogin';
import ForgotPasswordModal from '../components/common/ForgotPasswordModal';
import FlameIcon from '../assets/FlameIcon';
import IndiaEmblem from '../assets/IndiaEmblem';
import { ArrowLeft } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="min-h-screen bg-[#F4F7FB] flex flex-col justify-between antialiased">
      
      {/* Top Simple Bar */}
      <header className="bg-white border-b border-slate-200 py-3.5 px-4 sm:px-8 flex items-center justify-between shadow-xs">
        <Link to="/" className="flex items-center space-x-2 text-xs font-semibold text-slate-600 hover:text-[#0F284E] transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Thermal X Portal</span>
        </Link>

        <div className="flex items-center space-x-2">
          <IndiaEmblem size={24} />
          <span className="text-xs font-bold text-[#0F284E] hidden sm:inline">
            Government of India
          </span>
        </div>
      </header>

      {/* Main Login View matching Reference Image 1 */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <div className="w-full max-w-5xl">
          <OfficialLogin
            onForgotPasswordClick={() => setIsForgotModalOpen(true)}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-slate-400 border-t border-slate-200 bg-white">
        Thermal X &copy; 2026 &bull; Authorized Government Personnel Only &bull; SIH 26162
      </footer>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
      />
    </div>
  );
};
export default LoginPage;
