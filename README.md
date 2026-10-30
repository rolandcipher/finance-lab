# 📊 Finance Lab 2.1

**A transparent, editable financial planning and scenario simulator for
small businesses, built with Streamlit.**

Finance Lab turns a compact set of business assumptions into monthly
financial projections. It models the income statement, working capital
and cash flow; compares alternative scenarios; stress-tests assumptions
with Monte Carlo simulation; and exports results to Excel, Markdown and
CSV.

> ⚠️ **Disclaimer:** Finance Lab is an educational and planning tool.
> Its results depend on the assumptions entered and do not constitute
> accounting, financial, legal or tax advice. It is not a substitute for
> professional review.

------------------------------------------------------------------------

## ✨ Features

  -----------------------------------------------------------------------
  Area                                What you get
  ----------------------------------- -----------------------------------
  **Dashboard**                       KPIs for revenue, EBITDA, net
                                      income, cash, funding gap,
                                      break-even and safety margin;
                                      revenue/cost/EBITDA charts; cash
                                      chart; P&L waterfall; margin
                                      trends; automatic alerts; and a
                                      cash-flow reconciliation check

  **Assumptions**                     Business presets (Retail SME,
                                      Professional services, SaaS,
                                      Manufacturing), grouped inputs,
                                      editable assumptions, and save/load
                                      through JSON

  **Projection**                      Monthly income statement, cash flow
                                      and working-capital views, with CSV
                                      export

  **Scenarios**                       Editable pessimistic, base and
                                      optimistic cases; sensitivity
                                      heatmap (growth × cost); and
                                      tornado chart of the main cash
                                      drivers

  **Risk (Monte Carlo)**              Multiple simulated paths, fan
                                      chart, probability of running out
                                      of cash, and an estimated funding
                                      buffer to cover 95% of simulated
                                      paths

  **Report**                          Automatically generated executive
                                      report, downloadable as Markdown or
                                      Excel, plus CSV exports
  -----------------------------------------------------------------------

### Financial model capabilities

-   Monthly revenue projection and operating-cost assumptions.
-   Optional monthly inflation of fixed costs.
-   EBITDA, depreciation, interest, earnings before tax (EBT),
    illustrative taxes and net income.
-   Tax loss carry-forward.
-   Collection, supplier-payment and tax-payment lags.
-   Opening and closing balances for accounts receivable, accounts
    payable and taxes payable.
-   Net working capital (NWC) and monthly change in NWC.
-   Operating cash flow shown using both direct and indirect approaches,
    with a reconciliation check.
-   Initial CAPEX and a one-off financing cash injection (for example, a
    loan or equity contribution).
-   Monte Carlo cost-ratio shocks configurable as persistent or monthly.
-   Multi-currency labels (ARS, USD, EUR, GBP, BRL, MXN, CLP, COP, UYU),
    compact number formatting, and light/dark theme support.

------------------------------------------------------------------------

## 🚀 Quick start

``` bash
# 1. Clone the repository
git clone https://github.com/<your-user>/finance-lab.git
cd finance-lab

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run finance_lab_v2_1.py
```

The app opens at <http://localhost:8501>.

If you rename the application file to `app.py`, use
`streamlit run app.py` instead. Make sure the filename in the run
command and the filename selected in Streamlit Community Cloud match the
file in your repository.

------------------------------------------------------------------------

## 🧮 How the model works

### 1. Income statement

1.  **Revenue** grows geometrically from the initial monthly revenue
    assumption: `revenue[t] = initial × (1 + growth)^t`.
2.  **Variable costs** are calculated as a percentage of revenue.
3.  **Fixed costs** remain constant unless monthly fixed-cost inflation
    is enabled.
4.  **EBITDA** = revenue − variable costs − fixed costs.
5.  **EBT** = EBITDA − depreciation − interest.
6.  **Taxes** are calculated on positive taxable earnings according to
    the model's tax assumptions. When loss carry-forward is enabled,
    eligible previous losses offset later positive earnings.
7.  **Net income** = EBT − illustrative taxes.

### 2. Working capital and payment timing

Revenue and expenses are projected on an accrual basis, while cash
movements reflect the selected timing assumptions.

-   **Collections:** revenue is collected after the configured
    collection lag.
-   **Supplier payments:** variable costs are paid after the configured
    supplier-payment lag.
