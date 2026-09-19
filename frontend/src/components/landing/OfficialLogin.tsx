import React, { useState } from 'react';
import { User, Lock, Eye, EyeOff, Shield, AlertCircle, Loader2 } from 'lucide-react';
import GovBuildingBg from '../../assets/GovBuildingBg';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

interface OfficialLoginProps {
  onForgotPasswordClick: () => void;
}

export const OfficialLogin: React.FC<OfficialLoginProps> = ({ onForgotPasswordClick }) => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('official@thermalx.gov.in');
  const [password, setPassword] = useState('ThermalX@123');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please enter both Official Email / User ID and Password.');
      return;
    }

    setIsLoading(true);
    const result = await login(email, password);
    setIsLoading(false);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setErrorMessage(result.error || 'Invalid credentials. Please try again.');
    }
  };

  const fillDemoCredentials = () => {
    setEmail('official@thermalx.gov.in');
    setPassword('ThermalX@123');
    setErrorMessage(null);
  };

  return (
    <section id="official-login-section" className="py-12 lg:py-16 bg-[#F1F5F9]/60">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Downward indicator arrow matching Reference Image 1 transition */}
        <div className="flex justify-center mb-8">
          <div className="w-8 h-8 rounded-full bg-white border border-slate-300 shadow-sm flex items-center justify-center text-slate-500">
            ↓
          </div>
        </div>

        {/* The Official Login Split Card matching Reference Image 1 */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200/90 overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[520px]">
          
          {/* LEFT SIDE: Indian Government Sandstone Building & Emblem */}
          <div className="md:col-span-6 relative">
            <GovBuildingBg />
          </div>

          {/* RIGHT SIDE: Clean Official Login Form */}
          <div className="md:col-span-6 p-8 sm:p-10 lg:p-12 flex flex-col justify-center bg-white">
            
            <div className="mb-6">
              <h2 className="text-2xl sm:text-3xl font-bold text-[#0F284E] tracking-tight">
                Official Login
              </h2>
              <p className="text-sm text-slate-500 mt-1 font-normal">
                Access the Thermal X platform
              </p>
            </div>

            {/* Error banner */}
            {errorMessage && (
              <div className="mb-5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs sm:text-sm flex items-start space-x-2 animate-fadeIn">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Official Email / User ID */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Official Email / User ID
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="official@thermalx.gov.in"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0F284E]/20 focus:border-[#0F284E] transition-all bg-slate-50/50 hover:bg-white text-slate-800"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-10 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0F284E]/20 focus:border-[#0F284E] transition-all bg-slate-50/50 hover:bg-white text-slate-800"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Primary Login Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 bg-[#0F284E] hover:bg-[#173A6E] text-white font-semibold py-2.5 px-4 rounded-lg shadow-sm hover:shadow transition-all duration-200 flex items-center justify-center space-x-2 text-sm disabled:opacity-75 cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <span>Login</span>
                )}
              </button>

              {/* Forgot Password Link */}
              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={onForgotPasswordClick}
                  className="text-xs text-[#0284C7] hover:text-[#0369A1] font-medium hover:underline transition-colors"
                >
                  Forgot Password?
                </button>
              </div>

              {/* Quick autofill helper for easy evaluation */}
              <div className="text-center">
                <button
                  type="button"
                  onClick={fillDemoCredentials}
                  className="text-[11px] text-slate-400 hover:text-slate-600 underline"
                >
                  Use Demo Official Credentials
                </button>
              </div>

            </form>

            {/* Separator */}
            <div className="border-t border-slate-200/80 my-6"></div>

            {/* Security Notice matching Reference Image 1 */}
            <div className="flex items-start space-x-3 text-left">
              <div className="p-1 rounded bg-slate-100 text-slate-600 mt-0.5">
                <Shield className="w-4 h-4" />
              </div>
              <div className="flex flex-col text-[11px] leading-tight">
                <span className="font-bold text-slate-700">
                  Authorized Government Personnel Only
                </span>
                <span className="text-slate-400 mt-0.5">
                  Unauthorised access is prohibited.
                </span>
              </div>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
export default OfficialLogin;
