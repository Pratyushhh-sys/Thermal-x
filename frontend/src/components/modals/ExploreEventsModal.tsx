import React, { useState } from 'react';
import { X, Search, Filter, Factory, Flame, Zap, Shield, ArrowRight } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const ExploreEventsModal: React.FC = () => {
  const { events, activeFilter, selectEventById, activeModal, setActiveModal, setSelectedEvent, flyToLocation } = useThermal();

  const [search, setSearch] = useState('');
  const [selectedRisk, setSelectedRisk] = useState<string>('All');
  const [selectedSource, setSelectedSource] = useState<string>('All');
  const [selectedStatus, setSelectedStatus] = useState<string>('All');

  // Sync internal modal filters with the global activeFilter when opened
  React.useEffect(() => {
    if (activeModal === 'explore') {
      setSearch(''); // BUG-07: always reset search when modal opens
      if (activeFilter === 'high-risk') {
        setSelectedRisk('High');
        setSelectedSource('All');
        setSelectedStatus('All');
      } else if (activeFilter === 'industrial') {
        setSelectedRisk('All');
        setSelectedSource('Industrial');
        setSelectedStatus('All');
      } else if (activeFilter === 'investigation') {
        setSelectedRisk('High'); // Show high risk for investigation
        setSelectedSource('All');
        setSelectedStatus('All');
      } else {
        setSelectedRisk('All');
        setSelectedSource('All');
        setSelectedStatus('All');
      }
    }
  }, [activeModal, activeFilter]);

  if (activeModal !== 'explore') return null;

  const filtered = events.filter((e) => {
    const matchesSearch =
      search === '' ||
      e.id.toLowerCase().includes(search.toLowerCase()) ||
      e.location.toLowerCase().includes(search.toLowerCase()) ||
      e.probableSource.toLowerCase().includes(search.toLowerCase()) ||
      e.candidateSource.toLowerCase().includes(search.toLowerCase());

    const matchesRisk = selectedRisk === 'All' || e.risk === selectedRisk;
    const matchesSource = selectedSource === 'All' || e.probableSource === selectedSource || (selectedSource === 'Industrial' && e.probableSource === 'Mining');
    const matchesStatus = selectedStatus === 'All' || e.status === selectedStatus;

    return matchesSearch && matchesRisk && matchesSource && matchesStatus;
  });

  // Show at most 100 events to keep the list responsive
  const displayedEvents = filtered.slice(0, 100);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Top Header */}
        <div className="bg-[#0F284E] text-white p-5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-white/10 text-white">
              <Search className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg sm:text-xl font-bold">
                Explore Thermal Events & Attributions
              </h3>
              <p className="text-xs text-blue-200">
                Filter & investigate satellite-detected thermal sources across India
              </p>
            </div>
          </div>

          <button
            onClick={() => setActiveModal(null)}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Controls Bar */}
        <div className="p-4 bg-slate-50 border-b border-slate-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Search input */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by ID or location..."
              className="w-full pl-9 pr-3 py-2 bg-white rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Risk filter */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-500 whitespace-nowrap">Risk:</span>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="w-full p-2 bg-white rounded-lg border border-slate-300 focus:outline-none"
            >
              <option value="All">All Risk Levels</option>
              <option value="High">High Risk</option>
              <option value="Medium">Medium Risk</option>
              <option value="Low">Low Risk</option>
            </select>
          </div>

          {/* Source filter */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-500 whitespace-nowrap">Source:</span>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full p-2 bg-white rounded-lg border border-slate-300 focus:outline-none"
            >
              <option value="All">All Probable Sources</option>
              <option value="Agricultural">Agricultural</option>
              <option value="Forest">Forest</option>
              <option value="Industrial">Industrial</option>
              <option value="Mining">Mining</option>
              <option value="Other">Other</option>
              <option value="Pipeline">Pipeline</option>
              <option value="Power Plant">Power Plant</option>
              <option value="Settlement">Settlement</option>
            </select>
          </div>

          {/* Status filter */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-500 whitespace-nowrap">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full p-2 bg-white rounded-lg border border-slate-300 focus:outline-none"
            >
              <option value="All">All Statuses</option>
              <option value="In Progress">In Progress</option>
              <option value="Under Review">Under Review</option>
              <option value="Investigating">Investigating</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Table Results */}
        <div className="p-4 overflow-y-auto flex-1">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-400 font-semibold">
                <th className="pb-2.5">Event ID</th>
                <th className="pb-2.5">Location</th>
                <th className="pb-2.5">Attributed Facility</th>
                <th className="pb-2.5">FRP (MW)</th>
                <th className="pb-2.5">Confidence</th>
                <th className="pb-2.5">Risk</th>
                <th className="pb-2.5">Status</th>
                <th className="pb-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayedEvents.map((ev) => (
                <tr
                  key={ev.id}
                  className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                  onClick={() => {
                    selectEventById(ev.id);
                    flyToLocation(ev.lat, ev.lng, 10);
                    setActiveModal(null);
                  }}
                >
                  <td className="py-3 font-bold text-[#0F284E]">{ev.id}</td>
                  <td className="py-3 text-slate-700">{ev.location}</td>
                  <td className="py-3 text-slate-700 font-medium truncate max-w-sm" title={ev.candidateSource}>
                    <div className="flex items-center space-x-1.5 truncate">
                      <Factory className="w-3.5 h-3.5 text-blue-500/80 flex-shrink-0" />
                      <span className="truncate text-slate-800">{ev.candidateSource}</span>
                    </div>
                  </td>
                  <td className="py-3 font-semibold text-slate-800">{ev.frp}</td>
                  <td className="py-3 font-bold text-blue-600">{ev.confidence}%</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      ev.risk === 'High' ? 'bg-red-100 text-red-700' :
                      ev.risk === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                    }`}>
                      {ev.risk}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                      {ev.status}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <button className="text-blue-600 font-semibold hover:underline flex items-center space-x-1 ml-auto">
                      <span>View</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {displayedEvents.length === 0 && (
            <div className="text-center py-12 text-slate-400 text-sm">
              No thermal events matched your filter criteria.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing <strong>{displayedEvents.length}</strong> of <strong>{filtered.length}</strong> matched records
            {filtered.length > 100 && <span className="ml-2 text-amber-600 font-medium">(top 100 shown — use filters to narrow down)</span>}
          </span>
          <button
            onClick={() => setActiveModal(null)}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
export default ExploreEventsModal;
