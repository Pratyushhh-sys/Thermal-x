import React from 'react';

interface HeroSatelliteMapProps {
  onSelectAnomaly?: () => void;
}

export const HeroSatelliteMap: React.FC<HeroSatelliteMapProps> = ({ onSelectAnomaly }) => {
  return (
    <div className="relative w-full h-full min-h-[460px] lg:min-h-[520px] rounded-2xl overflow-hidden shadow-2xl bg-[#030914] flex items-center justify-center border border-slate-800/40">
      {/* Exact satellite image from Reference Image 1 */}
      <img
        src="/assets/hero_earth_satellite_clean.png"
        alt="Thermal X Satellite Intelligence - India Thermal Hotspots"
        className="w-full h-full object-cover object-right-top rounded-2xl select-none"
      />

      {/* Interactive clickable overlay over the top-right Anomaly card */}
      <div
        onClick={onSelectAnomaly}
        className="absolute top-4 right-4 sm:top-6 sm:right-6 w-64 sm:w-72 h-20 rounded-xl cursor-pointer hover:ring-2 hover:ring-cyan-400/60 transition-all"
        title="Thermal Anomaly Detected - Click to Login"
      />
    </div>
  );
};
export default HeroSatelliteMap;
