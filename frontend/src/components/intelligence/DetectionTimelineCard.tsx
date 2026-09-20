/**
 * DetectionTimelineCard — Feature 5
 * Shows the 7-day persistence summary using EXISTING backend persistence fields.
 *
 * Backend fields used:
 *   persistence.active_days_last_7       → integer count of active days
 *   persistence.persistence_ratio         → float 0–1
 *   persistence.observation_count_last_7  → total observations in window
 *   persistence.trend_label              → "intermittent" | "persistent" | etc.
 *   persistence.avg_frp, max_frp, min_frp → FRP stats
 *
 * IMPORTANT: The backend does NOT expose individual day-by-day observation records
 * (it only returns aggregate counts). Therefore this card does NOT fabricate a
 * per-day timeline. It shows the aggregate data honestly.
 *
 * If the backend ever exposes daily_observations[], this can be upgraded.
 */
import React from 'react';
import { Calendar, TrendingUp, Activity } from 'lucide-react';
import { ThermalEvent } from '../../data/mockData';

interface Props {
  event: ThermalEvent;
}

function trendColor(label: string): string {
  const l = label?.toLowerCase() ?? '';
  if (l.includes('persistent') || l.includes('active')) return 'text-red-600';
  if (l.includes('intermittent')) return 'text-amber-600';
  return 'text-slate-600';
}

export const DetectionTimelineCard: React.FC<Props> = ({ event }) => {
  const p = event.rawDetail?.persistence;

  if (!p) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">7-Day Detection Summary</p>
        <p className="text-xs text-slate-400 italic">Select an event to view detection history.</p>
      </div>
    );
  }

  const activeDays: number = p.active_days_last_7 ?? 0;
  const totalDays = 7;
  const ratio: number = p.persistence_ratio ?? 0;
  const trend: string = p.trend_label ?? 'Unknown';
  const obsCount: number = p.observation_count_last_7 ?? activeDays;
  const avgFrp: number | null = p.avg_frp ?? null;
  const maxFrp: number | null = p.max_frp ?? null;

  // Build a simplified visual bar for active vs inactive days
  // We know total active days but NOT which specific days — show as blocks honestly
  const pct = Math.round((activeDays / totalDays) * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center space-x-2 mb-3">
        <Calendar className="w-4 h-4 text-blue-600" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">7-Day Detection Summary</span>
      </div>

      {/* Active days visual */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-semibold text-slate-700">Active Days (Last 7)</span>
          <span className="text-[11px] font-bold text-slate-800 tabular-nums">{activeDays} / {totalDays}</span>
        </div>
        <div className="flex space-x-1">
          {Array.from({ length: totalDays }).map((_, i) => (
            <div
              key={i}
              className={`flex-1 h-4 rounded-sm ${i < activeDays ? 'bg-orange-500' : 'bg-slate-100 border border-slate-200'}`}
              title={i < activeDays ? 'Active' : 'No detection'}
            />
          ))}
        </div>
        <p className="text-[10px] text-slate-400 mt-1 italic">
          Filled blocks = active days (distribution unknown — backend reports aggregate only)
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-slate-50 rounded-lg p-2.5">
          <p className="text-slate-400 mb-0.5">Persistence</p>
          <p className="font-bold text-slate-800">{(ratio * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-2.5">
          <p className="text-slate-400 mb-0.5">Trend</p>
          <p className={`font-bold capitalize ${trendColor(trend)}`}>{trend}</p>
        </div>
        {obsCount != null && (
          <div className="bg-slate-50 rounded-lg p-2.5">
            <p className="text-slate-400 mb-0.5">Observations</p>
            <p className="font-bold text-slate-800">{obsCount}</p>
          </div>
        )}
        {avgFrp != null && (
          <div className="bg-slate-50 rounded-lg p-2.5">
            <p className="text-slate-400 mb-0.5">Avg FRP</p>
            <p className="font-bold text-slate-800">{avgFrp.toFixed(1)} MW</p>
          </div>
        )}
        {maxFrp != null && (
          <div className="bg-slate-50 rounded-lg p-2.5">
            <p className="text-slate-400 mb-0.5">Peak FRP</p>
            <p className="font-bold text-red-600">{maxFrp.toFixed(1)} MW</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DetectionTimelineCard;
