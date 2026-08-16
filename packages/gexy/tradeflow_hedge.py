from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.forward_greeks import black76_greeks, implied_volatility_from_forward_price
from packages.gexy.models import OptionType
from packages.gexy.replay import add_forward_horizon_labels


SPX_MULTIPLIER = 100.0

HEDGE_FLOW_FEATURES = (
    "hedge_greek_symbols",
    "hedge_greek_solved_symbols",
    "hedge_greek_solved_pct",
    "hedge_classified_contract_volume",
    "hedge_delta_units",
    "hedge_delta_notional",
    "hedge_call_delta_units",
    "hedge_put_delta_units",
    "hedge_gamma_units_per_point",
    "hedge_gax_notional_per_point",
    "hedge_gex_notional_per_1pct",
    "hedge_call_gamma_units_per_point",
    "hedge_put_gamma_units_per_point",
    "hedge_gross_abs_delta_notional",
    "hedge_gross_abs_gex_notional_per_1pct",
)


def _option_type(value: object) -> OptionType | None:
    text = str(value).strip().upper()
    if text == "C":
        return OptionType.CALL
    if text == "P":
        return OptionType.PUT
    return None


def build_symbol_minute_greeks(
    classified: pd.DataFrame,
    replay: pd.DataFrame,
) -> pd.DataFrame:
    """Build completed-minute Black-76 Greeks for symbols observed in TCBBO.

    The option midpoint is the median pre-trade NBBO midpoint across all TCBBO
    records for a symbol during minute M. Forward, discount factor, and time to
    expiry are taken from the exact replay row for minute M. The resulting Greek
    snapshot is only intended for use after minute M completes (timestamp M+1).
    No future minute is used.
    """
    required_trade = {
        "ts_recv",
        "symbol",
        "instrument_class",
        "strike_price",
        "bid_px_00",
        "ask_px_00",
    }
    missing_trade = sorted(required_trade.difference(classified.columns))
    if missing_trade:
        raise ValueError(
            f"classified TCBBO frame missing required columns: {', '.join(missing_trade)}"
        )

    required_replay = {
        "timestamp",
        "forward",
        "discount_factor_fit",
        "time_to_expiry_minutes",
    }
    missing_replay = sorted(required_replay.difference(replay.columns))
    if missing_replay:
        raise ValueError(
            f"replay frame missing required columns: {', '.join(missing_replay)}"
        )

    trades = classified.copy()
    trades["ts_recv"] = pd.to_datetime(trades["ts_recv"], utc=True, errors="coerce")
    for column in ("strike_price", "bid_px_00", "ask_px_00"):
        trades[column] = pd.to_numeric(trades[column], errors="coerce")
    trades["symbol"] = trades["symbol"].astype(str).str.strip()
    trades["instrument_class"] = trades["instrument_class"].astype(str).str.upper()
    trades = trades.dropna(
        subset=["ts_recv", "symbol", "instrument_class", "strike_price", "bid_px_00", "ask_px_00"]
    ).copy()
    trades = trades[
        (trades["strike_price"] > 0)
        & (trades["bid_px_00"] >= 0)
        & (trades["ask_px_00"] > 0)
        & (trades["ask_px_00"] >= trades["bid_px_00"])
        & trades["instrument_class"].isin(["C", "P"])
    ].copy()
    if trades.empty:
        raise ValueError("classified TCBBO frame contains no usable option quotes")

    trades["flow_minute"] = trades["ts_recv"].dt.floor("min")
    trades["pretrade_mid"] = (trades["bid_px_00"] + trades["ask_px_00"]) / 2.0
    symbol_minutes = (
        trades.groupby(["flow_minute", "symbol", "instrument_class", "strike_price"], as_index=False)
        .agg(
            greek_source_records=("pretrade_mid", "size"),
            representative_mid_price=("pretrade_mid", "median"),
        )
        .sort_values(["flow_minute", "symbol"])
        .reset_index(drop=True)
    )

    state = replay.copy()
    state["flow_minute"] = pd.to_datetime(state["timestamp"], utc=True, errors="coerce")
    for column in ("forward", "discount_factor_fit", "time_to_expiry_minutes"):
        state[column] = pd.to_numeric(state[column], errors="coerce")
    state = state.dropna(subset=["flow_minute"]).drop_duplicates("flow_minute", keep="last")
    state = state[["flow_minute", "forward", "discount_factor_fit", "time_to_expiry_minutes"]]

    merged = symbol_minutes.merge(state, on="flow_minute", how="left", validate="many_to_one")
    merged["greek_state_match"] = merged["forward"].notna()

    iv_values: list[float | None] = []
    delta_values: list[float | None] = []
    gamma_values: list[float | None] = []

    minutes_per_year = 365.0 * 24.0 * 60.0
    for row in merged.itertuples(index=False):
        option_type = _option_type(row.instrument_class)
        forward = float(row.forward) if pd.notna(row.forward) else float("nan")
        discount = (
            float(row.discount_factor_fit)
            if pd.notna(row.discount_factor_fit)
            else float("nan")
        )
        tte_minutes = (
            float(row.time_to_expiry_minutes)
            if pd.notna(row.time_to_expiry_minutes)
            else float("nan")
        )
        if (
            option_type is None
            or not np.isfinite(forward)
            or forward <= 0
            or not np.isfinite(discount)
            or discount <= 0
            or not np.isfinite(tte_minutes)
            or tte_minutes <= 0
        ):
            iv_values.append(None)
            delta_values.append(None)
            gamma_values.append(None)
            continue

        tte_years = tte_minutes / minutes_per_year
        iv = implied_volatility_from_forward_price(
            option_type=option_type,
            option_price=float(row.representative_mid_price),
            forward=forward,
            strike=float(row.strike_price),
            time_to_expiry_years=tte_years,
            discount_factor=discount,
        )
        if iv is None:
            iv_values.append(None)
            delta_values.append(None)
            gamma_values.append(None)
            continue

        greeks = black76_greeks(
            option_type=option_type,
            forward=forward,
            strike=float(row.strike_price),
            time_to_expiry_years=tte_years,
            volatility=iv,
            discount_factor=discount,
        )
        iv_values.append(iv)
        delta_values.append(greeks.delta_forward)
        gamma_values.append(greeks.gamma_forward)

    merged["implied_volatility"] = iv_values
    merged["delta_forward"] = delta_values
    merged["gamma_forward"] = gamma_values
    merged["greek_solved"] = merged["delta_forward"].notna() & merged["gamma_forward"].notna()
    merged["timestamp"] = merged["flow_minute"] + pd.to_timedelta(1, unit="min")
    return merged


