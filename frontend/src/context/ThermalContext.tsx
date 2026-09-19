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
}

const ThermalContext = createContext<ThermalContextType | undefined>(undefined);

const DEFAULT_CENTER: [number, number] = [23.5, 78.5]; // Central India
const DEFAULT_ZOOM = 5;

// Helper to map backend list item to frontend model
const mapEventListItem = (apiItem: any): ThermalEvent => {
  let riskTier = apiItem.risk_tier || 'Medium';
  if (riskTier) {
    riskTier = riskTier.charAt(0).toUpperCase() + riskTier.slice(1).toLowerCase();
  }
  return {
    id: apiItem.id,
    location: `${apiItem.location.lat.toFixed(4)}° N, ${apiItem.location.lon.toFixed(4)}° E`,
    state: "Unknown",
    coordinates: `${apiItem.location.lat}, ${apiItem.location.lon}`,
    lat: apiItem.location.lat,
    lng: apiItem.location.lon,
    risk: riskTier as 'High' | 'Medium' | 'Low',
    probableSource: apiItem.source_label || 'Unknown',
    confidence: 0,
    detectedOn: apiItem.acq_date || 'Unknown',
    status: 'Not Assessed',
    frp: `${apiItem.frp} MW`,
    intensity: 'Unknown',
    sensor: apiItem.satellite || 'Unknown',
    candidateSource: 'Unknown',
    candidateType: 'Unknown',
    distanceToSource: 'Unknown',
    thermalCorrelation: 'Unknown',
    temporalCorrelation: 'Unknown',
    historicalDetections: `${apiItem.active_days_last_7 || 0} active days`,
    attributionReasoning: 'Details not loaded',
    windSpeed: 'Unknown',
    plumeDirection: 'Unknown',
    markerType: riskTier === 'High' ? 'warning-red' : (apiItem.source_label === 'Industrial' ? 'factory-blue' : 'fire-orange'),
  };
};

export const ThermalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<ThermalEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<ThermalEvent | null>(null);
  const [facilities] = useState<IndustrialFacility[]>(import.meta.env.VITE_ENABLE_MOCK_GIS === 'true' ? mockFacilities : []);
  const [pipelines] = useState<PipelineTrack[]>(import.meta.env.VITE_ENABLE_MOCK_GIS === 'true' ? mockPipelines : []);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [mapLayers, setMapLayers] = useState<MapLayersState>({
    thermalEvents: true,
    industrialFacilities: import.meta.env.VITE_ENABLE_MOCK_GIS === 'true',
    pipelines: import.meta.env.VITE_ENABLE_MOCK_GIS === 'true',
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
          fetchEvents(100),
          fetchNotifications()
        ]);
        setSummary(summaryData);
        setEvents(eventsData.map(mapEventListItem));
        setNotifications(notifData);
        if (eventsData.length > 0) {
          // fetch detail for the first one just to prepopulate? Or just leave it null.
          // We'll leave it null initially until user selects.
        }
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
      setMapCenter([listEvent.lat, listEvent.lng]);
      setMapZoom(7);
      
      // Set the basic event immediately so UI feels responsive
      setSelectedEvent(listEvent);

      // Fetch rich details
      try {
        const detail = await fetchEventDetails(listEvent.id);
        
        let riskTier = detail.risk?.tier || 'Medium';
        if (riskTier) riskTier = riskTier.charAt(0).toUpperCase() + riskTier.slice(1).toLowerCase();

        const enrichedEvent: ThermalEvent = {
          ...listEvent,
          risk: riskTier as 'High' | 'Medium' | 'Low',
          probableSource: detail.classification?.thermal_only_estimate?.source || 'Unknown',
          confidence: Math.round((detail.classification?.thermal_only_estimate?.confidence || 0) * 100),
          detectedOn: `${detail.firms.acq_date || ''} ${detail.firms.acq_time || ''}`,
          status: 'Not Assessed',
          frp: `${detail.firms.frp} MW`,
          intensity: `${detail.firms.brightness} K`,
          sensor: detail.firms.satellite || 'Unknown',
          candidateSource: detail.gis_context?.nearest_industrial?.name || detail.gis_context?.nearest_mine?.name || 'Unknown Facility',
          candidateType: detail.gis_context?.nearest_industrial?.type || detail.gis_context?.nearest_mine?.type || 'Unknown Type',
          distanceToSource: detail.gis_context?.nearest_hazard_distance_m ? `${Math.round(detail.gis_context.nearest_hazard_distance_m)}m` : 'Unknown',
          thermalCorrelation: detail.risk?.components?.thermal ? `${Math.round(detail.risk.components.thermal)} / 100` : 'Unknown',
          temporalCorrelation: detail.risk?.components?.persistence ? `${Math.round(detail.risk.components.persistence)} / 100` : 'Unknown',
          historicalDetections: detail.persistence?.trend_label || 'Unknown',
          attributionReasoning: detail.risk?.reasons?.join(' ') || 'No reasoning available.',
          windSpeed: detail.environment?.wind_speed !== null ? `${detail.environment.wind_speed} m/s` : 'Unknown',
          plumeDirection: detail.environment?.wind_direction !== null ? `${detail.environment.wind_direction}°` : 'Unknown',
        };
        setSelectedEvent(enrichedEvent);
      } catch (err) {
        console.error("Failed fetching event details", err);
      }
    }
  };

  const flyToLocation = (lat: number, lng: number, zoom = 7) => {
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
    if (activeFilter === 'industrial') return e.probableSource === 'Industrial';
    if (activeFilter === 'investigation') return e.status === 'In Progress' || e.status === 'Investigating' || e.status === 'Under Review';
    return true;
  });

  return (
    <ThermalContext.Provider
      value={{
        events,
        selectedEvent,
        setSelectedEvent,
        selectEventById,
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
        loading
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
