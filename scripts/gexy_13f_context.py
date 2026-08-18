from __future__ import annotations

import argparse
from pathlib import Path

from packages.gexy.institutional_13f import parse_13f_information_table_xml


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize an already-downloaded SEC Form 13F INFORMATION TABLE XML document into slow "
            "institutional GEXY context. This command performs local processing only."
        )
    )
    parser.add_argument("--input-xml", required=True, type=Path)
    parser.add_argument("--manager", required=True)
    parser.add_argument("--report-period", required=True)
    parser.add_argument(
        "--filed-at",
        required=True,
        help="timezone-aware SEC filing acceptance timestamp used as causal available_at",
    )
    parser.add_argument("--accession", default=None)
    parser.add_argument(
        "--value-scale",
        type=float,
        default=1.0,
        help=(
            "reported-value multiplier; current amended Form 13F uses nearest dollars so default is 1.0. "
            "Set explicitly for historical source formats if needed."
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not args.input_xml.exists():
        raise SystemExit(f"input XML was not found: {args.input_xml}")

    try:
        holdings = parse_13f_information_table_xml(
            args.input_xml.read_text(encoding="utf-8"),
            manager=args.manager,
            report_period=args.report_period,
            filed_at=args.filed_at,
            accession=args.accession,
            value_scale=args.value_scale,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    holdings.to_csv(args.output, index=False)

    print("GEXY SEC 13F SLOW CONTEXT")
    print(f"INPUT: {args.input_xml}")
    print(f"MANAGER: {args.manager}")
    print(f"REPORT PERIOD: {args.report_period}")
    print(f"HOLDING ROWS: {len(holdings)}")
    print(f"OUTPUT: {args.output}")
    print("CAUSALITY: available_at is the filing acceptance time, never the quarter-end report period.")
    print("INTERPRETATION: slow ownership snapshot only; not intraday trade timing or intent.")
    print("NO NETWORK REQUESTS: this command reads only the local SEC XML file.")


if __name__ == "__main__":
    main()
