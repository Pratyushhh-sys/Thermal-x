# Thermal X - Project Documentation

## 1. Project Overview
Thermal X is a satellite-based industrial fire and thermal source attribution platform developed for the Smart India Hackathon 2026 (Problem Statement 26162). The platform is designed to ingest satellite thermal anomaly data, process it using machine learning, and attribute potential industrial, agricultural, or forest sources. It provides actionable intelligence to government agencies for regulatory enforcement and environmental monitoring.

## 2. Core Architecture
The application follows a modern decoupled architecture:

### Frontend (Client)
- **Framework:** React (Vite)
- **Styling:** Tailwind CSS with a custom Premium Light Theme (Glassmorphism, curated gradients, fluid shadows).
- **Mapping:** React-Leaflet integrated with OpenStreetMap tiles for performant geospatial visualization.
- **State Management:** Custom React Context API (`ThermalContext.tsx` and `AuthContext.tsx`) for global state and authentication.

### Backend (Server)
- **Framework:** FastAPI (Python)
- **API Endpoints:** RESTful endpoints providing geospatial querying, event filtering, and machine learning inference.
- **Geospatial Engine:** BallTree-based proximity lookups to calculate distances between thermal events and OpenStreetMap features.

## 3. Data Flow & Pipeline
1. **Data Acquisition:** The system ingests thermal anomaly data primarily sourced from NASA FIRMS (Fire Information for Resource Management System).
2. **Feature Engineering:** Geospatial coordinates are cross-referenced with OpenStreetMap (OSM) data to generate proximity features (e.g., distance to nearest factory, farm, or forest).
3. **Machine Learning Inference:** The XGBoost model receives the engineered features and predicts the most probable source category.
4. **Risk Scoring:** A composite risk score (0-100) is calculated based on Fire Radiative Power (FRP), temporal persistence (7-day window), proximity to critical infrastructure, and sensor confidence.
5. **Visualization:** The resulting intelligence is passed via the REST API to the React frontend for visualization on the Interactive Map.

## 4. Machine Learning Methodology
The core attribution engine uses **XGBoost Classifier** models.
- **Weak Labeling:** Due to the absence of ground-truth fire investigation reports, the models are trained using "weak labels" derived from precise geospatial intersection with OSM polygons. 
- **Experimentation Layers:**
  - *Experiment A:* Baseline model using all features. Prone to data leakage due to the inclusion of direct distance metrics.
  - *Experiment C:* The production model. It removes highly correlated distance features to prevent data leakage, relying instead on holistic contextual features to predict the source.

---

## 5. Addressing the Satellite Periodicity Limitation
**Question:** *If the satellite cannot provide live streaming data and its coverage is periodic, then won't a sudden thermal hotspot go undetected initially?*

**Answer:** 
Yes, this is a fundamental limitation of Low Earth Orbit (LEO) satellite intelligence systems.

**Why this happens:**
Satellites carrying the **VIIRS** (Visible Infrared Imaging Radiometer Suite) and **MODIS** sensors (like Suomi-NPP, NOAA-20, Aqua, and Terra) are not geostationary. They orbit the Earth and only pass over a specific location (like a state in India) roughly **1 to 2 times every 24 hours**. 

They do not act like security cameras providing a continuous 24/7 video feed. Instead, they operate like a scanner taking a "snapshot" of the Earth as they fly over.

**The Impact on Detection:**
If a severe industrial thermal anomaly or fire ignites immediately *after* the satellite has passed overhead, the system will be entirely blind to that event until the satellite completes its orbit and returns over that location (which can take anywhere from **6 to 12 hours** depending on the specific satellite constellation). 

**Conclusion:**
Thermal X is an **Investigative Intelligence and Near Real-Time (NRT) Monitoring Platform**, not an instant early warning system. It excels at identifying persistent thermal violations, illegal long-term flaring, and large-scale agricultural burning patterns, but it cannot guarantee instantaneous detection of sudden, short-lived fires.
