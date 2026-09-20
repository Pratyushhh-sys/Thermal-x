/**
 * WhyThisEventCard — Feature 2
 * Shows human-readable evidence bullets using ONLY existing backend fields.
 * No fabricated data. Each bullet is conditionally rendered.
 *
 * Backend fields used:
 *   firms.frp          → thermal intensity
 *   persistence.active_days_last_7, persistence_ratio → persistence
 *   gis_context.nearest_factory/mine/chemical/refinery distance → nearby infra
 *   classification.thermal_only_estimate.confidence → ML confidence
 *   gis_context.nearest_forest distance → forest context
 *   risk.reasons[]    → verbatim backend reasons (as a secondary source)
 */
import React from 'react';
import { Flame, Clock, Factory, Cpu, Trees, AlertTriangle, Mountain } from 'lucide-react';
import { ThermalEvent } from '../../data/mockData';

interface Props {
  event: ThermalEvent;
}

interface Bullet {
  icon: React.ReactNode;
  text: string;
}

function buildBullets(detail: any): Bullet[] {
  const bullets: Bullet[] = [];
  if (!detail) return bullets;

  const frp: number = detail.firms?.frp ?? 0;
  if (frp >= 100) {
    bullets.push({ icon: <Flame className="w-3.5 h-3.5 text-red-500" />, text: `Extremely high thermal intensity: FRP ${frp.toFixed(1)} MW` });
  } else if (frp >= 30) {
    bullets.push({ icon: <Flame className="w-3.5 h-3.5 text-orange-500" />, text: `High thermal intensity: FRP ${frp.toFixed(1)} MW` });
  } else if (frp > 0) {
    bullets.push({ icon: <Flame className="w-3.5 h-3.5 text-amber-500" />, text: `Moderate thermal intensity: FRP ${frp.toFixed(1)} MW` });
  }

  const activeDays: number = detail.persistence?.active_days_last_7 ?? 0;
  const persRatio: number = detail.persistence?.persistence_ratio ?? 0;
  if (activeDays > 0) {
    bullets.push({
      icon: <Clock className="w-3.5 h-3.5 text-blue-500" />,
      text: `Detected on ${activeDays} of last 7 days (${(persRatio * 100).toFixed(0)}% persistence)`,
    });
  }

  const nearestFactory = detail.gis_context?.nearest_factory;
  const nearestChemical = detail.gis_context?.nearest_chemical;
  const nearestRefinery = detail.gis_context?.nearest_refinery;
  const nearestMine = detail.gis_context?.nearest_mine;
  const nearestQuarry = detail.gis_context?.nearest_quarry;

  const closestIndustrial = [nearestFactory, nearestChemical, nearestRefinery]
    .filter(Boolean)
    .sort((a, b) => (a.distance_m ?? Infinity) - (b.distance_m ?? Infinity))[0];
  if (closestIndustrial && closestIndustrial.distance_m != null && closestIndustrial.distance_m < 5000) {
    bullets.push({
      icon: <Factory className="w-3.5 h-3.5 text-blue-600" />,
      text: `Industrial infrastructure (${closestIndustrial.type}) detected ${(closestIndustrial.distance_m / 1000).toFixed(1)} km away`,
    });
  }

  const closestMining = [nearestMine, nearestQuarry]
    .filter(Boolean)
    .sort((a, b) => (a.distance_m ?? Infinity) - (b.distance_m ?? Infinity))[0];
  if (closestMining && closestMining.distance_m != null && closestMining.distance_m < 5000) {
    bullets.push({
      icon: <Mountain className="w-3.5 h-3.5 text-purple-600" />,
      text: `Mining/quarry infrastructure (${closestMining.type}) detected ${(closestMining.distance_m / 1000).toFixed(1)} km away`,
    });
  }

  const nearestForest = detail.gis_context?.nearest_forest;
  if (nearestForest && nearestForest.distance_m != null && nearestForest.distance_m < 2000) {
    bullets.push({
      icon: <Trees className="w-3.5 h-3.5 text-green-600" />,
      text: `Forest area within ${(nearestForest.distance_m).toFixed(0)} m — potential vegetation fire`,
    });
  }

  const confidence: number = detail.classification?.thermal_only_estimate?.confidence ?? 0;
  if (confidence > 0) {
    bullets.push({
      icon: <Cpu className="w-3.5 h-3.5 text-indigo-500" />,
      text: `ML classification confidence: ${(confidence * 100).toFixed(0)}% (Experiment C — thermal+temporal only)`,
    });
  }

  const riskScore: number = detail.risk?.score ?? 0;
  if (riskScore >= 60) {
    bullets.push({
      icon: <AlertTriangle className="w-3.5 h-3.5 text-red-500" />,
      text: `Composite risk score: ${riskScore.toFixed(1)} / 100 — HIGH tier`,
    });
  } else if (riskScore >= 30) {
    bullets.push({
      icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />,
      text: `Composite risk score: ${riskScore.toFixed(1)} / 100 — MEDIUM tier`,
    });
  }

  return bullets;
}

export const WhyThisEventCard: React.FC<Props> = ({ event }) => {
  const bullets = buildBullets(event.rawDetail);

  if (bullets.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Why This Event?</p>
        <p className="text-xs text-slate-400 italic">Select an event to see investigative evidence.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-3">
        Why This Event? — Investigative Lead
      </p>
      <ul className="space-y-2">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start space-x-2.5">
            <span className="flex-shrink-0 mt-0.5">{b.icon}</span>
            <span className="text-[11px] text-slate-700 leading-relaxed">{b.text}</span>
          </li>
        ))}
      </ul>
      <p className="text-[10px] text-slate-400 mt-3 italic">
        Note: "Probable Source" is an investigative lead based on weak geographic labels — NOT a confirmed fire cause.
      </p>
    </div>
  );
};

export default WhyThisEventCard;
