from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class Metrics:
    """Generate JSON report sections from validated pandas DataFrames."""

    def __init__(
        self,
        customers_df: pd.DataFrame,
        subscriptions_df: pd.DataFrame,
        output_json: Path,
    ):
        self.customers_df = customers_df
        self.subscriptions_df = subscriptions_df
        self.output_json = output_json

    def full_report(self) -> dict[str, list[dict[str, float | int | str]]]:
        report = {}
        report.update(self.monthly_mrr())
        report.update(self.monthly_churned_customers_count())
        report.update(self.signup_cohorts_with_3_month_retention())
        self._write_report(report)
        return report

    def monthly_mrr(self) -> dict[str, list[dict[str, float | str]]]:
        """Return monthly MRR for each calendar month in the data window."""
        if self.subscriptions_df.empty:
            return {"monthly_mrr": []}

        window_start, window_end = self._reporting_window()

        monthly_rows: list[dict[str, float | str]] = []
        for month in pd.period_range(window_start, window_end, freq="M"):
            month_start = month.start_time.normalize()
            month_end = month.end_time.normalize()

            active_mask = (
                (self.subscriptions_df["start_date"] <= month_end)
                & (
                    self.subscriptions_df["end_date"].isna()
                    | (self.subscriptions_df["end_date"] >= month_start)
                )
            )
            month_mrr = self.subscriptions_df.loc[active_mask, "monthly_price"].sum()
            monthly_rows.append(
                {
                    "month": str(month),
                    "mrr": float(month_mrr),
                }
            )

        return {"monthly_mrr": monthly_rows}

    def monthly_churned_customers_count(self) -> dict[str, list[dict[str, int | str]]]:
        """Return churned customer counts by calendar month."""
        if self.subscriptions_df.empty:
            return {"monthly_churned_customers_count": []}

        subscriptions = self.subscriptions_df.sort_values(
            by=["customer_id", "start_date", "end_date"],
            na_position="last",
        ).copy()
        window_start, window_end = self._reporting_window()

        churned_by_month: dict[str, set[str]] = {}
        for month in pd.period_range(window_start, window_end, freq="M"):
            churned_by_month[str(month)] = set()

        for customer_id, customer_subscriptions in subscriptions.groupby("customer_id", sort=True):
            customer_rows = customer_subscriptions.reset_index(drop=True)
            for index, subscription in customer_rows.iterrows():
                end_date = subscription["end_date"]
                if pd.isna(end_date):
                    continue

                churn_deadline = end_date + pd.Timedelta(days=30)
                later_subscriptions = customer_rows.iloc[index + 1 :]
                resumed_within_grace = (
                    (
                        (later_subscriptions["start_date"] > end_date)
                        & (later_subscriptions["start_date"] <= churn_deadline)
                    ).any()
                    if not later_subscriptions.empty
                    else False
                )

                if resumed_within_grace:
                    continue

                churned_by_month[end_date.to_period("M").strftime("%Y-%m")].add(customer_id)

        monthly_rows = [
            {
                "month": str(month),
                "churned_customers_count": len(churned_by_month[str(month)]),
            }
            for month in pd.period_range(window_start, window_end, freq="M")
        ]

        return {"monthly_churned_customers_count": monthly_rows}

    def signup_cohorts_with_3_month_retention(
        self,
    ) -> dict[str, list[dict[str, float | int | str]]]:
        """Return 3-month retention metrics for signup cohorts."""
        if self.customers_df.empty:
            return {"signup_cohorts_with_3_month_retention": []}

        customers = self.customers_df.copy()
        customers["signup_cohort"] = customers["signup_date"].dt.to_period("M").astype(str)
        customers["retention_check_date"] = customers["signup_date"] + pd.DateOffset(months=3)

        active_after_3_months: list[int] = []
        for _, customer in customers.iterrows():
            customer_subscriptions = self.subscriptions_df[
                self.subscriptions_df["customer_id"] == customer["customer_id"]
            ]
            is_active = (
                (
                    (customer_subscriptions["start_date"] <= customer["retention_check_date"])
                    & (
                        customer_subscriptions["end_date"].isna()
                        | (
                            customer_subscriptions["end_date"]
                            >= customer["retention_check_date"]
                        )
                    )
                ).any()
                if not customer_subscriptions.empty
                else False
            )
            active_after_3_months.append(int(is_active))

        customers["active_after_3_months"] = active_after_3_months
        cohort_summary = (
            customers.groupby("signup_cohort", sort=True)
            .agg(
                cohort_size=("customer_id", "count"),
                active_after_3_months=("active_after_3_months", "sum"),
            )
            .reset_index()
        )
        cohort_summary["retention_rate_3m"] = (
            cohort_summary["active_after_3_months"] / cohort_summary["cohort_size"]
        )

        cohort_rows = [
            {
                "signup_month": row["signup_cohort"],
                "cohort_size": int(row["cohort_size"]),
                "active_after_3_months": int(row["active_after_3_months"]),
                "retention_rate_3m": float(row["retention_rate_3m"]),
            }
            for _, row in cohort_summary.iterrows()
        ]

        return {"signup_cohorts_with_3_month_retention": cohort_rows}

    def _reporting_window(self) -> tuple[pd.Period, pd.Period]:
        window_start = self.subscriptions_df["start_date"].min().to_period("M")
        end_dates = self.subscriptions_df["end_date"].dropna()
        if end_dates.empty:
            window_end = self.subscriptions_df["start_date"].max().to_period("M")
        else:
            latest_date = max(
                self.subscriptions_df["start_date"].max(),
                end_dates.max(),
            )
            window_end = latest_date.to_period("M")
        return window_start, window_end

    def _write_report(
        self,
        report: dict[str, list[dict[str, float | int | str]]],
    ) -> None:
        self.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
