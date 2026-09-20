export interface ThermalEvent {
  id: string;
  location: string;
  state: string;
  coordinates: string;
  lat: number;
  lng: number;
  risk: 'High' | 'Medium' | 'Low';
  riskScore?: number;
  probableSource: 'Agricultural' | 'Forest' | 'Industrial' | 'Mining' | 'Other' | 'Pipeline' | 'Power Plant' | 'Settlement' | 'Unknown' | string;
  confidence: number;
  detectedOn: string;
  status: 'In Progress' | 'Under Review' | 'Investigating' | 'Resolved' | 'Not Assessed';
  frp: string; // Fire Radiative Power
  intensity: string;
  sensor: string;
  candidateSource: string;
  candidateType: string;
  distanceToSource: string;
  thermalCorrelation: string;
  temporalCorrelation: string;
  historicalDetections: string;
  attributionReasoning: string;
  windSpeed: string;
  plumeDirection: string;
  markerType: 'fire-red' | 'fire-orange' | 'warning-red' | 'factory-blue' | 'check-green' | 'forest-green' | 'agri-yellow' | 'mine-purple';
  mapLabel?: string;
  // Full backend event detail response — populated when user selects this event
  rawDetail?: any;
}

export interface IndustrialFacility {
  id: string;
  name: string;
  type: string;
  location: string;
  lat: number;
  lng: number;
  capacity: string;
}

export interface PipelineTrack {
  id: string;
  name: string;
  points: [number, number][];
}

export interface NotificationItem {
  id: string;
  title: string;
  // Support both backend shape (message/timestamp) and legacy shape (description/time)
  description?: string;
  message?: string;
  time?: string;
  timestamp?: string;
  type: 'urgent' | 'info' | 'warning';
  read: boolean;
  eventId?: string;
}

