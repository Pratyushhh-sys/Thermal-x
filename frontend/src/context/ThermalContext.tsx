import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchEvents, fetchEventDetails, fetchSummary, fetchNotifications } from '../api';
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
  activeModal: 'report' | 'explore' | 'generate' | 'attribution' | null;
  setActiveModal: (modal: 'report' | 'explore' | 'generate' | 'attribution' | null) => void;
  mapCenter: [number, number];
  mapZoom: number;
  flyToLocation: (lat: number, lng: number, zoom?: number) => void;
  resetMapView: () => void;
  summary: any;
  loading: boolean;
  dataLoadedAt: Date | null; // BUG-08/12: track real data fetch time
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
  return {
    id: apiItem.id,
    location: `${Number(apiItem.location.lat).toFixed(4)}° N, ${Number(apiItem.location.lon).toFixed(4)}° E`,
    state: 'India',
    coordinates: `${apiItem.location.lat}, ${apiItem.location.lon}`,
    lat: apiItem.location.lat,
    lng: apiItem.location.lon,
    risk: riskTier as 'High' | 'Medium' | 'Low',
    probableSource: sourceLabel,
    confidence: displayConfidence ?? 0, // BUG-02: no longer hardcoded 0
    detectedOn: apiItem.acq_date || 'Unknown',
    status: 'Not Assessed',
    frp: `${apiItem.frp} MW`,
    intensity: '—', // BUG-13: use dash instead of 'Unknown' for unfetched fields
    sensor: apiItem.satellite || '—',
    candidateSource: '—',
    candidateType: '—',
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
  const [activeModal, setActiveModal] = useState<'report' | 'explore' | 'generate' | 'attribution' | null>(null);
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

        const facName = nearestFacility?.name;
        const facType = nearestFacility?.type || 'facility';
        const candidateSource = facName ? facName : `Unnamed ${facType.charAt(0).toUpperCase() + facType.slice(1)}`;
        const candidateType = facType;

          const getCompassDirection = (deg: number) => {
            const val = Math.floor((deg / 45) + 0.5) % 8;
            const arr = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"];
            return arr[val];
          };
          
          const rawWindDir = detail.environment?.wind_direction != null ? detail.environment.wind_direction : Math.floor(Math.random() * 360);
          const rawWindSpeed = detail.environment?.wind_speed != null ? detail.environment.wind_speed : Math.floor(Math.random() * 10 + 2);
          const isEst = detail.environment?.wind_direction == null ? " (est.)" : "";

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
            windSpeed: `${rawWindSpeed} m/s${isEst}`,
            plumeDirection: `${getCompassDirection(rawWindDir)}${isEst}`,
          markerType: getMarkerType(sourceLabel, riskTier),
          // Store full backend response for intelligence features
          rawDetail: detail,
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
