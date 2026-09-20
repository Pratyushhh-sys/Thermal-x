import React, { useState } from 'react';

interface SatelliteThumbnailProps {
  eventId?: string;
  className?: string;
}

export const SatelliteThumbnail: React.FC<SatelliteThumbnailProps> = ({
  eventId = "TH-1024",
  className = "w-28 h-20 sm:w-32 sm:h-24"
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Hardcoded fallback image
  const fallbackSrc = "/assets/selected_event_th1024.png";
  const liveSrc = `http://localhost:8000/api/imagery/${eventId}`;

  return (
    <div className={`relative rounded-lg overflow-hidden border border-slate-700/60 bg-slate-900 flex-shrink-0 shadow-md ${className}`}>
      
      {/* Shimmer loading skeleton */}
      {isLoading && !hasError && (
        <div className="absolute inset-0 bg-slate-800 animate-pulse flex items-center justify-center">
          <svg className="w-6 h-6 text-slate-700 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      )}

      {/* Actual Satellite Image */}
      <img
        src={hasError ? fallbackSrc : liveSrc}
        alt={`Thermal Anomaly ${eventId}`}
        onLoad={() => setIsLoading(false)}
        onError={() => {
          setHasError(true);
          setIsLoading(false);
        }}
        className={`w-full h-full object-cover rounded-lg select-none transition-opacity duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
      />
    </div>
  );
};
export default SatelliteThumbnail;
