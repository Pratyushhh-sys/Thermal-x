import React, { useState } from 'react';
import { X, FileText, Download, CheckCircle, Calendar, ShieldCheck, Loader2 } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';

export const GenerateReportModal: React.FC = () => {
  const { events, selectedEvent, activeModal, setActiveModal, selectEventById } = useThermal();

  const [selectedEventId, setSelectedEventId] = useState(selectedEvent?.id || '');
  const [reportType, setReportType] = useState('full-attribution');
  const [dateRange, setDateRange] = useState('last-7-days');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedSuccess, setGeneratedSuccess] = useState(false);

  if (activeModal !== 'generate') return null;

  const currentEv = events.find(e => e.id === selectedEventId) || selectedEvent;

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await selectEventById(selectedEventId);
      setGeneratedSuccess(true);
    } catch (err) {
      console.error("Failed to fetch event for report", err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Top Header */}
        <div className="bg-[#0F284E] text-white p-5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-white/10 text-white">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg sm:text-xl font-bold">
                Generate Official Attribution Report
              </h3>
              <p className="text-xs text-blue-200">
                Custom regulatory dossier for government enforcement & compliance
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              setActiveModal(null);
              setGeneratedSuccess(false);
            }}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs sm:text-sm">
          
          {generatedSuccess ? (
            <div className="py-8 text-center space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
                <CheckCircle className="w-8 h-8" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-900">
                  Report Dossier Successfully Generated
                </h4>
                <p className="text-xs text-slate-500 mt-1">
                  Document ID: TX-REP-{currentEv.id}-2026.pdf (Signed with NIC e-Stamp)
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 max-w-md mx-auto text-left space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Event ID:</span>
                  <span className="font-bold text-slate-800">{currentEv.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Target Facility:</span>
                  <span className="font-semibold text-slate-800">{currentEv.candidateSource}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">ML Confidence:</span>
                  <span className="font-bold text-emerald-600">{currentEv.confidence}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Security Classification:</span>
                  <span className="font-semibold text-blue-800">Restricted / For Official Use Only</span>
                </div>
              </div>

              <div className="flex justify-center space-x-3 pt-4">
                <button
                  onClick={() => setGeneratedSuccess(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs"
                >
                  Generate Another
                </button>
                <button
                  onClick={() => {
                    setActiveModal('report');
                    setGeneratedSuccess(false);
                  }}
                  className="px-5 py-2 bg-[#0F284E] hover:bg-[#173A6E] text-white font-semibold rounded-lg text-xs flex items-center space-x-2 shadow-sm"
                >
                  <Download className="w-4 h-4" />
                  <span>Open & Print Dossier</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Select Event */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Select Incident Event
                </label>
                <select
                  value={selectedEventId}
                  onChange={(e) => setSelectedEventId(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 rounded-lg border border-slate-300 text-slate-800 text-xs focus:ring-1 focus:ring-blue-500"
                >
                  {events.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.id} — {ev.location} ({ev.risk} Risk, {ev.candidateSource})
                    </option>
                  ))}
                </select>
              </div>

              {/* Report Template Type */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Report Template Format
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div
                    onClick={() => setReportType('full-attribution')}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      reportType === 'full-attribution' ? 'border-blue-600 bg-blue-50/50' : 'border-slate-200'
                    }`}
                  >
                    <div className="font-bold text-slate-800 text-xs">Full Attribution Dossier</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">Satellite imagery, wind vectors, candidate sources</div>
                  </div>

                  <div
                    onClick={() => setReportType('executive-summary')}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      reportType === 'executive-summary' ? 'border-blue-600 bg-blue-50/50' : 'border-slate-200'
                    }`}
                  >
                    <div className="font-bold text-slate-800 text-xs">Executive Regulatory Summary</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">CPCB compliance violation brief & timeline</div>
                  </div>
                </div>
              </div>

              {/* Time Horizon */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Temporal Horizon
                </label>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 rounded-lg border border-slate-300 text-slate-800 text-xs"
                >
                  <option value="single-day">Detection Day Only</option>
                  <option value="last-7-days">Last 7 Days (Baseline & Aftermath)</option>
                  <option value="last-30-days">Last 30 Days (Historical Trend)</option>
                  <option value="last-90-days">Quarterly Environmental Audit</option>
                </select>
              </div>

              {/* Security Classification Note */}
              <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 flex items-start space-x-2 text-xs text-amber-800">
                <ShieldCheck className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <span>
                  Generated reports contain forensic timestamp data watermarked for Central & State Pollution Control Board submission.
                </span>
              </div>

              {/* Action */}
              <div className="pt-2">
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="w-full py-3 bg-[#0F284E] hover:bg-[#173A6E] text-white font-semibold rounded-lg flex items-center justify-center space-x-2 text-xs shadow-md transition-colors cursor-pointer"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Synthesizing Satellite Data & AI Attribution Model...</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4" />
                      <span>Generate Report Now</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
export default GenerateReportModal;