def apply_dealer_hedge_proxy(
    classified: pd.DataFrame,
    symbol_minute_greeks: pd.DataFrame,
) -> pd.DataFrame:
    """Attach opposite-side liquidity-provider hedge proxies to classified trades.

    Sign convention:
      inferred buy  => aggressor bought option, liquidity provider proxy sold it
      inferred sell => aggressor sold option, liquidity provider proxy bought it

    ``hedge_delta_units`` is the index-equivalent delta-neutral hedge change the
    opposite-side liquidity-provider proxy would make. Positive means buy the
    underlying/index-equivalent hedge; negative means sell it.

    ``hedge_gamma_units_per_point`` is the change in that hedge demand for a
    +1-point move in the forward. Positive corresponds to customer option buying
    / opposite-side short-gamma flow; negative corresponds to customer option
    selling / opposite-side long-gamma flow. This remains a proxy, not observed
    dealer inventory or executed hedge flow.
    """
    required = {
        "ts_recv",
        "symbol",
        "instrument_class",
        "size",
        "signed_side",
    }
    missing = sorted(required.difference(classified.columns))
    if missing:
        raise ValueError(f"classified TCBBO frame missing required columns: {', '.join(missing)}")

    trades = classified.copy()
    trades["ts_recv"] = pd.to_datetime(trades["ts_recv"], utc=True, errors="coerce")
    trades["flow_minute"] = trades["ts_recv"].dt.floor("min")
    trades["symbol"] = trades["symbol"].astype(str).str.strip()
    trades["instrument_class"] = trades["instrument_class"].astype(str).str.upper()
    trades["size"] = pd.to_numeric(trades["size"], errors="coerce")
    trades["signed_side"] = pd.to_numeric(trades["signed_side"], errors="coerce")

    greek_columns = [
        "flow_minute",
        "symbol",
        "forward",
        "delta_forward",
        "gamma_forward",
        "greek_solved",
    ]
    missing_greek = sorted(set(greek_columns).difference(symbol_minute_greeks.columns))
    if missing_greek:
        raise ValueError(f"symbol-minute Greek frame missing columns: {', '.join(missing_greek)}")

    merged = trades.merge(
        symbol_minute_greeks[greek_columns],
        on=["flow_minute", "symbol"],
        how="left",
        validate="many_to_one",
    )
    for column in ("forward", "delta_forward", "gamma_forward"):
        merged[column] = pd.to_numeric(merged[column], errors="coerce")
    merged["hedge_greek_available"] = merged["delta_forward"].notna() & merged["gamma_forward"].notna()

    signed_contracts = merged["signed_side"] * merged["size"]
    merged["hedge_delta_units"] = signed_contracts * SPX_MULTIPLIER * merged["delta_forward"]
    merged["hedge_delta_notional"] = merged["hedge_delta_units"] * merged["forward"]
    merged["hedge_gamma_units_per_point"] = (
        signed_contracts * SPX_MULTIPLIER * merged["gamma_forward"]
    )
    merged["hedge_gax_notional_per_point"] = (
        merged["hedge_gamma_units_per_point"] * merged["forward"]
    )
    merged["hedge_gex_notional_per_1pct"] = (
        merged["hedge_gax_notional_per_point"] * merged["forward"] * 0.01
    )

    return merged


