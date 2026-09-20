import React from 'react';
import { X, BarChart3, Factory, CheckCircle2, ShieldCheck, ArrowRight, Activity, Crosshair } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';
import EvidenceBreakdownCard from '../intelligence/EvidenceBreakdownCard';

export const SourceAttributionModal: React.FC = () => {
  const { selectedEvent, activeModal, setActiveModal, events, selectEventById } = useThermal();

  if (activeModal !== 'attribution') return null;

  // Guard: need a selected event to show attribution
  if (!selectedEvent) {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs animate-fadeIn">
        <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden">
          <div className="bg-[#0F284E] text-white p-5 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-white/10"><BarChart3 className="w-5 h-5" /></div>
              <h3 className="text-lg font-bold">ML Source Attribution Engine</h3>
            </div>
            <button onClick={() => setActiveModal(null)} className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="p-10 text-center">
            <Crosshair className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h4 className="text-base font-bold text-slate-800 mb-2">No Event Selected</h4>
            <p className="text-sm text-slate-500 mb-6">Please select a thermal event from the map or the Explore Events table first, then open Attribution.</p>
            <div className="flex justify-center gap-3">
              <button onClick={() => setActiveModal('explore')} className="px-4 py-2 bg-[#0F284E] text-white text-xs font-semibold rounded-lg hover:bg-[#173A6E]">
                Open Explore Events
              </button>
              <button onClick={() => setActiveModal(null)} className="px-4 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200">
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className="bg-[#0F284E] text-white p-5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-white/10 text-white">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg sm:text-xl font-bold">
                Machine Learning Source Attribution Engine
              </h3>
              <p className="text-xs text-blue-200">
                Multi-factor probabilistic attribution for Event: {selectedEvent.id}
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

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs sm:text-sm">
          
          {/* Top Score Summary Banner */}
          <div className="p-5 rounded-xl bg-gradient-to-r from-blue-900 to-[#0F284E] text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-[11px] font-bold text-cyan-300 uppercase tracking-wider">
                Primary Candidate Source Attributed
              </span>
              <h4 className="text-lg sm:text-xl font-bold text-white mt-1">
                {selectedEvent.candidateSource}
              </h4>
              <p className="text-xs text-blue-200 mt-0.5">
                {selectedEvent.candidateType} &nbsp;•&nbsp; Proximity: {selectedEvent.distanceToSource}
              </p>
            </div>

            <div className="flex items-center space-x-4 bg-white/10 px-4 py-2.5 rounded-xl backdrop-blur-xs flex-shrink-0">
              <div className="text-right">
                <span className="text-[10px] text-blue-200 uppercase block">Model Confidence</span>
                <span className="text-2xl font-extrabold text-cyan-300">{selectedEvent.confidence}%</span>
              </div>
              <div className="w-10 h-10 rounded-full bg-cyan-400/20 border border-cyan-300 flex items-center justify-center text-cyan-300 font-bold">
                <Crosshair className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Explainability Feature Breakdown */}
          <div className="mt-4">
            <EvidenceBreakdownCard event={selectedEvent} />
          </div>

          {/* Model Reasoning Conclusion */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <h5 className="text-xs font-bold text-slate-800 uppercase">
              Attribution Scientific Consensus
            </h5>
            <p className="text-xs text-slate-600 leading-relaxed">
              {selectedEvent.attributionReasoning}
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs">
          <span className="text-slate-400">Validated under SIH 26162 ML Attribution Protocol</span>
          <button
            onClick={() => setActiveModal(null)}
            className="px-4 py-2 bg-[#0F284E] text-white font-semibold rounded-lg hover:bg-[#173A6E] transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};
export default SourceAttributionModal;
