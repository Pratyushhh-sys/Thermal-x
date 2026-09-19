import React from 'react';

interface FlameIconProps {
  className?: string;
  size?: number;
}

export const FlameIcon: React.FC<FlameIconProps> = ({ className = "w-8 h-8", size }) => {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size } : undefined}
    >
      <defs>
        <radialGradient id="flameOuter" cx="50%" cy="75%" r="65%">
          <stop offset="0%" stopColor="#FF7A00" />
          <stop offset="45%" stopColor="#FF3D00" />
          <stop offset="85%" stopColor="#D50000" />
          <stop offset="100%" stopColor="#8A0000" />
        </radialGradient>
        <linearGradient id="flameInner" x1="50%" y1="90%" x2="50%" y2="10%">
          <stop offset="0%" stopColor="#FFEA00" />
          <stop offset="40%" stopColor="#FF9100" />
          <stop offset="100%" stopColor="#FF3D00" />
        </linearGradient>
        <linearGradient id="flameCore" x1="50%" y1="95%" x2="50%" y2="30%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="50%" stopColor="#FFF9C4" />
          <stop offset="100%" stopColor="#FFE082" />
        </linearGradient>
        <filter id="flameGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Outer Flame Glow */}
      <path
        d="M32 2C32 2 39 16 38 24C38 27.5 39.5 29.5 41.5 27C44.5 23.5 47 18 47 18C47 18 55 28 55 42C55 53.6 44.7 63 32 63C19.3 63 9 53.6 9 42C9 30 19 19 25 11C28 7 32 2 32 2Z"
        fill="url(#flameOuter)"
        filter="url(#flameGlow)"
      />

      {/* Middle Dynamic Flame */}
      <path
        d="M32 12C32 12 36 21 35 27C34 32 37 34 39 31C41.5 27.5 43 23 43 23C43 23 49 31 49 42C49 50.8 41.4 58 32 58C22.6 58 15 50.8 15 42C15 32 22 23 27 18C29.5 15.5 32 12 32 12Z"
        fill="url(#flameInner)"
      />

      {/* Intense Core Flame */}
      <path
        d="M32 26C32 26 35 34 33 39C32 41.5 33.5 43 35 41C36.5 39 37 36 37 36C37 36 41 42 41 47C41 51.5 37 54 32 54C27 54 23 51.5 23 47C23 41 27 35 30 31C31 29.5 32 26 32 26Z"
        fill="url(#flameCore)"
      />
    </svg>
  );
};
export default FlameIcon;
