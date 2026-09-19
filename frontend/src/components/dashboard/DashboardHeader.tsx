import React from 'react';
import { Satellite } from 'lucide-react';

export const DashboardHeader: React.FC = () => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4 sm:py-5 border-b border-slate-200/80 mb-6">
      
      {/* Left Title & Subtitle matching Reference Image 2 */}
      <div className="flex items-center space-x-4">
        {/* Satellite circular icon badge */}
        <div className="w-12 h-12 rounded-full bg-[#E0F2FE] border border-[#BAE6FD] flex items-center justify-center flex-shrink-0 text-[#0284C7] shadow-xs">
          <Satellite className="w-6 h-6" />
        </div>

        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-[#0B2447] tracking-tight">
            Thermal Intelligence & Risk Monitoring
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-normal mt-0.5">
            Satellite-based industrial fire and thermal source attribution
          </p>
        </div>
      </div>

      {/* Right Slogan with Satellite graphic matching Reference Image 2 */}
      <div className="hidden md:flex items-center space-x-3 text-right">
        <div className="text-xs font-semibold text-slate-500">
          From Space <span className="text-slate-400">→</span> <span className="text-[#0F284E] font-bold">To Safer Tomorrow</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
          <Satellite className="w-4 h-4" />
        </div>
      </div>

    </div>
  );
};
export default DashboardHeader;
