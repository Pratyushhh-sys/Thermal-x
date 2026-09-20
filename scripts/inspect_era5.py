import os
import sys
from pathlib import Path
import json

def inspect_grib(file_path):
    print(f"Inspecting GRIB file: {file_path}")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        import xarray as xr
        import cfgrib
    except ImportError:
        print("ERROR: xarray or cfgrib not installed.")
        return

    try:
        # Opening GRIB files often results in multiple datasets if there are different hypercubes
        # (e.g. surface vs pressure levels). We'll try to open it and catch standard issues.
        print("Attempting to open dataset...")
        datasets = cfgrib.open_datasets(file_path)
        
        if not datasets:
            print("No datasets found in GRIB file.")
            return
            
        print(f"\nFound {len(datasets)} dataset(s) in GRIB file.")
        
        all_variables = {}
        for i, ds in enumerate(datasets):
            print(f"\n--- Dataset {i+1} ---")
            print(f"Dimensions: {ds.dims}")
            print(f"Coordinates: {list(ds.coords.keys())}")
            
            print("Variables:")
            for var_name, var_data in ds.data_vars.items():
                units = var_data.attrs.get('units', 'unknown')
                long_name = var_data.attrs.get('long_name', 'unknown')
                print(f"  - {var_name}: {long_name} ({units})")
                all_variables[var_name] = {
                    'units': units,
                    'long_name': long_name,
                    'dims': var_data.dims
                }
                
            if 'time' in ds.coords:
                times = ds.time.values
                print(f"Time range: {times.min()} to {times.max()} ({len(times)} steps)")
            
            if 'latitude' in ds.coords and 'longitude' in ds.coords:
                lats = ds.latitude.values
                lons = ds.longitude.values
                print(f"Latitude range: {lats.min()} to {lats.max()} ({len(lats)} points)")
                print(f"Longitude range: {lons.min()} to {lons.max()} ({len(lons)} points)")
                
        # Save a quick summary for other scripts if needed
        summary = {
            "file": str(file_path),
            "variables": all_variables
        }
        with open("data/era5_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
            
    except Exception as e:
        print(f"Error inspecting GRIB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    grib_path = Path("data/data.grib")
    inspect_grib(grib_path)
