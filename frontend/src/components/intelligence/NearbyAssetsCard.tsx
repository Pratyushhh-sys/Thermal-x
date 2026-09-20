/**
 * NearbyAssetsCard — Feature 4
 * Shows the nearest GIS/OSM feature distances from the existing backend gis_context.
 *
 * Backend fields used (from gis_context):
 *   nearest_factory, nearest_chemical, nearest_refinery, nearest_gas,
 *   nearest_mine, nearest_quarry, nearest_pipeline,
 *   nearest_forest, nearest_cropland
 *
 * Only shows assets where the backend returned actual data.
 * Shows "Unavailable" when the field is null in the backend response.
 * Does NOT fabricate counts or distances.
 */
import React from 'react';
import { MapPin, Factory, Mountain, Trees, Zap, Pipette } from 'lucide-react';
import { ThermalEvent } from '../../data/mockData';

interface Props {
  event: ThermalEvent;
}

interface AssetRow {
  label: string;
  key: string;
  icon: React.ReactNode;
}

const ASSETS: AssetRow[] = [
  { label: 'Factory',    key: 'nearest_factory',   icon: <Factory className="w-3.5 h-3.5 text-blue-500" /> },
  { label: 'Chemical',   key: 'nearest_chemical',  icon: <Factory className="w-3.5 h-3.5 text-purple-500" /> },
  { label: 'Refinery',   key: 'nearest_refinery',  icon: <Factory className="w-3.5 h-3.5 text-orange-500" /> },
  { label: 'Gas',        key: 'nearest_gas',       icon: <Zap className="w-3.5 h-3.5 text-yellow-500" /> },
  { label: 'Mine',       key: 'nearest_mine',      icon: <Mountain className="w-3.5 h-3.5 text-slate-600" /> },
  { label: 'Quarry',     key: 'nearest_quarry',    icon: <Mountain className="w-3.5 h-3.5 text-stone-500" /> },
  { label: 'Pipeline',   key: 'nearest_pipeline',  icon: <Pipette className="w-3.5 h-3.5 text-amber-600" /> },
  { label: 'Forest',     key: 'nearest_forest',    icon: <Trees className="w-3.5 h-3.5 text-green-600" /> },
  { label: 'Cropland',   key: 'nearest_cropland',  icon: <Trees className="w-3.5 h-3.5 text-lime-600" /> },
];

function fmtDistance(m: number | null | undefined): string {
  if (m == null) return 'Unavailable';
  if (m < 1000) return `${Math.round(m)} m`;
  return `${(m / 1000).toFixed(1)} km`;
}

function proximityColor(m: number | null | undefined): string {
  if (m == null) return 'text-slate-400';
  if (m < 1000) return 'text-red-600 font-bold';
  if (m < 5000) return 'text-amber-600 font-semibold';
  return 'text-slate-600';
}

export const NearbyAssetsCard: React.FC<Props> = ({ event }) => {
  const gis = event.rawDetail?.gis_context;

  if (!gis) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Nearby Assets</p>
        <p className="text-xs text-slate-400 italic">Select an event to view nearby GIS assets.</p>
      </div>
    );
  }

  // Filter to only assets that have actual backend data (non-null fields)
  const rows = ASSETS.map(asset => {
    const feat = gis[asset.key];
    return {
      ...asset,
      distance_m: feat?.distance_m ?? null,
      available: feat != null,
    };
  });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center space-x-2 mb-3">
        <MapPin className="w-4 h-4 text-emerald-600" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Nearby Assets (OSM)</span>
      </div>

      <div className="divide-y divide-slate-100">
        {rows.map(row => (
          <div key={row.key} className="flex items-center justify-between py-1.5">
            <div className="flex items-center space-x-2">
              {row.icon}
              <span className="text-[11px] text-slate-700 font-medium">{row.label}</span>
            </div>
            <span className={`text-[11px] tabular-nums ${proximityColor(row.distance_m)}`}>
              {row.available ? fmtDistance(row.distance_m) : 'Unavailable'}
            </span>
          </div>
        ))}
      </div>

      <p className="text-[10px] text-slate-400 mt-3 italic">
        Nearest feature distances from OpenStreetMap (OSM) cache. Red = within 1 km.
      </p>
    </div>
  );
};

export default NearbyAssetsCard;
