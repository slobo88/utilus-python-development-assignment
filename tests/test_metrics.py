from __future__ import annotations

from pathlib import Path

import pandas as pd

from metrics import Metrics


def build_metrics(
    customers_rows: list[dict[str, object]],
    subscriptions_rows: list[dict[str, object]],
) -> Metrics:
    customers_df = pd.DataFrame(customers_rows)
    subscriptions_df = pd.DataFrame(subscriptions_rows)

    if not customers_df.empty:
        customers_df["signup_date"] = pd.to_datetime(customers_df["signup_date"])

    if not subscriptions_df.empty:
        subscriptions_df["start_date"] = pd.to_datetime(subscriptions_df["start_date"])
        subscriptions_df["end_date"] = pd.to_datetime(subscriptions_df["end_date"])

    return Metrics(customers_df, subscriptions_df, Path("unused.json"))


def test_monthly_churned_customers_count_ignores_resubscription_within_30_days() -> None:
    metrics = build_metrics(
        customers_rows=[
            {"customer_id": "C001", "signup_date": "2024-01-01", "country": "NL"},
        ],
        subscriptions_rows=[
            {
                "customer_id": "C001",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "plan": "basic",
                "monthly_price": 30,
            },
            {
                "customer_id": "C001",
                "start_date": "2024-02-29",
                "end_date": None,
                "plan": "basic",
                "monthly_price": 30,
            },
        ],
    )

    result = metrics.monthly_churned_customers_count()

    assert result == {
        "monthly_churned_customers_count": [
            {"month": "2024-01", "churned_customers_count": 0},
            {"month": "2024-02", "churned_customers_count": 0},
        ]
    }


def test_monthly_churned_customers_count_counts_customer_after_30_day_gap() -> None:
    metrics = build_metrics(
        customers_rows=[
            {"customer_id": "C001", "signup_date": "2024-01-01", "country": "NL"},
        ],
        subscriptions_rows=[
            {
                "customer_id": "C001",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "plan": "basic",
                "monthly_price": 30,
            },
            {
                "customer_id": "C001",
                "start_date": "2024-03-02",
                "end_date": None,
                "plan": "basic",
                "monthly_price": 30,
            },
        ],
    )

    result = metrics.monthly_churned_customers_count()

    assert result["monthly_churned_customers_count"][0] == {
        "month": "2024-01",
        "churned_customers_count": 1,
    }


def test_signup_cohorts_with_3_month_retention_uses_exact_three_month_date() -> None:
    metrics = build_metrics(
        customers_rows=[
            {"customer_id": "C001", "signup_date": "2024-01-31", "country": "NL"},
            {"customer_id": "C002", "signup_date": "2024-01-15", "country": "DE"},
        ],
        subscriptions_rows=[
            {
                "customer_id": "C001",
                "start_date": "2024-01-31",
                "end_date": "2024-04-30",
                "plan": "basic",
                "monthly_price": 30,
            },
            {
                "customer_id": "C002",
                "start_date": "2024-01-15",
                "end_date": "2024-04-14",
                "plan": "basic",
                "monthly_price": 25,
            },
        ],
    )

    result = metrics.signup_cohorts_with_3_month_retention()

    assert result == {
        "signup_cohorts_with_3_month_retention": [
            {
                "signup_month": "2024-01",
                "cohort_size": 2,
                "active_after_3_months": 1,
                "retention_rate_3m": 0.5,
            }
        ]
    }
