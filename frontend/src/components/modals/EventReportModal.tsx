import React from 'react';
import { X, FileText, Download, Printer, MapPin, Factory, Calendar, ShieldAlert, Wind, Activity, CheckCircle2 } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';
import SatelliteThumbnail from '../../assets/SatelliteThumbnail';

export const EventReportModal: React.FC = () => {
  const { selectedEvent, activeModal, setActiveModal } = useThermal();

  if (activeModal !== 'report' || !selectedEvent) return null;

  const handlePrint = () => {
    const originalTitle = document.title;
    document.title = `THERMAL INVESTIGATION REPORT — ${selectedEvent.id}`;
    window.print();
    document.title = originalTitle;
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden print-content">
        
        {/* Modal Top Bar */}
        <div className="bg-[#0F284E] text-white p-5 flex items-center justify-between no-print">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-white/10 text-white">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-semibold text-blue-200 uppercase tracking-wider">
                Thermal Intelligence Attribution Dossier
              </div>
              <h3 className="text-lg sm:text-xl font-bold">
                Incident Report: {selectedEvent.id}
              </h3>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrint}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Print Dossier"
            >
              <Printer className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActiveModal(null)}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-800 text-xs sm:text-sm">
          
          {/* Header Overview Card */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="md:col-span-4 flex items-center justify-center">
              <SatelliteThumbnail eventId={selectedEvent.id} className="w-full h-32 sm:h-36" />
            </div>

            <div className="md:col-span-8 flex flex-col justify-between space-y-2">
              <div className="flex items-center justify-between">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  selectedEvent.risk === 'High' ? 'bg-red-100 text-red-700' :
                  selectedEvent.risk === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                }`}>
                  {selectedEvent.risk} Risk Thermal Anomaly
                </span>
                <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-md border border-blue-200">
                  ML Confidence: {selectedEvent.confidence}%
                </span>
              </div>

              <div>
                <div className="text-base font-bold text-slate-900">{selectedEvent.candidateSource}</div>
                <div className="text-xs text-slate-500 mt-0.5 flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedEvent.location} &nbsp;|&nbsp; Coordinates: {selectedEvent.coordinates}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/80 text-[11px]">
                <div>
                  <span className="text-slate-400 block">Fire Radiative Power</span>
                  <span className="font-bold text-slate-800">{selectedEvent.frp}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Thermal Intensity</span>
                  <span className="font-bold text-slate-800">{selectedEvent.intensity}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Primary Sensor</span>
                  <span className="font-bold text-slate-800 truncate block">{selectedEvent.sensor}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Attribution Reasoning & Meteorological Telemetry */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* Machine Learning Source Attribution */}
            <div className="p-4 rounded-xl border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-[#0F284E] uppercase tracking-wider flex items-center space-x-1.5">
                <Factory className="w-4 h-4 text-blue-600" />
                <span>Source Attribution Analysis</span>
              </h4>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Candidate Facility:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.candidateSource}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Facility Type:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.candidateType}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Proximity Distance:</span>
                  <span className="font-semibold text-emerald-600">{selectedEvent.distanceToSource}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Thermal Correlation:</span>
                  <span className="font-semibold text-blue-600">{selectedEvent.thermalCorrelation}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Historical Anomalies:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.historicalDetections}</span>
                </div>
              </div>
            </div>

            {/* Environmental & Wind Vector */}
            <div className="p-4 rounded-xl border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-[#0F284E] uppercase tracking-wider flex items-center space-x-1.5">
                <Wind className="w-4 h-4 text-cyan-600" />
                <span>Atmospheric Dispersion & Vector</span>
              </h4>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Surface Wind:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.windSpeed}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Plume Vector:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.plumeDirection}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Investigation Status:</span>
                  <span className="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">{selectedEvent.status}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Detected Timestamp:</span>
                  <span className="font-semibold text-slate-800">{selectedEvent.detectedOn}</span>
                </div>
              </div>
            </div>

          </div>

          {/* Official Attribution Explanation Narrative */}
          <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 space-y-2 print-avoid-break">
            <div className="text-xs font-bold text-[#0F284E] uppercase tracking-wide">
              Attribution Scientific Explainability
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              {selectedEvent.attributionReasoning}
            </p>
          </div>
          
          {/* DISCLAIMER */}
          <div className="p-3 mt-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-[10px] sm:text-xs leading-relaxed font-medium print-avoid-break">
            <strong>IMPORTANT DISCLAIMER:</strong> This report identifies a "Probable Source" and "Investigative Lead" based on geographic proximity and thermal machine learning. It is <strong>not confirmed fire-cause attribution</strong> and must be verified by on-the-ground regulatory authorities.
          </div>

        </div>

        {/* Modal Footer */}
        <div className="bg-slate-50 p-4 border-t border-slate-200 flex items-center justify-between no-print">
          <span className="text-[11px] text-slate-400">
            Certified by Thermal X Satellite Intelligence Unit • SIH 26162
          </span>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setActiveModal(null)}
              className="px-4 py-2 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-semibold text-xs rounded-lg transition-colors cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handlePrint}
              className="px-4 py-2 bg-[#0F284E] hover:bg-[#173A6E] text-white font-semibold text-xs rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Print / Save as PDF</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
export default EventReportModal;
