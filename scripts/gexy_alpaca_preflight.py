from __future__ import annotations

import sys
from urllib.error import HTTPError, URLError

from packages.gexy.alpaca_provider import AlpacaHttpClient, DATA_BASE, PAPER_BASE


def _check(name: str, fn) -> bool:
    try:
        fn()
    except HTTPError as exc:
        print(f"{name}: FAIL HTTP {exc.code}")
        if exc.code == 401:
            print("  authentication rejected; verify the APCA paper key/secret pair")
        elif exc.code == 403:
            print("  authenticated but access is forbidden for this endpoint/feed")
        return False
    except URLError as exc:
        print(f"{name}: FAIL network error: {exc.reason}")
        return False
    except Exception as exc:
        print(f"{name}: FAIL {type(exc).__name__}: {exc}")
        return False
    print(f"{name}: OK")
    return True


def main() -> int:
    try:
        client = AlpacaHttpClient()
    except RuntimeError as exc:
        print(f"credentials: FAIL {exc}")
        return 2

    print("credentials: PRESENT")
    trading_ok = _check(
        "paper trading auth",
        lambda: client.get(f"{PAPER_BASE}/v2/account"),
    )
    data_ok = _check(
        "SPX indicative option data",
        lambda: client.get(
            f"{DATA_BASE}/v1beta1/options/snapshots/SPX",
            {"feed": "indicative", "limit": 1},
        ),
    )

    if trading_ok and data_ok:
        print("GEXY Alpaca preflight: PASS")
        return 0
    print("GEXY Alpaca preflight: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
