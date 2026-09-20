import sys
import requests

def check_nasa_api():
    url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/ba126370fd392fe22ef85005491b984b/VIIRS_SNPP_NRT/67,6,98,37/1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("NASA API is ONLINE")
            sys.exit(0)
        else:
            print(f"NASA API returned status {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"NASA API connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_nasa_api()
