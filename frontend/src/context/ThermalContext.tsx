import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchEvents, fetchEventDetails, fetchSummary, fetchNotifications, fetchForwardHistory } from '../api';
import {
  ThermalEvent,
  IndustrialFacility,
  PipelineTrack,
  NotificationItem,
  mockFacilities,
  mockPipelines
} from '../data/mockData';

export interface MapLayersState {
  thermalEvents: boolean;
  industrialFacilities: boolean;
  pipelines: boolean;
  majorRoads: boolean;
  settlements: boolean;
  boundary: boolean;
}

interface ThermalContextType {
  events: ThermalEvent[];
  selectedEvent: ThermalEvent | null;
  setSelectedEvent: (event: ThermalEvent | null) => void;
  selectEventById: (id: string) => void;
  eventDetailLoading: boolean; // BUG-13: expose detail loading for UI spinner
  facilities: IndustrialFacility[];
  pipelines: PipelineTrack[];
  mapLayers: MapLayersState;
  toggleMapLayer: (layer: keyof MapLayersState) => void;
  activeFilter: 'all' | 'high-risk' | 'industrial' | 'investigation';
  setActiveFilter: (filter: 'all' | 'high-risk' | 'industrial' | 'investigation') => void;
  filteredEvents: ThermalEvent[];
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  notifications: NotificationItem[];
  markNotificationRead: (id: string) => void;
  unreadCount: number;
  activeModal: 'report' | 'explore' | 'generate' | 'attribution' | 'forward-alert' | null;
  setActiveModal: (modal: 'report' | 'explore' | 'generate' | 'attribution' | 'forward-alert' | null) => void;
  mapCenter: [number, number];
  mapZoom: number;
  flyToLocation: (lat: number, lng: number, zoom?: number) => void;
  resetMapView: () => void;
  summary: any;
  loading: boolean;
  dataLoadedAt: Date | null; // BUG-08/12: track real data fetch time
  forwardHistory: any[];
  refreshForwardHistory: () => Promise<void>;
}

const ThermalContext = createContext<ThermalContextType | undefined>(undefined);

const DEFAULT_CENTER: [number, number] = [23.5, 78.5]; // Central India
const DEFAULT_ZOOM = 5;

// Map API source_label to a markerType color
const getMarkerType = (sourceLabel: string, riskTier: string): ThermalEvent['markerType'] => {
  if (riskTier === 'High') return 'warning-red';
  switch (sourceLabel) {
    case 'Industrial': return 'factory-blue';
    case 'Forest': return 'forest-green';
    case 'Agricultural': return 'agri-yellow';
    case 'Mining': return 'mine-purple';
    case 'Pipeline': return 'fire-red';
    case 'Power Plant': return 'fire-red';
    default: return 'fire-orange';
  }
};

const getCompassDirection = (degrees: number): string => {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(degrees / 45) % 8;
  return directions[index < 0 ? index + 8 : index];
};

