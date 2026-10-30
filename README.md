# 📊 Finance Lab

**A transparent, editable financial planning and scenario simulator for small businesses, built with Streamlit.**

Enter a handful of assumptions and Finance Lab projects a monthly income statement and cash flow, compares scenarios, stress-tests the plan with Monte Carlo simulation, and exports the results as Excel, Markdown or CSV.

> ⚠️ **Disclaimer:** Finance Lab is an educational / demonstration tool. Its output is only as good as the assumptions you enter and does not constitute accounting, financial, legal or tax advice.

---

## ✨ Features

| Area | What you get |
|---|---|
| **Dashboard** | KPIs (revenue, EBITDA, net income, cash, funding gap, break-even, safety margin), revenue/cost/EBITDA chart, cash chart, P&L waterfall, margin trends and automatic alerts |
| **Assumptions** | Presets (Retail SME, Professional services, SaaS, Manufacturing), grouped inputs, save / load assumptions as JSON |
| **Projection** | Monthly income statement, cash flow and full-detail views with CSV export |
| **Scenarios** | Editable pessimistic / base / optimistic cases, sensitivity heatmap (growth × cost) and tornado chart of the biggest cash drivers |
| **Risk (Monte Carlo)** | Thousands of simulated paths, fan chart, probability of running out of cash, funding buffer needed to cover 95% of paths |
| **Report** | Auto-generated executive report, downloadable as Markdown, Excel workbook or CSV |

Other details: multi-currency labels (ARS, USD, EUR, GBP, BRL, MXN, CLP, COP, UYU), compact number formatting, optional monthly fixed-cost inflation, loss carry-forward, tax payment lag, one-off cash injection (loan or equity), and light/dark theme support.

## 🚀 Quick start

```bash
# 1. Clone the repository
git clone https://github.com/<your-user>/finance-lab.git
cd finance-lab

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at <http://localhost:8501>.

## 🧮 How the model works

1. **Revenue** grows geometrically: `revenue[t] = initial × (1 + growth)^t`.
2. **Variable costs** are a percentage of revenue; **fixed costs** are constant, or inflate monthly if you set an inflation rate.
3. **EBITDA** = revenue − variable costs − fixed costs; **EBT** = EBITDA − depreciation − interest.
4. **Taxes** apply to positive EBT only; with loss carry-forward enabled, earlier losses offset later profits.
5. **Cash timing:** collections, supplier payments and tax payments are delayed by 0, 1 or 2 whole months. Opening receivables and payables are spread evenly across the lag window.
6. **Net cash flow** = collections − supplier payments − fixed costs − interest − taxes paid − CAPEX + cash injection. Depreciation is non-cash.
7. **Monte Carlo** adds normally distributed noise to monthly growth and to the variable-cost ratio, then reports percentiles and shortfall probabilities.

### Known simplifications

No VAT, payroll taxes, seasonality, inventory, debt schedules, dividends, or separate price/volume effects. Lags are whole-month approximations.

## 🗂 Project structure

```
finance-lab/
├── app.py                 # Streamlit app (UI + financial engine)
├── requirements.txt
├── .streamlit/
│   └── config.toml        # Theme and Streamlit settings
├── .gitignore
└── README.md
```

## ☁️ Deploy for free

1. Push this repository to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud), click **New app**, and select the repository, branch and `app.py`.
3. Click **Deploy**.

## 🛠 Tech stack

[Streamlit](https://streamlit.io) · [Plotly](https://plotly.com/python/) · [pandas](https://pandas.pydata.org) · [NumPy](https://numpy.org) · [openpyxl](https://openpyxl.readthedocs.io)

Tested with Python 3.11+ and Streamlit 1.66.

## 📄 License

Released under the MIT License. Add a `LICENSE` file to your repository if you want to make this explicit.
