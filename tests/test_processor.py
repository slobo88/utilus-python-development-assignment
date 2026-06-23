from __future__ import annotations

from pathlib import Path

import pytest

from processor import CSVProcessor


def write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_processor(tmp_path: Path, customers_csv: str, subscriptions_csv: str) -> CSVProcessor:
    customers_path = tmp_path / "customers.csv"
    subscriptions_path = tmp_path / "subscriptions.csv"
    write_csv(customers_path, customers_csv)
    write_csv(subscriptions_path, subscriptions_csv)
    return CSVProcessor(customers_path, subscriptions_path)


def test_read_customers_rejects_invalid_country_and_duplicate_customer_id(
    tmp_path: Path,
) -> None:
    processor = build_processor(
        tmp_path,
        customers_csv=(
            "customer_id,signup_date,country\n"
            "C001,2024-01-01,nl\n"
            "C001,2024-01-02,DE\n"
        ),
        subscriptions_csv=(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-01,,basic,30\n"
        ),
    )

    with pytest.raises(ValueError) as exc_info:
        processor.read_customers()

    message = str(exc_info.value)
    assert "country must be a two-letter uppercase code" in message
    assert "customer_id must be unique" in message


def test_read_subscriptions_rejects_overlapping_subscription_periods(tmp_path: Path) -> None:
    processor = build_processor(
        tmp_path,
        customers_csv=(
            "customer_id,signup_date,country\n"
            "C001,2024-01-01,NL\n"
        ),
        subscriptions_csv=(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-01,2024-02-15,basic,30\n"
            "C001,2024-02-01,2024-03-01,pro,50\n"
        ),
    )

    with pytest.raises(ValueError) as exc_info:
        processor.read_subscriptions()

    assert "overlapping subscription periods" in str(exc_info.value)


def test_main_removes_unknown_subscription_customer_ids_and_logs_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    processor = build_processor(
        tmp_path,
        customers_csv=(
            "customer_id,signup_date,country\n"
            "C001,2024-01-01,NL\n"
        ),
        subscriptions_csv=(
            "customer_id,start_date,end_date,plan,monthly_price\n"
            "C001,2024-01-01,,basic,30\n"
            "C999,2024-01-05,,basic,20\n"
        ),
    )

    with caplog.at_level("WARNING"):
        customers_df, subscriptions_df = processor.main()

    assert customers_df["customer_id"].tolist() == ["C001"]
    assert subscriptions_df["customer_id"].tolist() == ["C001"]
    assert "Removed 1 subscription rows" in caplog.text
    assert "C999" in caplog.text