const MAJOR_FACILITIES = [
  { name: 'AM/NS Hazira Steel & Metallurgy Complex', type: 'Integrated Steel Plant', lat: 21.115, lon: 72.652 },
  { name: 'Reliance Hazira Petrochemical Manufacturing Complex', type: 'Petrochemical Cracker', lat: 21.140, lon: 72.690 },
  { name: 'ONGC Hazira Gas Processing Plant', type: 'Gas Processing Terminal', lat: 21.120, lon: 72.665 },
  { name: 'L&T Heavy Engineering Manufacturing Campus, Hazira', type: 'Heavy Engineering', lat: 21.108, lon: 72.640 },
  { name: 'Reliance Jamnagar Mega Refining Complex', type: 'Crude Oil Refinery', lat: 22.355, lon: 69.839 },
  { name: 'Nayara Energy Vadinar Refinery', type: 'Petroleum Refinery', lat: 22.390, lon: 69.750 },
  { name: 'OPaL Petrochemical Complex, Dahej SEZ', type: 'Petrochemical Cracker', lat: 21.710, lon: 72.580 },
  { name: 'Ankleshwar GIDC Industrial Chemical Works', type: 'Chemical Cluster', lat: 21.625, lon: 73.010 },
  { name: 'Adani Mundra Thermal Power & SEZ Complex', type: 'Thermal Power / Industrial', lat: 22.840, lon: 69.700 },
  { name: 'Gujarat Refinery (IOCL) Vadodara', type: 'Crude Oil Refinery', lat: 22.360, lon: 73.130 },
  { name: 'Morbi Ceramic & Vitrified Industrial Hub', type: 'Ceramics Cluster', lat: 22.810, lon: 70.830 },
  { name: 'JSPL Angul Integrated Steel & Pellet Plant', type: 'Integrated Steel Plant', lat: 20.840, lon: 85.080 },
  { name: 'Mahanadi Coalfields Talcher Colliery', type: 'Coal Mining', lat: 20.950, lon: 85.220 },
  { name: 'NTPC Talcher Super Thermal Power Station', type: 'Thermal Power', lat: 20.915, lon: 85.180 },
  { name: 'Tata Steel Meramandali Works, Dhenkanal', type: 'Integrated Steel Plant', lat: 20.810, lon: 85.290 },
  { name: 'Vedanta Jharsuguda Aluminium Smelter', type: 'Aluminium Smelting', lat: 21.820, lon: 84.030 },
  { name: 'Rourkela Steel Plant (SAIL) Complex', type: 'Integrated Steel Plant', lat: 22.215, lon: 84.870 },
  { name: 'Tata Steel Kalinganagar Integrated Works', type: 'Integrated Steel Plant', lat: 20.965, lon: 86.015 },
  { name: 'NTPC Korba Super Thermal Power Station', type: 'Thermal Power Plant', lat: 22.368, lon: 82.684 },
  { name: 'BALCO Korba Aluminium Smelter Complex', type: 'Aluminium Smelter', lat: 22.395, lon: 82.745 },
  { name: 'SECL Gevra Open Cast Coal Mine (Korba)', type: 'Open Cast Coal Mine', lat: 22.345, lon: 82.590 },
  { name: 'Bhilai Steel Plant (SAIL) Integrated Works', type: 'Integrated Steel Plant', lat: 21.190, lon: 81.380 },
  { name: 'Jindal Steel & Power Raigarh Integrated Works', type: 'Steel & Captive Power', lat: 21.910, lon: 83.390 },
  { name: 'Tata Steel Jamshedpur Main Works', type: 'Integrated Steel Plant', lat: 22.800, lon: 86.200 },
  { name: 'Bokaro Steel Plant (SAIL) Industrial Complex', type: 'Integrated Steel Plant', lat: 23.670, lon: 86.150 },
  { name: 'BCCL Jharia Coking Coal Extraction Complex', type: 'Coking Coal Mine', lat: 23.750, lon: 86.420 },
  { name: 'Haldia Petrochemicals Refining Complex', type: 'Petrochemical & Refinery', lat: 22.050, lon: 88.080 },
  { name: 'Durgapur Steel Plant (SAIL) Sinter & Furnace', type: 'Integrated Steel Plant', lat: 23.515, lon: 87.310 },
  { name: 'BPCL Mahul Marine Refinery & Aromatics', type: 'Crude Oil Refinery', lat: 19.010, lon: 72.890 },
  { name: 'JSW Steel Dolvi Integrated Blast Furnace', type: 'Integrated Steel Plant', lat: 18.705, lon: 73.020 },
  { name: 'Chandrapur Super Thermal Power Station', type: 'Coal Thermal Power', lat: 19.980, lon: 79.290 },
  { name: 'Cairn Barmer Mangala Hydrocarbon Terminal', type: 'Oil & Gas Extraction', lat: 25.980, lon: 72.220 },
  { name: 'JSW Rajwest Lignite Power Station, Barmer', type: 'Lignite Power Station', lat: 25.920, lon: 72.150 },
  { name: 'HZL Chanderiya Lead-Zinc Smelting Complex', type: 'Non-Ferrous Smelter', lat: 24.830, lon: 74.630 },
  { name: 'Kota Super Thermal Power Station', type: 'Coal Thermal Power', lat: 25.180, lon: 75.820 },
  { name: 'HPCL-Mittal Energy (HMEL) Bathinda Refinery', type: 'Petroleum Refinery', lat: 30.150, lon: 74.920 },
  { name: 'Moga Agro-Biomass & Grain Processing Facility', type: 'Agro-Industrial Biomass', lat: 30.820, lon: 75.170 },
  { name: 'NTPC Vindhyachal Super Thermal Station (Singrauli)', type: 'Super Thermal Power', lat: 24.095, lon: 82.670 },
  { name: 'JSW Steel Vijayanagar Works, Toranagallu', type: 'Integrated Steel Plant', lat: 15.180, lon: 76.680 },
  { name: 'Bagalkot Cement & Mineral Extraction Works', type: 'Cement & Mineral Quarry', lat: 16.550, lon: 75.300 },
  { name: 'MRPL Mangalore Petroleum Refinery', type: 'Crude Oil Refinery', lat: 12.980, lon: 74.850 },
  { name: 'Peenya Industrial Metallurgy & Manufacturing Zone', type: 'Industrial Foundry', lat: 13.030, lon: 77.520 },
  { name: 'RINL Vizag Steel Plant', type: 'Integrated Steel Plant', lat: 17.630, lon: 83.180 },
  { name: 'NTPC Ramagundam Super Thermal Power Station', type: 'Super Thermal Power', lat: 18.760, lon: 79.450 },
  { name: 'Singareni Collieries Ramagundam Coal Mines', type: 'Coal Mining Sector', lat: 18.790, lon: 79.490 },
  { name: 'CPCL Manali Petroleum Refinery, Chennai', type: 'Crude Oil Refinery', lat: 13.160, lon: 80.260 },
  { name: 'Neyveli Lignite Corporation (NLC) Thermal Unit', type: 'Lignite Mining & Power', lat: 11.590, lon: 79.480 },
];

