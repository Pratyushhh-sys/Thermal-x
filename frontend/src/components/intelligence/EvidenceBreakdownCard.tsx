/**
 * EvidenceBreakdownCard — Feature 3
 * Visualises the EXISTING risk component scores as progress bars.
 *
 * Backend fields used:
 *   risk.components.thermal      → Thermal signal strength (0–100)
 *   risk.components.persistence  → Temporal persistence (0–100)
 *   risk.components.osm          → GIS/OSM proximity (0–100)
 *   risk.components.ai           → AI/ML classification confidence (0–100)
 *   risk.score                   → Overall composite score
 *   risk.weights                 → Component weights (for label)
 *
 * The backend is the single source of truth. No recalculation in React.
 */
import React from 'react';
import { BarChart3 } from 'lucide-react';
import { ThermalEvent } from '../../data/mockData';

interface Props {
  event: ThermalEvent;
}

interface ComponentBar {
  label: string;
  key: 'thermal' | 'persistence' | 'osm' | 'ai';
  fullLabel: string;
  color: string;
  weightKey: 'thermal' | 'persistence' | 'osm' | 'ai';
}

const COMPONENTS: ComponentBar[] = [
  { label: 'Thermal',     key: 'thermal',     fullLabel: 'Thermal Intensity',   color: 'bg-orange-500', weightKey: 'thermal'     },
  { label: 'Persistence', key: 'persistence', fullLabel: 'Temporal Persistence', color: 'bg-blue-500',   weightKey: 'persistence' },
  { label: 'GIS / OSM',  key: 'osm',         fullLabel: 'GIS Proximity',        color: 'bg-emerald-500', weightKey: 'osm'        },
  { label: 'AI Model',   key: 'ai',          fullLabel: 'ML Classification',    color: 'bg-indigo-500', weightKey: 'ai'          },
];

function ScoreBar({ value, color }: { value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] font-bold text-slate-700 w-7 text-right tabular-nums">{Math.round(pct)}</span>
    </div>
  );
}

export const EvidenceBreakdownCard: React.FC<Props> = ({ event }) => {
  const components = event.rawDetail?.risk?.components;
  const weights = event.rawDetail?.risk?.weights;
  const score = event.rawDetail?.risk?.score;

  if (!components) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Evidence Breakdown</p>
        <p className="text-xs text-slate-400 italic">Select an event to view evidence breakdown.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <BarChart3 className="w-4 h-4 text-blue-600" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Evidence Breakdown</span>
        </div>
        {score != null && (
          <span className="text-[10px] font-bold text-slate-500">
            Composite: <span className="text-slate-800">{score.toFixed(1)} / 100</span>
          </span>
        )}
      </div>

      <div className="space-y-3">
        {COMPONENTS.map(({ label, key, fullLabel, color, weightKey }) => {
          const rawValue: number | undefined = components[key];
          if (rawValue == null) return null;
          const weightPct = weights?.[weightKey] != null ? `${Math.round(weights[weightKey] * 100)}%` : '';
          return (
            <div key={key}>
              <div className="flex justify-between mb-1">
                <span className="text-[11px] font-semibold text-slate-700">{label}</span>
                <span className="text-[10px] text-slate-400">{fullLabel}{weightPct ? ` · ${weightPct} weight` : ''}</span>
              </div>
              <ScoreBar value={rawValue} color={color} />
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-slate-400 mt-3 italic">
        Scores are the backend risk component values (0–100). Not independent probabilities.
      </p>
    </div>
  );
};

export default EvidenceBreakdownCard;
