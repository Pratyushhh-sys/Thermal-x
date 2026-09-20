import React from 'react';
import { MapPin, Factory, Crosshair, Calendar, FileText, ArrowRight } from 'lucide-react';
import SatelliteThumbnail from '../../assets/SatelliteThumbnail';
import { useThermal } from '../../context/ThermalContext';
import InvestigationPriorityCard from '../intelligence/InvestigationPriorityCard';
import WhyThisEventCard from '../intelligence/WhyThisEventCard';
import EvidenceBreakdownCard from '../intelligence/EvidenceBreakdownCard';
import NearbyAssetsCard from '../intelligence/NearbyAssetsCard';
import DetectionTimelineCard from '../intelligence/DetectionTimelineCard';

export const SelectedEventPanel: React.FC = () => {
  const { selectedEvent, setActiveModal, eventDetailLoading } = useThermal();

  if (!selectedEvent) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-sm flex flex-col items-center justify-center text-center">
        <Crosshair className="w-12 h-12 text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">No Event Selected</h3>
        <p className="text-xs text-slate-500 mt-1">Select a thermal anomaly on the map to view detailed telemetry and AI attribution.</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-4 sm:p-5 premium-shadow">
      
      {/* Header matching Reference Image 2 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-slate-900">
          Selected Event
        </h2>
        <button
          onClick={() => setActiveModal('explore')}
          className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center space-x-1 group"
        >
          <span>View All Events</span>
          <span className="group-hover:translate-x-0.5 transition-transform">→</span>
        </button>
      </div>

      {/* Main Event Card Body */}
      <div className="space-y-4">
        
        {/* Top Info: Thumbnail + Title & Risk */}
        <div className="flex items-start space-x-3.5">
          {/* Satellite Thumbnail with ID Badge */}
          <SatelliteThumbnail eventId={selectedEvent.id} />

          {/* Title, Risk Badge, Location, Coordinates */}
          <div className="flex-1 min-w-0">
            {/* BUG-06: Risk Badge — correct color per tier, not always red */}
          {(() => {
            const riskColors = {
              High: 'bg-red-50 text-red-600 border-red-200',
              Medium: 'bg-amber-50 text-amber-700 border-amber-200',
              Low: 'bg-green-50 text-green-700 border-green-200',
            };
            const dotColors = { High: 'bg-red-600', Medium: 'bg-amber-500', Low: 'bg-green-600' };
            const tier = (selectedEvent.risk as 'High' | 'Medium' | 'Low') || 'Low';
            return (
              <div className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border mb-1 ${riskColors[tier] || riskColors.Low}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${dotColors[tier] || dotColors.Low}`}></span>
                <span>
                  {tier} Risk {selectedEvent.riskScore != null ? `(${Math.round(selectedEvent.riskScore)}%)` : ''}
                </span>
              </div>
            );
          })()}

            {/* Event ID */}
            <h3 className="text-xl font-extrabold text-slate-900 tracking-tight leading-tight">
              {selectedEvent.id}
            </h3>

            {/* Location */}
            <div className="flex items-center space-x-1 text-xs text-slate-700 font-medium mt-1">
              <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
              <span className="truncate">{selectedEvent.location}</span>
            </div>

            {/* Coordinates */}
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">
              {selectedEvent.coordinates}
            </div>
          </div>
        </div>

        {/* Telemetry Attributes List matching Reference Image 2 */}
        <div className="space-y-2.5 pt-2 border-t border-slate-100 text-xs">
          
          {/* Probable Source */}
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center space-x-2 text-slate-500">
              <div className="w-6 h-6 rounded-md bg-blue-50 flex items-center justify-center text-blue-600">
                <Factory className="w-3.5 h-3.5" />
              </div>
              <span>Probable Source</span>
            </div>
            <span className="font-semibold text-slate-800">
              {selectedEvent.probableSource}
            </span>
          </div>

          {/* Confidence — BUG-13: show spinner while detail loads */}
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center space-x-2 text-slate-500">
              <div className="w-6 h-6 rounded-md bg-cyan-50 flex items-center justify-center text-cyan-600">
                <Crosshair className="w-3.5 h-3.5" />
              </div>
              <span>Confidence</span>
            </div>
            <span className="font-semibold text-slate-800">
              {eventDetailLoading ? (
                <span className="inline-flex items-center space-x-1 text-slate-400">
                  <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  <span className="text-xs">Loading...</span>
                </span>
              ) : `${selectedEvent.confidence}%`}
            </span>
          </div>

          {/* Detected On */}
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center space-x-2 text-slate-500">
              <div className="w-6 h-6 rounded-md bg-purple-50 flex items-center justify-center text-purple-600">
                <Calendar className="w-3.5 h-3.5" />
              </div>
              <span>Detected On</span>
            </div>
            <span className="font-semibold text-slate-800 text-[11px] text-right">
              {selectedEvent.detectedOn}
            </span>
          </div>

        </div>

        {/* --- INTELLIGENCE SUITE ENHANCEMENTS --- */}
        <div className="space-y-3 pt-3 border-t border-slate-100">
          <InvestigationPriorityCard event={selectedEvent} />
          <WhyThisEventCard event={selectedEvent} />
          <EvidenceBreakdownCard event={selectedEvent} />
          <NearbyAssetsCard event={selectedEvent} />
          <DetectionTimelineCard event={selectedEvent} />
        </div>

        {/* Action Button: Open Event Report → matching Reference Image 2 */}
        <button
          onClick={() => setActiveModal('report')}
          className="w-full mt-3 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white text-xs sm:text-sm font-semibold py-3 px-4 rounded-xl premium-shadow transition-all duration-200 flex items-center justify-center space-x-2 group cursor-pointer"
        >
          <FileText className="w-4 h-4" />
          <span>Open Event Report</span>
          <span className="group-hover:translate-x-1 transition-transform">→</span>
        </button>

      </div>

    </div>
  );
};
export default SelectedEventPanel;
