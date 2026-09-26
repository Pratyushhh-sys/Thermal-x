import React from 'react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import DashboardHeader from '../components/dashboard/DashboardHeader';
import SummaryCards from '../components/dashboard/SummaryCards';
import ThermalMap from '../components/dashboard/ThermalMap';
import SelectedEventPanel from '../components/dashboard/SelectedEventPanel';
import RecentInvestigations from '../components/dashboard/RecentInvestigations';
import QuickActions from '../components/dashboard/QuickActions';
import EventReportModal from '../components/modals/EventReportModal';
import ExploreEventsModal from '../components/modals/ExploreEventsModal';
import GenerateReportModal from '../components/modals/GenerateReportModal';
import SourceAttributionModal from '../components/modals/SourceAttributionModal';
import ForwardAlertModal from '../components/modals/ForwardAlertModal';

export const DashboardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-transparent flex flex-col antialiased">
      {/* Top Dashboard Navbar matching Reference Image 2 */}
      <DashboardNavbar />

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1700px] w-full mx-auto px-4 sm:px-6 py-4 sm:py-6">
        
        {/* Dashboard Header matching Reference Image 2 */}
        <DashboardHeader />

        {/* 4 Summary Cards matching Reference Image 2 */}
        <SummaryCards />

        {/* Main Map & Event Details Layout matching Reference Image 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          
          {/* LEFT: Main Interactive Satellite Leaflet Map (Col 1 to 7/8) - Fixed in place */}
          <div className="lg:col-span-7 xl:col-span-8 w-full lg:sticky lg:top-24 self-start">
            <ThermalMap />
          </div>

          {/* RIGHT: Selected Event Details (Col 8/9 to 12) */}
          <div className="lg:col-span-5 xl:col-span-4 w-full h-[540px] lg:h-[610px] overflow-y-auto pr-1 pb-2">
            <SelectedEventPanel />
          </div>

        </div>

        {/* Prominent Recent Investigations Table */}
        <div className="mt-6">
          <RecentInvestigations />
        </div>

        {/* Bottom Quick Actions Row matching Reference Image 2 */}
        <div className="mt-6">
          <QuickActions />
        </div>

      </main>

      {/* Footer */}
      <footer className="mt-8 border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        Thermal X &copy; 2026 &bull; SIH Problem Statement 26162 &bull; Satellite Intelligence & Industrial Thermal Attribution
      </footer>

      {/* Interactive Modals */}
      <EventReportModal />
      <ExploreEventsModal />
      <GenerateReportModal />
      <SourceAttributionModal />
      <ForwardAlertModal />
    </div>
  );
};
export default DashboardPage;
