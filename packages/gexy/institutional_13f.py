from __future__ import annotations

from collections.abc import Iterable
from xml.etree import ElementTree as ET

import pandas as pd


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, path: Iterable[str]) -> str | None:
    current = element
    for name in path:
        next_element = next((child for child in current if _local_name(child.tag) == name), None)
        if next_element is None:
            return None
        current = next_element
    if current.text is None:
        return None
    value = current.text.strip()
    return value or None


def parse_13f_information_table_xml(
    xml_text: str,
    *,
    manager: str,
    report_period: str | pd.Timestamp,
    filed_at: str | pd.Timestamp,
    accession: str | None = None,
    value_scale: float = 1.0,
) -> pd.DataFrame:
    """Parse an SEC Form 13F INFORMATION TABLE XML document into causal context.

    ``available_at`` equals the filing acceptance timestamp supplied as
    ``filed_at``. The quarter-end ``report_period`` is preserved separately and
    is never used as the event availability time.

    SEC Form 13F filings using the amended form report dollar values rounded to
    the nearest dollar. Historical/pre-amendment data may use different scaling,
    so ``value_scale`` remains explicit and is recorded in the output rather than
    silently assumed from the report period.

    13F holdings are slow institutional ownership context only. They do not reveal
    when during the quarter a position was established, whether it remained after
    quarter-end, or the intent behind the holding.
    """
    if value_scale <= 0:
        raise ValueError("value_scale must be positive")

    observed_at = pd.Timestamp(filed_at)
    if observed_at.tzinfo is None:
        raise ValueError("filed_at must include an explicit timezone/acceptance time")
    observed_at = observed_at.tz_convert("UTC")

    period = pd.Timestamp(report_period)
    if period.tzinfo is not None:
        period = period.tz_convert("UTC").tz_localize(None)
    period = period.normalize()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"invalid 13F information-table XML: {exc}") from exc

    info_tables = [element for element in root.iter() if _local_name(element.tag) == "infoTable"]
    rows: list[dict[str, object]] = []
    for entry in info_tables:
        reported_value = pd.to_numeric(_child_text(entry, ["value"]), errors="coerce")
        shares = pd.to_numeric(
            _child_text(entry, ["shrsOrPrnAmt", "sshPrnamt"]),
            errors="coerce",
        )
        voting_sole = pd.to_numeric(
            _child_text(entry, ["votingAuthority", "Sole"]),
            errors="coerce",
        )
        voting_shared = pd.to_numeric(
            _child_text(entry, ["votingAuthority", "Shared"]),
            errors="coerce",
        )
        voting_none = pd.to_numeric(
            _child_text(entry, ["votingAuthority", "None"]),
            errors="coerce",
        )
        rows.append(
            {
                "available_at": observed_at,
                "report_period": period.date(),
                "manager": manager,
                "accession": accession,
                "issuer": _child_text(entry, ["nameOfIssuer"]),
                "title_of_class": _child_text(entry, ["titleOfClass"]),
                "cusip": _child_text(entry, ["cusip"]),
                "figi": _child_text(entry, ["figi"]),
                "reported_value": reported_value,
                "value_scale": float(value_scale),
                "market_value_usd": (
                    float(reported_value) * float(value_scale)
                    if pd.notna(reported_value)
                    else float("nan")
                ),
                "shares_or_principal": shares,
                "shares_or_principal_type": _child_text(
                    entry,
                    ["shrsOrPrnAmt", "sshPrnamtType"],
                ),
                "put_call": _child_text(entry, ["putCall"]),
                "investment_discretion": _child_text(entry, ["investmentDiscretion"]),
                "other_manager": _child_text(entry, ["otherManager"]),
                "voting_sole": voting_sole,
                "voting_shared": voting_shared,
                "voting_none": voting_none,
                "context_type": "institutional_13f_snapshot",
                "timing_precision": "quarter_end_snapshot_available_at_filing",
            }
        )

    columns = [
        "available_at",
        "report_period",
        "manager",
        "accession",
        "issuer",
        "title_of_class",
        "cusip",
        "figi",
        "reported_value",
        "value_scale",
        "market_value_usd",
        "shares_or_principal",
        "shares_or_principal_type",
        "put_call",
        "investment_discretion",
        "other_manager",
        "voting_sole",
        "voting_shared",
        "voting_none",
        "context_type",
        "timing_precision",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)[columns]
