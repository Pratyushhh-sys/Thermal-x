import React, { useState } from 'react';
import Navbar from '../components/landing/Navbar';
import HeroSection from '../components/landing/HeroSection';
import OfficialLogin from '../components/landing/OfficialLogin';
import ForgotPasswordModal from '../components/common/ForgotPasswordModal';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Flame, Factory, MapPin, FileText, BarChart3, Satellite, Shield, Bell, ChevronDown, ChevronUp, Mail, Phone, Building2 } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToLogin = () => scrollTo('official-login-section');

  const handleNavSection = (section: string) => {
    const map: Record<string, string> = {
      home: 'hero-section',
      about: 'about-section',
      features: 'features-section',
      impact: 'impact-section',
      contact: 'contact-section',
    };
    const id = map[section.toLowerCase()];
    if (id) scrollTo(id);
    else scrollToLogin();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAFA]">
      <Navbar
        onOfficialLoginClick={scrollToLogin}
        onNavigateSection={handleNavSection}
      />

      <main className="flex-1">
        {/* Hero Section */}
        <div id="hero-section">
          <HeroSection
            onLoginClick={scrollToLogin}
            onLearnMoreClick={() => scrollTo('about-section')}
            onSelectAnomaly={scrollToLogin}
          />
        </div>

        {/* About Section */}
        <section id="about-section" className="py-16 bg-white border-y border-slate-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <span className="text-xs font-bold tracking-[0.25em] text-indigo-600 uppercase">About Thermal X</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-3 mb-4">What is Thermal X?</h2>
              <p className="text-base text-slate-500 max-w-3xl mx-auto leading-relaxed">
                Thermal X is a satellite-based industrial fire and thermal source attribution platform developed for
                the Smart India Hackathon 2026 (PS 26162). It integrates FIRMS satellite data with an XGBoost
                machine learning pipeline to automatically classify thermal anomalies across India into probable
                industrial, agricultural, forest, mining, and pipeline sources.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  icon: <Satellite className="w-6 h-6 text-blue-600" />,
                  title: 'VIIRS & MODIS Satellite Data',
                  desc: 'Real-time fire radiative power (FRP) data from NASA FIRMS covering all of India with sub-375m resolution for precise thermal detection.',
                },
                {
                  icon: <BarChart3 className="w-6 h-6 text-purple-600" />,
                  title: 'XGBoost ML Attribution',
                  desc: 'Dual XGBoost classifiers (Exp A & C) trained on 20,800+ events with OSM geospatial features for high-confidence source attribution.',
                },
                {
                  icon: <Shield className="w-6 h-6 text-emerald-600" />,
                  title: 'Regulatory Compliance Ready',
                  desc: 'Risk scoring aligned with CPCB standards, generating forensic dossiers suitable for State Pollution Control Board enforcement actions.',
                },
              ].map((item, i) => (
                <div key={i} className="p-6 rounded-2xl border border-slate-200 bg-slate-50 hover:shadow-md transition-shadow">
                  <div className="w-12 h-12 rounded-xl bg-white border border-slate-200 flex items-center justify-center mb-4 shadow-sm">
                    {item.icon}
                  </div>
                  <h3 className="text-sm font-bold text-slate-800 mb-2">{item.title}</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features-section" className="py-20 bg-[#FAFAFA]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="text-xs font-bold tracking-[0.25em] text-teal-600 uppercase">Platform Features</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-3 mb-4">Everything You Need</h2>
              <p className="text-base text-slate-500 max-w-2xl mx-auto">
                A complete toolkit for monitoring, analyzing, and attributing thermal anomalies across India.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { icon: <Flame className="w-5 h-5 text-orange-500" />, title: 'Real-time Monitoring', desc: '20,800+ thermal events loaded from NASA FIRMS satellite data with 26-day observation window.' },
                { icon: <MapPin className="w-5 h-5 text-blue-500" />, title: 'Interactive Map', desc: 'OpenStreetMap-based map showing place names with color-coded thermal markers by source type.' },
                { icon: <Factory className="w-5 h-5 text-indigo-500" />, title: 'Source Attribution', desc: 'Dual ML models classify events into Agricultural, Forest, Industrial, Mining, and Other categories.' },
                { icon: <FileText className="w-5 h-5 text-purple-500" />, title: 'Forensic Reports', desc: 'Generate regulatory dossiers with satellite imagery data, FRP analytics, and risk scores.' },
                { icon: <Bell className="w-5 h-5 text-red-500" />, title: 'Smart Alerts', desc: 'Automatic notifications for highest fire radiative power events requiring immediate investigation.' },
                { icon: <BarChart3 className="w-5 h-5 text-emerald-500" />, title: '4-Factor Risk Score', desc: 'Composite 0–100 risk score (HIGH/MEDIUM/LOW) using FRP, persistence, proximity, and temporal data.' },
                { icon: <Satellite className="w-5 h-5 text-cyan-500" />, title: 'Dual Satellite Sensors', desc: 'VIIRS (375m) and MODIS (1km) sensor coverage for cross-verification of thermal anomalies.' },
                { icon: <Shield className="w-5 h-5 text-amber-500" />, title: 'Secure Access', desc: 'Government official authentication with role-based access control for authorized personnel only.' },
              ].map((f, i) => (
                <div key={i} className="bg-white p-6 rounded-2xl premium-shadow hover:-translate-y-1 transition-all border border-slate-100/50">
                  <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center mb-4 border border-slate-100">
                    {f.icon}
                  </div>
                  <h4 className="text-xs font-bold text-slate-800 mb-1.5">{f.title}</h4>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Impact Section */}
        <section id="impact-section" className="py-20 bg-white border-y border-slate-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="text-xs font-bold tracking-[0.25em] text-indigo-600 uppercase">Measured Impact</span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-3 mb-4">Platform at a Glance</h2>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
              {[
                { value: '20,828', label: 'Thermal Events Indexed', color: 'text-orange-600' },
                { value: '9 / 10', label: 'OSM Feature Types Cached', color: 'text-blue-600' },
                { value: '25', label: 'ML Features (Exp C)', color: 'text-purple-600' },
                { value: '26 days', label: 'Historical Observation Window', color: 'text-emerald-600' },
              ].map((stat, i) => (
                <div key={i} className="text-center p-6 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className={`text-3xl sm:text-4xl font-extrabold ${stat.color} mb-2`}>{stat.value}</div>
                  <div className="text-xs text-slate-500 font-medium">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* FAQ */}
            <div className="max-w-3xl mx-auto">
              <h3 className="text-lg font-bold text-slate-800 mb-5 text-center">Frequently Asked Questions</h3>
              {[
                { q: 'What satellite data does Thermal X use?', a: 'Thermal X uses NASA FIRMS data sourced from VIIRS (375m resolution) and MODIS (1km) instruments aboard Suomi-NPP and Aqua/Terra satellites. The data covers all of India with a 26-day observation window.' },
                { q: 'How is the risk score calculated?', a: 'The risk score (0–100) is calculated using 4 factors: FRP thermal magnitude (40%), persistence over 7 days (20%), proximity to industrial/hazard facilities (20%), and satellite sensor reliability (20%). Scores ≥60 are HIGH risk.' },
                { q: 'Is this data used for real enforcement actions?', a: 'The platform generates "Probable Source" classifications based on weak geographic OSM labels — NOT verified fire-cause ground truth. All outputs should be treated as investigative leads requiring field verification before regulatory action.' },
                { q: 'How accurate is the ML model?', a: 'Experiment C (25 features, no data leakage) is the primary deployment model. It uses XGBoost with OSM geospatial proximity features. Accuracy metrics are documented in the model metadata and evaluation reports.' },
              ].map((faq, i) => (
                <div key={i} className="border border-slate-200 rounded-xl mb-3 overflow-hidden">
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    className="w-full text-left p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800">{faq.q}</span>
                    {openFaq === i ? <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                  </button>
                  {openFaq === i && (
                    <div className="px-4 pb-4 text-xs text-slate-500 leading-relaxed border-t border-slate-100 pt-3">
                      {faq.a}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section id="contact-section" className="py-20 bg-gradient-to-br from-indigo-900 to-slate-900 border-t border-slate-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <span className="text-xs font-bold tracking-[0.25em] text-teal-400 uppercase">Contact & Support</span>
              <h2 className="text-3xl font-extrabold text-white mt-3 mb-4">Get In Touch</h2>
              <p className="text-sm text-slate-300 max-w-2xl mx-auto">
                For access requests, technical support, or regulatory inquiries about Thermal X, reach out to the development team or the Ministry of Environment.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {[
                { icon: <Mail className="w-5 h-5 text-teal-400" />, title: 'Email Support', lines: ['support@thermalx.gov.in', 'For technical issues & access'], action: 'mailto:support@thermalx.gov.in' },
                { icon: <Building2 className="w-5 h-5 text-teal-400" />, title: 'MoEF&CC', lines: ['Ministry of Environment, Forest', 'and Climate Change, New Delhi'], action: 'https://moef.gov.in/' },
                { icon: <Phone className="w-5 h-5 text-teal-400" />, title: 'NIC Helpdesk', lines: ['+91-11-24301361', 'National Informatics Centre'], action: 'tel:+911124301361' },
              ].map((c, i) => (
                <div key={i} className="bg-white/10 border border-white/20 rounded-2xl p-6 text-center hover:bg-white/15 transition-colors">
                  <div className="w-11 h-11 rounded-full bg-white/10 flex items-center justify-center mx-auto mb-4">
                    {c.icon}
                  </div>
                  <h4 className="text-sm font-bold text-white mb-2">{c.title}</h4>
                  {c.lines.map((l, j) => (
                    <p key={j} className="text-xs text-slate-300">{l}</p>
                  ))}
                  {c.action && (
                    <a href={c.action} target={c.action.startsWith('http') ? '_blank' : '_self'} rel="noreferrer" className="mt-4 inline-flex items-center text-xs font-semibold text-teal-400 hover:text-teal-300 transition-colors">
                      {c.action.startsWith('http') ? 'Visit Website →' : c.lines[0]}
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Official Login Section */}
        <OfficialLogin
          onForgotPasswordClick={() => setIsForgotModalOpen(true)}
        />
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>© 2026 Thermal X — Smart India Hackathon (SIH 26162). Ministry of Environment, Forest and Climate Change & NIC.</p>
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">Security Standard: CERT-In Compliant</span>
            <span>•</span>
            <span className="text-slate-400">Satellite Sensor: INSAT-3DR / VIIRS / MODIS</span>
          </div>
        </div>
      </footer>

      <ForgotPasswordModal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
      />
    </div>
  );
};
export default LandingPage;