def aggregate_hedge_flow_minutes(weighted_trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate Greek-weighted trades into features available at minute M+1."""
    required = {
        "flow_minute",
        "symbol",
        "instrument_class",
        "size",
        "signed_side",
        "hedge_greek_available",
        "hedge_delta_units",
        "hedge_delta_notional",
        "hedge_gamma_units_per_point",
        "hedge_gax_notional_per_point",
        "hedge_gex_notional_per_1pct",
    }
    missing = sorted(required.difference(weighted_trades.columns))
    if missing:
        raise ValueError(f"weighted trade frame missing required columns: {', '.join(missing)}")

    frame = weighted_trades.copy()
    frame["flow_minute"] = pd.to_datetime(frame["flow_minute"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["flow_minute"]).copy()
    frame["classified"] = pd.to_numeric(frame["signed_side"], errors="coerce") != 0
    frame["usable"] = frame["classified"] & frame["hedge_greek_available"].fillna(False)
    frame["is_call"] = frame["instrument_class"].astype(str).str.upper() == "C"
    frame["is_put"] = frame["instrument_class"].astype(str).str.upper() == "P"

    rows: list[dict[str, object]] = []
    for minute, group in frame.groupby("flow_minute", sort=True):
        classified = group.loc[group["classified"]]
        usable = group.loc[group["usable"]]
        calls = usable.loc[usable["is_call"]]
        puts = usable.loc[usable["is_put"]]
        symbols = int(classified["symbol"].nunique())
        solved_symbols = int(usable["symbol"].nunique())
        classified_volume = float(classified["size"].sum())

        delta_units = float(usable["hedge_delta_units"].sum())
        delta_notional = float(usable["hedge_delta_notional"].sum())
        gamma_units = float(usable["hedge_gamma_units_per_point"].sum())
        gax = float(usable["hedge_gax_notional_per_point"].sum())
        gex = float(usable["hedge_gex_notional_per_1pct"].sum())

        rows.append(
            {
                "flow_minute": pd.Timestamp(minute),
                "timestamp": pd.Timestamp(minute) + pd.to_timedelta(1, unit="min"),
                "hedge_greek_symbols": symbols,
                "hedge_greek_solved_symbols": solved_symbols,
                "hedge_greek_solved_pct": solved_symbols / symbols if symbols else np.nan,
                "hedge_classified_contract_volume": classified_volume,
                "hedge_delta_units": delta_units,
                "hedge_delta_notional": delta_notional,
                "hedge_call_delta_units": float(calls["hedge_delta_units"].sum()),
                "hedge_put_delta_units": float(puts["hedge_delta_units"].sum()),
                "hedge_gamma_units_per_point": gamma_units,
                "hedge_gax_notional_per_point": gax,
                "hedge_gex_notional_per_1pct": gex,
                "hedge_call_gamma_units_per_point": float(
                    calls["hedge_gamma_units_per_point"].sum()
                ),
                "hedge_put_gamma_units_per_point": float(
                    puts["hedge_gamma_units_per_point"].sum()
                ),
                "hedge_gross_abs_delta_notional": float(
                    usable["hedge_delta_notional"].abs().sum()
                ),
                "hedge_gross_abs_gex_notional_per_1pct": float(
                    usable["hedge_gex_notional_per_1pct"].abs().sum()
                ),
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def join_hedge_flow_to_replay(
    hedge_flow: pd.DataFrame,
    replay: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Join M+1 hedge-flow availability timestamps to exact replay rows/labels."""
    left = hedge_flow.copy()
    if "timestamp" not in left.columns:
        raise ValueError("hedge flow frame must contain timestamp")
    if "timestamp" not in replay.columns or "forward" not in replay.columns:
        raise ValueError("replay frame must contain timestamp and forward")

    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True, errors="coerce")
    left = left.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    right = replay.copy()
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True, errors="coerce")
    right = right.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    right = add_forward_horizon_labels(right, horizons_minutes)

    merged = left.merge(right, on="timestamp", how="left", validate="one_to_one", indicator=True)
    merged["replay_match"] = merged["_merge"] == "both"
    return merged.drop(columns=["_merge"]).sort_values("timestamp").reset_index(drop=True)
