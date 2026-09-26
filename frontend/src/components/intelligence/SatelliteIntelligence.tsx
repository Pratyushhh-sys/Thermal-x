import React, { useState, useEffect } from 'react';
import {
  Satellite, RefreshCw, ExternalLink, AlertTriangle, Layers,
  ChevronDown, ChevronUp, Clock, Info, Thermometer, Eye
} from 'lucide-react';
import { fetchEventImagery } from '../../api';

interface SatelliteIntelligenceProps {
  event: any;
}

// IRON heatmap legend stops (matches Python evalscript)
const IRON_LEGEND = [
  { pct: 0,   label: '270 K', color: '#050505' },
  { pct: 25,  label: '297 K', color: '#7f0000' },
  { pct: 50,  label: '325 K', color: '#ff6600' },
  { pct: 75,  label: '352 K', color: '#ffff00' },
  { pct: 100, label: '380 K', color: '#ffffff' },
];

export const SatelliteIntelligence: React.FC<SatelliteIntelligenceProps> = ({ event }) => {
  const [mode, setMode] = useState<'optical' | 'thermal' | 'compare'>('optical');
  const [metaLoading, setMetaLoading] = useState(true);
  const [meta, setMeta] = useState<any>(null);
  const [metaError, setMetaError] = useState(false);

  const [opticalLoading, setOpticalLoading] = useState(true);
  const [opticalError, setOpticalError]   = useState(false);
  const [thermalLoading, setThermalLoading] = useState(false);
  const [thermalImgError, setThermalImgError] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [showOpticalMeta, setShowOpticalMeta] = useState(false);
  const [showThermalMeta, setShowThermalMeta] = useState(false);

  // Fetch imagery metadata whenever the event changes
  useEffect(() => {
    setMetaLoading(true);
    setMetaError(false);
    setMeta(null);
    fetchEventImagery(event.id)
      .then(data => { setMeta(data); setMetaLoading(false); })
      .catch(() => { setMetaError(true); setMetaLoading(false); });
  }, [event.id]);

  // Reset optical loading state
  useEffect(() => {
    setOpticalLoading(true);
    setOpticalError(false);
  }, [event.id, refreshKey]);

  // Reset thermal loading state when switching to thermal/compare
  useEffect(() => {
    if (mode === 'thermal' || mode === 'compare') {
      setThermalLoading(true);
      setThermalImgError(false);
    }
  }, [event.id, mode]);

  // ------------------------------------------------------------------ //
  //  Optical / SAR viewer
  // ------------------------------------------------------------------ //
  const renderOpticalViewer = (compact = false) => (
    <div className={`relative w-full ${compact ? 'h-52' : 'h-64 sm:h-80'} bg-slate-900 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center group shadow-inner`}>
      {opticalLoading && (
        <div className="absolute inset-0 z-10 bg-slate-900 flex flex-col items-center justify-center p-4 text-center">
          <div className="relative mb-3">
            <div className="w-12 h-12 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
            <Satellite className="w-5 h-5 text-blue-400 absolute inset-0 m-auto" />
          </div>
          <div className="text-xs font-semibold text-slate-200">Acquiring Sentinel-2 L2A Tile...</div>
        </div>
      )}

      {opticalError && (
        <div className="absolute top-2 left-2 right-2 z-20 bg-amber-500/90 backdrop-blur-xs text-slate-950 px-3 py-1.5 rounded-lg text-[11px] font-medium flex items-center justify-between border border-amber-400">
          <div className="flex items-center space-x-1.5">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Live acquisition unavailable — showing cached preview.</span>
          </div>
        </div>
      )}

      <img
        src={opticalError ? '/assets/selected_event_th1024.png' : `/api/imagery/${event.id}?v=${refreshKey}`}
        alt={`Sentinel-2 L2A optical image for event ${event.id}`}
        onLoad={() => setOpticalLoading(false)}
        onError={() => { setOpticalError(true); setOpticalLoading(false); }}
        className={`w-full h-full object-cover select-none transition-opacity duration-500 ${opticalLoading ? 'opacity-0' : 'opacity-100'}`}
      />

      {/* HUD badge */}
      <div className="absolute bottom-2 left-2 z-10 bg-slate-950/75 backdrop-blur-xs text-white px-2.5 py-1 rounded-md text-[10px] font-mono border border-white/10 flex items-center space-x-2">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span>SENTINEL-2 L2A • TRUE-COLOR RGB</span>
        <span>•</span>
        <span>10 m</span>
      </div>
    </div>
  );

  // ------------------------------------------------------------------ //
  //  Thermal viewer
  // ------------------------------------------------------------------ //
  const renderThermalViewer = (compact = false) => {
    if (metaLoading) {
      return (
        <div className={`w-full ${compact ? 'h-52' : 'h-64 sm:h-80'} bg-slate-100 rounded-xl flex items-center justify-center border border-slate-200`}>
          <span className="text-slate-500 text-sm flex items-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Loading thermal metadata...</span>
          </span>
        </div>
      );
    }

    const thermal = meta?.thermal;

    // ---- Unavailable state ----
    if (!thermal || !thermal.available) {
      return (
        <div className={`w-full ${compact ? 'h-52' : 'h-64 sm:h-80'} bg-slate-50 rounded-xl border border-slate-200 flex flex-col items-center justify-center text-center p-5 space-y-3`}>
          <div className="p-3 bg-slate-100 rounded-full text-slate-400">
            <Layers className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-700">Thermal Imagery Unavailable</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
              {thermal?.reason || 'No compatible Sentinel-3 SLSTR scene is available for this event.'}
            </p>
          </div>

          {/* Diagnostic info box */}
          <div className="text-[11px] bg-white border border-slate-200 px-3 py-2 rounded-lg text-left w-full max-w-xs space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-400">Search Window:</span>
              <span className="font-medium text-slate-700">
                {thermal?.metadata?.temporal_window || '±6 Hours'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Data Source:</span>
              <span className="font-medium text-slate-700">
                {thermal?.source || 'Sentinel-3 SLSTR'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Event Time:</span>
              <span className="font-medium text-slate-700">
                {thermal?.metadata?.event_time || event.detectedOn}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Band:</span>
              <span className="font-medium text-slate-700">
                {thermal?.metadata?.band || 'S8 (10.85 µm — TIR)'}
              </span>
            </div>
          </div>
        </div>
      );
    }

    // ---- Available thermal image ----
    return (
      <div className={`relative w-full ${compact ? 'h-52' : 'h-64 sm:h-80'} bg-slate-900 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center group shadow-inner`}>
        {thermalLoading && (
          <div className="absolute inset-0 z-10 bg-slate-900 flex flex-col items-center justify-center p-4 text-center">
            <div className="relative mb-3">
              <div className="w-12 h-12 rounded-full border-2 border-orange-500/20 border-t-orange-500 animate-spin" />
              <Thermometer className="w-5 h-5 text-orange-400 absolute inset-0 m-auto" />
            </div>
            <div className="text-xs font-semibold text-slate-200">Loading Sentinel-3 SLSTR TIR...</div>
          </div>
        )}

        {thermalImgError ? (
          <div className="flex flex-col items-center justify-center text-center p-4 space-y-2">
            <AlertTriangle className="w-8 h-8 text-amber-400" />
            <p className="text-xs text-slate-300 max-w-xs">
              Thermal imagery could not be loaded. The event data and optical imagery remain available.
            </p>
          </div>
        ) : (
          <img
            src={`${thermal.image_url}?v=${refreshKey}`}
            alt={`Sentinel-3 SLSTR thermal infrared image for event ${event.id}`}
            onLoad={() => setThermalLoading(false)}
            onError={() => { setThermalImgError(true); setThermalLoading(false); }}
            className={`w-full h-full object-cover select-none transition-opacity duration-500 ${thermalLoading ? 'opacity-0' : 'opacity-100'}`}
          />
        )}

        {/* IRON heatmap legend (vertical, right side) */}
        {!thermalImgError && !thermalLoading && (
          <div className="absolute top-2 right-2 z-10 bg-slate-950/80 backdrop-blur-xs text-white p-2 rounded-lg border border-white/10 flex flex-col items-center space-y-1 min-w-[60px]">
            <div className="text-[8px] uppercase font-bold text-slate-300 mb-0.5">Temp (K)</div>
            <div className="flex items-stretch space-x-1.5">
              {/* Gradient bar */}
              <div
                className="w-3 h-24 rounded-sm"
                style={{ background: 'linear-gradient(to bottom, #ffffff, #ffff00, #ff6600, #7f0000, #050505)' }}
              />
              {/* Labels */}
              <div className="flex flex-col justify-between text-[9px] font-mono">
                <span>{thermal.metadata?.max_temp || '380 K'}</span>
                <span>{thermal.metadata?.min_temp || '270 K'}</span>
              </div>
            </div>
            <div className="text-[8px] text-orange-300 mt-0.5">IRON</div>
          </div>
        )}

        {/* Acquisition delta badge */}
        {thermal.time_delta_label && !thermalImgError && !thermalLoading && (
          <div className="absolute top-2 left-2 z-10 bg-orange-900/80 backdrop-blur-xs text-orange-100 px-2 py-1 rounded-md text-[10px] font-medium border border-orange-500/30 flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{thermal.time_delta_label}</span>
          </div>
        )}

        {/* HUD badge bottom */}
        {!thermalImgError && (
          <div className="absolute bottom-2 left-2 z-10 bg-slate-950/75 backdrop-blur-xs text-white px-2.5 py-1 rounded-md text-[10px] font-mono border border-white/10 flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-orange-400 animate-pulse" />
            <span>SENTINEL-3 SLSTR • S8 TIR</span>
            <span>•</span>
            <span>~1 km</span>
          </div>
        )}
      </div>
    );
  };

  // ------------------------------------------------------------------ //
  //  Metadata panel
  // ------------------------------------------------------------------ //
  const renderOpticalMetadata = () => {
    const opt = meta?.optical;
    if (!opt) return null;
    const m = opt.metadata || {};
    return (
      <div className="mt-3 p-3 bg-slate-50 border border-slate-100 rounded-lg text-[11px] text-slate-700 space-y-1.5">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Optical / SAR Metadata</div>
        {[
          { label: 'Satellite', value: m.satellite || 'Sentinel-2A / Sentinel-2B' },
          { label: 'Product', value: m.product || 'S2_L2A' },
          { label: 'Bands', value: m.bands || 'B04 (R), B03 (G), B02 (B)' },
          { label: 'Resolution', value: m.resolution || '10 m' },
          { label: 'Processing', value: m.processing_level || 'L2A' },
          { label: 'Coordinates', value: event.coordinates },
          { label: 'Acquisition', value: opt.acquisition_time || 'Recent window' },
        ].map(({ label, value }) => value ? (
          <div key={label} className="flex justify-between items-start gap-2">
            <span className="text-slate-400 shrink-0">{label}:</span>
            <span className="font-medium text-slate-700 text-right">{value}</span>
          </div>
        ) : null)}
      </div>
    );
  };

  const renderThermalMetadata = () => {
    const th = meta?.thermal;
    if (!th) return null;
    const m = th.metadata || {};
    const rows = [
      { label: 'Satellite', value: m.satellite || 'Sentinel-3A / Sentinel-3B' },
      { label: 'Product', value: m.product || 'SL_2_LST___' },
      { label: 'Band', value: m.band || 'S8 (10.85 µm — TIR)' },
      { label: 'Resolution', value: m.resolution || '~1 km' },
      { label: 'Processing', value: m.processing_level || 'L2' },
      { label: 'Temp Units', value: m.temperature_units || 'Kelvin (K)' },
      ...(th.available ? [
        { label: 'Min Temp', value: m.min_temp || '270 K' },
        { label: 'Max Temp', value: m.max_temp || '380 K' },
      ] : []),
      { label: 'Search Window', value: m.temporal_window || '±6 hours' },
      { label: 'Color Ramp', value: m.color_ramp || 'IRON heatmap' },
      { label: 'Coordinates', value: event.coordinates },
      ...(th.acquisition_time ? [{ label: 'Acquisition', value: th.acquisition_time }] : []),
      ...(th.available ? [] : [{ label: 'Status', value: 'Unavailable' }]),
    ];
    return (
      <div className="mt-3 p-3 bg-orange-50/60 border border-orange-100 rounded-lg text-[11px] text-slate-700 space-y-1.5">
        <div className="text-[10px] font-bold text-orange-400 uppercase tracking-wider mb-2">Thermal (SLSTR) Metadata</div>
        {rows.map(({ label, value }) => value ? (
          <div key={label} className="flex justify-between items-start gap-2">
            <span className="text-slate-400 shrink-0">{label}:</span>
            <span className="font-medium text-slate-700 text-right">{value}</span>
          </div>
        ) : null)}
        {!th.available && th.reason && (
          <div className="pt-1 mt-1 border-t border-orange-200 text-orange-700 leading-relaxed">
            <Info className="w-3 h-3 inline mr-1" />
            {th.reason}
          </div>
        )}
        {!th.available && (
          <div className="pt-1 text-slate-500 text-[10px]">
            Note: Sentinel-2 L2A does not provide thermal infrared imagery.
            True TIR requires Sentinel-3 SLSTR (S8 band, 10.85 µm).
          </div>
        )}
      </div>
    );
  };

  // ------------------------------------------------------------------ //
  //  Satellite evidence summary (for risk intelligence integration)
  // ------------------------------------------------------------------ //
  const thermalAvailable = meta?.thermal?.available === true;
  const opticalAvailable = meta?.optical?.available === true;

  // ------------------------------------------------------------------ //
  //  Main render
  // ------------------------------------------------------------------ //
  return (
    <div className="p-4 sm:p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-4">

      {/* Header and Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between space-y-3 sm:space-y-0">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-md bg-blue-50 text-blue-700 border border-blue-100">
            <Satellite className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-[#0F284E] uppercase tracking-wider">
              Satellite Intelligence
            </h4>
            {!metaLoading && !metaError && (
              <div className="flex items-center space-x-2 mt-0.5">
                <span className={`inline-flex items-center space-x-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded ${opticalAvailable ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-400'}`}>
                  <Eye className="w-2.5 h-2.5" />
                  <span>Optical</span>
                </span>
                <span className={`inline-flex items-center space-x-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded ${thermalAvailable ? 'bg-orange-50 text-orange-700 border border-orange-200' : 'bg-slate-100 text-slate-400'}`}>
                  <Thermometer className="w-2.5 h-2.5" />
                  <span>Thermal {thermalAvailable ? '✓' : '—'}</span>
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button
            onClick={() => setMode('optical')}
            className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-colors ${mode === 'optical' ? 'bg-white text-blue-700 shadow-sm border border-slate-200' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Optical / SAR
          </button>
          <button
            onClick={() => setMode('thermal')}
            className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-colors ${mode === 'thermal' ? 'bg-white text-orange-600 shadow-sm border border-slate-200' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Thermal
          </button>
          <button
            onClick={() => setMode('compare')}
            className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-colors ${mode === 'compare' ? 'bg-white text-purple-700 shadow-sm border border-slate-200' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Compare
          </button>
        </div>
      </div>

      {/* ---- Main Viewer ---- */}
      {mode === 'optical' && renderOpticalViewer()}
      {mode === 'thermal' && renderThermalViewer()}

      {mode === 'compare' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <div className="text-[11px] font-bold text-blue-700 uppercase px-1 flex items-center space-x-1">
              <Eye className="w-3 h-3" />
              <span>Optical / SAR</span>
            </div>
            {renderOpticalViewer(true)}
            {/* Optical metadata inline */}
            {!metaLoading && meta?.optical && (
              <div className="px-1 text-[10px] text-slate-500 space-y-0.5">
                <div><span className="font-medium text-slate-700">Source:</span> {meta.optical.source}</div>
                <div><span className="font-medium text-slate-700">Acq:</span> {meta.optical.acquisition_time || 'Recent window'}</div>
                <div><span className="font-medium text-slate-700">Resolution:</span> {meta.optical.metadata?.resolution || '10 m'}</div>
              </div>
            )}
          </div>
          <div className="space-y-1.5">
            <div className="text-[11px] font-bold text-orange-700 uppercase px-1 flex items-center space-x-1">
              <Thermometer className="w-3 h-3" />
              <span>Thermal Infrared</span>
            </div>
            {renderThermalViewer(true)}
            {/* Thermal metadata inline */}
            {!metaLoading && meta?.thermal && (
              <div className="px-1 text-[10px] text-slate-500 space-y-0.5">
                <div><span className="font-medium text-slate-700">Source:</span> {meta.thermal.source || 'Sentinel-3 SLSTR'}</div>
                <div><span className="font-medium text-slate-700">Acq:</span> {meta.thermal.acquisition_time || (meta.thermal.available ? 'Available' : 'Unavailable')}</div>
                <div><span className="font-medium text-slate-700">Band:</span> {meta.thermal.metadata?.band || 'S8 (10.85 µm — TIR)'}</div>
                {meta.thermal.acquisition_time && meta.optical.acquisition_time &&
                  meta.thermal.acquisition_time !== meta.optical.acquisition_time && (
                  <div className="text-amber-600 font-medium flex items-center space-x-1">
                    <AlertTriangle className="w-2.5 h-2.5" />
                    <span>Optical and thermal scenes have different acquisition times.</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Action buttons (optical mode) ---- */}
      {mode === 'optical' && (
        <div className="flex items-center justify-between pt-1">
          <button
            onClick={() => setShowOpticalMeta(v => !v)}
            className="px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors border border-slate-200 flex items-center space-x-1"
          >
            {showOpticalMeta ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            <span>Image Metadata</span>
          </button>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setRefreshKey(k => k + 1)}
              className="px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors flex items-center space-x-1"
            >
              <RefreshCw className={`w-3 h-3 ${opticalLoading ? 'animate-spin text-blue-600' : ''}`} />
              <span>Refresh</span>
            </button>
            <a
              href={`/api/imagery/${event.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 text-[11px] font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors flex items-center space-x-1"
            >
              <ExternalLink className="w-3 h-3" />
              <span>Full View</span>
            </a>
          </div>
        </div>
      )}

      {mode === 'thermal' && !metaLoading && (
        <div className="flex items-center justify-between pt-1">
          <button
            onClick={() => setShowThermalMeta(v => !v)}
            className="px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors border border-slate-200 flex items-center space-x-1"
          >
            {showThermalMeta ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            <span>Thermal Metadata</span>
          </button>
          {meta?.thermal?.available && (
            <a
              href={`/api/imagery/${event.id}/thermal`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 text-[11px] font-medium text-orange-700 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-md transition-colors flex items-center space-x-1"
            >
              <ExternalLink className="w-3 h-3" />
              <span>Full View</span>
            </a>
          )}
        </div>
      )}

      {/* ---- Expandable Metadata Panels ---- */}
      {showOpticalMeta && renderOpticalMetadata()}
      {showThermalMeta && renderThermalMetadata()}

      {/* ---- Satellite evidence summary (always visible at bottom) ---- */}
      {!metaLoading && !metaError && (
        <div className="pt-3 border-t border-slate-100">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Satellite Evidence</div>
          <div className="grid grid-cols-2 gap-2">
            <div className={`flex items-center space-x-2 p-2 rounded-lg border text-[11px] ${opticalAvailable ? 'bg-emerald-50 border-emerald-100 text-emerald-800' : 'bg-slate-50 border-slate-100 text-slate-500'}`}>
              <Eye className="w-3.5 h-3.5 flex-shrink-0" />
              <div>
                <div className="font-semibold">Optical/SAR</div>
                <div className="text-[10px] opacity-80">{opticalAvailable ? 'Sentinel-2 L2A' : 'Unavailable'}</div>
              </div>
            </div>
            <div className={`flex items-center space-x-2 p-2 rounded-lg border text-[11px] ${thermalAvailable ? 'bg-orange-50 border-orange-100 text-orange-800' : 'bg-slate-50 border-slate-100 text-slate-500'}`}>
              <Thermometer className="w-3.5 h-3.5 flex-shrink-0" />
              <div>
                <div className="font-semibold">Thermal IR</div>
                <div className="text-[10px] opacity-80">{thermalAvailable ? 'Sentinel-3 SLSTR S8' : 'Not available'}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SatelliteIntelligence;
