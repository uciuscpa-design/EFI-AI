from __future__ import annotations

import json

from packages.gexy.databento_preflight import build_databento_preflight


def main() -> int:
    report = build_databento_preflight()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready_for_connectivity_test" else 1


if __name__ == "__main__":
    raise SystemExit(main())
