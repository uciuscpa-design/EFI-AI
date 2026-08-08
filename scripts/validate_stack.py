import os
import sys
from urllib.request import urlopen

base = os.getenv("EFI_HEALTH_URL", "http://127.0.0.1:8000")
checks = ("/health", "/ready")
for path in checks:
    with urlopen(base + path, timeout=10) as response:
        if response.status != 200:
            raise SystemExit(f"{path}: HTTP {response.status}")
print("EFI-AI stack validation passed")
