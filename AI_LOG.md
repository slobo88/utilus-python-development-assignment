# AI Usage Log

Tool used: Codex

Relevant prompts and guidance used during the assignment:

1. "For this project here are some things to be taken into consideration"
2. Non-functional requirements provided by the user:
   - Organize the code for structure and extensibility.
   - Add tests covering churn logic and 3-month retention, including edge cases.
   - Use type hints and documentation.
   - Include a short `DESIGN.md`.
   - Include a note containing the relevant AI chat logs or prompts used.

Implementation notes produced from those prompts:

- Refactor the CSV processor into separate modules for loading, validation, metrics, and orchestration.
- Model churn with a 30-day re-subscription grace rule.
- Model 3-month retention as active status exactly 3 calendar months after signup.
- Keep malformed rows in the validation report while still computing metrics from valid rows.

Additional prompts recorded during the assignment:

3. "Lets take a step back and take it step by step. the process should start by processing the CSV input files. for 
   now focous only on reading each file given to the processor and based on the verify if the data is correct. Well use pandas for these to be able to do the following work with dataframes.

For customers_csv
- customer_id (string)
- signup_date (ISO date, e.g. 2024-01-15)
- country (string)

for subscriptions_csv
- customer_id (string)
- start_date (ISO date)
- end_date (ISO date or empty for active)
- plan (string, e.g. basic, pro)
- monthly_price (numeric)

Dont continue with development after the parsing of the csvs. keep in mind to fail with a clear message when required columns are missing or malformed"

4. "Add both this prompt and the prevous ont to the AI_LOG.mg. from here on out always do this
Okay now with the data processed, there are some checks we want to do use the two dataframe model generate the first part of the json output report.

Monthly MRR (Monthly Recurring Revenue) for each calendar month.

For each month, sum monthly_price of all subscriptions that are active in that month.

for this create a new class called Metrics. this class should accept both data frames and the json output when being initialised. on the function monthly_mrr. here we should do the operation based on the subscription_df and return a json with the reuslt for each month."

5. "okay now for the next step add to metrics monthly_churned_customers_count. this should return a json file for the number of churned customers for each month. A churn event is when a subscription has an end_date and the customer has no new subscription starting within 30 days after that end_date."

6. "okay not for the next function add to metrics signup_cohorts_with_3_month_retention. this must again return a json with:
1.Group customers by signup month.
2.For each cohort, compute:

   - cohort_size
    - active_after_3_months: number of customers that still have any active subscription 3 months after their signup date.
    - retention_rate_3m= active_after_3_months / cohort_size."

7. "okay we need to add one more step to the processing. customer IDs that are present on `subscriptions_df` but not on `customers_df` list should be removed from the df. this should not throw an exception, but should be logged into consol. the log should contain the descrptive data"

8. "okay lets add some more checks to the data. countries must be e.g. NL, DE, as in capital letters and 2 letters. customer_id must also be unique"

9. "on the subscriptions, a customer cant have 2 active subscriptions at the same time. add a validation for that as well. define this as active for the same customer there cannot be 2 rows on the file where the periode of start_date to end_date, overlaps with another"
