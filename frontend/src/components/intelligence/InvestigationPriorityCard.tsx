/**
 * InvestigationPriorityCard — Feature 1
 * Displays an operational priority label derived from the existing backend risk tier.
 * No new risk formula. Only a UI interpretation.
 */
import React from 'react';
import { ShieldAlert, ShieldCheck, ShieldEllipsis } from 'lucide-react';
import { ThermalEvent } from '../../data/mockData';

interface Props {
  event: ThermalEvent;
}

function getPriority(risk: string): { code: string; label: string; reason: string; color: string; bg: string; border: string; Icon: React.ElementType } {
  switch (risk) {
    case 'High':
      return {
        code: 'P1',
        label: 'Immediate Review',
        reason: 'High-risk thermal event — elevated FRP or persistent detection near infrastructure. Requires urgent investigation.',
        color: 'text-red-700',
        bg: 'bg-red-50',
        border: 'border-red-200',
        Icon: ShieldAlert,
      };
    case 'Medium':
      return {
        code: 'P2',
        label: 'High Priority',
        reason: 'Medium-risk thermal event — moderate thermal intensity or moderate persistence detected. Schedule investigation.',
        color: 'text-amber-700',
        bg: 'bg-amber-50',
        border: 'border-amber-200',
        Icon: ShieldEllipsis,
      };
    default:
      return {
        code: 'P3',
        label: 'Monitor',
        reason: 'Low-risk thermal event — weak signal or intermittent detection. Continue passive monitoring.',
        color: 'text-emerald-700',
        bg: 'bg-emerald-50',
        border: 'border-emerald-200',
        Icon: ShieldCheck,
      };
  }
}

export const InvestigationPriorityCard: React.FC<Props> = ({ event }) => {
  const p = getPriority(event.risk);
  const { Icon } = p;

  return (
    <div className={`rounded-xl border ${p.border} ${p.bg} p-4`}>
      <div className="flex items-center space-x-2 mb-2">
        <Icon className={`w-4 h-4 ${p.color}`} />
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Investigation Priority</span>
      </div>
      <div className={`text-lg font-extrabold ${p.color} leading-tight`}>
        {p.code} — {p.label}
      </div>
      <p className={`text-[11px] mt-1.5 leading-relaxed ${p.color} opacity-80`}>
        {p.reason}
      </p>
    </div>
  );
};

export default InvestigationPriorityCard;
