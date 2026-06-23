# Design Note

## Structure

The current implementation is organized around three main files:

- `main.py`: CLI entry point. It validates input paths, runs CSV processing, and triggers report generation.
- `processor.py`: pandas-based CSV loading and validation layer. It is responsible for turning both CSV files into validated DataFrames before any metrics are computed.
- `metrics.py`: report generation layer. It receives validated DataFrames and writes JSON sections for each metric.

The dependency footprint is intentionally small. The main runtime dependency is `pandas` from [requirements.txt](/Users/sofialobo/utilus-python-development-assignment/requirements.txt:1), which is used both for parsing and for the time-based metric calculations.

## Business rules

### CSV processing

`customers_csv` is validated for:

- required columns: `customer_id`, `signup_date`, `country`
- non-empty required values
- `signup_date` in ISO `YYYY-MM-DD`
- `country` as a two-letter uppercase code such as `NL` or `DE`
- unique `customer_id`

`subscriptions_csv` is validated for:

- required columns: `customer_id`, `start_date`, `end_date`, `plan`, `monthly_price`
- non-empty required values except `end_date`
- `start_date` and `end_date` in ISO `YYYY-MM-DD`, with empty `end_date` allowed for active subscriptions
- numeric `monthly_price`
- no overlapping subscription periods for the same `customer_id`

After validation, subscription rows whose `customer_id` does not exist in `customers_df` are removed. This is not treated as a hard failure; it is logged to the console and processing continues.

### Metrics

- **Monthly MRR**: for each calendar month, sum `monthly_price` for subscriptions active at any point in that month.
- **Monthly churned customers count**: a churn event occurs when a subscription has an `end_date` and the same customer has no later subscription starting within 30 days after that date.
- **Signup cohorts with 3-month retention**: customers are grouped by signup month. A customer is counted as retained if they have any active subscription exactly 3 calendar months after their signup date.

## Extensibility

The intended extension point for new reporting logic is `metrics.py`. Each metric is implemented as a method on `Metrics`, and each method writes one section into the shared JSON output. Adding a new metric should follow the same pattern:

1. accept the validated DataFrames already produced by `processor.py`
2. compute one well-scoped report section
3. merge that section into the JSON output

If validation rules grow further, they should stay in `processor.py` so the metrics layer can continue to assume clean inputs.

## Assumptions and trade-offs

- Validation currently fails fast per file: if a file contains malformed rows, processing stops with a clear aggregated error message for that file.
- Unknown subscription customer IDs are treated as a data-cleaning issue rather than a fatal validation error.
- Overlap detection for subscriptions is inclusive. If two periods touch or intersect for the same customer, they are considered invalid.
- The report file is built incrementally by metric section. That keeps each metric self-contained, but it also means `Metrics` owns both calculation and JSON persistence.
