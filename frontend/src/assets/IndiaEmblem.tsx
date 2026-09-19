import React from 'react';

interface IndiaEmblemProps {
  className?: string;
  size?: number;
}

export const IndiaEmblem: React.FC<IndiaEmblemProps> = ({ className = "w-9 h-10", size }) => {
  return (
    <svg
      viewBox="0 0 100 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={size ? { width: size, height: size * 1.2 } : undefined}
    >
      <defs>
        <linearGradient id="emblemGold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#87682C" />
          <stop offset="35%" stopColor="#D4AF37" />
          <stop offset="70%" stopColor="#AA8232" />
          <stop offset="100%" stopColor="#5B451A" />
        </linearGradient>
        <linearGradient id="emblemSlate" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="100%" stopColor="#0F172A" />
        </linearGradient>
      </defs>

      {/* Top Abacus Capital with 3 Lions representation */}
      {/* Center Lion Head */}
      <path
        d="M50 8C43 8 40 14 40 22C40 26 42 29 45 32C41 34 38 38 38 44C38 48 40 51 44 53L43 62H57L56 53C60 51 62 48 62 44C62 38 59 34 55 32C58 29 60 26 60 22C60 14 57 8 50 8Z"
        fill="url(#emblemGold)"
      />
      {/* Left Lion Head profile */}
      <path
        d="M36 16C31 16 26 21 26 28C26 33 29 37 33 39C30 42 28 47 28 52C28 56 30 59 34 62H40L38 52C36 50 35 47 35 44C35 40 37 37 40 35C38 32 37 28 37 25C37 20 38 18 36 16Z"
        fill="url(#emblemGold)"
      />
      {/* Right Lion Head profile */}
      <path
        d="M64 16C69 16 74 21 74 28C74 33 71 37 67 39C70 42 72 47 72 52C72 56 70 59 66 62H60L62 52C64 50 65 47 65 44C65 40 63 37 60 35C62 32 63 28 63 25C63 20 62 18 64 16Z"
        fill="url(#emblemGold)"
      />

      {/* Lion Details / Manes */}
      <circle cx="47" cy="20" r="1.5" fill="#1E293B" />
      <circle cx="53" cy="20" r="1.5" fill="#1E293B" />
      <path d="M48 25L50 27L52 25" stroke="#1E293B" strokeWidth="1" strokeLinecap="round" />
      <path d="M46 30C48 32 52 32 54 30" stroke="#1E293B" strokeWidth="1" />

      {/* Capital Base Plate */}
      <rect x="20" y="62" width="60" height="7" rx="1.5" fill="url(#emblemGold)" />

      {/* Abacus frieze */}
      <rect x="22" y="69" width="56" height="15" fill="url(#emblemGold)" />

      {/* Ashoka Chakra in Center */}
      <circle cx="50" cy="76.5" r="6" stroke="#0F284E" strokeWidth="1.2" fill="#FFFFFF" />
      <circle cx="50" cy="76.5" r="1.2" fill="#0F284E" />
      {/* Spokes */}
      <path d="M50 71.5V81.5M45 76.5H55M46.5 73L53.5 80M46.5 80L53.5 73" stroke="#0F284E" strokeWidth="0.8" />

      {/* Bull and Horse relief representation */}
      {/* Bull on right */}
      <path d="M60 74C62 72 65 72 67 74C68 76 67 79 65 80H58L60 74Z" fill="#3B2A0F" opacity="0.6" />
      {/* Galloping Horse on left */}
      <path d="M40 74C38 72 35 72 33 74C32 76 33 79 35 80H42L40 74Z" fill="#3B2A0F" opacity="0.6" />

      {/* Bell / Inverted Lotus Base */}
      <path
        d="M20 84C20 84 26 96 50 96C74 96 80 84 80 84H20Z"
        fill="url(#emblemGold)"
      />
      {/* Lotus Petals */}
      <path d="M50 85V95M42 85C43 90 45 94 46 95M58 85C57 90 55 94 54 95M34 85C36 89 39 92 42 94M66 85C64 89 61 92 58 94" stroke="#5B451A" strokeWidth="1" />

      {/* Plinth Base */}
      <rect x="16" y="96" width="68" height="5" rx="1" fill="url(#emblemGold)" />

      {/* Motto: Satyameva Jayate representation */}
      <text
        x="50"
        y="113"
        textAnchor="middle"
        fontSize="8"
        fontFamily="serif"
        fontWeight="bold"
        fill="#334155"
        letterSpacing="1"
      >
        सत्यमेव जयते
      </text>
    </svg>
  );
};
export default IndiaEmblem;
