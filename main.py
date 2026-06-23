from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from metrics import Metrics
from processor import CSVProcessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate CSV inputs and generate monthly MRR, churn, and cohort retention JSON report sections."
    )
    parser.add_argument("customers_csv", type=Path, help="Path to the customers CSV file.")
    parser.add_argument(
        "subscriptions_csv",
        type=Path,
        help="Path to the subscriptions CSV file.",
    )
    parser.add_argument(
        "output_json",
        type=Path,
        help="Path to the output JSON report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    customers_csv = args.customers_csv
    if not customers_csv.is_file():
        parser.error(f"customers_csv not found: {customers_csv}")

    subscriptions_csv = args.subscriptions_csv
    if not subscriptions_csv.is_file():
        parser.error(f"subscriptions_csv not found: {subscriptions_csv}")

    output_json = args.output_json
    if output_json.suffix != ".json":
        parser.error(f"output_json must end with .json: {output_json}")

    processor = CSVProcessor(customers_csv, subscriptions_csv)
    try:
        customers_df, subscriptions_df = processor.main()
    except ValueError as exc:
        parser.exit(status=1, message=f"{exc}\n")

    metrics = Metrics(customers_df, subscriptions_df, output_json)
    metrics.full_report()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
