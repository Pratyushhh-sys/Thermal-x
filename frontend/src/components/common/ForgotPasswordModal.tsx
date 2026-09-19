import React from 'react';
import { ShieldCheck, X, Mail, PhoneCall } from 'lucide-react';
import IndiaEmblem from '../../assets/IndiaEmblem';

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex flex-col items-center text-center">
          <div className="mb-3">
            <IndiaEmblem size={36} />
          </div>
          
          <h3 className="text-lg font-bold text-[#0F284E]">
            Government Official Credential Support
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Thermal X Security Directorate
          </p>

          <div className="my-5 p-4 rounded-xl bg-blue-50/70 border border-blue-100 text-left w-full space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-[#0F284E]">
              <ShieldCheck className="w-4 h-4 text-blue-600 flex-shrink-0" />
              <span>Strict Security Protocol</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Automated public password resets are disabled for authorized government monitoring infrastructure. 
              Please contact your designated Departmental Nodal Officer or submit a ticket to the central helpdesk.
            </p>
          </div>

          <div className="w-full space-y-2 text-xs text-slate-600 text-left bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <div className="flex items-center space-x-2">
              <Mail className="w-3.5 h-3.5 text-slate-400" />
              <span>Support Desk: <span className="font-semibold text-slate-800">admin-support@thermalx.gov.in</span></span>
            </div>
            <div className="flex items-center space-x-2">
              <PhoneCall className="w-3.5 h-3.5 text-slate-400" />
              <span>NIC Helpline: <span className="font-semibold text-slate-800">1800-11-26162 (Toll Free)</span></span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="mt-6 w-full py-2.5 bg-[#0F284E] hover:bg-[#173A6E] text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            Understood, Return to Login
          </button>
        </div>
      </div>
    </div>
  );
};
export default ForgotPasswordModal;
