import urllib.request
import threading

def fetch():
    req = urllib.request.Request(
        'https://3x3299bnk6.execute-api.ap-south-1.amazonaws.com/prod/api/v1/zones',
        headers={'Origin': 'http://127.0.0.1:5173'}
    )
    try:
        urllib.request.urlopen(req)
        print("200")
    except Exception as e:
        print(f"Error: {e}")

threads = []
for i in range(10):
    t = threading.Thread(target=fetch)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
