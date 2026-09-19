import React from 'react';
import { Flame, AlertTriangle, Factory, Search, ChevronRight } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const SummaryCards: React.FC = () => {
  const { activeFilter, setActiveFilter, setActiveModal, summary } = useThermal();

  const totalActive = summary?.total_events || 0;
  const highRisk = summary?.risk_summary?.high || 0;
  const industrialSource = summary?.source_distribution?.Industrial || 0;
  const requiringInvestigation = 0; // Hardcoded per user instruction for Status

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      
      {/* CARD 1: Active Thermal Events */}
      <div
        onClick={() => {
          setActiveFilter('all');
          setActiveModal('explore');
        }}
        className={`bg-white rounded-xl border p-4 sm:p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center justify-between group ${
          activeFilter === 'all' ? 'border-orange-300 ring-1 ring-orange-200' : 'border-slate-200/90'
        }`}
      >
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-[#FFEDD5] flex items-center justify-center flex-shrink-0 text-[#EA580C] group-hover:scale-105 transition-transform">
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-600">
              Active Thermal Events
            </div>
            <div className="text-2xl font-bold text-slate-900 leading-tight mt-0.5">
              {totalActive.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-[#EA580C] flex items-center space-x-1 mt-1">
              <span>View All</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>

      {/* CARD 2: High-Risk Events */}
      <div
        onClick={() => {
          setActiveFilter('high-risk');
          setActiveModal('explore');
        }}
        className={`bg-white rounded-xl border p-4 sm:p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center justify-between group ${
          activeFilter === 'high-risk' ? 'border-red-300 ring-1 ring-red-200' : 'border-slate-200/90'
        }`}
      >
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-[#FEE2E2] flex items-center justify-center flex-shrink-0 text-[#DC2626] group-hover:scale-105 transition-transform">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-600">
              High-Risk Events
            </div>
            <div className="text-2xl font-bold text-slate-900 leading-tight mt-0.5">
              {highRisk.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-[#DC2626] flex items-center space-x-1 mt-1">
              <span>View Risk Events</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>

      {/* CARD 3: Industrial-Source Events */}
      <div
        onClick={() => {
          setActiveFilter('industrial');
          setActiveModal('attribution');
        }}
        className={`bg-white rounded-xl border p-4 sm:p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center justify-between group ${
          activeFilter === 'industrial' ? 'border-blue-300 ring-1 ring-blue-200' : 'border-slate-200/90'
        }`}
      >
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-[#DBEAFE] flex items-center justify-center flex-shrink-0 text-[#2563EB] group-hover:scale-105 transition-transform">
            <Factory className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-600">
              Industrial-Source Events
            </div>
            <div className="text-2xl font-bold text-slate-900 leading-tight mt-0.5">
              {industrialSource.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-[#2563EB] flex items-center space-x-1 mt-1">
              <span>View Source Attribution</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>

      {/* CARD 4: Requiring Investigation */}
      <div
        onClick={() => {
          setActiveFilter('investigation');
          setActiveModal('explore');
        }}
        className={`bg-white rounded-xl border p-4 sm:p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center justify-between group ${
          activeFilter === 'investigation' ? 'border-green-300 ring-1 ring-green-200' : 'border-slate-200/90'
        }`}
      >
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-[#DCFCE7] flex items-center justify-center flex-shrink-0 text-[#16A34A] group-hover:scale-105 transition-transform">
            <Search className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-600">
              Requiring Investigation
            </div>
            <div className="text-2xl font-bold text-slate-900 leading-tight mt-0.5">
              {requiringInvestigation.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-[#16A34A] flex items-center space-x-1 mt-1">
              <span>View Investigations</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-500 transition-colors" />
      </div>

    </div>
  );
};
export default SummaryCards;
