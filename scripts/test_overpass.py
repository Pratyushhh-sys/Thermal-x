import requests

headers = {'User-Agent': 'ThermalSourceAttribution/1.0 SIH2026 PS26162 (research)'}
q = '[out:json][timeout:30]; node["landuse"="industrial"](6,67,37,98); out center;'

mirrors = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
    'https://overpass.openstreetmap.ru/api/interpreter',
]

for url in mirrors:
    try:
        r = requests.post(url, data={'data': q}, headers=headers, timeout=30)
        print(f'URL: {url}')
        print(f'  Status: {r.status_code}')
        print(f'  Body[:200]: {r.text[:200]}')
    except Exception as e:
        print(f'URL: {url}')
        print(f'  ERROR: {e}')
    print()
