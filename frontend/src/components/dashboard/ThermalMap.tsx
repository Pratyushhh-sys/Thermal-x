import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Search, Plus, Minus, Crosshair, Flame, Factory, Layers, Navigation } from 'lucide-react';
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

// Create custom SVG Leaflet DivIcons matching Reference Image 2
const createCustomMarker = (event: ThermalEvent, isSelected: boolean) => {
  let iconHtml = '';
  const isHighRisk = event.risk === 'High';
  const label = event.mapLabel || (event.probableSource !== 'Unknown' ? event.probableSource : event.id);

  if (event.markerType === 'fire-red') {
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker group cursor-pointer">
        ${isSelected ? '<div class="hotspot-pulse bg-red-500/50"></div>' : ''}
        <div class="hotspot-core w-8 h-8 rounded-full bg-gradient-to-tr from-red-600 to-orange-500 border-2 border-white flex items-center justify-center shadow-lg ${isSelected ? 'ring-4 ring-orange-400' : ''}">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C12 2 15 8 15 12C15 13.5 15.5 14.5 16.5 13.5C18 12 19 9 19 9C19 9 22 14 22 19C22 23 18 26 12 26C6 26 2 23 2 19C2 14 6 9 9 5C10.5 3 12 2 12 2Z"/></svg>
        </div>
        <div class="mt-1 px-1.5 py-0.5 bg-black/75 backdrop-blur-xs text-white text-[10px] font-bold rounded shadow-md border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
  } else if (event.markerType === 'fire-orange') {
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker group cursor-pointer">
        ${isSelected ? '<div class="hotspot-pulse bg-orange-500/50"></div>' : ''}
        <div class="hotspot-core w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-400 border-2 border-white flex items-center justify-center shadow-lg ${isSelected ? 'ring-4 ring-amber-400' : ''}">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C12 2 15 8 15 12C15 13.5 15.5 14.5 16.5 13.5C18 12 19 9 19 9C19 9 22 14 22 19C22 23 18 26 12 26C6 26 2 23 2 19C2 14 6 9 9 5C10.5 3 12 2 12 2Z"/></svg>
        </div>
        <div class="mt-1 px-1.5 py-0.5 bg-black/75 backdrop-blur-xs text-white text-[10px] font-bold rounded shadow-md border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
  } else if (event.markerType === 'warning-red') {
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker group cursor-pointer">
        ${isSelected ? '<div class="hotspot-pulse bg-red-600/50"></div>' : ''}
        <div class="hotspot-core w-8 h-8 rounded-full bg-red-600 border-2 border-white flex items-center justify-center shadow-lg ${isSelected ? 'ring-4 ring-red-400' : ''}">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div class="mt-1 px-1.5 py-0.5 bg-black/75 backdrop-blur-xs text-white text-[10px] font-bold rounded shadow-md border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
  } else if (event.markerType === 'factory-blue') {
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker group cursor-pointer">
        <div class="hotspot-core w-8 h-8 rounded-full bg-blue-600 border-2 border-white flex items-center justify-center shadow-lg ${isSelected ? 'ring-4 ring-blue-400' : ''}">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/></svg>
        </div>
        <div class="mt-1 px-1.5 py-0.5 bg-black/75 backdrop-blur-xs text-white text-[10px] font-bold rounded shadow-md border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
  } else {
    // check-green
    iconHtml = `
      <div class="relative flex flex-col items-center custom-hotspot-marker group cursor-pointer">
        <div class="hotspot-core w-8 h-8 rounded-full bg-emerald-600 border-2 border-white flex items-center justify-center shadow-lg ${isSelected ? 'ring-4 ring-emerald-400' : ''}">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div class="mt-1 px-1.5 py-0.5 bg-black/75 backdrop-blur-xs text-white text-[10px] font-bold rounded shadow-md border border-white/20 whitespace-nowrap">
          ${label}
        </div>
      </div>
    `;
  }

  return L.divIcon({
    className: 'custom-leaflet-div-icon',
    html: iconHtml,
    iconSize: [36, 48],
    iconAnchor: [18, 24],
    popupAnchor: [0, -24],
  });
};

export const ThermalMap: React.FC = () => {
  const {
    events,
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
    <div className="relative w-full h-[540px] lg:h-[610px] rounded-xl overflow-hidden border border-slate-300 shadow-md bg-[#0B1E36]">
      
      {/* Real Leaflet Satellite Interactive Map */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full"
        ref={setMapInstance}
      >
        {/* Esri World Imagery Satellite Tile Layer (matches screenshot photorealistic terrain) */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="&copy; Esri &mdash; Earthstar Geographics"
          maxZoom={18}
        />

        {/* Boundary Layer if enabled */}
        {mapLayers.boundary && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            opacity={0.65}
          />
        )}

        {/* Programmatic fly-to controller */}
        <MapController center={mapCenter} zoom={mapZoom} />

        {/* Pipelines Layer matching Reference Image 2 connected lines */}
        {mapLayers.pipelines && pipelines.map(pipe => (
          <Polyline
            key={pipe.id}
            positions={pipe.points}
            pathOptions={{
              color: '#F59E0B',
              weight: 2.5,
              dashArray: '5, 8',
              opacity: 0.85
            }}
          />
        ))}

        {/* Thermal Event Hotspot Markers */}
        {mapLayers.thermalEvents && events.map(ev => (
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

          {/* Industrial Facilities */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.industrialFacilities}
              onChange={() => toggleMapLayer('industrialFacilities')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <Factory className="w-3.5 h-3.5 text-blue-600" />
            <span className="font-medium">Industrial Facilities</span>
          </label>

          {/* Pipelines */}
          <label className="flex items-center space-x-2 cursor-pointer hover:text-slate-900 text-slate-700">
            <input
              type="checkbox"
              checked={mapLayers.pipelines}
              onChange={() => toggleMapLayer('pipelines')}
              className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
            />
            <span className="w-3.5 h-0.5 bg-amber-500 inline-block rounded-full"></span>
            <span className="font-medium">Pipelines</span>
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

      {/* Floating Geographic Water Body & Country Labels matching Reference Image 2 */}
      <div className="absolute top-12 right-24 text-white/40 text-xs font-bold tracking-widest pointer-events-none uppercase">
        CHINA
      </div>
      <div className="absolute top-20 left-20 text-white/40 text-xs font-bold tracking-widest pointer-events-none uppercase">
        PAKISTAN
      </div>
      <div className="absolute top-28 right-36 text-white/40 text-xs font-bold tracking-widest pointer-events-none uppercase">
        NEPAL
      </div>
      <div className="absolute bottom-20 left-12 text-white/50 text-xs font-semibold tracking-wide pointer-events-none italic">
        Arabian Sea
      </div>
      <div className="absolute bottom-20 right-28 text-white/50 text-xs font-semibold tracking-wide pointer-events-none italic">
        Bay of Bengal
      </div>
      <div className="absolute top-48 left-1/2 -translate-x-1/2 text-white/30 text-base font-extrabold tracking-[0.3em] pointer-events-none uppercase">
        INDIA
      </div>

    </div>
  );
};
export default ThermalMap;
