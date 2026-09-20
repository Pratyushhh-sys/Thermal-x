import React from 'react';
import { Factory, Flame, Zap, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const RecentInvestigations: React.FC = () => {
  const { filteredEvents, selectedEvent, selectEventById, setActiveModal } = useThermal();

  // Show top 4 investigations matching Reference Image 2
  const recentEvents = filteredEvents.slice(0, 4);

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'Industrial':
        return <Factory className="w-3.5 h-3.5 text-blue-600 inline mr-1" />;
      case 'Pipeline':
        return <Flame className="w-3.5 h-3.5 text-amber-600 inline mr-1" />;
      case 'Power Plant':
        return <Zap className="w-3.5 h-3.5 text-purple-600 inline mr-1" />;
      default:
        return <Factory className="w-3.5 h-3.5 text-slate-500 inline mr-1" />;
    }
  };

  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'High':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
            <span>High</span>
          </span>
        );
      case 'Medium':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <span>Medium</span>
          </span>
        );
      case 'Low':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-50 text-green-700 border border-green-200">
            <span className="w-1.5 h-1.5 rounded-full bg-green-600"></span>
            <span>Low</span>
          </span>
        );
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'In Progress':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            In Progress
          </span>
        );
      case 'Under Review':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            Under Review
          </span>
        );
      case 'Investigating':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            Investigating
          </span>
        );
      case 'Resolved':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Resolved
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="glass-card p-4 sm:p-5 premium-shadow">
      
      {/* Header matching Reference Image 2 */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-bold text-slate-900">
          Recent Investigations
        </h2>
        <button
          onClick={() => setActiveModal('explore')}
          className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center space-x-1 group"
        >
          <span>View All</span>
          <span className="group-hover:translate-x-0.5 transition-transform">→</span>
        </button>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-[11px] font-semibold text-slate-400">
              <th className="pb-2 font-medium">Event ID</th>
              <th className="pb-2 font-medium">Location</th>
              <th className="pb-2 font-medium">Probable Source</th>
              <th className="pb-2 font-medium">Risk</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium text-right">Detected On</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {recentEvents.map((ev) => {
              const isSelected = selectedEvent?.id === ev.id;
              return (
                <tr
                  key={ev.id}
                  onClick={() => selectEventById(ev.id)}
                  className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                    isSelected ? 'bg-blue-50/60 font-medium' : ''
                  }`}
                >
                  {/* Event ID */}
                  <td className="py-2.5 font-bold text-[#0F284E] whitespace-nowrap">
                    {ev.id}
                  </td>

                  {/* Location */}
                  <td className="py-2.5 text-slate-700 whitespace-nowrap">
                    {ev.location}
                  </td>

                  {/* Probable Source */}
                  <td className="py-2.5 text-slate-600 whitespace-nowrap">
                    <span className="flex items-center">
                      {getSourceIcon(ev.probableSource)}
                      <span>{ev.probableSource}</span>
                    </span>
                  </td>

                  {/* Risk */}
                  <td className="py-2.5 whitespace-nowrap">
                    {getRiskBadge(ev.risk)}
                  </td>

                  {/* Status */}
                  <td className="py-2.5 whitespace-nowrap">
                    {getStatusBadge(ev.status)}
                  </td>

                  {/* Detected On */}
                  <td className="py-2.5 text-slate-500 whitespace-nowrap text-right text-[11px]">
                    {ev.detectedOn.replace(' (IST)', '')}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
};
export default RecentInvestigations;
