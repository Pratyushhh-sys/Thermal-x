import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, Cloud, ChevronDown, User, Settings, Shield, LogOut, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import FlameIcon from '../../assets/FlameIcon';
import { useAuth } from '../../context/AuthContext';
import { useThermal } from '../../context/ThermalContext';
import { useNavigate } from 'react-router-dom';
import { SystemHealthIndicator } from '../intelligence/SystemHealthIndicator';

export const DashboardNavbar: React.FC = () => {
  const { user, logout } = useAuth();
  const {
    events,
    selectEventById,
    notifications,
    markNotificationRead,
    unreadCount,
    searchQuery,
    setSearchQuery,
    dataLoadedAt, // BUG-08/12
  } = useThermal();
  const navigate = useNavigate();

  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSystemHealthOpen, setIsSystemHealthOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(() =>
    new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata' })
  );

  useEffect(() => {
    const tick = () =>
      setCurrentTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata' }));
    const interval = setInterval(tick, 60000); // BUG-08: update every minute
    return () => clearInterval(interval);
  }, []);

  // BUG-12: compute relative data freshness from real load timestamp
  const [relativeTime, setRelativeTime] = React.useState('just now');
  useEffect(() => {
    const compute = () => {
      if (!dataLoadedAt) { setRelativeTime('loading...'); return; }
      const diffMs = Date.now() - dataLoadedAt.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) setRelativeTime('just now');
      else if (diffMin === 1) setRelativeTime('1 min ago');
      else setRelativeTime(`${diffMin} min ago`);
    };
    compute();
    const t = setInterval(compute, 30000);
    return () => clearInterval(t);
  }, [dataLoadedAt]);

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const healthRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotificationOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsSearchFocused(false);
      }
      if (healthRef.current && !healthRef.current.contains(e.target as Node)) {
        setIsSystemHealthOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Search results filtering
  const searchResults = searchQuery.trim()
    ? events.filter(e =>
        e.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.state.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.probableSource.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.candidateSource.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.coordinates.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 h-20 flex items-center justify-between gap-4">
        
        {/* Left: Brand / SIH Identity matching Reference Image 2 */}
        <div className="flex items-center space-x-3 flex-shrink-0 cursor-pointer" onClick={() => navigate('/dashboard')}>
          <div className="flex-shrink-0">
            <FlameIcon size={32} />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-xl font-extrabold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">
              Thermal X
            </span>
            <span className="text-xs font-semibold text-slate-400 border-l border-slate-300 pl-2">
              SIH 2026 | PS 26162
            </span>
          </div>
        </div>

        {/* Center: Large Global Search Bar matching Reference Image 2 */}
        <div className="flex-1 max-w-lg relative hidden sm:block" ref={searchRef}>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              placeholder="Search location, facility, event ID, or coordinates..."
              className="w-full pl-10 pr-4 py-2.5 text-xs sm:text-sm bg-slate-50/50 hover:bg-white focus:bg-white rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/15 focus:border-indigo-500 text-slate-800 placeholder:text-slate-400 transition-all shadow-sm"
            />
          </div>

          {/* Live Search Dropdown */}
          {isSearchFocused && searchResults.length > 0 && (
            <div className="absolute top-full mt-1.5 left-0 right-0 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-fadeIn max-h-80 overflow-y-auto">
              <div className="p-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                Matching Thermal Events & Facilities ({searchResults.length})
              </div>
              {searchResults.map((ev) => (
                <div
                  key={ev.id}
                  onClick={() => {
                    selectEventById(ev.id);
                    setIsSearchFocused(false);
                    setSearchQuery('');
                  }}
                  className="p-3 hover:bg-blue-50/70 cursor-pointer border-b border-slate-100 last:border-0 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-1 rounded-md">
                      {ev.id}
                    </span>
                    <div>
                      <div className="text-xs font-semibold text-slate-800">{ev.location}</div>
                      <div className="text-[11px] text-slate-500">{ev.candidateSource}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      ev.risk === 'High' ? 'bg-red-100 text-red-700' :
                      ev.risk === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                    }`}>
                      {ev.risk} Risk
                    </span>
                    <span className="text-[11px] text-slate-400">{ev.confidence}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Controls: Live Monitoring, Freshness, Notifications, Profile */}
        <div className="flex items-center space-x-3 sm:space-x-5 flex-shrink-0">
          
          {/* Live Monitoring Badge with Pulsing Dot */}
          <div className="hidden md:flex flex-col items-end text-right">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span className="tracking-wide">LIVE MONITORING</span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">
              Last update: {currentTime} (IST)
            </span>
          </div>

          {/* Data Freshness Indicator — BUG-12: use real relative time */}
          <div className="hidden lg:flex items-center space-x-2 pl-3 border-l border-slate-200 text-slate-500">
            <Cloud className="w-5 h-5 text-slate-400" />
            <div className="flex flex-col text-left">
              <span className="text-[10px] font-medium text-slate-400 leading-tight">Data freshness</span>
              <span className="text-xs font-bold text-slate-700 leading-tight">{relativeTime}</span>
            </div>
          </div>

          {/* System Health Indicator Dropdown */}
          <div className="hidden lg:block relative" ref={healthRef}>
            <button
              onClick={() => setIsSystemHealthOpen(!isSystemHealthOpen)}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
              title="System Status"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-xs font-semibold text-slate-700">System OK</span>
            </button>

            {isSystemHealthOpen && (
              <div className="absolute right-0 mt-2 w-72 z-50 animate-fadeIn">
                <SystemHealthIndicator />
              </div>
            )}
          </div>

          {/* Notification Bell Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setIsNotificationOpen(!isNotificationOpen)}
              className="relative p-2 rounded-lg text-slate-500 hover:text-[#0F284E] hover:bg-slate-100 transition-colors"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-xs">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notification Menu */}
            {isNotificationOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-fadeIn">
                <div className="p-3.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-[#0F284E] uppercase tracking-wider">
                    Alerts & Notifications
                  </span>
                  <span className="text-[11px] text-blue-600 font-medium cursor-pointer hover:underline" onClick={() => notifications.forEach(n => markNotificationRead(n.id))}>
                    Mark all read
                  </span>
                </div>

                <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {/* BUG-09: show empty state when no notifications */}
                  {notifications.length === 0 ? (
                    <div className="p-8 text-center text-slate-400">
                      <Bell className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      <p className="text-xs font-medium">No notifications yet</p>
                    </div>
                  ) : notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => {
                        markNotificationRead(n.id);
                        if (n.eventId) selectEventById(n.eventId);
                      }}
                      className={`p-3.5 hover:bg-slate-50 cursor-pointer transition-colors flex items-start space-x-3 ${
                        !n.read ? 'bg-blue-50/40' : ''
                      }`}
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        {n.type === 'urgent' && <AlertTriangle className="w-4 h-4 text-red-500" />}
                        {n.type === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                        {n.type === 'info' && <Info className="w-4 h-4 text-blue-500" />}
                      </div>
                      <div className="flex-1 min-w-0 text-left">
                        <div className="text-xs font-semibold text-slate-800 flex items-center justify-between">
                          <span>{n.title}</span>
                          <span className="text-[10px] text-slate-400 font-normal">{n.time ?? (n as any).timestamp ?? ''}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed line-clamp-2">
                          {n.description ?? (n as any).message ?? ''}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Admin User Profile Dropdown */}
          <div className="relative pl-1 sm:pl-2" ref={profileRef}>
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="flex items-center space-x-2.5 p-1.5 rounded-xl hover:bg-slate-50 premium-shadow transition-all group cursor-pointer border border-transparent hover:border-slate-100"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-teal-500 text-white flex items-center justify-center text-xs font-bold shadow-sm">
                {user?.initials || 'AS'}
              </div>
              <div className="hidden sm:flex flex-col text-left pr-1">
                <span className="text-xs font-bold text-slate-800 leading-tight">
                  {user?.name || 'Admin'}
                </span>
                <span className="text-[10px] text-slate-400 leading-tight">
                  Official
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-transform" />
            </button>

            {/* Profile Menu Dropdown */}
            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-fadeIn">
                <div className="p-3 border-b border-slate-100 bg-slate-50">
                  <div className="text-xs font-bold text-slate-800">{user?.name || 'Admin'}</div>
                  <div className="text-[11px] text-slate-500 truncate">{user?.email || 'official@thermalx.gov.in'}</div>
                </div>

                <div className="py-1">
                  {/* BUG-11: Profile buttons previously did nothing — now they scroll to map or open modals */}
                  <button
                    onClick={() => { setIsProfileOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    className="w-full px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2.5 text-left"
                  >
                    <User className="w-3.5 h-3.5 text-slate-400" />
                    <span>Profile &amp; Credentials</span>
                  </button>

                  <button
                    onClick={() => { setIsProfileOpen(false); }}
                    className="w-full px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2.5 text-left"
                    title="Settings are managed at the system level"
                  >
                    <Settings className="w-3.5 h-3.5 text-slate-400" />
                    <span>Account Settings</span>
                  </button>

                  <button
                    onClick={() => { setIsProfileOpen(false); }}
                    className="w-full px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2.5 text-left"
                    title="Audit logs are server-side — contact admin"
                  >
                    <Shield className="w-3.5 h-3.5 text-slate-400" />
                    <span>Security &amp; Audit Logs</span>
                  </button>
                </div>

                <div className="border-t border-slate-100 py-1 bg-slate-50/50">
                  <button
                    onClick={handleLogout}
                    className="w-full px-3.5 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center space-x-2.5 text-left font-medium"
                  >
                    <LogOut className="w-3.5 h-3.5 text-red-500" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    </header>
  );
};
export default DashboardNavbar;
