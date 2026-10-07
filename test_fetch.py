import urllib.request
import json

req = urllib.request.Request(
    'https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/reports',
    headers={
        'Origin': 'http://127.0.0.1:5173',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
)
try:
    with urllib.request.urlopen(req) as f:
        print(f.status)
        print(f.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode('utf-8'))
