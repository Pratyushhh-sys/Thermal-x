import React, { useState, useEffect } from 'react';
import { X, Send, AlertTriangle, ShieldAlert, FileText, CheckCircle, Info, Activity } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';
import { fetchAuthorities, forwardAlert } from '../../api';

export const ForwardAlertModal: React.FC = () => {
  const { selectedEvent, activeModal, setActiveModal, refreshForwardHistory } = useThermal();
  const [authorities, setAuthorities] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [authorityId, setAuthorityId] = useState('');
  const [officerName, setOfficerName] = useState('');
  const [contactInfo, setContactInfo] = useState('');
  const [message, setMessage] = useState('');
  const [includeReport, setIncludeReport] = useState(true);
  
  const [step, setStep] = useState<'form' | 'confirm' | 'success'>('form');
  const [error, setError] = useState<string | null>(null);
  const [trackingId, setTrackingId] = useState('');
  const [submittedStatus, setSubmittedStatus] = useState('');

  useEffect(() => {
    if (activeModal === 'forward-alert' && selectedEvent) {
      // Reset state
      setStep('form');
      setError(null);
      setAuthorityId('');
      setOfficerName('');
      setContactInfo('');
      setIncludeReport(true);
      
      // Auto-generate message
      const defaultMsg = `High-risk thermal anomaly detected by the satellite-based monitoring system.

Event ID: ${selectedEvent.id}
Risk Level: ${selectedEvent.risk.toUpperCase()}
Risk Score: ${Math.round(selectedEvent.riskScore || 0)}/100
Classification: ${selectedEvent.probableSource} (Probable)
FRP: ${selectedEvent.frp}
Location: ${selectedEvent.coordinates}
Detection Time: ${selectedEvent.detectedOn} UTC
Satellite Evidence: Optical (Sentinel-2 L2A) and Thermal Infrared (Sentinel-3 SLSTR S8) analysis attached.

The system recommends immediate review of this event based on the calculated risk score and observed thermal characteristics.

Please review the incident and take appropriate action according to your operational procedures.`;
      
      setMessage(defaultMsg);

      // Load authorities
      fetchAuthorities()
        .then(data => setAuthorities(data))
        .catch(err => console.error('Failed to load authorities', err));
    }
  }, [activeModal, selectedEvent]);

  if (activeModal !== 'forward-alert' || !selectedEvent) return null;

  const isCritical = (selectedEvent.risk as string) === 'Critical' || (selectedEvent.riskScore != null && selectedEvent.riskScore >= 90);
  const isHigh = selectedEvent.risk === 'High' || isCritical;

  if (!isHigh) {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fadeIn">
        <div className="bg-white rounded-2xl max-w-md w-full p-6 text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold mb-2">Event Not Eligible for Forwarding</h3>
          <p className="text-sm text-slate-500 mb-6">Only HIGH or CRITICAL risk events can be forwarded to authorities.</p>
          <button onClick={() => setActiveModal(null)} className="btn-primary w-full py-2">Close</button>
        </div>
      </div>
    );
  }

  const selectedAuthObj = authorities.find(a => a.id === authorityId);

  const handleReview = () => {
    if (!authorityId) {
      setError('Please select a concerned authority.');
      return;
    }
    if (message.length < 10) {
      setError('Message must be at least 10 characters.');
      return;
    }
    setError(null);
    setStep('confirm');
  };

  const handleConfirmSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        authority_id: authorityId,
        authority_name: selectedAuthObj?.name || 'Unknown',
        authority_officer: officerName || undefined,
        authority_contact: contactInfo || selectedAuthObj?.contact_placeholder || undefined,
        message,
        include_report: includeReport,
        forwarded_by: 'ThermalX_Operator', // Mock user
      };
      const res = await forwardAlert(selectedEvent.id, payload);
      setTrackingId(res.tracking_id);
      setSubmittedStatus(res.status);
      setStep('success');
      refreshForwardHistory();
    } catch (err: any) {
      setError(err.message || 'Unable to forward this alert. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-5 bg-slate-950/70 backdrop-blur-xs overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className={`p-4 sm:p-5 flex items-center justify-between text-white ${isCritical ? 'bg-red-700' : 'bg-red-600'}`}>
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-white/20">
              {isCritical ? <ShieldAlert className="w-5 h-5" /> : <Send className="w-5 h-5" />}
            </div>
            <div>
              <div className="text-[11px] font-semibold text-white/80 uppercase tracking-wider">
                Emergency Response Workflow
              </div>
              <h3 className="text-lg font-bold">
                {isCritical ? '🚨 Forward Critical Alert' : 'Forward High-Risk Incident'}
              </h3>
            </div>
          </div>
          <button onClick={() => setActiveModal(null)} className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto flex-1 text-sm text-slate-800">
          
          {step === 'form' && (
            <div className="space-y-6">
              
              {/* Event Summary Box */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row gap-4 justify-between">
                <div>
                  <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Incident Summary</div>
                  <div className="font-bold text-slate-900 text-lg mb-1">{selectedEvent.id}</div>
                  <div className="text-xs text-slate-600">{selectedEvent.location}</div>
                  <div className="text-xs text-slate-600 mt-1">Classification: {selectedEvent.probableSource}</div>
                </div>
                <div className="text-left sm:text-right">
                  <div className={`inline-flex px-2 py-1 rounded text-xs font-bold ${isCritical ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-orange-100 text-orange-700 border border-orange-200'}`}>
                    {selectedEvent.risk} Risk ({Math.round(selectedEvent.riskScore || 0)}/100)
                  </div>
                  <div className="text-xs text-slate-600 mt-2">Detected: {selectedEvent.detectedOn}</div>
                  <div className="text-xs text-slate-600">FRP: {selectedEvent.frp}</div>
                </div>
              </div>

              {/* Authority Selection */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-900">Concerned Authority</h4>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Select Authority <span className="text-red-500">*</span></label>
                  <select 
                    value={authorityId}
                    onChange={(e) => setAuthorityId(e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                  >
                    <option value="">-- Select Authority --</option>
                    {authorities.map(a => (
                      <option key={a.id} value={a.id}>{a.name} {a.department ? `(${a.department})` : ''}</option>
                    ))}
                  </select>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Authority / Officer Name (Optional)</label>
                    <input 
                      type="text" 
                      value={officerName}
                      onChange={(e) => setOfficerName(e.target.value)}
                      placeholder="e.g. District Collector"
                      className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Official Contact (Optional)</label>
                    <input 
                      type="text" 
                      value={contactInfo}
                      onChange={(e) => setContactInfo(e.target.value)}
                      placeholder={selectedAuthObj?.contact_placeholder || "email or phone"}
                      className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* Message Box */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900">Forward Message</h4>
                <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs p-2 rounded flex items-start gap-2">
                  <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <p>Use appropriate wording like "thermal anomaly detected" or "potential incident". Do not claim a confirmed violation unless verified.</p>
                </div>
                <textarea 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={8}
                  className="w-full p-3 text-sm rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                />
              </div>

              {/* Attachments */}
              <div>
                <label className="flex items-center space-x-2 cursor-pointer p-3 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors">
                  <input 
                    type="checkbox" 
                    checked={includeReport}
                    onChange={(e) => setIncludeReport(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                  />
                  <FileText className="w-4 h-4 text-slate-500" />
                  <span className="text-sm font-semibold text-slate-700">Include Comprehensive Incident Report (Auto-generated)</span>
                </label>
              </div>

              {error && (
                <div className="p-3 bg-red-50 text-red-700 text-sm font-medium rounded-lg border border-red-200">
                  {error}
                </div>
              )}
            </div>
          )}

          {step === 'confirm' && (
            <div className="space-y-6 text-center py-4">
              <AlertTriangle className={`w-16 h-16 mx-auto mb-4 ${isCritical ? 'text-red-600' : 'text-amber-500'}`} />
              <h3 className="text-xl font-bold text-slate-900">Confirm Forwarding</h3>
              <p className="text-slate-600 max-w-md mx-auto">
                Are you sure you want to forward this {selectedEvent.risk.toLowerCase()}-risk incident to the <span className="font-bold text-slate-900">{selectedAuthObj?.name}</span>?
              </p>
              
              <div className="text-left bg-slate-50 p-4 rounded-xl border border-slate-200 max-w-lg mx-auto mt-4">
                <div className="text-xs text-slate-500 font-semibold mb-2">Message Preview:</div>
                <div className="text-sm font-mono text-slate-700 whitespace-pre-wrap text-left max-h-40 overflow-y-auto">
                  {message}
                </div>
                {includeReport && (
                  <div className="mt-3 pt-3 border-t border-slate-200 flex items-center space-x-2 text-xs font-semibold text-blue-600">
                    <FileText className="w-3.5 h-3.5" />
                    <span>+ Incident Report Attached</span>
                  </div>
                )}
              </div>

              {error && (
                <div className="p-3 bg-red-50 text-red-700 text-sm font-medium rounded-lg border border-red-200 max-w-lg mx-auto">
                  {error}
                </div>
              )}
            </div>
          )}

          {step === 'success' && (
            <div className="space-y-6 text-center py-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-2xl font-bold text-slate-900">Alert Forwarded Successfully</h3>
              <p className="text-slate-600 max-w-md mx-auto">
                The alert for event <span className="font-bold">{selectedEvent.id}</span> has been forwarded to <span className="font-bold">{selectedAuthObj?.name}</span>.
              </p>
              
              <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl max-w-sm mx-auto inline-block text-left">
                <div className="text-xs text-slate-500 mb-1">Tracking ID</div>
                <div className="text-sm font-mono font-bold text-slate-900">{trackingId}</div>
                <div className="text-xs text-slate-500 mt-2 mb-1">Status</div>
                <div className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded inline-block">{submittedStatus}</div>
              </div>
              
              <div className="text-xs text-slate-400 max-w-md mx-auto mt-4">
                Note: This is a prototype system. The alert has been recorded in the forwarding history but no actual external communication was sent.
              </div>
            </div>
          )}
          
        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end space-x-3">
          {step === 'form' && (
            <>
              <button 
                onClick={() => setActiveModal(null)} 
                className="px-4 py-2 border border-slate-300 rounded-lg font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleReview}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors shadow-sm flex items-center"
              >
                Review & Forward
              </button>
            </>
          )}
          
          {step === 'confirm' && (
            <>
              <button 
                onClick={() => setStep('form')} 
                disabled={loading}
                className="px-4 py-2 border border-slate-300 rounded-lg font-semibold text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
              >
                Back to Edit
              </button>
              <button 
                onClick={handleConfirmSubmit}
                disabled={loading}
                className={`px-4 py-2 text-white rounded-lg font-bold transition-colors shadow-sm flex items-center space-x-2 ${isCritical ? 'bg-red-600 hover:bg-red-700' : 'bg-red-600 hover:bg-red-700'}`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    <span>Forwarding...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Confirm & Forward</span>
                  </>
                )}
              </button>
            </>
          )}

          {step === 'success' && (
            <button 
              onClick={() => setActiveModal(null)} 
              className="px-6 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-semibold transition-colors shadow-sm"
            >
              Done
            </button>
          )}
        </div>

      </div>
    </div>
  );
};

export default ForwardAlertModal;