import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Search, Plus, Minus, Crosshair, Flame, Factory, Navigation, Satellite } from 'lucide-react';
import { useThermal } from '../../context/ThermalContext';
import { ThermalEvent } from '../../data/mockData';

// Leaflet map controller to handle programmatic pan & zoom
const MapController: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
};

const createCustomMarker = (event: ThermalEvent, isSelected: boolean) => {
  const label = event.mapLabel || (event.probableSource !== 'Unknown' ? event.probableSource : event.id);

  // Define styling based on marker type
  let colorConfig = { core: 'bg-emerald-500', pulse: 'bg-emerald-500/50', ring: 'ring-emerald-400' };
  let iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';

  if (event.markerType === 'fire-red') {
    colorConfig = { core: 'bg-gradient-to-tr from-red-600 to-orange-500', pulse: 'bg-red-500/50', ring: 'ring-orange-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C12 2 15 8 15 12C15 13.5 15.5 14.5 16.5 13.5C18 12 19 9 19 9C19 9 22 14 22 19C22 23 18 26 12 26C6 26 2 23 2 19C2 14 6 9 9 5C10.5 3 12 2 12 2Z"/></svg>';
  } else if (event.markerType === 'fire-orange') {
    colorConfig = { core: 'bg-gradient-to-tr from-orange-500 to-amber-400', pulse: 'bg-orange-500/50', ring: 'ring-amber-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C12 2 15 8 15 12C15 13.5 15.5 14.5 16.5 13.5C18 12 19 9 19 9C19 9 22 14 22 19C22 23 18 26 12 26C6 26 2 23 2 19C2 14 6 9 9 5C10.5 3 12 2 12 2Z"/></svg>';
  } else if (event.markerType === 'warning-red') {
    colorConfig = { core: 'bg-red-600', pulse: 'bg-red-600/50', ring: 'ring-red-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
  } else if (event.markerType === 'factory-blue') {
    colorConfig = { core: 'bg-blue-600', pulse: 'bg-blue-500/50', ring: 'ring-blue-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/></svg>';
  } else if (event.markerType === 'agri-yellow') {
    colorConfig = { core: 'bg-gradient-to-tr from-yellow-500 to-lime-400', pulse: 'bg-yellow-400/50', ring: 'ring-yellow-300' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/></svg>';
  } else if (event.markerType === 'forest-green') {
    colorConfig = { core: 'bg-gradient-to-tr from-green-600 to-emerald-400', pulse: 'bg-green-500/50', ring: 'ring-green-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M17 12C17 9.24 14.76 7 12 7S7 9.24 7 12c0 2.22 1.39 4.12 3.35 4.79V19h3.3v-2.21C15.61 16.12 17 14.22 17 12z"/></svg>';
  } else if (event.markerType === 'mine-purple') {
    colorConfig = { core: 'bg-gradient-to-tr from-purple-700 to-violet-400', pulse: 'bg-purple-500/50', ring: 'ring-purple-400' };
    iconSvg = '<svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>';
  }

  let iconHtml = '';
  
  if (isSelected) {
    // Huge pulsing marker with label when selected
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker cursor-pointer z-50">
        <div class="hotspot-pulse ${colorConfig.pulse}"></div>
        <div class="hotspot-core w-8 h-8 rounded-full ${colorConfig.core} border-2 border-white flex items-center justify-center shadow-lg ring-4 ${colorConfig.ring}">
          ${iconSvg}
        </div>
        <div class="mt-1 px-2 py-1 bg-slate-900/90 backdrop-blur-md text-white text-[11px] font-bold rounded shadow-xl border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
    return L.divIcon({
      className: 'custom-leaflet-div-icon',
      html: iconHtml,
      iconSize: [40, 56],
      iconAnchor: [20, 28],
    });
  } else {
    // Tiny uncluttered dot when not selected
    iconHtml = `
      <div class="relative flex flex-col items-center cursor-pointer opacity-80 hover:opacity-100 hover:scale-125 transition-all">
        <div class="w-3 h-3 rounded-full ${colorConfig.core} border border-white/80 shadow-sm"></div>
      </div>
    `;
    return L.divIcon({
      className: 'custom-leaflet-div-icon',
      html: iconHtml,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
  }
};

export const ThermalMap: React.FC = () => {
  const {
    events,
    filteredEvents,
    selectedEvent,
    selectEventById,
    pipelines,
    facilities,
    mapLayers,
    toggleMapLayer,
    mapCenter,
    mapZoom,
    flyToLocation,
    resetMapView
  } = useThermal();

  const [mapSearchText, setMapSearchText] = useState('');
  const [mapInstance, setMapInstance] = useState<L.Map | null>(null);
  const [useSatellite, setUseSatellite] = useState(false);

  const handleMapSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!mapSearchText.trim()) return;

    const query = mapSearchText.toLowerCase();
    const found = events.find(
      ev => ev.location.toLowerCase().includes(query) ||
            ev.state.toLowerCase().includes(query) ||
            ev.id.toLowerCase().includes(query) ||
            ev.candidateSource.toLowerCase().includes(query)
    );

    if (found) {
      selectEventById(found.id);
      setMapSearchText('');
    }
  };

  const zoomIn = () => {
    if (mapInstance) mapInstance.zoomIn();
  };

  const zoomOut = () => {
    if (mapInstance) mapInstance.zoomOut();
  };

  return (
    <div className="relative w-full h-[540px] lg:h-[610px] rounded-2xl overflow-hidden border border-slate-100 premium-shadow bg-slate-900">
      
      {/* Real Leaflet Satellite Interactive Map */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full"
        ref={setMapInstance}
        maxBounds={[
          [6.5, 68.0], // South West
          [37.5, 97.5] // North East
        ]}
        maxBoundsViscosity={1.0}
        minZoom={4}
      >
        {/* Base tile layer — Esri World Street Map (Clean, no API key needed) */}
        {!useSatellite && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri"
            maxZoom={19}
          />
        )}
        {/* Satellite tile layer — Esri imagery */}
        {useSatellite && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="&copy; Esri &mdash; Earthstar Geographics"
            maxZoom={18}
          />
        )}
        {/* When satellite is on, overlay labels from Esri */}
        {useSatellite && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            attribution=""
            maxZoom={19}
          />
        )}

        {/* Boundary Layer if enabled */}
        {mapLayers.boundary && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            opacity={0.8}
          />
        )}

        {/* Programmatic fly-to controller */}
        <MapController center={mapCenter} zoom={mapZoom} />

        {/* Thermal Event Hotspot Markers — BUG-10: cap at 300 to prevent DOM jank */}
        {mapLayers.thermalEvents && filteredEvents.slice(0, 300).map(ev => (
          <Marker
            key={ev.id}
            position={[ev.lat, ev.lng]}
            icon={createCustomMarker(ev, selectedEvent?.id === ev.id)}
            eventHandlers={{
              click: () => {
                selectEventById(ev.id);
              }
            }}
          />
        ))}
      </MapContainer>

      {/* FLOATING OVERLAY: Top Left Search On Map matching Reference Image 2 */}
      <div className="absolute top-4 left-4 z-[1000] w-64 sm:w-72">
        <form onSubmit={handleMapSearch} className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-3.5 h-3.5" />
          </div>
          <input
            type="text"
            value={mapSearchText}
            onChange={(e) => setMapSearchText(e.target.value)}
            placeholder="Search on map..."
            className="w-full pl-9 pr-3 py-2 text-xs bg-white/95 backdrop-blur-md rounded-lg border border-slate-200 shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 placeholder:text-slate-400"
          />
        </form>
      </div>

      {/* FLOATING OVERLAY: Top Right Zoom & Target Controls matching Reference Image 2 */}
      <div className="absolute top-4 right-4 z-[1000] flex flex-col space-y-1.5">
        <button
          onClick={zoomIn}
          className="w-8 h-8 rounded-md bg-white hover:bg-slate-50 text-slate-700 shadow-md border border-slate-200 flex items-center justify-center transition-colors font-bold text-base"
          title="Zoom in"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          className="w-8 h-8 rounded-md bg-white hover:bg-slate-50 text-slate-700 shadow-md border border-slate-200 flex items-center justify-center transition-colors font-bold text-base"
          title="Zoom out"
        >
          <Minus className="w-4 h-4" />
        </button>
        {/* Satellite / Map toggle button */}
        <button
          onClick={() => setUseSatellite(prev => !prev)}
          className="w-8 h-8 rounded-md bg-white hover:bg-slate-50 text-slate-700 shadow-md border border-slate-200 flex items-center justify-center transition-colors text-[10px] font-bold"
          title={useSatellite ? 'Switch to Map view' : 'Switch to Satellite view'}
        >
          <Satellite className={`w-4 h-4 ${useSatellite ? 'text-blue-600' : 'text-slate-600'}`} />
        </button>
        <button
          onClick={resetMapView}
          className="w-8 h-8 rounded-md bg-white hover:bg-slate-50 text-slate-700 shadow-md border border-slate-200 flex items-center justify-center transition-colors"
          title="Reset View to India"
        >
          <Crosshair className="w-4 h-4 text-slate-600" />
        </button>
      </div>

      {/* FLOATING OVERLAY: Bottom Left "Map Layers →" Panel matching Reference Image 2 */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-md rounded-lg p-3 shadow-xl border border-slate-200/90 text-xs w-48 select-none">
        <div className="font-bold text-slate-800 mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
          <span className="flex items-center space-x-1.5">
            <span>Map Layers</span>
            <span className="text-slate-400">→</span>
          </span>
        </div>

        <div className="space-y-1.5">
          {/* Thermal Events */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.thermalEvents}
              onChange={() => toggleMapLayer('thermalEvents')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <Flame className="w-3.5 h-3.5 text-orange-500" />
            <span className="font-medium">Thermal Events</span>
          </label>

          {/* Major Roads */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.majorRoads}
              onChange={() => toggleMapLayer('majorRoads')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <span className="w-3.5 h-0.5 bg-slate-400 inline-block"></span>
            <span className="font-medium">Major Roads</span>
          </label>

          {/* Settlements */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.settlements}
              onChange={() => toggleMapLayer('settlements')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span>
            <span className="font-medium">Settlements</span>
          </label>

          {/* Boundary */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.boundary}
              onChange={() => toggleMapLayer('boundary')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <span className="w-3.5 border-b border-dashed border-slate-500 inline-block"></span>
            <span className="font-medium">Boundary</span>
          </label>
        </div>
      </div>

      {/* FLOATING OVERLAY: Bottom Right Scale & Compass Indicator */}
      <div className="absolute bottom-4 right-4 z-[1000] flex items-center space-x-3 bg-black/40 backdrop-blur-xs px-2.5 py-1 rounded text-white text-[10px] font-mono pointer-events-none">
        <div className="flex items-center space-x-1 border-r border-white/30 pr-2">
          <span>0</span>
          <span className="w-8 h-0.5 bg-white inline-block"></span>
          <span>250</span>
          <span className="w-8 h-0.5 bg-white inline-block"></span>
          <span>500 km</span>
        </div>
        <div className="flex items-center space-x-0.5 text-slate-200">
          <Navigation className="w-3 h-3 text-cyan-400 transform -rotate-45" />
          <span className="font-bold text-[9px]">N</span>
        </div>
      </div>

    </div>
  );
};
export default ThermalMap;
