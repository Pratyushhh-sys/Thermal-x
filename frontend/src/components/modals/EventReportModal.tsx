import React, { useState, useEffect } from 'react';
import { X, FileText, Download, Printer, MapPin, Factory, Calendar, ShieldAlert, Wind, Activity, CheckCircle2, Satellite, Eye, RefreshCw, AlertTriangle, Layers, ExternalLink } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';
import SatelliteThumbnail from '../../assets/SatelliteThumbnail';

export const EventReportModal: React.FC = () => {
  const { selectedEvent, activeModal, setActiveModal } = useThermal();
  const [imageryLoading, setImageryLoading] = useState(true);
  const [imageryError, setImageryError] = useState(false);
  const [imageryRefreshKey, setImageryRefreshKey] = useState(0);

  useEffect(() => {
    setImageryLoading(true);
    setImageryError(false);
  }, [selectedEvent?.id, imageryRefreshKey]);

  if (activeModal !== 'report' || !selectedEvent) return null;

  const handlePrint = () => {
    const originalTitle = document.title;
    document.title = `THERMAL INVESTIGATION REPORT — ${selectedEvent.id}`;
    window.print();
    document.title = originalTitle;
  };

  const hasValue = (val: string | number | undefined | null) => {
    if (val === undefined || val === null) return false;
    const str = String(val).trim().toLowerCase();
    if (str === 'unknown' || str === '—' || str === '-' || str.includes('unavailable')) return false;
    return true;
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
                {hasValue(selectedEvent.candidateSource) && (
                  <div className="text-base font-bold text-slate-900">{selectedEvent.candidateSource}</div>
                )}
                <div className="text-xs text-slate-500 mt-0.5 flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedEvent.location} &nbsp;|&nbsp; Coordinates: {selectedEvent.coordinates}</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/80 text-[11px]">
                {hasValue(selectedEvent.frp) && (
                  <div>
                    <span className="text-slate-400 block">Fire Radiative Power</span>
                    <span className="font-bold text-slate-800">{selectedEvent.frp}</span>
                  </div>
                )}
                {hasValue(selectedEvent.intensity) && (
                  <div>
                    <span className="text-slate-400 block">Thermal Intensity</span>
                    <span className="font-bold text-slate-800">{selectedEvent.intensity}</span>
                  </div>
                )}
                {hasValue(selectedEvent.sensor) && (
                  <div>
                    <span className="text-slate-400 block">Primary Sensor</span>
                    <span className="font-bold text-slate-800 truncate block">{selectedEvent.sensor}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Site Imagery (Sentinel-2 L2A) */}
          <div className="p-4 sm:p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 rounded-md bg-blue-50 text-blue-700 border border-blue-100">
                  <Satellite className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#0F284E] uppercase tracking-wider">
                    Site Imagery (Sentinel-2 L2A)
                  </h4>
                  <div className="text-[11px] text-slate-500">
                    Multispectral optical observation • ESA Copernicus Constellation
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setImageryRefreshKey((k) => k + 1)}
                  className="px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors flex items-center space-x-1 cursor-pointer"
                  title="Reload Sentinel-2 tile"
                >
                  <RefreshCw className={`w-3 h-3 ${imageryLoading ? 'animate-spin text-blue-600' : ''}`} />
                  <span>Refresh</span>
                </button>
                <a
                  href={`/api/imagery/${selectedEvent.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 text-[11px] font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors flex items-center space-x-1"
                  title="Open high resolution tile in new tab"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Full View</span>
                </a>
              </div>
            </div>

            {/* Satellite Image Frame with Skeleton */}
            <div className="relative w-full h-64 sm:h-80 bg-slate-900 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center group shadow-inner">
              
              {/* Skeleton loading state with spinner */}
              {imageryLoading && (
                <div className="absolute inset-0 z-10 bg-slate-900 flex flex-col items-center justify-center p-4 text-center">
                  <div className="relative mb-3">
                    <div className="w-12 h-12 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
                    <Satellite className="w-5 h-5 text-blue-400 absolute inset-0 m-auto" />
                  </div>
                  <div className="text-xs font-semibold text-slate-200">
                    Acquiring Sentinel-2 L2A Tile...
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 max-w-sm">
                    Processing 60-day cloud-free mosaic (≤20% cloud cover) via Copernicus Data Space Process API.
                  </div>
                </div>
              )}

              {/* Error state banner */}
              {imageryError && (
                <div className="absolute top-2 left-2 right-2 z-20 bg-amber-500/90 backdrop-blur-xs text-slate-950 px-3 py-1.5 rounded-lg text-[11px] font-medium flex items-center justify-between border border-amber-400">
                  <div className="flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-slate-950 flex-shrink-0" />
                    <span>Live acquisition returned cloudy or unavailable; rendered backup multispectral preview.</span>
                  </div>
                  <button
                    onClick={() => setImageryRefreshKey((k) => k + 1)}
                    className="underline text-[11px] font-bold ml-2 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              )}

              {/* Dynamic Image Element */}
              <img
                src={imageryError ? '/assets/selected_event_th1024.png' : `/api/imagery/${selectedEvent.id}?v=${imageryRefreshKey}`}
                alt={`Sentinel-2 satellite observation for thermal event ${selectedEvent.id}`}
                onLoad={() => setImageryLoading(false)}
                onError={() => {
                  setImageryError(true);
                  setImageryLoading(false);
                }}
                className={`w-full h-full object-cover select-none transition-opacity duration-500 ${
                  imageryLoading ? 'opacity-0' : 'opacity-100'
                }`}
              />

              {/* Overlay HUD indicators */}
              <div className="absolute bottom-2 left-2 z-10 bg-slate-950/75 backdrop-blur-xs text-white px-2.5 py-1 rounded-md text-[10px] font-mono border border-white/10 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>SENTINEL-2 L2A • TRUE-COLOR RGB</span>
                <span>•</span>
                <span>RES: 10M GSD</span>
              </div>
            </div>

            {/* Telemetry metadata footer strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-600">
              <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Instrument</span>
                <span className="font-semibold text-slate-800">MSI Level-2A BOA</span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Bands Used</span>
                <span className="font-semibold text-slate-800">B04 (R), B03 (G), B02 (B)</span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Cloud Filter</span>
                <span className="font-semibold text-slate-800">Max ≤ 20% Cloud Mask</span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Inspection Radius</span>
                <span className="font-semibold text-slate-800">2.0 km Bounding Box</span>
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
                {hasValue(selectedEvent.candidateSource) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Candidate Facility:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.candidateSource}</span>
                  </div>
                )}
                {hasValue(selectedEvent.candidateType) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Facility Type:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.candidateType}</span>
                  </div>
                )}
                {hasValue(selectedEvent.distanceToSource) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Proximity Distance:</span>
                    <span className="font-semibold text-emerald-600">{selectedEvent.distanceToSource}</span>
                  </div>
                )}
                {hasValue(selectedEvent.thermalCorrelation) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Thermal Correlation:</span>
                    <span className="font-semibold text-blue-600">{selectedEvent.thermalCorrelation}</span>
                  </div>
                )}
                {hasValue(selectedEvent.historicalDetections) && (
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Historical Anomalies:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.historicalDetections}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Investigation & Timeline */}
            <div className="p-4 rounded-xl border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-[#0F284E] uppercase tracking-wider flex items-center space-x-1.5">
                <Activity className="w-4 h-4 text-purple-600" />
                <span>Investigation & Timeline</span>
              </h4>

              <div className="space-y-2 text-xs">
                {hasValue(selectedEvent.status) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Investigation Status:</span>
                    <span className="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">{selectedEvent.status}</span>
                  </div>
                )}
                {hasValue(selectedEvent.detectedOn) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Detected Timestamp:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.detectedOn}</span>
                  </div>
                )}
                {hasValue(selectedEvent.riskScore) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Computed Risk Score:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.riskScore} / 100</span>
                  </div>
                )}
                {hasValue(selectedEvent.confidence) && (
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">AI Confidence:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.confidence}%</span>
                  </div>
                )}
                {hasValue(selectedEvent.sensor) && (
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Detection Instrument:</span>
                    <span className="font-semibold text-slate-800">{selectedEvent.sensor}</span>
                  </div>
                )}
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
