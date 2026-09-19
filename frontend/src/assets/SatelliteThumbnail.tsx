import React from 'react';

interface SatelliteThumbnailProps {
  eventId?: string;
  className?: string;
}

export const SatelliteThumbnail: React.FC<SatelliteThumbnailProps> = ({
  eventId = "TH-1024",
  className = "w-28 h-20 sm:w-32 sm:h-24"
}) => {
  return (
    <div className={`relative rounded-lg overflow-hidden border border-slate-700/60 bg-slate-900 flex-shrink-0 shadow-md ${className}`}>
      {/* Exact satellite refinery thumbnail from Reference Image 2 */}
      <img
        src="/assets/selected_event_th1024.png"
        alt={`Thermal Anomaly ${eventId}`}
        className="w-full h-full object-cover rounded-lg select-none"
      />
    </div>
  );
};
export default SatelliteThumbnail;
