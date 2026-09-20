import React from 'react';
import FlameIcon from '../../assets/FlameIcon';
import IndiaEmblem from '../../assets/IndiaEmblem';

interface NavbarProps {
  onOfficialLoginClick: () => void;
  onNavigateSection?: (sectionId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOfficialLoginClick, onNavigateSection }) => {
  return (
    <header className="sticky top-0 z-40 glass-panel">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        
        {/* Left: Brand Identity matching Reference Image 1 */}
        <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <div className="flex-shrink-0 transition-transform duration-300 group-hover:scale-105">
            <FlameIcon size={38} />
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-extrabold tracking-tight text-slate-900 leading-none group-hover:text-indigo-600 transition-colors">
              Thermal X
            </span>
            <span className="text-[11px] font-medium text-slate-500 tracking-normal mt-1">
              Satellite Intelligence for a Safer India
            </span>
          </div>
        </div>

        {/* Center: Navigation Links matching Reference Image 1 */}
        <nav className="hidden md:flex items-center space-x-8">
          {['Home', 'About', 'Features', 'Impact', 'Contact'].map((item) => (
            <button
              key={item}
              onClick={() => onNavigateSection ? onNavigateSection(item.toLowerCase()) : null}
              className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors py-1 relative group"
            >
              {item}
              <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-indigo-600 transition-all duration-200 group-hover:w-full"></span>
            </button>
          ))}
        </nav>

        {/* Right: Government of India Emblem & Official Login Button */}
        <div className="flex items-center space-x-4 sm:space-x-6">
          {/* Government of India Emblem & Text */}
          <div className="flex items-center space-x-2.5 pl-2 sm:pl-4 border-l border-slate-200/60">
            <IndiaEmblem size={28} className="text-slate-800" />
            <div className="hidden lg:flex flex-col text-left">
              <span className="text-[12px] font-bold text-slate-900 leading-tight">
                Government of India
              </span>
              <span className="text-[10px] text-slate-500 font-medium leading-tight">
                Satellite-Based Monitoring Initiative
              </span>
            </div>
          </div>

          {/* Official Login Button matching Reference Image 1 */}
          <button
            onClick={onOfficialLoginClick}
            className="inline-flex items-center space-x-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white text-xs sm:text-sm font-semibold px-5 py-2.5 rounded-lg premium-shadow transition-all duration-200 group"
          >
            <span>Official Login</span>
            <span className="transition-transform duration-200 group-hover:translate-x-1">→</span>
          </button>
        </div>

      </div>
    </header>
  );
};
export default Navbar;