export const mockThermalEvents: ThermalEvent[] = [
  {
    id: 'TH-1024',
    location: 'Punjab, India',
    state: 'Punjab',
    coordinates: '31.5204° N, 75.1531° E',
    lat: 31.5204,
    lng: 75.1531,
    risk: 'High',
    probableSource: 'Industrial',
    confidence: 91,
    detectedOn: '14 Sep 2025, 09:42 AM (IST)',
    status: 'In Progress',
    frp: '142.6 MW',
    intensity: '840 K',
    sensor: 'INSAT-3DR TIR / VIIRS 375m',
    candidateSource: 'Bathinda Petrochemical & Fertilizer Complex',
    candidateType: 'Refinery / Fertilizer Stack',
    distanceToSource: '1.4 km',
    thermalCorrelation: '94%',
    temporalCorrelation: '91%',
    historicalDetections: '8 events recorded in past 90 days',
    attributionReasoning: 'Thermal flare dispersion matches prevailing NW wind at 14 km/h. Emission footprint aligns with cracking unit emergency blowoff cycle.',
    windSpeed: '14 km/h NW',
    plumeDirection: 'South-East',
    markerType: 'fire-red',
    mapLabel: 'Punjab'
  },
  {
    id: 'TH-0876',
    location: 'Gujarat, India',
    state: 'Gujarat',
    coordinates: '22.2587° N, 71.1924° E',
    lat: 22.2587,
    lng: 71.1924,
    risk: 'Medium',
    probableSource: 'Pipeline',
    confidence: 84,
    detectedOn: '13 Sep 2025, 16:20 PM (IST)',
    status: 'Under Review',
    frp: '86.2 MW',
    intensity: '685 K',
    sensor: 'MODIS Aqua / Terra Thermal Bands',
    candidateSource: 'Hazira-Bijapur Gas Transmission Trunkline Section 4',
    candidateType: 'High-Pressure Hydrocarbon Pipeline',
    distanceToSource: '0.8 km',
    thermalCorrelation: '88%',
    temporalCorrelation: '81%',
    historicalDetections: '2 anomalous signatures in 12 months',
    attributionReasoning: 'Heat anomaly detected adjacent to mainline block valve #14 right-of-way corridor with gas pressure gradient drop.',
    windSpeed: '19 km/h WSW',
    plumeDirection: 'East-North-East',
    markerType: 'fire-red',
    mapLabel: 'Gujarat'
  },
  {
    id: 'TH-0643',
    location: 'Rajasthan, India',
    state: 'Rajasthan',
    coordinates: '27.0238° N, 74.2179° E',
    lat: 27.0238,
    lng: 74.2179,
    risk: 'High',
    probableSource: 'Industrial',
    confidence: 89,
    detectedOn: '12 Sep 2025, 22:17 PM (IST)',
    status: 'Investigating',
    frp: '128.4 MW',
    intensity: '790 K',
    sensor: 'VIIRS Suomi-NPP Thermal I-4 Band',
    candidateSource: 'Nagaur Zinc Smelter & Mineral Processing Facility',
    candidateType: 'Non-Ferrous Metallurgical Smelter',
    distanceToSource: '1.2 km',
    thermalCorrelation: '90%',
    temporalCorrelation: '87%',
    historicalDetections: '14 unnotified night-time emissions',
    attributionReasoning: 'Smelter furnace slag tapping thermal signature detected outside permitted operational hours. High spatial correlation with slag pit.',
    windSpeed: '8 km/h NE',
    plumeDirection: 'South-West',
    markerType: 'fire-orange',
    mapLabel: 'Rajasthan'
  },
  {
    id: 'TH-0531',
    location: 'Maharashtra, India',
    state: 'Maharashtra',
    coordinates: '19.7515° N, 75.7139° E',
    lat: 19.7515,
    lng: 75.7139,
    risk: 'Low',
    probableSource: 'Power Plant',
    confidence: 95,
    detectedOn: '11 Sep 2025, 11:08 AM (IST)',
    status: 'Resolved',
    frp: '45.1 MW',
    intensity: '540 K',
    sensor: 'Landsat 9 TIRS-2',
    candidateSource: 'Chandrapur Super Thermal Power Station Unit 5',
    candidateType: 'Coal-Fired Thermal Power Station',
    distanceToSource: '0.4 km',
    thermalCorrelation: '96%',
    temporalCorrelation: '95%',
    historicalDetections: 'Permitted continuous cooling discharge',
    attributionReasoning: 'Scheduled routine boiler blowdown into cooling discharge canal; verified within CPCB thermal limits.',
    windSpeed: '11 km/h S',
    plumeDirection: 'North',
    markerType: 'check-green',
    mapLabel: 'Maharashtra'
  },
  // Additional points corresponding to markers shown on the dashboard map (Reference Image 2)
  {
    id: 'TH-0912',
    location: 'Delhi NCR, India',
    state: 'Delhi',
    coordinates: '28.6139° N, 77.2090° E',
    lat: 28.6139,
    lng: 77.2090,
    risk: 'High',
    probableSource: 'Industrial',
    confidence: 88,
    detectedOn: '14 Sep 2025, 08:15 AM (IST)',
    status: 'In Progress',
    frp: '115.0 MW',
    intensity: '780 K',
    sensor: 'INSAT-3DR TIR',
    candidateSource: 'Okhla Industrial Area Cluster Phase 3',
    candidateType: 'Manufacturing & Chemical Processing',
    distanceToSource: '0.9 km',
    thermalCorrelation: '89%',
    temporalCorrelation: '85%',
    historicalDetections: '5 events in past 60 days',
    attributionReasoning: 'High surface heat radiance localized over chemical recycling warehouse.',
    windSpeed: '10 km/h NW',
    plumeDirection: 'South-East',
    markerType: 'warning-red',
    mapLabel: 'Delhi'
  },
  {
    id: 'TH-0744',
    location: 'Mumbai, Maharashtra',
    state: 'Maharashtra',
    coordinates: '19.0760° N, 72.8777° E',
    lat: 19.0760,
    lng: 72.8777,
    risk: 'Medium',
    probableSource: 'Industrial',
    confidence: 93,
    detectedOn: '13 Sep 2025, 14:05 PM (IST)',
    status: 'In Progress',
    frp: '98.5 MW',
    intensity: '710 K',
    sensor: 'VIIRS Suomi-NPP',
    candidateSource: 'Trombay Petrochemical Refinery & Storage Terminal',
    candidateType: 'Oil & Gas Refinery',
    distanceToSource: '0.5 km',
    thermalCorrelation: '95%',
    temporalCorrelation: '92%',
    historicalDetections: 'Regulated continuous flare',
    attributionReasoning: 'Elevated hydrocarbon flare during maintenance changeover.',
    windSpeed: '16 km/h W',
    plumeDirection: 'East',
    markerType: 'factory-blue',
    mapLabel: 'Mumbai'
  },
  {
    id: 'TH-0418',
    location: 'Hyderabad, Telangana',
    state: 'Telangana',
    coordinates: '17.3850° N, 78.4867° E',
    lat: 17.3850,
    lng: 78.4867,
    risk: 'Low',
    probableSource: 'Settlement',
    confidence: 78,
    detectedOn: '10 Sep 2025, 18:30 PM (IST)',
    status: 'Resolved',
    frp: '32.0 MW',
    intensity: '510 K',
    sensor: 'MODIS Terra',
    candidateSource: 'Pashamylaram Industrial Estate Buffer Zone',
    candidateType: 'Municipal Biomass / Waste',
    distanceToSource: '3.1 km',
    thermalCorrelation: '74%',
    temporalCorrelation: '69%',
    historicalDetections: 'Seasonal localized brush fire',
    attributionReasoning: 'Open ground agricultural and biomass residue burning outside plant fence line.',
    windSpeed: '12 km/h E',
    plumeDirection: 'West',
    markerType: 'check-green',
    mapLabel: 'Hyderabad'
  },
  {
    id: 'TH-0329',
    location: 'Bengaluru, Karnataka',
    state: 'Karnataka',
    coordinates: '12.9716° N, 77.5946° E',
    lat: 12.9716,
    lng: 77.5946,
    risk: 'Low',
    probableSource: 'Industrial',
    confidence: 82,
    detectedOn: '09 Sep 2025, 15:45 PM (IST)',
    status: 'Resolved',
    frp: '38.4 MW',
    intensity: '530 K',
    sensor: 'Landsat 9 TIRS-2',
    candidateSource: 'Peenya Industrial Zone Complex',
    candidateType: 'Light Metallurgy & Casting',
    distanceToSource: '1.1 km',
    thermalCorrelation: '85%',
    temporalCorrelation: '82%',
    historicalDetections: 'Normal daytime operation',
    attributionReasoning: 'Casting foundry furnace heat dissipation during daytime batch casting.',
    windSpeed: '14 km/h SW',
    plumeDirection: 'North-East',
    markerType: 'check-green',
    mapLabel: 'Bengaluru'
  },
  {
    id: 'TH-0622',
    location: 'Madhya Pradesh, India',
    state: 'Madhya Pradesh',
    coordinates: '23.4733° N, 77.9479° E',
    lat: 23.4733,
    lng: 77.9479,
    risk: 'High',
    probableSource: 'Industrial',
    confidence: 87,
    detectedOn: '12 Sep 2025, 19:10 PM (IST)',
    status: 'In Progress',
    frp: '112.3 MW',
    intensity: '760 K',
    sensor: 'INSAT-3DR TIR',
    candidateSource: 'Bina Refinery & Petrochemicals Complex',
    candidateType: 'Crude Oil Refinery',
    distanceToSource: '1.8 km',
    thermalCorrelation: '91%',
    temporalCorrelation: '88%',
    historicalDetections: '6 events in past 90 days',
    attributionReasoning: 'Sudden flare combustion spike detected following grid power fluctuation.',
    windSpeed: '9 km/h N',
    plumeDirection: 'South',
    markerType: 'warning-red'
  }
];

