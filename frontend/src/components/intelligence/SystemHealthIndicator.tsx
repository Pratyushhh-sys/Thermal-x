/**
 * SystemHealthIndicator — Feature 6
 * Shows real system status from GET /api/health.
 *
 * Backend fields used:
 *   status           → "ok" | other
 *   model_loaded     → boolean
 *   events_available → integer
 *   osm_cache_types  → integer (9 = all loaded)
 *   details.classes  → ML class list
 *   details.obs_window.obs_start / obs_end → data window
 *
 * Does NOT hardcode "Online". Reflects actual API response.
 */
import React, { useState, useCallback } from 'react';
import { Activity, RefreshCw, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { fetchHealth } from '../../api';

interface HealthData {
  status: string;
  model_loaded: boolean;
  events_available: number;
  osm_cache_types: number;
  details?: {
    classes?: string[];
    obs_window?: { obs_start?: string; obs_end?: string; obs_days?: number };
    osm_types_loaded?: string[];
  };
}

type ComponentStatus = 'ok' | 'warn' | 'error' | 'loading';

interface StatusRow {
  label: string;
  status: ComponentStatus;
  detail: string;
}

function buildRows(h: HealthData | null, err: string | null): StatusRow[] {
  if (err) {
    return [{ label: 'Backend', status: 'error', detail: 'Unreachable' }];
  }
  if (!h) return [];

  const rows: StatusRow[] = [];

  rows.push({
    label: 'Backend API',
    status: h.status === 'ok' ? 'ok' : 'warn',
    detail: h.status === 'ok' ? 'Online' : h.status,
  });

  rows.push({
    label: 'ML Model',
    status: h.model_loaded ? 'ok' : 'error',
    detail: h.model_loaded ? `Loaded (Exp C + A)` : 'Not loaded',
  });

  rows.push({
    label: 'Event Data',
    status: (h.events_available ?? 0) > 0 ? 'ok' : 'warn',
    detail: (h.events_available ?? 0) > 0 ? `${(h.events_available ?? 0).toLocaleString()} events` : 'No events',
  });

  const osmTotal = 9; // 9 OSM feature types expected
  const osmLoaded = h.osm_cache_types ?? 0;
  rows.push({
    label: 'OSM Cache',
    status: osmLoaded === osmTotal ? 'ok' : osmLoaded > 0 ? 'warn' : 'error',
    detail: `${osmLoaded} / ${osmTotal} feature types`,
  });

  const obsWindow = h.details?.obs_window;
  if (obsWindow?.obs_start && obsWindow?.obs_end) {
    rows.push({
      label: 'Data Window',
      status: 'ok',
      detail: `${obsWindow.obs_start} → ${obsWindow.obs_end} (${obsWindow.obs_days ?? '?'} days)`,
    });
  }

  return rows;
}

function StatusIcon({ status }: { status: ComponentStatus }) {
  if (status === 'loading') return <RefreshCw className="w-3.5 h-3.5 text-slate-400 animate-spin" />;
  if (status === 'ok') return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
  if (status === 'warn') return <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />;
  return <XCircle className="w-3.5 h-3.5 text-red-500" />;
}

interface Props {
  initialData?: HealthData | null;
}

export const SystemHealthIndicator: React.FC<Props> = ({ initialData = null }) => {
  const [health, setHealth] = useState<HealthData | null>(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }));
    } catch (e) {
      setError('Backend unreachable');
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load once on mount if no initial data
  React.useEffect(() => {
    if (!initialData) refresh();
  }, []);

  const rows = buildRows(health, error);
  const overallOk = !error && health?.status === 'ok' && health?.model_loaded;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Activity className={`w-4 h-4 ${overallOk ? 'text-emerald-500' : 'text-amber-500'}`} />
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">System Status</span>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center space-x-1 text-[10px] text-blue-600 hover:text-blue-800 font-medium transition-colors disabled:opacity-50"
          title="Refresh system status"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {rows.length === 0 && loading && (
        <p className="text-xs text-slate-400 italic">Checking system status...</p>
      )}

      <div className="space-y-2">
        {rows.map(row => (
          <div key={row.label} className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <StatusIcon status={loading ? 'loading' : row.status} />
              <span className="text-[11px] text-slate-700 font-medium">{row.label}</span>
            </div>
            <span className="text-[10px] text-slate-500 tabular-nums">{row.detail}</span>
          </div>
        ))}
      </div>

      {lastChecked && (
        <p className="text-[10px] text-slate-400 mt-3">Last checked: {lastChecked} IST</p>
      )}
      {error && (
        <p className="text-[10px] text-red-500 mt-2 font-medium">{error}</p>
      )}
    </div>
  );
};

export default SystemHealthIndicator;