const resolveFacilityName = (lat: number, lon: number, sourceLabel: string = ''): string => {
  let best = null;
  let minDist = Infinity;
  for (const fac of MAJOR_FACILITIES) {
    const dLat = (fac.lat - lat) * 111.0;
    const dLon = (fac.lon - lon) * (111.0 * Math.cos((lat * Math.PI) / 180));
    const dist = Math.sqrt(dLat * dLat + dLon * dLon);
    if (dist < minDist) {
      minDist = dist;
      best = fac;
    }
  }

  if (best && minDist <= 50.0) {
    return best.name;
  }

  const base = best ? best.name.split(' ')[0] : 'Regional';
  if (sourceLabel.includes('Mining')) return `${base} Mineral Extraction & Colliery Sector`;
  if (sourceLabel.includes('Forest')) return `${base} Forest Reserve Thermal Division`;
  if (sourceLabel.includes('Agri')) return `${base} Agro-Biomass & Crop Co-Gen Field`;
  return `${base} Industrial Development Cluster`;
};

// Helper to map backend list item to frontend model
const mapEventListItem = (apiItem: any): ThermalEvent => {
  let riskTier = apiItem.risk_tier || 'Medium';
  if (riskTier) {
    riskTier = riskTier.charAt(0).toUpperCase() + riskTier.slice(1).toLowerCase();
  }
  const sourceLabel = apiItem.source_label || 'Unknown';
  // BUG-02: Derive a meaningful display confidence from risk_score (0-100 → percentage)
  // risk_score is on 0-100 scale; we show it as a rough confidence proxy until detail is loaded
  const rawScore = apiItem.risk_score ?? null;
  const displayConfidence = rawScore !== null ? Math.round(Math.min(100, Math.max(0, rawScore))) : null;

  const lat = apiItem.location?.lat || 0;
  const lon = apiItem.location?.lon || 0;
  const candidateSource = apiItem.candidate_source || resolveFacilityName(lat, lon, sourceLabel);
  const candidateType = apiItem.candidate_type || 'Industrial Facility';

  return {
    id: apiItem.id,
    location: `${Number(lat).toFixed(4)}° N, ${Number(lon).toFixed(4)}° E`,
    state: 'India',
    coordinates: `${lat}, ${lon}`,
    lat: lat,
    lng: lon,
    risk: riskTier as 'High' | 'Medium' | 'Low',
    probableSource: sourceLabel,
    confidence: displayConfidence ?? 0, // BUG-02: no longer hardcoded 0
    detectedOn: apiItem.acq_date || 'Unknown',
    status: 'Not Assessed',
    frp: `${apiItem.frp} MW`,
    intensity: '—', // BUG-13: use dash instead of 'Unknown' for unfetched fields
    sensor: apiItem.satellite || '—',
    candidateSource: candidateSource,
    candidateType: candidateType,
    distanceToSource: '—',
    thermalCorrelation: '—',
    temporalCorrelation: '—',
    historicalDetections: `${apiItem.active_days_last_7 || 0} active days`,
    attributionReasoning: 'Click to load full analysis.',
    windSpeed: '—',
    plumeDirection: '—',
    markerType: getMarkerType(sourceLabel, riskTier),
  };
};

