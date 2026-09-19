import React from 'react';
import { Flame, Factory, MapPin, FileText, ChevronDown, ArrowRight } from 'lucide-react';
import HeroSatelliteMap from '../../assets/HeroSatelliteMap';
import IndiaSkyline from '../../assets/IndiaSkyline';

interface HeroSectionProps {
  onLoginClick: () => void;
  onLearnMoreClick: () => void;
  onSelectAnomaly?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onLoginClick,
  onLearnMoreClick,
  onSelectAnomaly
}) => {
  return (
    <section className="relative overflow-hidden pt-8 pb-16 lg:pt-12 lg:pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          
          {/* LEFT SIDE: Hero Typography, Features, and Buttons */}
          <div className="lg:col-span-6 flex flex-col justify-center text-left">
            
            {/* Eyebrow text matching Reference Image 1 */}
            <div className="text-xs sm:text-[13px] font-bold tracking-[0.2em] text-[#2563EB] uppercase mb-4 flex items-center space-x-2">
              <span>MONITOR</span>
              <span>•</span>
              <span>ANALYZE</span>
              <span>•</span>
              <span>ATTRIBUTE</span>
              <span>•</span>
              <span>PREVENT</span>
            </div>

            {/* Main Heading matching Reference Image 1 */}
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0B2447] tracking-tight leading-[1.15] mb-5">
              Detect Thermal Risks. <br />
              Enable <span className="text-[#0284C7]">Safer Communities.</span>
            </h1>

            {/* Supporting paragraph text matching Reference Image 1 */}
            <p className="text-sm sm:text-base text-slate-600 leading-relaxed mb-8 max-w-xl font-normal">
              Thermal X uses satellite data and AI to detect thermal anomalies
              and help attribute potential industrial fire sources — empowering
              government agencies with timely, data-driven insights.
            </p>

            {/* Four Feature Indicators in a Row matching Reference Image 1 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
              
              {/* Feature 1 */}
              <div className="flex items-center space-x-2.5">
                <div className="w-10 h-10 rounded-full border border-slate-300 bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  <Flame className="w-5 h-5 text-[#0F284E]" />
                </div>
                <div className="text-[11px] font-semibold text-slate-700 leading-tight">
                  Real-time <br />
                  <span className="font-normal text-slate-500">Thermal Monitoring</span>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="flex items-center space-x-2.5">
                <div className="w-10 h-10 rounded-full border border-slate-300 bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  <Factory className="w-5 h-5 text-[#0F284E]" />
                </div>
                <div className="text-[11px] font-semibold text-slate-700 leading-tight">
                  Industrial Source <br />
                  <span className="font-normal text-slate-500">Attribution</span>
                </div>
              </div>

              {/* Feature 3 */}
              <div className="flex items-center space-x-2.5">
                <div className="w-10 h-10 rounded-full border border-slate-300 bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  <MapPin className="w-5 h-5 text-[#0F284E]" />
                </div>
                <div className="text-[11px] font-semibold text-slate-700 leading-tight">
                  Geospatial <br />
                  <span className="font-normal text-slate-500">Visualization</span>
                </div>
              </div>

              {/* Feature 4 */}
              <div className="flex items-center space-x-2.5">
                <div className="w-10 h-10 rounded-full border border-slate-300 bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  <FileText className="w-5 h-5 text-[#0F284E]" />
                </div>
                <div className="text-[11px] font-semibold text-slate-700 leading-tight">
                  Actionable <br />
                  <span className="font-normal text-slate-500">Reports</span>
                </div>
              </div>

            </div>

            {/* Hero Buttons matching Reference Image 1 */}
            <div className="flex flex-wrap items-center gap-4 mb-10">
              <button
                onClick={onLoginClick}
                className="inline-flex items-center space-x-2 bg-[#0F284E] hover:bg-[#173A6E] text-white text-sm font-semibold px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 group"
              >
                <span>Login as Government Official</span>
                <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
              </button>

              <button
                onClick={onLearnMoreClick}
                className="inline-flex items-center space-x-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-sm font-semibold px-5 py-3 rounded-lg shadow-sm hover:shadow transition-all duration-200 group"
              >
                <span>Learn More</span>
                <ChevronDown className="w-4 h-4 text-slate-500 transition-transform duration-200 group-hover:translate-y-0.5" />
              </button>
            </div>

            {/* Bottom Hero Message with Indian Monument Skyline & Tricolor Accent */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
              <IndiaSkyline className="w-36 h-10 text-slate-400/80 flex-shrink-0" />
              
              <div className="flex items-center space-x-2.5 text-xs text-slate-600 font-medium">
                {/* Indian Tricolor Flag miniature */}
                <div className="w-5 h-3 rounded-xs border border-slate-300 overflow-hidden flex flex-col flex-shrink-0 shadow-xs">
                  <div className="h-1 bg-[#FF9933]"></div>
                  <div className="h-1 bg-white relative flex items-center justify-center">
                    <div className="w-1 h-1 rounded-full bg-[#000080]"></div>
                  </div>
                  <div className="h-1 bg-[#138808]"></div>
                </div>
                <span>Safer Industries. Cleaner Environment. A Stronger India.</span>
              </div>
            </div>

          </div>

          {/* RIGHT SIDE: Satellite Earth View with Thermal Hotspots */}
          <div className="lg:col-span-6 w-full h-full min-h-[480px] lg:min-h-[560px]">
            <HeroSatelliteMap onSelectAnomaly={onSelectAnomaly} />
          </div>

        </div>
      </div>
    </section>
  );
};
export default HeroSection;
