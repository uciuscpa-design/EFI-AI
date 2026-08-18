from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from packages.gexy.off_exchange_streaming import (
    ALPACA_SIP_STOCKS_URL,
    MASSIVE_DELAYED_STOCKS_URL,
    MASSIVE_REALTIME_STOCKS_URL,
    alpaca_auth_message,
    alpaca_trade_subscription,
    decode_websocket_payload,
    massive_auth_message,
    massive_trade_subscription,
    stamp_raw_stream_records,
)


def _parse_symbols(value: str) -> tuple[str, ...]:
    result = tuple(sorted({item.strip().upper() for item in value.split(",") if item.strip()}))
    if not result:
        raise argparse.ArgumentTypeError("--symbols must contain at least one ticker")
    return result


def _status_is_authenticated(provider: str, records: list[dict[str, object]]) -> bool:
    if provider == "alpaca_sip":
        return any(
            str(item.get("T", "")).lower() == "success"
            and str(item.get("msg", "")).lower() == "authenticated"
            for item in records
        )
    return any(
        str(item.get("status", "")).lower() in {"auth_success", "authenticated"}
        or "authenticated" in str(item.get("message", "")).lower()
        for item in records
    )


def _status_has_error(records: list[dict[str, object]]) -> bool:
    for item in records:
        if str(item.get("T", "")).lower() == "error":
            return True
        if str(item.get("status", "")).lower() in {"auth_failed", "error"}:
            return True
    return False


async def _capture(
    *,
    provider: str,
    symbols: tuple[str, ...],
    output: Path,
    duration_seconds: float,
    massive_delayed: bool,
) -> None:
    try:
        import websockets
    except ImportError as exc:
        raise SystemExit(
            "websockets is not installed. Run this script with an explicit temporary dependency, "
            "for example: uv run --with websockets python scripts/gexy_off_exchange_live_capture.py ..."
        ) from exc

    if provider == "massive":
        api_key = os.getenv("MASSIVE_API_KEY", "")
        if not api_key:
            raise SystemExit("MASSIVE_API_KEY was not found in the environment")
        endpoint = MASSIVE_DELAYED_STOCKS_URL if massive_delayed else MASSIVE_REALTIME_STOCKS_URL
        auth = massive_auth_message(api_key)
        subscription = massive_trade_subscription(symbols)
    else:
        api_key = os.getenv("APCA_API_KEY_ID", "")
        secret_key = os.getenv("APCA_API_SECRET_KEY", "")
        if not api_key or not secret_key:
            raise SystemExit("APCA_API_KEY_ID/APCA_API_SECRET_KEY were not found in the environment")
        endpoint = ALPACA_SIP_STOCKS_URL
        auth = alpaca_auth_message(api_key, secret_key)
        subscription = alpaca_trade_subscription(symbols)

    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = asyncio.get_running_loop().time() + duration_seconds

    async with websockets.connect(endpoint, max_size=None) as websocket:
        await websocket.send(json.dumps(auth))

        authenticated = False
        for _ in range(8):
            payload = await asyncio.wait_for(websocket.recv(), timeout=10)
            records = decode_websocket_payload(payload)
            if _status_has_error(records):
                raise SystemExit(f"{provider} authentication/feed access error: {records}")
            if _status_is_authenticated(provider, records):
                authenticated = True
                break
        if not authenticated:
            raise SystemExit(f"{provider} did not confirm authentication; subscription was not started")

        await websocket.send(json.dumps(subscription))

        with output.open("a", encoding="utf-8") as handle:
            while asyncio.get_running_loop().time() < deadline:
                remaining = max(0.05, deadline - asyncio.get_running_loop().time())
                try:
                    payload = await asyncio.wait_for(websocket.recv(), timeout=min(1.0, remaining))
                except TimeoutError:
                    continue
                records = decode_websocket_payload(payload)
                stamped = stamp_raw_stream_records(records, provider=provider)
                for record in stamped:
                    handle.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
                handle.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Capture raw push-based stock trade messages from Massive or Alpaca SIP into an immutable "
            "GEXY JSONL file. Default mode is fail-closed/dry-run; --connect is required to open a feed."
        )
    )
    parser.add_argument("--provider", required=True, choices=("massive", "alpaca_sip"))
    parser.add_argument("--symbols", required=True, type=_parse_symbols)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--duration-seconds", type=float, default=60.0)
    parser.add_argument(
        "--massive-delayed",
        action="store_true",
        help="use Massive delayed stock stream instead of the real-time endpoint",
    )
    parser.add_argument(
        "--connect",
        action="store_true",
        help="explicitly open the selected live/delayed WebSocket; omitted by default",
    )
    args = parser.parse_args()

    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be positive")

    print("GEXY OFF-EXCHANGE RAW STREAM CAPTURE PLAN")
    print(f"PROVIDER: {args.provider}")
    print(f"SYMBOLS: {','.join(args.symbols)}")
    print(f"DURATION: {args.duration_seconds:.1f}s")
    print(f"OUTPUT: {args.output}")
    print("TRANSPORT: WebSocket push stream; no REST polling loop")
    print("RAW-FIRST: source messages are written before any TRF/off-exchange feature transformation")
    print("CAUSAL CLOCK: each received message is stamped with gexy_received_at")

    if not args.connect:
        print("DRY RUN ONLY: no network connection opened. Re-run with --connect only after feed access is reviewed.")
        return

    if args.provider == "alpaca_sip":
        print("ACCESS GATE: Alpaca SIP entitlement is required; an entitlement error is not bypassed.")
    else:
        print("ACCESS GATE: selected Massive plan/endpoint must permit the requested stock stream.")

    asyncio.run(
        _capture(
            provider=args.provider,
            symbols=args.symbols,
            output=args.output,
            duration_seconds=args.duration_seconds,
            massive_delayed=args.massive_delayed,
        )
    )
    print("CAPTURE COMPLETE")


if __name__ == "__main__":
    main()