export const ThermalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<ThermalEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<ThermalEvent | null>(null);
  const [eventDetailLoading, setEventDetailLoading] = useState(false); // BUG-13
  const [facilities] = useState<IndustrialFacility[]>(mockFacilities); // BUG-14: use mock data
  const [pipelines] = useState<PipelineTrack[]>(mockPipelines); // BUG-14: use mock data
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [dataLoadedAt, setDataLoadedAt] = useState<Date | null>(null); // BUG-08/12: real timestamp
  const [forwardHistory, setForwardHistory] = useState<any[]>([]);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [mapLayers, setMapLayers] = useState<MapLayersState>({
    thermalEvents: true,
    industrialFacilities: false,
    pipelines: false,
    majorRoads: false,
    settlements: false,
    boundary: false,
  });

  const [activeFilter, setActiveFilter] = useState<'all' | 'high-risk' | 'industrial' | 'investigation'>('all');
  const [activeModal, setActiveModal] = useState<'report' | 'explore' | 'generate' | 'attribution' | 'forward-alert' | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>(DEFAULT_CENTER);
  const [mapZoom, setMapZoom] = useState<number>(DEFAULT_ZOOM);

  useEffect(() => {
    async function loadData() {
      try {
        const [summaryData, eventsData, notifData] = await Promise.all([
          fetchSummary(),
          fetchEvents(1000),
          fetchNotifications()
        ]);
        setSummary(summaryData);
        const mappedEvents: ThermalEvent[] = (eventsData as any[]).map(mapEventListItem);
        const isSriLanka = (lat: number, lng: number) => lat > 5.9 && lat < 9.9 && lng > 79.5 && lng < 81.9;
        const indianEvents = mappedEvents.filter((ev: ThermalEvent) => 
          (ev.lat > 6.5 && ev.lat < 36.0 && ev.lng > 68.0 && ev.lng < 98.0) && !isSriLanka(ev.lat, ev.lng)
        );
        setEvents(indianEvents);
        setDataLoadedAt(new Date()); // BUG-08/12: record actual fetch time
        // Normalize backend notification shape: { message, timestamp } → { description, time }
        const normalizedNotifs = notifData.map((n: any): NotificationItem => ({
          id: n.id,
          title: n.title,
          description: n.message || n.description || '',
          time: n.timestamp ? new Date(n.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : (n.time || ''),
          type: n.type as 'urgent' | 'info' | 'warning',
          read: n.read ?? false,
          eventId: n.eventId,
        }));
        setNotifications(normalizedNotifs);
      } catch (err) {
        console.error("Error loading initial data", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const toggleMapLayer = (layer: keyof MapLayersState) => {
    setMapLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  const selectEventById = async (id: string) => {
    const listEvent = events.find(e => e.id.toLowerCase() === id.toLowerCase());
    if (listEvent) {
      // Zoom to 10 so the heat zone is clearly visible on the map
      setMapCenter([listEvent.lat, listEvent.lng]);
      setMapZoom(10);

      // Set the basic event immediately so UI feels responsive
      setSelectedEvent(listEvent);
      setEventDetailLoading(true); // BUG-13: signal that detail is loading
      
      // Load forward history immediately
      try {
        const history = await fetchForwardHistory(listEvent.id);
        setForwardHistory(history.records || []);
      } catch (e) {
        console.error("Failed to load forward history", e);
        setForwardHistory([]);
      }

      // Fetch rich details
      try {
        const detail = await fetchEventDetails(listEvent.id);
        let riskTier = detail.risk?.tier || listEvent.risk;
        // Fix casing
        if (riskTier) riskTier = riskTier.charAt(0).toUpperCase() + riskTier.slice(1).toLowerCase();
        const riskScore = detail.risk?.score || 0;

        const sourceLabel = detail.classification?.thermal_only_estimate?.source || listEvent.probableSource || 'Unknown';
        // Determine nearest hazard correctly based on distance
        let nearestFacility: any = null;
        if (detail.gis_context) {
          const hazardTypes = ['nearest_industrial', 'nearest_factory', 'nearest_chemical', 'nearest_refinery', 'nearest_gas', 'nearest_mine', 'nearest_quarry', 'nearest_pipeline'];
          let minDist = Infinity;
          for (const ht of hazardTypes) {
            const fac = detail.gis_context[ht];
            if (fac && fac.distance_m != null && fac.distance_m < minDist) {
              minDist = fac.distance_m;
              nearestFacility = fac;
            }
          }
        }

        const facName = nearestFacility?.name && !nearestFacility.name.startsWith('Unnamed') ? nearestFacility.name : null;
        const facType = nearestFacility?.type || listEvent.candidateType || 'Industrial Facility';
        const candidateSource = facName || listEvent.candidateSource || resolveFacilityName(listEvent.lat, listEvent.lng, listEvent.probableSource);
        const candidateType = facType;

        let formattedWindSpeed = 'Unknown';
        let formattedPlume = 'Unknown';
        
        if (detail.weather && detail.weather.weather_match_status === 'Matched') {
          const w = detail.weather;
          if (w.wind_speed_10m !== null && w.wind_speed_10m !== undefined) {
            formattedWindSpeed = `${Number(w.wind_speed_10m).toFixed(1)} m/s`;
            if (w.wind_direction_10m_deg !== null && w.wind_direction_10m_deg !== undefined) {
              const windCompass = getCompassDirection(w.wind_direction_10m_deg);
              formattedWindSpeed += ` @ ${Math.round(w.wind_direction_10m_deg)}° (${windCompass})`;
            }
          }
          if (w.dispersion_direction_deg !== null && w.dispersion_direction_deg !== undefined) {
            const windCompass = getCompassDirection(w.wind_direction_10m_deg || 0);
            const dispCompass = getCompassDirection(w.dispersion_direction_deg);
            formattedPlume = `${windCompass} → ${dispCompass}`;
          }
        } else if (detail.weather && detail.weather.weather_match_status !== 'Matched') {
          formattedWindSpeed = 'Unavailable for this event';
          formattedPlume = 'Unavailable for this event';
        }

        const enrichedEvent: ThermalEvent = {
          ...listEvent,
          risk: riskTier as 'High' | 'Medium' | 'Low',
          riskScore: riskScore,
          probableSource: sourceLabel,
          confidence: Math.round((detail.classification?.thermal_only_estimate?.confidence || 0) * 100),
          detectedOn: `${detail.firms?.acq_date || ''} ${detail.firms?.acq_time || '12:00'}`.trim(),
          status: 'Not Assessed',
          frp: `${detail.firms?.frp ?? ''} MW`,
          intensity: `${detail.firms?.brightness ?? ''} K`,
          sensor: detail.firms?.satellite || (detail.firms?.day_night === 'D' ? 'VIIRS-SNPP' : 'MODIS'),
          candidateSource: candidateSource,
          candidateType: candidateType,
          distanceToSource: nearestFacility?.distance_m != null ? `${Math.round(nearestFacility.distance_m)}m` : 'Unknown',
          thermalCorrelation: detail.risk?.components?.thermal != null ? `${Math.round(detail.risk.components.thermal)} / 100` : 'Unknown',
          temporalCorrelation: detail.risk?.components?.persistence != null ? `${Math.round(detail.risk.components.persistence)} / 100` : 'Unknown',
          historicalDetections: detail.persistence?.trend_label || `${detail.persistence?.active_days_7 ?? 0} active days`,
          attributionReasoning: Array.isArray(detail.risk?.reasons) ? detail.risk.reasons.join(' ') : 'No reasoning available.',
          windSpeed: formattedWindSpeed,
          plumeDirection: formattedPlume,
          markerType: getMarkerType(sourceLabel, riskTier),
          // Store full backend response for intelligence features
          rawDetail: detail,

          // WEATHER
          weatherMatch: detail.weather?.weather_match_status || 'Unknown',
          weatherTime: detail.weather?.weather_time_used || 'Unknown',
          temperature_2m_C: detail.weather?.temperature_2m_C,
          relative_humidity_2m_percent: detail.weather?.relative_humidity_2m_percent,
          precipitation_mm: detail.weather?.precipitation_mm,
          wind_speed_10m: detail.weather?.wind_speed_10m,
          wind_direction_10m_deg: detail.weather?.wind_direction_10m_deg,
          weather_match_status: detail.weather?.weather_match_status,
        };
        setSelectedEvent(enrichedEvent);
      } catch (err) {
        console.error('Failed fetching event details', err);
      } finally {
        setEventDetailLoading(false); // BUG-13: always clear loading
      }
    }
  };

  const flyToLocation = (lat: number, lng: number, zoom = 10) => {
    setMapCenter([lat, lng]);
    setMapZoom(zoom);
  };

  const resetMapView = () => {
    setMapCenter(DEFAULT_CENTER);
    setMapZoom(DEFAULT_ZOOM);
  };

  const refreshForwardHistory = async () => {
    if (selectedEvent) {
      try {
        const history = await fetchForwardHistory(selectedEvent.id);
        setForwardHistory(history.records || []);
      } catch (e) {
        console.error("Failed to load forward history", e);
      }
    }
  };

  const markNotificationRead = (id: string) => {
    setNotifications(prev => prev.map(item => item.id === id ? { ...item, read: true } : item));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  const filteredEvents = events.filter(e => {
    if (activeFilter === 'high-risk') return e.risk === 'High';
    if (activeFilter === 'industrial') return e.probableSource === 'Industrial' || e.probableSource === 'Mining';
    // 'Not Assessed' means needs investigation; include High-risk too
    if (activeFilter === 'investigation') return e.status === 'In Progress' || e.status === 'Investigating' || e.status === 'Under Review' || e.risk === 'High';
    return true;
  });

  return (
    <ThermalContext.Provider
      value={{
        events,
        selectedEvent,
        setSelectedEvent,
        selectEventById,
        eventDetailLoading,
        facilities,
        pipelines,
        mapLayers,
        toggleMapLayer,
        activeFilter,
        setActiveFilter,
        filteredEvents,
        searchQuery,
        setSearchQuery,
        notifications,
        markNotificationRead,
        unreadCount,
        activeModal,
        setActiveModal,
        mapCenter,
        mapZoom,
        flyToLocation,
        resetMapView,
        summary,
        loading,
        dataLoadedAt,
        forwardHistory,
        refreshForwardHistory,
      }}
    >
      {children}
    </ThermalContext.Provider>
  );
};

export const useThermal = () => {
  const context = useContext(ThermalContext);
  if (!context) throw new Error('useThermal must be used within a ThermalProvider');
  return context;
};
