import urllib.request
import threading
import json

def fetch_post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Origin': 'http://127.0.0.1:5173', 'Content-Type': 'application/json'}
    )
    try:
        urllib.request.urlopen(req)
        print(f"200 {url}")
    except Exception as e:
        print(f"Error {url}: {e}")

payload = {
    "rainfall_mm": 25,
    "river_level": "LOW",
    "population_density": 900,
    "road_accessibility": 90,
    "shelter_capacity": 85,
    "medical_capacity": 90,
    "historical_risk": 10
}

threads = []
for i in range(5):
    t1 = threading.Thread(target=fetch_post, args=('https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/risk/analyze', payload))
    t2 = threading.Thread(target=fetch_post, args=('https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/simulation/flood', payload))
    threads.extend([t1, t2])
    t1.start()
    t2.start()

for t in threads:
    t.join()