export const mockFacilities: IndustrialFacility[] = [
  {
    id: 'FAC-01',
    name: 'Bathinda Petrochemical & Fertilizer Complex',
    type: 'Petrochemical / Fertilizer',
    location: 'Bathinda, Punjab',
    lat: 30.2110,
    lng: 74.9455,
    capacity: '11.3 MMTPA'
  },
  {
    id: 'FAC-02',
    name: 'Reliance Jamnagar Mega Refinery',
    type: 'Oil & Gas Refinery',
    location: 'Jamnagar, Gujarat',
    lat: 22.3556,
    lng: 69.8392,
    capacity: '33 MMTPA'
  },
  {
    id: 'FAC-03',
    name: 'Nagaur Zinc & Lead Smelting Works',
    type: 'Non-Ferrous Metallurgical Smelter',
    location: 'Nagaur, Rajasthan',
    lat: 27.2000,
    lng: 73.7400,
    capacity: '600,000 TPA'
  },
  {
    id: 'FAC-04',
    name: 'Bina Petrochemicals & Refinery',
    type: 'Refinery',
    location: 'Sagar, Madhya Pradesh',
    lat: 24.1800,
    lng: 78.1900,
    capacity: '7.8 MMTPA'
  },
  {
    id: 'FAC-05',
    name: 'BPCL Mumbai Marine Refinery',
    type: 'Refinery Complex',
    location: 'Mahul, Mumbai, Maharashtra',
    lat: 19.0100,
    lng: 72.8900,
    capacity: '12 MMTPA'
  },
  {
    id: 'FAC-06',
    name: 'NTPC Korba Super Thermal Power Plant',
    type: 'Coal Thermal Power',
    location: 'Korba, Chhattisgarh',
    lat: 22.3688,
    lng: 82.6841,
    capacity: '2,600 MW'
  }
];

