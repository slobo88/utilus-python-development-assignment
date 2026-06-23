from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


class CSVProcessor:
    """Read CSV inputs into pandas DataFrames and validate required fields."""

    CUSTOMER_COLUMNS = ("customer_id", "signup_date", "country")
    SUBSCRIPTION_COLUMNS = (
        "customer_id",
        "start_date",
        "end_date",
        "plan",
        "monthly_price",
    )
    ISO_DATE_FORMAT = "%Y-%m-%d"
    logger = logging.getLogger(__name__)

    def __init__(self, customers_csv: Path, subscriptions_csv: Path):
        self.customers_csv = customers_csv
        self.subscriptions_csv = subscriptions_csv

    def main(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load and validate both CSV files, then stop."""
        errors: list[str] = []
        customers_df: pd.DataFrame | None = None
        subscriptions_df: pd.DataFrame | None = None

        try:
            customers_df = self.read_customers()
        except ValueError as exc:
            errors.append(str(exc))

        try:
            subscriptions_df = self.read_subscriptions()
        except ValueError as exc:
            errors.append(str(exc))

        if errors:
            raise ValueError("\n\n".join(errors))

        subscriptions_df = self._remove_unknown_customer_subscriptions(
            customers_df=customers_df,
            subscriptions_df=subscriptions_df,
        )

        return customers_df, subscriptions_df

    def read_customers(self) -> pd.DataFrame:
        customers = self._read_csv(self.customers_csv)
        self._validate_required_columns(
            columns=customers.columns,
            required_columns=self.CUSTOMER_COLUMNS,
            csv_name="customers_csv",
        )

        customers = self._normalize_columns(customers, self.CUSTOMER_COLUMNS)
        errors = [
            *self._validate_required_values(customers, self.CUSTOMER_COLUMNS),
            *self._validate_iso_dates(customers, "signup_date", allow_empty=False),
            *self._validate_country_codes(customers, "country"),
            *self._validate_unique_values(customers, "customer_id"),
        ]
        self._raise_validation_error("customers_csv", errors)

        customers["signup_date"] = pd.to_datetime(
            customers["signup_date"],
            format=self.ISO_DATE_FORMAT,
        )
        return customers

    def read_subscriptions(self) -> pd.DataFrame:
        subscriptions = self._read_csv(self.subscriptions_csv)
        self._validate_required_columns(
            columns=subscriptions.columns,
            required_columns=self.SUBSCRIPTION_COLUMNS,
            csv_name="subscriptions_csv",
        )

        subscriptions = self._normalize_columns(subscriptions, self.SUBSCRIPTION_COLUMNS)
        errors = [
            *self._validate_required_values(
                subscriptions,
                ("customer_id", "start_date", "plan", "monthly_price"),
            ),
            *self._validate_iso_dates(subscriptions, "start_date", allow_empty=False),
            *self._validate_iso_dates(subscriptions, "end_date", allow_empty=True),
            *self._validate_numeric_values(subscriptions, "monthly_price"),
        ]
        self._raise_validation_error("subscriptions_csv", errors)

        subscriptions["start_date"] = pd.to_datetime(
            subscriptions["start_date"],
            format=self.ISO_DATE_FORMAT,
        )
        subscriptions["end_date"] = pd.to_datetime(
            subscriptions["end_date"].replace("", pd.NA),
            format=self.ISO_DATE_FORMAT,
        )
        subscriptions["monthly_price"] = pd.to_numeric(subscriptions["monthly_price"])

        overlap_errors = self._validate_no_overlapping_subscriptions(subscriptions)
        self._raise_validation_error("subscriptions_csv", overlap_errors)

        return subscriptions

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(path, dtype="string", keep_default_na=False)
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Failed to read CSV file {path}: {exc}") from exc

    @staticmethod
    def _normalize_columns(dataframe: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
        normalized = dataframe.loc[:, list(columns)].copy()
        for column in columns:
            normalized[column] = normalized[column].str.strip()
        return normalized

    @staticmethod
    def _validate_required_columns(
        columns: pd.Index,
        required_columns: tuple[str, ...],
        csv_name: str,
    ) -> None:
        missing_columns = [column for column in required_columns if column not in columns]
        if missing_columns:
            raise ValueError(
                f"Invalid {csv_name}: missing required columns: {', '.join(missing_columns)}"
            )

    def _validate_required_values(
        self,
        dataframe: pd.DataFrame,
        required_columns: tuple[str, ...],
    ) -> list[str]:
        errors: list[str] = []
        for column in required_columns:
            invalid_rows = dataframe.index[dataframe[column] == ""].tolist()
            if invalid_rows:
                errors.append(
                    f"{column} is blank at rows {self._format_rows(invalid_rows)}"
                )
        return errors

    def _validate_iso_dates(
        self,
        dataframe: pd.DataFrame,
        column: str,
        allow_empty: bool,
    ) -> list[str]:
        format_mask = dataframe[column].str.fullmatch(r"\d{4}-\d{2}-\d{2}")
        parsed_dates = pd.to_datetime(
            dataframe[column].replace("", pd.NA),
            format=self.ISO_DATE_FORMAT,
            errors="coerce",
        )

        if allow_empty:
            invalid_mask = (~format_mask.fillna(False) & (dataframe[column] != "")) | (
                parsed_dates.isna() & (dataframe[column] != "")
            )
        else:
            invalid_mask = (~format_mask.fillna(False)) | parsed_dates.isna()

        if not invalid_mask.any():
            return []

        invalid_rows = dataframe.index[invalid_mask].tolist()
        invalid_values = dataframe.loc[invalid_mask, column].tolist()
        details = ", ".join(
            f"row {row}: {value!r}"
            for row, value in zip(self._to_csv_rows(invalid_rows), invalid_values)
        )
        return [f"{column} must be ISO YYYY-MM-DD; invalid values at {details}"]

    def _validate_numeric_values(self, dataframe: pd.DataFrame, column: str) -> list[str]:
        parsed_values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_mask = parsed_values.isna() | (dataframe[column] == "")

        if not invalid_mask.any():
            return []

        invalid_rows = dataframe.index[invalid_mask].tolist()
        invalid_values = dataframe.loc[invalid_mask, column].tolist()
        details = ", ".join(
            f"row {row}: {value!r}"
            for row, value in zip(self._to_csv_rows(invalid_rows), invalid_values)
        )
        return [f"{column} must be numeric; invalid values at {details}"]

    def _validate_country_codes(self, dataframe: pd.DataFrame, column: str) -> list[str]:
        invalid_mask = (
            ~dataframe[column].str.fullmatch(r"[A-Z]{2}").fillna(False)
        ) & (dataframe[column] != "")

        if not invalid_mask.any():
            return []

        invalid_rows = dataframe.index[invalid_mask].tolist()
        invalid_values = dataframe.loc[invalid_mask, column].tolist()
        details = ", ".join(
            f"row {row}: {value!r}"
            for row, value in zip(self._to_csv_rows(invalid_rows), invalid_values)
        )
        return [f"{column} must be a two-letter uppercase code; invalid values at {details}"]

    def _validate_unique_values(self, dataframe: pd.DataFrame, column: str) -> list[str]:
        duplicate_mask = dataframe[column].duplicated(keep=False)

        if not duplicate_mask.any():
            return []

        duplicate_rows = dataframe.index[duplicate_mask].tolist()
        duplicate_values = dataframe.loc[duplicate_mask, column].tolist()
        details = ", ".join(
            f"row {row}: {value!r}"
            for row, value in zip(self._to_csv_rows(duplicate_rows), duplicate_values)
        )
        return [f"{column} must be unique; duplicate values at {details}"]

    def _validate_no_overlapping_subscriptions(self, dataframe: pd.DataFrame) -> list[str]:
        errors: list[str] = []
        subscriptions = dataframe.copy()
        subscriptions["effective_end_date"] = subscriptions["end_date"].fillna(pd.Timestamp.max)

        for customer_id, customer_rows in subscriptions.groupby("customer_id", sort=True):
            customer_rows = customer_rows.sort_values(
                by=["start_date", "effective_end_date"]
            )
            previous_rows: list[tuple[int, pd.Timestamp, pd.Timestamp]] = []

            for row_index, row in customer_rows.iterrows():
                start_date = row["start_date"]
                end_date = row["effective_end_date"]

                for previous_index, previous_start, previous_end in previous_rows:
                    if start_date <= previous_end and previous_start <= end_date:
                        errors.append(
                            "customer_id has overlapping subscription periods at "
                            f"rows {self._to_csv_rows([previous_index])[0]} and "
                            f"{self._to_csv_rows([row_index])[0]} for value {customer_id!r}"
                        )

                previous_rows.append((row_index, start_date, end_date))

        return errors

    @staticmethod
    def _raise_validation_error(csv_name: str, errors: list[str]) -> None:
        if errors:
            raise ValueError(f"Invalid {csv_name}:\n- " + "\n- ".join(errors))

    @classmethod
    def _remove_unknown_customer_subscriptions(
        cls,
        customers_df: pd.DataFrame,
        subscriptions_df: pd.DataFrame,
    ) -> pd.DataFrame:
        valid_customer_ids = set(customers_df["customer_id"])
        unknown_customer_mask = ~subscriptions_df["customer_id"].isin(valid_customer_ids)

        if not unknown_customer_mask.any():
            return subscriptions_df

        removed_rows = subscriptions_df.loc[unknown_customer_mask].copy()
        unknown_customer_ids = sorted(removed_rows["customer_id"].unique().tolist())
        cls.logger.warning(
            "Removed %s subscription rows with customer_id values not present in customers_df: %s",
            len(removed_rows),
            ", ".join(unknown_customer_ids),
        )
        return subscriptions_df.loc[~unknown_customer_mask].copy()

    @staticmethod
    def _to_csv_rows(indexes: list[int]) -> list[int]:
        return [index + 2 for index in indexes]

    def _format_rows(self, indexes: list[int]) -> str:
        return ", ".join(str(row) for row in self._to_csv_rows(indexes))
