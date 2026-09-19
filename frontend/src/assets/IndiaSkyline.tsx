import React from 'react';

interface IndiaSkylineProps {
  className?: string;
}

export const IndiaSkyline: React.FC<IndiaSkylineProps> = ({ className = "w-48 h-12 text-[#688399]" }) => {
  return (
    <svg
      viewBox="0 0 400 100"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      preserveAspectRatio="none"
    >
      {/* Base line */}
      <rect x="0" y="94" width="400" height="6" />

      {/* Monument 1: India Gate / Arch (Left) */}
      <rect x="15" y="55" width="48" height="40" rx="1" />
      {/* Archway cutout */}
      <path d="M28 95V74C28 67 34 62 39 62C44 62 50 67 50 74V95H28Z" fill="#F4F7FB" />
      {/* India Gate Attic top */}
      <rect x="11" y="49" width="56" height="7" rx="1" />
      <rect x="18" y="44" width="42" height="6" />

      {/* Building 2: Domes & Pillars (Parliament / Red fort) */}
      <rect x="75" y="70" width="30" height="25" />
      {/* Small Minaret / Tower */}
      <rect x="70" y="58" width="6" height="37" />
      <polygon points="73,50 69,58 77,58" />
      <rect x="104" y="58" width="6" height="37" />
      <polygon points="107,50 103,58 111,58" />
      {/* Central dome */}
      <path d="M82 70C82 60 90 54 90 48C90 54 98 60 98 70H82Z" />

      {/* Monument 3: Qutub Minar (Tall fluted minaret) */}
      <polygon points="128,15 132,15 138,95 122,95" />
      {/* Balconies on minar */}
      <rect x="123" y="35" width="14" height="3" rx="0.5" />
      <rect x="122" y="55" width="16" height="3" rx="0.5" />
      <rect x="120" y="75" width="20" height="3" rx="0.5" />
      <polygon points="130,5 128,15 132,15" />

      {/* Monument 4: Taj Mahal / Humayun Tomb dome and minarets */}
      {/* Left minaret */}
      <rect x="160" y="40" width="5" height="55" />
      <polygon points="162.5,33 159,40 166,40" />
      {/* Right minaret */}
      <rect x="225" y="40" width="5" height="55" />
      <polygon points="227.5,33 224,40 231,40" />
      {/* Main structure */}
      <rect x="172" y="60" width="46" height="35" rx="1" />
      <path d="M185 95V78C185 73 189 70 195 70C201 70 205 73 205 78V95H185Z" fill="#F4F7FB" />
      {/* Onion Dome */}
      <path d="M185 60C182 52 188 42 195 35C202 42 208 52 205 60H185Z" />
      {/* Dome finial */}
      <line x1="195" y1="35" x2="195" y2="28" stroke="currentColor" strokeWidth="2" />
      {/* Side chhatris */}
      <rect x="176" y="52" width="7" height="9" />
      <path d="M175 52C175 48 179.5 45 179.5 45C179.5 45 184 48 184 52H175Z" />
      <rect x="207" y="52" width="7" height="9" />
      <path d="M206 52C206 48 210.5 45 210.5 45C210.5 45 215 48 215 52H206Z" />

      {/* Traditional Indian Haveli / Pavilion row */}
      <rect x="245" y="68" width="40" height="27" />
      <path d="M250 68C250 62 255 58 265 58C275 58 280 62 280 68H250Z" />
      <circle cx="265" cy="56" r="2" />

      {/* Distant trees and modern towers silhouette */}
      <polygon points="300,95 304,78 308,95" />
      <polygon points="310,95 315,72 320,95" />
      <polygon points="322,95 326,80 330,95" />
      <rect x="335" y="65" width="12" height="30" />
      <rect x="352" y="58" width="15" height="37" />
      <rect x="372" y="70" width="10" height="25" />
      <polygon points="388,95 392,82 396,95" />
    </svg>
  );
};
export default IndiaSkyline;
