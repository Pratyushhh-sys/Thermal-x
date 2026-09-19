"""
backend/schemas/event_schema.py
================================
Pydantic v2 response schemas for the thermal event intelligence API.

All schema fields use snake_case. All distances are in meters.
All FRP values are in megawatts (MW) as reported by FIRMS VIIRS.

Label disclaimer:
    classification.label = "Probable Source"  (NOT "Confirmed Fire Cause")
    source_label is a weak geographic label derived from OSM proximity.
    It is NOT verified fire-cause ground truth.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------
class LocationSchema(BaseModel):
    lat: float = Field(description="Latitude (WGS84)")
    lon: float = Field(description="Longitude (WGS84)")


class FIRMSSchema(BaseModel):
    frp: float = Field(description="Fire Radiative Power (MW)")
    brightness: float = Field(description="Brightness temperature Ti4 (K)")
    brightness_ti5: Optional[float] = Field(None, description="Brightness temperature Ti5 (K)")
    brightness_diff: Optional[float] = Field(None, description="Ti4 - Ti5 temperature difference (K)")
    confidence: Optional[float] = Field(None, description="Detection confidence (0-100 or 'h/m/l' mapped to numeric)")
    satellite: Optional[str] = Field(None, description="Satellite identifier (e.g. N, N20, T)")
    acq_date: Optional[str] = Field(None, description="Acquisition date (YYYY-MM-DD)")
    acq_time: Optional[str] = Field(None, description="Acquisition time (HHMM UTC)")
    scan: Optional[float] = Field(None, description="Scan pixel size (km)")
    track: Optional[float] = Field(None, description="Track pixel size (km)")
    day_night: Optional[str] = Field(None, description="Day/Night flag: D or N")


class PersistenceSchema(BaseModel):
    active_days_last_7: int = Field(description="Days with a detection within 1 km radius in the past 7 days")
    persistence_ratio: float = Field(description="active_days_last_7 / 7")
    observation_count_last_7: int = Field(description="Total hotspot observations within 1 km in past 7 days")
    avg_frp: Optional[float] = Field(None, description="Mean FRP of nearby events in window (MW)")
    max_frp: Optional[float] = Field(None, description="Maximum FRP in window (MW)")
    min_frp: Optional[float] = Field(None, description="Minimum FRP in window (MW)")
    frp_trend: float = Field(0.0, description="Linear FRP trend over window (MW/day; positive = intensifying)")
    frp_std: float = Field(0.0, description="FRP standard deviation in window (MW)")
    night_count: int = Field(0, description="Nighttime detections in window")
    day_count: int = Field(0, description="Daytime detections in window")
    trend_label: str = Field(description="Human label: persistent / intermittent / new / declining")


class NearbyFacilitySchema(BaseModel):
    type: str = Field(description="OSM feature type (industrial, factory, mine, etc.)")
    name: Optional[str] = Field(None, description="Facility name from OSM (null if not available in cache)")
    distance_m: float = Field(description="Haversine distance from event to facility (meters)")
    lat: Optional[float] = Field(None, description="Facility latitude")
    lon: Optional[float] = Field(None, description="Facility longitude")


class BufferItemSchema(BaseModel):
    type: str
    name: Optional[str] = None
    distance_m: float


class GISContextSchema(BaseModel):
    nearest_industrial: Optional[NearbyFacilitySchema] = None
    nearest_factory: Optional[NearbyFacilitySchema] = None
    nearest_chemical: Optional[NearbyFacilitySchema] = None
    nearest_refinery: Optional[NearbyFacilitySchema] = None
    nearest_gas: Optional[NearbyFacilitySchema] = None
    nearest_mine: Optional[NearbyFacilitySchema] = None
    nearest_quarry: Optional[NearbyFacilitySchema] = None
    nearest_pipeline: Optional[NearbyFacilitySchema] = None
    nearest_forest: Optional[NearbyFacilitySchema] = None
    nearest_cropland: Optional[NearbyFacilitySchema] = None
    buffers: Dict[str, List[BufferItemSchema]] = Field(
        default_factory=lambda: {"100m": [], "500m": [], "1000m": []},
        description="Infrastructure within distance buffers"
    )
    nearest_hazard_distance_m: Optional[float] = Field(
        None,
        description="Distance to the nearest industrial/mining hazard (m)"
    )


class ClassificationResultSchema(BaseModel):
    """
    AI source classification result.

    IMPORTANT: source_label is a WEAK GEOGRAPHIC LABEL from OSM proximity.
    This is a 'Probable Source' estimate, NOT a 'Confirmed Fire Cause'.
    """
    source: str = Field(description="Most probable source class")
    label: str = Field(
        default="Probable Source",
        description="Always 'Probable Source' — NOT 'Confirmed Fire Cause'"
    )
    confidence: float = Field(description="Probability of the predicted class (0-1)")
    probabilities: Dict[str, float] = Field(description="Class probabilities for all 5 classes")
    model_experiment: str = Field(description="Which experiment model produced this prediction")
    label_type: str = Field(
        default="weak_geographic_labels_NOT_verified_fire_cause",
        description="Source label type disclaimer"
    )


class ClassificationPairSchema(BaseModel):
    """Both Exp A (contextual) and Exp C (thermal-only honest) predictions."""
    contextual_estimate: Optional[ClassificationResultSchema] = Field(
        None,
        description="Exp A prediction (uses OSM context — HIGH leakage risk, best practical estimate)"
    )
    thermal_only_estimate: ClassificationResultSchema = Field(
        description="Exp C prediction (thermal+temporal only — NO leakage, conservative honest estimate)"
    )
    recommended: str = Field(
        default="thermal_only_estimate",
        description="Which estimate to use. thermal_only_estimate = leakage-free."
    )


class RiskComponentsSchema(BaseModel):
    thermal: float = Field(description="Thermal intensity score (0-100)")
    persistence: float = Field(description="Persistence score (0-100)")
    osm: float = Field(description="OSM proximity score (0-100)")
    ai: float = Field(description="AI classification confidence score (0-100)")


class RiskSchema(BaseModel):
    score: float = Field(description="Composite risk score (0-100)")
    tier: str = Field(description="Risk tier: HIGH / MEDIUM / LOW")
    components: RiskComponentsSchema
    reasons: List[str] = Field(description="Human-readable explanation for the risk score")
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "thermal": 0.30,
            "persistence": 0.30,
            "osm": 0.20,
            "ai": 0.20,
        },
        description="Risk formula weights (fixed per SIH specification)"
    )


class EventMetadataSchema(BaseModel):
    event_id: str
    model_primary: str = Field(description="Primary model used for risk/classification")
    model_contextual: Optional[str] = Field(None, description="Secondary contextual model")
    label_type: str = Field(default="weak_geographic_labels_NOT_verified_fire_cause")
    dataset: str = Field(default="FIRMS VIIRS (NASA)")
    obs_window: str = Field(default="2026-08-24 to 2026-09-18 (26 days)")
    persistence_radius_km: float = Field(default=1.0)


class EnvironmentSchema(BaseModel):
    wind_speed: Optional[float] = Field(None, description="Wind speed (km/h or m/s)")
    wind_direction: Optional[float] = Field(None, description="Wind direction (degrees)")
    temperature: Optional[float] = Field(None, description="Temperature (C or K)")
    humidity: Optional[float] = Field(None, description="Relative humidity (%)")


# ---------------------------------------------------------------------------
# Top-level response schemas
# ---------------------------------------------------------------------------
class EventResponse(BaseModel):
    """Complete intelligence result for a single thermal event."""
    id: str
    location: LocationSchema
    firms: FIRMSSchema
    persistence: PersistenceSchema
    gis_context: GISContextSchema
    classification: ClassificationPairSchema
    risk: RiskSchema
    environment: EnvironmentSchema
    metadata: EventMetadataSchema


class EventListItem(BaseModel):
    """Lightweight summary for event list endpoint."""
    id: str
    location: LocationSchema
    frp: float
    acq_date: Optional[str] = None
    source_label: Optional[str] = Field(None, description="Pre-computed OSM-derived label (weak geographic label)")
    risk_tier: Optional[str] = None
    risk_score: Optional[float] = None
    active_days_last_7: int = 0
    satellite: Optional[str] = None


class RiskSummarySchema(BaseModel):
    high: int
    medium: int
    low: int
    not_computed: int = 0


class SummaryResponse(BaseModel):
    total_events: int
    source_distribution: Dict[str, int]
    risk_summary: RiskSummarySchema
    avg_frp: float
    max_frp: float
    persistent_events: int = Field(description="Events with active_days_last_7 >= 4")
    high_frp_events: int = Field(description="Events with FRP >= 50 MW")
    observation_window: str
    dataset: str = "FIRMS VIIRS (NASA) — India bbox 67,6,98,37"
    label_disclaimer: str = (
        "source_label is a weak geographic label from OSM proximity. "
        "NOT verified fire-cause ground truth."
    )


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_experiment: str
    model_feature_count: int
    events_available: int
    osm_cache_types: int
    label_disclaimer: str = (
        "source_label = weak geographic label (NOT verified fire cause)"
    )
    details: Dict[str, Any] = Field(default_factory=dict)
