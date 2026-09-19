import React from 'react';

export const GovBuildingBg: React.FC = () => {
  return (
    <div className="relative w-full h-full min-h-[460px] md:min-h-[520px] rounded-l-2xl overflow-hidden bg-[#241A14]">
      {/* Exact Sandstone Architecture & Emblem from Reference Image 1 */}
      <img
        src="/assets/login_sandstone_official.png"
        alt="Thermal X Secure Access - Government of India"
        className="w-full h-full object-cover rounded-l-2xl select-none"
      />
    </div>
  );
};
export default GovBuildingBg;
