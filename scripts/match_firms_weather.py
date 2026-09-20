import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import xarray as xr
from datetime import timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

# Define paths
GRIB_FILE = Path("data/data.grib")
FIRMS_FILE = Path("data/features/source_classification_features.csv")
OUTPUT_FILE = Path("data/processed/firms_weather_enriched.csv")
REPORT_FILE = Path("reports/weather_matching_report.json")

MAX_TIME_DIFF_MINUTES = 60

def calculate_wind_speed(u, v):
    return np.sqrt(u**2 + v**2)

def calculate_wind_direction(u, v):
    """
    Calculate meteorological wind direction (direction FROM which wind blows)
    0=North, 90=East, 180=South, 270=West
    """
    # math.atan2(v, u) gives angle of the vector (TO which wind blows)
    # Meteorological direction is FROM which it blows, so we add 180 (or subtract)
    direction = (270 - np.degrees(np.arctan2(v, u))) % 360
    return direction

def calculate_relative_humidity(t2m, d2m):
    """
    Calculate relative humidity using temperature and dewpoint (both in Kelvin or Celsius).
    Using Magnus-Tetens approximation. Expects Celsius.
    """
    # e = 6.11 * 10.0 ** (7.5 * d2m / (237.3 + d2m))
    # es = 6.11 * 10.0 ** (7.5 * t2m / (237.3 + t2m))
    # rh = (e / es) * 100
    # Simplified approximation:
    t_c = t2m - 273.15
    d_c = d2m - 273.15
    rh = 100 * (np.exp((17.625 * d_c) / (243.04 + d_c)) / np.exp((17.625 * t_c) / (243.04 + t_c)))
    return np.clip(rh, 0, 100)

