import React from 'react';
import { Map, Search, FileText, BarChart3, ChevronRight } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const QuickActions: React.FC = () => {
  const { setActiveModal, resetMapView } = useThermal();

  const handleLiveMapClick = () => {
    resetMapView();
    window.scrollTo({ top: 120, behavior: 'smooth' });
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
      
      {/* 1. View Live Map */}
      <div
        onClick={handleLiveMapClick}
        className="glass-card p-4 premium-shadow hover:-translate-y-1 transition-all cursor-pointer flex items-center justify-between group"
      >
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <Map className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800">
              View Live Map
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Real-time thermal activity
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
      </div>

      {/* 2. Explore Events */}
      <div
        onClick={() => setActiveModal('explore')}
        className="glass-card p-4 premium-shadow hover:-translate-y-1 transition-all cursor-pointer flex items-center justify-between group"
      >
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <Search className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800">
              Explore Events
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Filter & search events
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-600 group-hover:translate-x-0.5 transition-all" />
      </div>

      {/* 3. Generate Report */}
      <div
        onClick={() => setActiveModal('generate')}
        className="glass-card p-4 premium-shadow hover:-translate-y-1 transition-all cursor-pointer flex items-center justify-between group"
      >
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800">
              Generate Report
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Create custom reports
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
      </div>

      {/* 4. Source Attribution */}
      <div
        onClick={() => setActiveModal('attribution')}
        className="glass-card p-4 premium-shadow hover:-translate-y-1 transition-all cursor-pointer flex items-center justify-between group"
      >
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800">
              Source Attribution
            </h4>
            <p className="text-[11px] text-slate-400 mt-0.5">
              ML-based classification
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-0.5 transition-all" />
      </div>

    </div>
  );
};
export default QuickActions;
