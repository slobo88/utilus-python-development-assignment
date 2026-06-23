# Design Note

## Structure

The code is split into small modules instead of placing all logic in `main.py`:

- `main.py`: CLI parsing and input/output path checks.
- `processor.py`: orchestration layer that loads data, validates it, computes metrics, and writes JSON.
- `metrics.py`: pure metric functions for MRR, churn, and 3-month retention.

This keeps the CLI thin and makes the business rules testable without going through file I/O.

## Business rules

- **MRR**: monthly recurring revenue is calculated as a month-end snapshot. A subscription contributes its `monthly_price` if it is active on the last day of the month.
- **Churn**: a customer churns on a subscription end date only if there is no later subscription for that customer starting within 30 days. Monthly churn is grouped by the month of that end date.
- **3-month retention**: cohorts are based on customer signup month. A customer is retained if they have an active subscription exactly 3 calendar months after signup. Cohorts whose 3-month checkpoint is beyond the reporting window are excluded.

## Extensibility

New metrics should be added as new pure functions in `metrics.py` and then wired into the report in `processor.py`. If the metric needs different aggregation inputs later, the next step would be introducing a dedicated service module (for example `metrics_ltv.py`) without changing the CLI contract.

## Assumptions and trade-offs

- Dirty rows are reported and skipped so the sample data can still produce metrics.
- CSVs with broken headers still fail fast because the file shape is not trustworthy.
- When duplicate customers or overlapping subscriptions appear, the first valid row wins and later conflicting rows are rejected with validation issues.
- The reporting window ends at the latest observed valid date in the input data, so open-ended subscriptions are not projected indefinitely into future months.