-   **Tax payments:** taxes are paid after the configured tax-payment
    lag.
-   **Opening balances:** opening accounts receivable, accounts payable
    and taxes payable are incorporated into the corresponding cash
    schedules.
-   **Closing balances:** the model calculates month-end receivables,
    payables and taxes payable.
-   **Net working capital:** the model calculates NWC and its
    month-to-month change.

Collection, supplier-payment and tax-payment lags are whole-month
approximations. Opening balances are allocated across the applicable lag
window according to the model's simplified schedule.

### 3. Cash flow

The model calculates operating cash flow using both:

-   **Direct method:** cash collections less supplier payments, fixed
    costs, interest and taxes paid.
-   **Indirect method:** net income adjusted for non-cash depreciation
    and changes in working capital.

The dashboard and report expose the difference between the two
operating-cash-flow calculations as a reconciliation check. The model
also includes the configured initial CAPEX and one-off financing cash
injection when calculating net cash flow and closing cash.

Depreciation is treated as a non-cash expense. It reduces accounting
earnings but is not itself a cash payment.

### 4. Monte Carlo risk analysis

Monte Carlo simulation generates multiple possible paths by applying
normally distributed variation to monthly revenue growth and the
variable-cost ratio. The cost-ratio shock can be configured to behave
as:

-   **Persistent:** a sampled cost-ratio shock carries through the
    simulated path.
-   **Monthly:** a new cost-ratio shock is sampled for each month.

The simulation summarizes the resulting distribution of outcomes,
including cash shortfall risk and the estimated funding buffer required
to cover 95% of simulated paths. These are scenario estimates, not
probabilities calibrated from historical business data.

------------------------------------------------------------------------

## ⚠️ Known simplifications and limitations

Finance Lab 2.1 is a simplified planning model, not a full accounting or
financial-management system.

It does **not** currently provide:

-   VAT / sales-tax accounting or detailed tax returns.
-   Payroll taxes, social contributions or detailed employee-cost
    schedules.
-   Seasonality, inventory movements or a full inventory valuation
    model.
-   Separate price and sales-volume drivers.
-   Detailed loan amortization, principal repayments, debt covenants or
    dividend schedules.
-   A complete balance sheet or a full fixed-asset register.
-   Detailed depreciation schedules for multiple asset purchases and
    disposals.
-   Partial-month payment schedules; timing lags are modeled in whole
    months.

The tax calculation is illustrative and should not be used to determine
actual tax liabilities. Likewise, the working-capital and cash-flow
schedules are simplified representations and should be checked against
the business's accounting records before making financial decisions.

------------------------------------------------------------------------

## 🗂 Project structure

The main application file in this release is `finance_lab_v2_1.py`.

``` text
finance-lab/
├── finance_lab_v2_1.py    # Streamlit application, UI and financial engine
├── requirements.txt       # Python dependencies
├── .streamlit/
│   └── config.toml        # Theme and Streamlit settings
├── .gitignore
└── README.md
```

If you prefer the conventional `app.py` filename, rename
`finance_lab_v2_1.py` to `app.py` and update the run/deployment command
accordingly.

------------------------------------------------------------------------

## ☁️ Deploy with Streamlit Community Cloud

1.  Push the repository to GitHub.
2.  Open [Streamlit Community Cloud](https://streamlit.io/cloud).
3.  Create a new app and select the repository and branch.
4.  Set the app's main file path to `finance_lab_v2_1.py` (or `app.py`
    if you renamed it).
5.  Deploy.

Keep `requirements.txt` in the repository root so the deployment
environment can install the dependencies.

------------------------------------------------------------------------

## 🛠 Tech stack

[Streamlit](https://streamlit.io) · [Plotly](https://plotly.com/python/)
· [pandas](https://pandas.pydata.org) · [NumPy](https://numpy.org) ·
[openpyxl](https://openpyxl.readthedocs.io)

The original project README specified Python 3.11+ and Streamlit 1.66.
Confirm the versions in your `requirements.txt` and deployment
environment before publishing a release.

------------------------------------------------------------------------

## 📄 License

Released under the MIT License **only if** the repository includes an
applicable `LICENSE` file. If it does not, add the license file and
confirm that the project is intended to be distributed under MIT before
describing the project as MIT-licensed.
