import urllib.request
import threading
import json

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={'Origin': 'http://127.0.0.1:5173', 'Accept': 'application/json'}
    )
    try:
        urllib.request.urlopen(req)
        print(f"200 {url}")
    except Exception as e:
        print(f"Error {url}: {e}")

fetch('https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/zones')
fetch('https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/reports')
fetch('https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/resources/summary')