// Major Pipeline Network Polylines across India matching Reference Image 2
export const mockPipelines: PipelineTrack[] = [
  {
    id: 'PIPE-01',
    name: 'North-West Gas Trunkline (Hazira - Jagdishpur Corridor)',
    points: [
      [21.1702, 72.8311], // Surat/Hazira
      [22.3072, 73.1812], // Vadodara
      [23.2599, 77.4126], // Bhopal/Bina
      [26.8467, 80.9462], // Lucknow/Jagdishpur
      [28.6139, 77.2090], // Delhi NCR
      [31.5204, 75.1531]  // Punjab / Bathinda
    ]
  },
  {
    id: 'PIPE-02',
    name: 'Western Energy Corridor',
    points: [
      [22.4707, 70.0577], // Jamnagar
      [23.0225, 72.5714], // Ahmedabad
      [26.9124, 75.7873], // Jaipur
      [28.6139, 77.2090]  // Delhi
    ]
  },
  {
    id: 'PIPE-03',
    name: 'Central-Southern Hydrocarbon Grid',
    points: [
      [19.0760, 72.8777], // Mumbai
      [18.5204, 73.8567], // Pune
      [17.3850, 78.4867], // Hyderabad
      [12.9716, 77.5946]  // Bengaluru
    ]
  },
  {
    id: 'PIPE-04',
    name: 'Eastern Industrial Gas Pipeline',
    points: [
      [23.2599, 77.4126], // Bina
      [24.5854, 80.8322], // Satna
      [25.5941, 85.1376], // Patna
      [22.5726, 88.3639]  // Haldia/Kolkata
    ]
  }
];

export const mockNotifications: NotificationItem[] = [
  {
    id: 'NOTIF-01',
    title: 'High-risk thermal event detected',
    description: 'Event TH-1024 flagged in Punjab. FRP: 142.6 MW exceeding baseline by 320%.',
    time: '2 min ago',
    type: 'urgent',
    read: false,
    eventId: 'TH-1024'
  },
  {
    id: 'NOTIF-02',
    title: 'New industrial-source candidate identified',
    description: 'Bathinda Petrochemical & Fertilizer Complex attributed with 91% ML confidence.',
    time: '15 min ago',
    type: 'info',
    read: false,
    eventId: 'TH-1024'
  },
  {
    id: 'NOTIF-03',
    title: 'Investigation requires attention',
    description: 'TH-0876 in Gujarat pipeline corridor marked Under Review by Regional Field Office.',
    time: '1 hour ago',
    type: 'warning',
    read: false,
    eventId: 'TH-0876'
  }
];

export const summaryMetrics = {
  activeEvents: 12,
  highRiskEvents: 5,
  industrialEvents: 4,
  requiringInvestigation: 4,
  liveFreshness: '2 min ago',
  lastUpdate: '10:24 AM (IST)'
};
