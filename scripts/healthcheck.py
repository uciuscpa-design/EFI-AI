import json
import sys
from urllib.request import urlopen

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/health"
with urlopen(url, timeout=5) as response:
    payload = json.load(response)
if payload.get("status") != "ok":
    raise SystemExit(1)
print(json.dumps(payload))
