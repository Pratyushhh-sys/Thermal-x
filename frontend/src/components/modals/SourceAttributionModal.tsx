import React from 'react';
import { X, BarChart3, Factory, CheckCircle2, ShieldCheck, ArrowRight, Activity, Crosshair } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const SourceAttributionModal: React.FC = () => {
  const { selectedEvent, activeModal, setActiveModal, events, selectEventById } = useThermal();

  if (activeModal !== 'attribution') return null;

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
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center space-x-1.5">
              <Activity className="w-4 h-4 text-blue-600" />
              <span>Attribution Feature Weight Decomposition (SHAP / Explainable AI)</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Feature 1: Spatial Proximity */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700">1. Geospatial Proximity</span>
                  <span className="font-bold text-blue-600">35% Weight (High)</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-blue-600 h-full rounded-full" style={{ width: '92%' }}></div>
                </div>
                <p className="text-[11px] text-slate-500">
                  Anomaly origin is situated {selectedEvent.distanceToSource} from candidate stack boundary, well within the 2.5 km atmospheric boundary layer limit.
                </p>
              </div>

              {/* Feature 2: Temporal Correlation */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700">2. Temporal Flare Correlation</span>
                  <span className="font-bold text-blue-600">25% Weight (Very High)</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: '91%' }}></div>
                </div>
                <p className="text-[11px] text-slate-500">
                  Satellite overpass thermal peak corresponds exactly with the plant operational telemetry surge recorded at {selectedEvent.temporalCorrelation}.
                </p>
              </div>

              {/* Feature 3: Atmospheric Dispersion Plume */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700">3. Atmospheric Dispersion Alignment</span>
                  <span className="font-bold text-blue-600">20% Weight</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-cyan-500 h-full rounded-full" style={{ width: '88%' }}></div>
                </div>
                <p className="text-[11px] text-slate-500">
                  Observed heat plume vector ({selectedEvent.plumeDirection}) perfectly coincides with ERA5 surface wind vector ({selectedEvent.windSpeed}).
                </p>
              </div>

              {/* Feature 4: Historical Occurrence */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700">4. Historical Emission Baseline</span>
                  <span className="font-bold text-blue-600">20% Weight</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div className="bg-purple-500 h-full rounded-full" style={{ width: '84%' }}></div>
                </div>
                <p className="text-[11px] text-slate-500">
                  {selectedEvent.historicalDetections}. Radiative power exceeds standard operating threshold by 240%.
                </p>
              </div>

            </div>
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