def match_weather():
    print(f"Loading FIRMS data from {FIRMS_FILE}...")
    firms_df = pd.read_csv(FIRMS_FILE)
    
    # Ensure datetime column exists or construct it
    if 'datetime_utc' in firms_df.columns:
        firms_df['timestamp'] = pd.to_datetime(firms_df['datetime_utc'])
    elif 'hour' in firms_df.columns:
        # Construct from acq_date and hour
        firms_df['timestamp'] = pd.to_datetime(firms_df['acq_date']) + pd.to_timedelta(firms_df['hour'], unit='h')
    else:
        # Construct from acq_date and acq_time
        def parse_acq_time(t):
            t_str = str(t).zfill(4)
            return f"{t_str[:2]}:{t_str[2:]}:00"
        time_strs = firms_df['acq_time'].apply(parse_acq_time)
        firms_df['timestamp'] = pd.to_datetime(firms_df['acq_date'] + ' ' + time_strs)

    print(f"Loading ERA5 GRIB data from {GRIB_FILE}...")
    try:
        import cfgrib
        datasets = cfgrib.open_datasets(str(GRIB_FILE))
        if not datasets:
            raise ValueError("No datasets found in GRIB")
        
        # Find the dataset that contains surface variables like t2m or u10
        ds = None
        for d in datasets:
            if 't2m' in d.data_vars or 'u10' in d.data_vars:
                ds = d
                break
        
        if ds is None:
            print("Warning: Could not find typical surface variables (t2m, u10). Using first dataset.")
            ds = datasets[0]
            
    except Exception as e:
        print(f"Error opening GRIB file: {e}")
        return
        
    print(f"GRIB Variables found: {list(ds.data_vars)}")
    
    # Initialize columns
    new_cols = {
        'weather_time_used': [],
        'time_difference_minutes': [],
        'weather_grid_latitude': [],
        'weather_grid_longitude': [],
        'weather_grid_distance_km': [],
        'weather_match_status': []
    }
    
    # Variables to track
    vars_to_extract = ['t2m', 'd2m', 'u10', 'v10', 'tp', 'sp', 'tcc', 'ssrd']
    available_vars = [v for v in vars_to_extract if v in ds.data_vars]
    
    for v in available_vars:
        new_cols[v] = []

    # Get coordinate arrays for fast nearest neighbour
    era_lats = ds.latitude.values
    era_lons = ds.longitude.values
    era_times = pd.to_datetime(ds.time.values)
    
    print(f"Processing {len(firms_df)} FIRMS events...")
    
    for idx, row in firms_df.iterrows():
        target_lat = row['latitude']
        target_lon = row['longitude']
        target_time = row['timestamp']
        
        # Temporal Match
        time_diffs = np.abs(era_times - target_time)
        best_time_idx = time_diffs.argmin()
        best_time = era_times[best_time_idx]
        diff_mins = time_diffs[best_time_idx].total_seconds() / 60.0
        
        # Spatial Match
        lat_idx = np.abs(era_lats - target_lat).argmin()
        lon_idx = np.abs(era_lons - target_lon).argmin()
        
        matched_lat = era_lats[lat_idx]
        matched_lon = era_lons[lon_idx]
        
        # Simple Euclidean distance for the grid distance (approximation)
        # 1 deg ~ 111 km
        dist_km = np.sqrt((target_lat - matched_lat)**2 + ((target_lon - matched_lon) * np.cos(np.radians(target_lat)))**2) * 111.0
        
        status = "MATCHED"
        if diff_mins > MAX_TIME_DIFF_MINUTES:
            status = "TIME_MISMATCH"
            
        new_cols['weather_time_used'].append(best_time)
        new_cols['time_difference_minutes'].append(diff_mins)
        new_cols['weather_grid_latitude'].append(matched_lat)
        new_cols['weather_grid_longitude'].append(matched_lon)
        new_cols['weather_grid_distance_km'].append(dist_km)
        new_cols['weather_match_status'].append(status)
        
        if status == "MATCHED":
            # Extract variables
            # cfgrib datasets might have dimensions (time, latitude, longitude) or (time, step, surface, latitude, longitude)
            # We select the scalar value using indexing
            # To make it robust across cfgrib structures, we use isel
            # But the dimensions depend on the variable
            for v in available_vars:
                # Find the dimensions of this variable
                var_da = ds[v]
                sel_dict = {}
                for dim in var_da.dims:
                    if dim == 'time': sel_dict['time'] = best_time_idx
                    elif dim == 'latitude': sel_dict['latitude'] = lat_idx
                    elif dim == 'longitude': sel_dict['longitude'] = lon_idx
                    else: sel_dict[dim] = 0 # take first for other dims like step, surface
                
                try:
                    val = var_da.isel(**sel_dict).values.item()
                    new_cols[v].append(val)
                except Exception:
                    new_cols[v].append(np.nan)
        else:
            for v in available_vars:
                new_cols[v].append(np.nan)
                
    # Add to dataframe
    for col, values in new_cols.items():
        firms_df[col] = values
        
    # Derived Features
    print("Calculating derived atmospheric features...")
    if 't2m' in firms_df.columns:
        firms_df['temperature_2m_C'] = firms_df['t2m'] - 273.15
    if 'd2m' in firms_df.columns:
        firms_df['dewpoint_2m_C'] = firms_df['d2m'] - 273.15
        if 't2m' in firms_df.columns:
            firms_df['relative_humidity_2m_percent'] = calculate_relative_humidity(firms_df['t2m'], firms_df['d2m'])
            
    if 'u10' in firms_df.columns and 'v10' in firms_df.columns:
        firms_df['wind_speed_10m'] = calculate_wind_speed(firms_df['u10'], firms_df['v10'])
        firms_df['wind_direction_10m_deg'] = calculate_wind_direction(firms_df['u10'], firms_df['v10'])
        
    if 'tp' in firms_df.columns:
        # tp in ERA5 is usually in meters, convert to mm
        firms_df['precipitation_mm'] = firms_df['tp'] * 1000.0
        
    if 'sp' in firms_df.columns:
        # sp in ERA5 is in Pa, convert to hPa
        firms_df['surface_pressure_hPa'] = firms_df['sp'] / 100.0
        
    if 'tcc' in firms_df.columns:
        # tcc is 0-1, convert to percent
        firms_df['cloud_cover_percent'] = firms_df['tcc'] * 100.0
        
    if 'ssrd' in firms_df.columns:
        firms_df['surface_solar_radiation'] = firms_df['ssrd']

    # We do NOT drop original FIRMS columns
    print(f"Saving enriched dataset to {OUTPUT_FILE}...")
    firms_df.to_csv(OUTPUT_FILE, index=False)
    
    # Generate Report
    report = {
        "total_firms_events": len(firms_df),
        "matched_events": len(firms_df[firms_df['weather_match_status'] == 'MATCHED']),
        "unmatched_events": len(firms_df[firms_df['weather_match_status'] != 'MATCHED']),
        "match_percentage": round((len(firms_df[firms_df['weather_match_status'] == 'MATCHED']) / len(firms_df)) * 100, 2),
        "average_temporal_difference_mins": round(firms_df['time_difference_minutes'].mean(), 2),
        "average_spatial_distance_km": round(firms_df['weather_grid_distance_km'].mean(), 2),
        "available_variables": available_vars
    }
    
    if 'temperature_2m_C' in firms_df.columns:
        report['min_temp_c'] = round(firms_df['temperature_2m_C'].min(), 2)
        report['max_temp_c'] = round(firms_df['temperature_2m_C'].max(), 2)
    if 'wind_speed_10m' in firms_df.columns:
        report['min_wind_speed'] = round(firms_df['wind_speed_10m'].min(), 2)
        report['max_wind_speed'] = round(firms_df['wind_speed_10m'].max(), 2)
        
    os.makedirs(REPORT_FILE.parent, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
        
    print("\n==================================================")
    print("WEATHER MATCHING COMPLETE")
    print(f"FIRMS EVENTS: {report['total_firms_events']}")
    print(f"MATCHED: {report['matched_events']}")
    print(f"UNMATCHED: {report['unmatched_events']}")
    print(f"MATCH RATE: {report['match_percentage']}%")
    print(f"Average temporal difference: {report['average_temporal_difference_mins']} minutes")
    print(f"Average spatial distance: {report['average_spatial_distance_km']} km")
    print("==================================================")
    
if __name__ == "__main__":
    match_weather()
