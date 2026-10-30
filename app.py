"""Finance Lab — financial planning & scenario simulator.

A transparent, editable monthly model (P&L + cash flow) built with Streamlit.
Features: assumptions presets, scenario comparison, sensitivity heatmap,
tornado chart, Monte Carlo risk analysis, and Excel / Markdown / CSV exports.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import html
import io
import json
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_NAME = "Finance Lab"
APP_VERSION = "2.0"

st.set_page_config(
    page_title=f"{APP_NAME} | Financial planning simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Constants & defaults
# --------------------------------------------------------------------------- #
ACCENT, INDIGO, AMBER = "#14b8a6", "#6366f1", "#f59e0b"
RED, GREEN, SLATE = "#ef4444", "#22c55e", "#94a3b8"

CURRENCIES = ["ARS", "USD", "EUR", "GBP", "BRL", "MXN", "CLP", "COP", "UYU"]
HORIZONS = [6, 12, 18, 24, 36]
LAGS = [0, 1, 2]
LAG_LABELS = {0: "Same month", 1: "1 month", 2: "2 months"}

DEFAULTS: dict = {
    # general
    "preset": "Custom",
    "currency": "ARS",
    "months": 12,
    "company": "Demo Company",
    "start_month": date.today().replace(day=1),
    "compact": True,
    # operating
    "revenue": 10_000_000.0,
    "growth": 2.0,
    "variable_cost_pct": 55.0,
    "fixed_costs": 2_500_000.0,
    "fixed_inflation": 0.0,
    # cash & working capital
    "opening_cash": 5_000_000.0,
    "collection_lag": 1,
    "payment_lag": 1,
    "tax_lag": 0,
    "opening_receivables": 0.0,
    "opening_payables": 0.0,
    # investment, financing & tax
    "capex": 0.0,
    "depreciation": 0.0,
    "interest": 0.0,
    "tax_pct": 30.0,
    "loss_carryforward": True,
    "injection": 0.0,
    "injection_month": 1,
    # scenario deltas (percentage points)
    "sc_pess_growth": -3.0,
    "sc_pess_cost": 5.0,
    "sc_opt_growth": 3.0,
    "sc_opt_cost": -3.0,
}

# Keys that feed the financial engine.
PARAM_KEYS = [
    "revenue", "growth", "variable_cost_pct", "fixed_costs", "fixed_inflation",
    "opening_cash", "collection_lag", "payment_lag", "tax_lag",
    "opening_receivables", "opening_payables", "capex", "depreciation",
    "interest", "tax_pct", "loss_carryforward", "injection", "injection_month",
]
ASSUMPTION_KEYS = PARAM_KEYS + ["sc_pess_growth", "sc_pess_cost", "sc_opt_growth", "sc_opt_cost"]

# Valid ranges, used to sanitise uploaded JSON files.
RANGES = {
    "revenue": (0.0, 1e13), "growth": (-20.0, 20.0), "variable_cost_pct": (0.0, 95.0),
    "fixed_costs": (0.0, 1e13), "fixed_inflation": (0.0, 10.0), "opening_cash": (0.0, 1e13),
    "opening_receivables": (0.0, 1e13), "opening_payables": (0.0, 1e13), "capex": (0.0, 1e13),
    "depreciation": (0.0, 1e13), "interest": (0.0, 1e13), "tax_pct": (0.0, 50.0),
    "injection": (0.0, 1e13), "injection_month": (1, 36),
    "sc_pess_growth": (-15.0, 15.0), "sc_pess_cost": (-30.0, 30.0),
    "sc_opt_growth": (-15.0, 15.0), "sc_opt_cost": (-30.0, 30.0),
}

PRESETS: dict[str, dict] = {
    "Custom": {},
    "Retail SME": dict(
        revenue=25_000_000.0, growth=1.5, variable_cost_pct=68.0, fixed_costs=5_000_000.0,
        opening_cash=6_000_000.0, collection_lag=0, payment_lag=1, capex=2_000_000.0,
        depreciation=150_000.0, interest=300_000.0, tax_pct=30.0,
    ),
    "Professional services": dict(
        revenue=8_000_000.0, growth=2.0, variable_cost_pct=35.0, fixed_costs=3_000_000.0,
        opening_cash=4_000_000.0, collection_lag=2, payment_lag=1, tax_pct=30.0,
    ),
    "Early-stage SaaS": dict(
        revenue=4_000_000.0, growth=6.0, variable_cost_pct=20.0, fixed_costs=5_000_000.0,
        opening_cash=30_000_000.0, collection_lag=0, payment_lag=1, capex=3_000_000.0,
        depreciation=100_000.0, tax_pct=25.0,
    ),
    "Light manufacturing": dict(
        revenue=40_000_000.0, growth=1.0, variable_cost_pct=60.0, fixed_costs=10_000_000.0,
        opening_cash=12_000_000.0, collection_lag=2, payment_lag=1, opening_receivables=30_000_000.0,
        opening_payables=15_000_000.0, capex=15_000_000.0, depreciation=500_000.0,
        interest=800_000.0, tax_pct=30.0,
    ),
}


def _version() -> tuple[int, int]:
    try:
        return tuple(int(x) for x in st.__version__.split(".")[:2])  # type: ignore[return-value]
    except Exception:
        return (0, 0)


# Newer Streamlit replaced `use_container_width=True` with `width="stretch"`.
STRETCH = {"width": "stretch"} if _version() >= (1, 50) else {"use_container_width": True}

# Initialise session state once.
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

# --------------------------------------------------------------------------- #
# Visual system
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
<style>
    .stApp {{zoom: 1;}}
    .block-container {{padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px;}}
    [data-testid="stMetric"] {{
        background: rgba(128,128,128,.07); border: 1px solid rgba(128,128,128,.18);
        padding: 14px 16px; border-radius: 14px;
    }}
    [data-testid="stMetricLabel"] p {{font-size: .78rem; opacity: .75; font-weight: 600;}}
    .eyebrow {{font-size: .2rem; letter-spacing: .14em; font-weight: 700; opacity: .65;}}
    .hero {{
        padding: 1.3rem 1.5rem; border-radius: 18px; margin: .4rem 0 1.1rem 0;
        border: 1px solid rgba(20,184,166,.35);
        background: linear-gradient(120deg, rgba(20,184,166,.16), rgba(99,102,241,.12));
    }}
    .hero h3 {{margin: .3rem 0 .6rem 0;}}
    .chip {{
        display: inline-block; padding: .18rem .7rem; margin-right: .4rem; border-radius: 999px;
        font-size: .78rem; font-weight: 600; background: rgba(128,128,128,.16);
    }}
    .small-note {{font-size: .82rem; opacity: .72;}}
    div[data-testid="stTabs"] button {{font-weight: 600;}}
    section[data-testid="stSidebar"] .stExpander {{border-radius: 12px;}}
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Helpers: formatting, sanitising, presets
# --------------------------------------------------------------------------- #
def money(v: float | None, cur: str | None = None, compact: bool | None = None) -> str:
    """Format a number as currency, optionally compacted (K / M / B)."""
    cur = cur or st.session_state["currency"]
    compact = st.session_state["compact"] if compact is None else compact
    if v is None or not np.isfinite(v):
        return "—"
    sign = "-" if v < 0 else ""
    a = abs(float(v))
    if compact:
        for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
            if a >= div:
                return f"{sign}{cur} {a / div:,.2f}{suffix}"
    return f"{sign}{cur} {a:,.0f}"


def pct(v: float) -> str:
    return f"{v:.1f}%"


def sanitize(raw: dict) -> dict:
    """Validate and clamp values loaded from an uploaded JSON file."""
    out: dict = {}
    data = raw.get("assumptions", raw) if isinstance(raw, dict) else {}
    for key, default in DEFAULTS.items():
        if key == "preset" or key not in data:
            continue
        val = data[key]
        try:
            if key == "start_month":
                out[key] = date.fromisoformat(str(val)[:10]).replace(day=1)
            elif key == "currency":
                out[key] = val if val in CURRENCIES else default
            elif key == "months":
                out[key] = int(val) if int(val) in HORIZONS else default
            elif key in ("collection_lag", "payment_lag", "tax_lag"):
                out[key] = int(val) if int(val) in LAGS else default
            elif key == "company":
                out[key] = str(val)[:80]
            elif isinstance(default, bool):
                out[key] = bool(val)
            elif key == "injection_month":
                lo, hi = RANGES[key]
                out[key] = int(min(max(int(val), lo), hi))
            elif isinstance(default, float):
                lo, hi = RANGES.get(key, (-1e13, 1e13))
                out[key] = float(min(max(float(val), lo), hi))
        except (ValueError, TypeError):
            continue
    out["preset"] = "Custom"
    return out


def apply_preset() -> None:
    name = st.session_state["preset"]
    if name == "Custom":
        return
    base = {k: DEFAULTS[k] for k in ASSUMPTION_KEYS}
    st.session_state.update({**base, **PRESETS[name]})


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## ⚙️ Control panel")

    with st.expander("💾 Load / save assumptions"):
        uploaded = st.file_uploader("Load assumptions (.json)", type="json", label_visibility="collapsed")
        if uploaded is not None:
            token = (uploaded.name, uploaded.size)
            if st.session_state.get("_loaded_file") != token:
                try:
                    st.session_state.update(sanitize(json.load(uploaded)))
                    st.session_state["_loaded_file"] = token
                    st.toast("Assumptions loaded ✔")
                except Exception:
                    st.error("That file isn't a valid Finance Lab assumptions file.")
        save_slot = st.empty()

    st.selectbox("Start from a preset", list(PRESETS), key="preset", on_change=apply_preset,
                 help="Illustrative starting points. Every value stays editable below.")

    with st.expander("General", expanded=True):
        st.selectbox("Currency", CURRENCIES, key="currency")
        st.select_slider("Projection horizon (months)", options=HORIZONS, key="months")
        st.text_input("Project / company name", key="company")
        st.date_input("Projection start", key="start_month")
        st.toggle("Compact numbers (K / M / B)", key="compact")

    with st.expander("Operations", expanded=True):
        st.number_input("Initial monthly revenue", min_value=0.0, step=250_000.0, format="%.0f", key="revenue")
        st.slider("Monthly revenue growth (%)", -20.0, 20.0, step=0.5, key="growth")
        st.slider("Variable costs (% of revenue)", 0.0, 95.0, step=0.5, key="variable_cost_pct")
        st.number_input("Monthly fixed costs", min_value=0.0, step=100_000.0, format="%.0f", key="fixed_costs")
        st.slider("Fixed-cost inflation (% per month)", 0.0, 10.0, step=0.1, key="fixed_inflation",
                  help="Optional. Raises fixed costs every month, e.g. for high-inflation economies.")

    with st.expander("Cash & working capital"):
        st.number_input("Opening cash", min_value=0.0, step=250_000.0, format="%.0f", key="opening_cash")
        st.selectbox("Customer collection lag", LAGS, format_func=LAG_LABELS.get, key="collection_lag")
        st.selectbox("Supplier payment lag", LAGS, format_func=LAG_LABELS.get, key="payment_lag")
        st.selectbox("Tax payment lag", LAGS, format_func=LAG_LABELS.get, key="tax_lag")
        st.number_input("Opening accounts receivable", min_value=0.0, step=100_000.0, format="%.0f",
                        key="opening_receivables")
        st.number_input("Opening accounts payable", min_value=0.0, step=100_000.0, format="%.0f",
                        key="opening_payables")

    with st.expander("Investment, financing & tax"):
        st.number_input("Initial investment (CAPEX)", min_value=0.0, step=100_000.0, format="%.0f", key="capex")
        st.number_input("Monthly depreciation", min_value=0.0, step=50_000.0, format="%.0f", key="depreciation")
        st.number_input("Monthly interest expense", min_value=0.0, step=50_000.0, format="%.0f", key="interest")
        st.slider("Effective tax rate (%)", 0.0, 50.0, step=1.0, key="tax_pct")
        st.checkbox("Carry losses forward against future profits", key="loss_carryforward")
        st.number_input("One-off cash injection (loan / equity)", min_value=0.0, step=250_000.0,
                        format="%.0f", key="injection")
        st.number_input("Injection month (1 = first month)", min_value=1, max_value=36, step=1,
                        key="injection_month")

    st.caption("Results depend entirely on the assumptions entered. They do not replace financial "
               "statements, tax advice or a professional assessment.")

# --------------------------------------------------------------------------- #
# Financial engine (vectorised: one row per simulation path)
# --------------------------------------------------------------------------- #
def _delay(x: np.ndarray, lag: int) -> np.ndarray:
    """Shift each row `lag` columns to the right, filling with zeros."""
    out = np.zeros_like(x)
    if lag == 0:
        return x.copy()
    if lag < x.shape[1]:
        out[:, lag:] = x[:, :-lag]
    return out


def simulate(p: dict, growth: np.ndarray, cost_frac: np.ndarray) -> dict[str, np.ndarray]:
    """Monthly accrual + cash model.

    growth     : (S, N) monthly revenue growth in %
    cost_frac  : (S, N) variable costs as a fraction of revenue
    Returns a dict of (S, N) arrays. S = 1 for a deterministic run.
    """
    S, N = growth.shape
    idx = np.arange(N)

    factors = np.clip(1 + growth / 100, 0.01, None)
    factors[:, 0] = 1.0
    revenue = p["revenue"] * np.cumprod(factors, axis=1)
    variable_costs = revenue * cost_frac
    fixed_costs = np.tile(p["fixed_costs"] * (1 + p["fixed_inflation"] / 100) ** idx, (S, 1))
    depreciation = np.full((S, N), float(p["depreciation"]))
    interest = np.full((S, N), float(p["interest"]))

    ebitda = revenue - variable_costs - fixed_costs
    ebt = ebitda - depreciation - interest

    # Taxes, with optional loss carry-forward.
    taxes = np.zeros((S, N))
    loss_pool = np.zeros(S)
    rate = p["tax_pct"] / 100
    for i in range(N):
        profit = np.maximum(ebt[:, i], 0.0)
        if p["loss_carryforward"]:
            used = np.minimum(loss_pool, profit)
            loss_pool = loss_pool - used + np.maximum(-ebt[:, i], 0.0)
            profit = profit - used
        taxes[:, i] = profit * rate
    net_income = ebt - taxes

    # Cash timing. Opening balances are collected / paid evenly over the lag window.
    collections = _delay(revenue, p["collection_lag"])
    if p["collection_lag"] > 0:
        k = min(p["collection_lag"], N)
        collections[:, :k] += p["opening_receivables"] / p["collection_lag"]
    supplier_payments = _delay(variable_costs, p["payment_lag"])
    if p["payment_lag"] > 0:
        k = min(p["payment_lag"], N)
        supplier_payments[:, :k] += p["opening_payables"] / p["payment_lag"]
    taxes_paid = _delay(taxes, p["tax_lag"])

    capex = np.zeros((S, N))
    capex[:, 0] = p["capex"]
    funding = np.zeros((S, N))
    funding[:, min(int(p["injection_month"]), N) - 1] = p["injection"]

    net_cash_flow = (collections - supplier_payments - fixed_costs - interest
                     - taxes_paid - capex + funding)
    closing = p["opening_cash"] + np.cumsum(net_cash_flow, axis=1)

    return {
        "revenue": revenue, "variable_costs": variable_costs, "fixed_costs": fixed_costs,
        "ebitda": ebitda, "depreciation": depreciation, "interest": interest, "taxes": taxes,
        "net_income": net_income, "collections": collections,
        "supplier_payments": supplier_payments, "taxes_paid": taxes_paid, "capex": capex,
        "funding": funding, "net_cash_flow": net_cash_flow,
        "opening_cash": closing - net_cash_flow, "closing_cash": closing,
    }


COLUMN_MAP = {
    "revenue": "Revenue", "variable_costs": "Variable costs", "fixed_costs": "Fixed costs",
    "ebitda": "EBITDA", "depreciation": "Depreciation", "interest": "Interest",
    "taxes": "Estimated taxes", "net_income": "Estimated net income",
    "collections": "Collections", "supplier_payments": "Supplier payments",
    "taxes_paid": "Taxes paid", "capex": "CAPEX", "funding": "Cash injection",
    "net_cash_flow": "Net cash flow", "opening_cash": "Opening cash", "closing_cash": "Closing cash",
}


def run_model(p: dict, n: int, periods: pd.DatetimeIndex,
              growth_delta: float = 0.0, cost_delta: float = 0.0) -> pd.DataFrame:
    """Deterministic run (one path) returned as a tidy monthly DataFrame."""
    growth = np.full((1, n), p["growth"] + growth_delta)
    cost = np.full((1, n), np.clip(p["variable_cost_pct"] + cost_delta, 0, 99) / 100)
    res = simulate(p, growth, cost)
    df = pd.DataFrame({"Month": periods})
    for key, label in COLUMN_MAP.items():
        df[label] = res[key][0]
    return df


def compute_kpis(df: pd.DataFrame, p: dict) -> dict:
    revenue, ebitda = df["Revenue"].sum(), df["EBITDA"].sum()
    min_idx = df["Closing cash"].idxmin()
    neg = df.loc[df["Closing cash"] < 0, "Month"]
    contribution = 1 - p["variable_cost_pct"] / 100
    breakeven = p["fixed_costs"] / contribution if contribution > 0 else np.inf
    return {
        "revenue": revenue,
        "ebitda": ebitda,
        "margin": ebitda / revenue * 100 if revenue else 0.0,
        "net_income": df["Estimated net income"].sum(),
        "ending_cash": df["Closing cash"].iloc[-1],
        "min_cash": df.loc[min_idx, "Closing cash"],
        "min_cash_month": df.loc[min_idx, "Month"],
        "first_negative": neg.iloc[0] if len(neg) else None,
        "funding_gap": max(0.0, -df["Closing cash"].min()),
        "breakeven": breakeven,
        "safety_margin": (p["revenue"] - breakeven) / p["revenue"] * 100
        if p["revenue"] > 0 and np.isfinite(breakeven) else np.nan,
    }


# --------------------------------------------------------------------------- #
# Build parameters and run the base case
# --------------------------------------------------------------------------- #
months = int(st.session_state["months"])
currency = st.session_state["currency"]
company = st.session_state["company"].strip() or "Demo Company"
params = {k: st.session_state[k] for k in PARAM_KEYS}
params["injection_month"] = min(int(params["injection_month"]), months)
periods = pd.date_range(pd.Timestamp(st.session_state["start_month"]).replace(day=1),
                        periods=months, freq="MS")

base = run_model(params, months, periods)
kpi = compute_kpis(base, params)

# Scenario definitions (editable inside the Scenarios tab).
scenario_specs = [
    ("Pessimistic", st.session_state["sc_pess_growth"], st.session_state["sc_pess_cost"],
     "Slower growth and cost pressure"),
    ("Base", 0.0, 0.0, "Current assumptions"),
    ("Optimistic", st.session_state["sc_opt_growth"], st.session_state["sc_opt_cost"],
     "Faster growth and cost improvements"),
]
scenario_frames: dict[str, pd.DataFrame] = {}
scenario_rows = []
for sc_name, g_delta, c_delta, sc_desc in scenario_specs:
    frame = run_model(params, months, periods, g_delta, c_delta)
    scenario_frames[sc_name] = frame
    k = compute_kpis(frame, params)
    scenario_rows.append({
        "Scenario": sc_name,
        "Monthly growth (%)": params["growth"] + g_delta,
        "Variable costs (%)": float(np.clip(params["variable_cost_pct"] + c_delta, 0, 99)),
        "Total revenue": k["revenue"], "Total EBITDA": k["ebitda"],
        "Net income": k["net_income"], "Closing cash": k["ending_cash"],
        "Lowest cash": k["min_cash"],
        "Cash runs out": k["first_negative"].strftime("%b %Y") if k["first_negative"] is not None else "Never",
        "Description": sc_desc,
    })
scenario_df = pd.DataFrame(scenario_rows)

# Assumption table (reused by the Assumptions tab, report and Excel export).
assumption_rows = [
    ("Initial monthly revenue", params["revenue"], currency),
    ("Monthly revenue growth", params["growth"], "%"),
    ("Variable costs", params["variable_cost_pct"], "% of revenue"),
    ("Monthly fixed costs", params["fixed_costs"], currency),
    ("Fixed-cost inflation", params["fixed_inflation"], "% per month"),
    ("Opening cash", params["opening_cash"], currency),
    ("Collection lag", params["collection_lag"], "months"),
    ("Supplier payment lag", params["payment_lag"], "months"),
    ("Tax payment lag", params["tax_lag"], "months"),
    ("Opening accounts receivable", params["opening_receivables"], currency),
    ("Opening accounts payable", params["opening_payables"], currency),
    ("Initial CAPEX", params["capex"], currency),
    ("Monthly depreciation", params["depreciation"], currency),
    ("Monthly interest expense", params["interest"], currency),
    ("Effective tax rate", params["tax_pct"], "%"),
    ("Loss carry-forward", "Yes" if params["loss_carryforward"] else "No", ""),
    ("Cash injection", params["injection"], f"{currency}, month {params['injection_month']}"),
]

# Save-assumptions button (placed into the slot created at the top of the sidebar).
export_payload = {"app": APP_NAME, "version": APP_VERSION, "assumptions": {
    k: (st.session_state[k].isoformat() if k == "start_month" else st.session_state[k])
    for k in DEFAULTS if k not in ("preset", "company")} | {"company": company,
                                                          "start_month": st.session_state["start_month"].isoformat()}}
save_slot.download_button("⬇ Save current assumptions (.json)",
                          data=json.dumps(export_payload, indent=2).encode("utf-8"),
                          file_name="finance_lab_assumptions.json", mime="application/json")

# --------------------------------------------------------------------------- #
# Chart helpers
# --------------------------------------------------------------------------- #
def style(fig: go.Figure, title: str, height: int = 360, ytitle: str | None = None) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)), height=height,
        margin=dict(l=10, r=10, t=55, b=10), hovermode="x unified",
        legend=dict(orientation="h", y=-0.2), yaxis_title=ytitle or currency,
    )
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, **STRETCH)


def chart_revenue_costs(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=df["Month"], y=df["EBITDA"], name="EBITDA", opacity=0.55,
                marker_color=[GREEN if v >= 0 else RED for v in df["EBITDA"]])
    fig.add_scatter(x=df["Month"], y=df["Revenue"], name="Revenue", mode="lines+markers",
                    line=dict(width=3, color=ACCENT))
    fig.add_scatter(x=df["Month"], y=df["Variable costs"] + df["Fixed costs"], name="Operating costs",
                    mode="lines", line=dict(width=2, dash="dot", color=AMBER))
    return style(fig, "Revenue, operating costs and EBITDA")


def chart_cash(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=df["Month"], y=df["Net cash flow"], name="Net cash flow", opacity=0.55,
                marker_color=[GREEN if v >= 0 else RED for v in df["Net cash flow"]])
    fig.add_scatter(x=df["Month"], y=df["Closing cash"], name="Closing cash", mode="lines+markers",
                    line=dict(width=3, color=INDIGO), fill="tozeroy", fillcolor="rgba(99,102,241,.12)")
    fig.add_hline(y=0, line_dash="dash", line_color=RED)
    return style(fig, "Cash balance and monthly cash flow")


def chart_waterfall(df: pd.DataFrame) -> go.Figure:
    vals = [df["Revenue"].sum(), -df["Variable costs"].sum(), -df["Fixed costs"].sum(),
            -df["Depreciation"].sum(), -df["Interest"].sum(), -df["Estimated taxes"].sum()]
    net = sum(vals)
    fig = go.Figure(go.Waterfall(
        x=["Revenue", "Variable costs", "Fixed costs", "Depreciation", "Interest", "Taxes", "Net income"],
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        y=vals + [0], text=[money(v) for v in vals] + [money(net)], textposition="outside",
        connector={"line": {"color": SLATE}},
        increasing={"marker": {"color": GREEN}}, decreasing={"marker": {"color": RED}},
        totals={"marker": {"color": ACCENT}},
    ))
    fig.update_layout(showlegend=False)
    return style(fig, "From revenue to net income (whole horizon)", height=380)


def chart_margins(df: pd.DataFrame) -> go.Figure:
    rev = df["Revenue"].replace(0, np.nan)
    fig = go.Figure()
    fig.add_scatter(x=df["Month"], y=(df["EBITDA"] / rev * 100).fillna(0), name="EBITDA margin",
                    mode="lines+markers", line=dict(width=3, color=ACCENT))
    fig.add_scatter(x=df["Month"], y=(df["Estimated net income"] / rev * 100).fillna(0), name="Net margin",
                    mode="lines+markers", line=dict(width=3, color=INDIGO))
    fig.add_hline(y=0, line_dash="dash", line_color=SLATE)
    return style(fig, "Margins over time", height=380, ytitle="% of revenue")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown('<div class="eyebrow">FINANCIAL PLANNING & SCENARIO SIMULATOR</div>', unsafe_allow_html=True)
st.title(APP_NAME)
st.caption("Business financial planning simulator · Illustrative, editable and transparent model")

tab_dash, tab_inputs, tab_projection, tab_scenarios, tab_risk, tab_report = st.tabs([
    "📊 Dashboard", "🧩 Assumptions", "📅 Projection", "🔀 Scenarios", "🎲 Risk (Monte Carlo)", "📝 Report",
])

# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
with tab_dash:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{html.escape(company.upper())} · EXECUTIVE SUMMARY</div>'
        f"<h3>Projected financial outlook</h3>"
        f'<span class="chip">{months} months</span><span class="chip">{currency}</span>'
        f'<span class="chip">{periods[0].strftime("%b %Y")} → {periods[-1].strftime("%b %Y")}</span></div>',
        unsafe_allow_html=True,
    )

    r1 = st.columns(4)
    r1[0].metric("Total revenue", money(kpi["revenue"]), f"{params['growth']:+.1f}% / month")
    r1[1].metric("Total EBITDA", money(kpi["ebitda"]), f"{kpi['margin']:.1f}% margin")
    r1[2].metric("Estimated net income", money(kpi["net_income"]))
    r1[3].metric("Closing cash", money(kpi["ending_cash"]),
                 f"{money(kpi['ending_cash'] - params['opening_cash'])} vs. start")

    r2 = st.columns(4)
    r2[0].metric("Lowest cash point", money(kpi["min_cash"]),
                 kpi["min_cash_month"].strftime("%b %Y"), delta_color="off")
    r2[1].metric("Funding gap", money(kpi["funding_gap"]),
                 "Extra cash needed" if kpi["funding_gap"] > 0 else "None needed",
                 delta_color="inverse" if kpi["funding_gap"] > 0 else "normal")
    r2[2].metric("EBITDA break-even revenue", money(kpi["breakeven"]) + " / mo")
    safety = kpi["safety_margin"]
    r2[3].metric("Safety margin", pct(safety) if np.isfinite(safety) else "—",
                 "Above break-even" if np.isfinite(safety) and safety >= 0 else "Below break-even",
                 delta_color="normal" if np.isfinite(safety) and safety >= 0 else "inverse")

    st.write("")
    c_left, c_right = st.columns(2)
    with c_left:
        show(chart_revenue_costs(base))
    with c_right:
        show(chart_cash(base))
    c_left, c_right = st.columns(2)
    with c_left:
        show(chart_waterfall(base))
    with c_right:
        show(chart_margins(base))

    st.markdown("#### Signals to review")
    alerts: list[tuple[str, str]] = []
    if kpi["first_negative"] is not None:
        alerts.append(("error", f"Cash turns negative in **{kpi['first_negative'].strftime('%b %Y')}**. "
                                f"You would need about **{money(kpi['funding_gap'])}** of extra funding. "
                                "Review collection and payment terms, costs, or financing."))
    elif kpi["min_cash"] < params["fixed_costs"]:
        alerts.append(("warning", "Thin liquidity buffer: the lowest cash point covers less than one "
                                  "month of fixed costs."))
    if kpi["margin"] < 10:
        alerts.append(("warning", "Cumulative EBITDA margin is below 10%. The cost structure deserves a review."))
    if (base["EBITDA"] < 0).any():
        alerts.append(("warning", f"EBITDA is negative in {(base['EBITDA'] < 0).sum()} of {months} months."))
    if np.isfinite(safety) and safety < 0:
        alerts.append(("warning", f"Initial revenue is below the EBITDA break-even level of "
                                  f"{money(kpi['breakeven'])} per month."))
    if params["growth"] < 0:
        alerts.append(("warning", "Monthly revenue is projected to shrink. Consider the cumulative impact on liquidity."))
    if params["collection_lag"] > 0 and params["opening_receivables"] == 0:
        alerts.append(("info", "Collection lag is above zero but opening receivables are 0, so early collections "
                               "start from nothing. This can overstate early-month cash stress."))
    if not alerts:
        alerts.append(("success", "No basic alerts under the current assumptions. This does not guarantee "
                                  "future solvency or profitability."))
    for level, message in alerts:
        getattr(st, level)(message)

# --------------------------------------------------------------------------- #
# Assumptions
# --------------------------------------------------------------------------- #
with tab_inputs:
    st.subheader("Model assumptions")
    st.write("Everything is derived from the inputs in the sidebar. Change them there, or load a preset / saved file.")
    shown = pd.DataFrame(assumption_rows, columns=["Variable", "Value", "Unit"])
    shown["Value"] = shown["Value"].map(lambda v: f"{v:,.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))
    st.dataframe(shown, hide_index=True, **STRETCH)

    with st.expander("How the model works"):
        st.markdown(
            """
- **Revenue** grows geometrically: `revenue[t] = initial × (1 + growth)^t`.
- **Variable costs** are a fixed percentage of revenue; **fixed costs** can optionally inflate monthly.
- **EBITDA** = revenue − variable costs − fixed costs. **EBT** = EBITDA − depreciation − interest.
- **Taxes** apply to positive EBT only. With *loss carry-forward* enabled, past losses offset future profits.
- **Cash timing:** collections, supplier payments and tax payments are delayed by whole months (0, 1 or 2).
  Opening receivables / payables are spread evenly across the lag window.
- **Cash flow** = collections − supplier payments − fixed costs − interest − taxes paid − CAPEX + cash injection.
  Depreciation is non-cash.
            """
        )
    st.warning("Simplifications: no VAT, payroll taxes, seasonality, inventory, new debt schedules, dividends, "
               "or separate price / volume effects. Tax is an approximation on positive pre-tax profit.")

# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #
def style_table(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    num_cols = [c for c in df.columns if c != "Month"]
    styler = df.style.format({c: "{:,.0f}" for c in num_cols})
    negative = lambda v: f"color: {RED}" if isinstance(v, (int, float)) and v < 0 else ""  # noqa: E731
    return styler.map(negative, subset=num_cols) if hasattr(styler, "map") else styler.applymap(negative, subset=num_cols)


with tab_projection:
    st.subheader("Monthly projection")
    view = st.radio("View", ["Income statement", "Cash flow", "Full detail"], horizontal=True)
    views = {
        "Income statement": ["Month", "Revenue", "Variable costs", "Fixed costs", "EBITDA", "Depreciation",
                             "Interest", "Estimated taxes", "Estimated net income"],
        "Cash flow": ["Month", "Collections", "Supplier payments", "Fixed costs", "Interest", "Taxes paid",
                      "CAPEX", "Cash injection", "Net cash flow", "Opening cash", "Closing cash"],
        "Full detail": list(base.columns),
    }
    display = base[views[view]].copy()
    display["Month"] = display["Month"].dt.strftime("%b %Y")
    st.dataframe(style_table(display), hide_index=True, **STRETCH)
    st.download_button("⬇ Download projection (CSV)", data=base.to_csv(index=False).encode("utf-8-sig"),
                       file_name="finance_lab_projection.csv", mime="text/csv")

# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #
with tab_scenarios:
    st.subheader("Scenario comparison")
    st.write("Adjust how far the pessimistic and optimistic cases move away from your base assumptions "
             "(in percentage points).")
    e1, e2, e3, e4 = st.columns(4)
    e1.number_input("Pessimistic: growth Δ (pp)", -15.0, 15.0, step=0.5, key="sc_pess_growth")
    e2.number_input("Pessimistic: variable cost Δ (pp)", -30.0, 30.0, step=0.5, key="sc_pess_cost")
    e3.number_input("Optimistic: growth Δ (pp)", -15.0, 15.0, step=0.5, key="sc_opt_growth")
    e4.number_input("Optimistic: variable cost Δ (pp)", -30.0, 30.0, step=0.5, key="sc_opt_cost")

    money_cols = ["Total revenue", "Total EBITDA", "Net income", "Closing cash", "Lowest cash"]
    fmt = {c: (lambda x: money(x, compact=False)) for c in money_cols}
    fmt |= {"Monthly growth (%)": "{:.1f}", "Variable costs (%)": "{:.1f}"}
    st.dataframe(scenario_df.style.format(fmt), hide_index=True, **STRETCH)

    fig = go.Figure()
    for (name, frame), color in zip(scenario_frames.items(), [RED, INDIGO, GREEN]):
        fig.add_scatter(x=frame["Month"], y=frame["Closing cash"], mode="lines+markers", name=name,
                        line=dict(color=color, width=3 if name == "Base" else 2))
    fig.add_hline(y=0, line_dash="dash", line_color=SLATE)
    show(style(fig, "Closing cash by scenario", height=400))
    st.caption("Optimistic and pessimistic cases are illustrative sensitivities, not probabilities or forecasts.")

    st.divider()
    st.subheader("Sensitivity heatmap")
    metric_choice = st.radio("Metric", ["Closing cash", "Lowest cash", "Total EBITDA"], horizontal=True)
    g_vals = np.arange(-5.0, 5.1, 1.0)
    c_vals = np.arange(-10.0, 10.1, 2.5)
    grid_g, grid_c = np.meshgrid(g_vals, c_vals)
    growth_arr = np.repeat((params["growth"] + grid_g.ravel())[:, None], months, axis=1)
    cost_arr = np.repeat((np.clip(params["variable_cost_pct"] + grid_c.ravel(), 0, 99) / 100)[:, None], months, axis=1)
    sens = simulate(params, growth_arr, cost_arr)
    z = {"Closing cash": sens["closing_cash"][:, -1], "Lowest cash": sens["closing_cash"].min(axis=1),
         "Total EBITDA": sens["ebitda"].sum(axis=1)}[metric_choice].reshape(grid_g.shape)
    heat = go.Figure(go.Heatmap(
        z=z, x=[f"{params['growth'] + g:.1f}%" for g in g_vals],
        y=[f"{np.clip(params['variable_cost_pct'] + c, 0, 99):.1f}%" for c in c_vals],
        colorscale="RdYlGn", zmid=0, text=[[money(v) for v in row] for row in z],
        texttemplate="%{text}", textfont=dict(size=10), colorbar=dict(title=currency),
    ))
    heat.update_layout(title=f"{metric_choice}: monthly growth (x) vs. variable costs (y)", height=460,
                       margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Monthly growth",
                       yaxis_title="Variable costs (% of revenue)")
    show(heat)

    st.divider()
    st.subheader("What moves closing cash the most?")
    drivers = [
        ("Initial revenue (±10%)", "revenue", "mult", 0.10),
        ("Monthly growth (±2 pp)", "growth", "add", 2.0),
        ("Variable costs (±5 pp)", "variable_cost_pct", "add", 5.0),
        ("Fixed costs (±10%)", "fixed_costs", "mult", 0.10),
        ("Tax rate (±5 pp)", "tax_pct", "add", 5.0),
        ("Fixed-cost inflation (±1 pp)", "fixed_inflation", "add", 1.0),
    ]

    def ending_cash(overrides: dict) -> float:
        q = {**params, **overrides}
        return run_model(q, months, periods)["Closing cash"].iloc[-1]

    base_end, rows = kpi["ending_cash"], []
    for label, key, mode, size in drivers:
        lo = params[key] * (1 - size) if mode == "mult" else max(params[key] - size, RANGES[key][0] if key in RANGES else -99)
        hi = params[key] * (1 + size) if mode == "mult" else params[key] + size
        rows.append((label, ending_cash({key: lo}) - base_end, ending_cash({key: hi}) - base_end))
    rows.sort(key=lambda r: max(abs(r[1]), abs(r[2])))
    tornado = go.Figure()
    tornado.add_bar(y=[r[0] for r in rows], x=[r[1] for r in rows], name="Input lower", orientation="h", marker_color=AMBER)
    tornado.add_bar(y=[r[0] for r in rows], x=[r[2] for r in rows], name="Input higher", orientation="h", marker_color=INDIGO)
    tornado.update_layout(barmode="overlay", title="Change in closing cash vs. base case", height=380,
                          margin=dict(l=10, r=10, t=55, b=10), legend=dict(orientation="h", y=-0.2),
                          xaxis_title=f"Δ closing cash ({currency})")
    show(tornado)

# --------------------------------------------------------------------------- #
# Monte Carlo
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def run_monte_carlo(p_items: tuple, n: int, runs: int, g_sigma: float, c_sigma: float, seed: int) -> dict:
    p = dict(p_items)
    rng = np.random.default_rng(seed)
    growth = p["growth"] + rng.normal(0, g_sigma, (runs, n))
    cost = np.clip((p["variable_cost_pct"] + rng.normal(0, c_sigma, (runs, 1))) / 100, 0, 0.99)
    res = simulate(p, growth, np.broadcast_to(cost, (runs, n)).copy())
    return {k: res[k] for k in ("revenue", "ebitda", "closing_cash")}


with tab_risk:
    st.subheader("Monte Carlo risk analysis")
    st.write("Instead of one fixed path, simulate thousands of possible futures by adding random noise to monthly "
             "growth and to the variable-cost ratio. Results show *ranges and probabilities*, not predictions.")
    m1, m2, m3, m4 = st.columns(4)
    runs = m1.select_slider("Simulations", [500, 1_000, 2_000, 5_000, 10_000], value=2_000)
    g_sigma = m2.slider("Growth volatility (pp / month)", 0.0, 10.0, 2.0, 0.5)
    c_sigma = m3.slider("Cost-ratio uncertainty (pp)", 0.0, 10.0, 2.0, 0.5)
    seed = m4.number_input("Random seed", 0, 99_999, 42, step=1)

    mc = run_monte_carlo(tuple(sorted(params.items())), months, int(runs), g_sigma, c_sigma, int(seed))
    cash = mc["closing_cash"]
    p5, p25, p50, p75, p95 = np.percentile(cash, [5, 25, 50, 75, 95], axis=0)
    ever_negative = np.minimum.accumulate(cash, axis=1) < 0
    prob_shortfall = ever_negative[:, -1].mean() * 100
    shortfall = np.maximum(0, -cash.min(axis=1))
    buffer95 = np.percentile(shortfall, 95)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Probability cash goes negative", pct(prob_shortfall),
              "Low risk" if prob_shortfall < 5 else "Needs attention",
              delta_color="normal" if prob_shortfall < 5 else "inverse")
    k2.metric("Median closing cash", money(p50[-1]))
    k3.metric("Closing cash range (P5 – P95)", f"{money(p5[-1])} → {money(p95[-1])}")
    k4.metric("Buffer to cover 95% of paths", money(buffer95))

    fan = go.Figure()
    fan.add_scatter(x=periods, y=p95, line=dict(width=0), showlegend=False, hoverinfo="skip")
    fan.add_scatter(x=periods, y=p5, line=dict(width=0), fill="tonexty", fillcolor="rgba(20,184,166,.15)", name="P5 – P95")
    fan.add_scatter(x=periods, y=p75, line=dict(width=0), showlegend=False, hoverinfo="skip")
    fan.add_scatter(x=periods, y=p25, line=dict(width=0), fill="tonexty", fillcolor="rgba(20,184,166,.30)", name="P25 – P75")
    fan.add_scatter(x=periods, y=p50, name="Median", line=dict(color=ACCENT, width=3))
    fan.add_scatter(x=periods, y=base["Closing cash"], name="Base case", line=dict(color=INDIGO, width=2, dash="dot"))
    fan.add_hline(y=0, line_dash="dash", line_color=RED)
    show(style(fan, "Closing cash: fan chart", height=420))

    d_left, d_right = st.columns(2)
    with d_left:
        hist = go.Figure(go.Histogram(x=cash[:, -1], nbinsx=50, marker_color=ACCENT, opacity=0.85))
        hist.add_vline(x=0, line_dash="dash", line_color=RED)
        hist.add_vline(x=float(p50[-1]), line_dash="dot", line_color=INDIGO)
        hist.update_layout(title="Distribution of closing cash", height=360, margin=dict(l=10, r=10, t=55, b=10),
                           xaxis_title=currency, yaxis_title="Simulations", showlegend=False)
        show(hist)
    with d_right:
        risk = go.Figure(go.Scatter(x=periods, y=ever_negative.mean(axis=0) * 100, mode="lines+markers",
                                    line=dict(color=RED, width=3), fill="tozeroy", fillcolor="rgba(239,68,68,.12)"))
        show(style(risk, "Probability of having run out of cash by month", height=360, ytitle="% of simulations"))
    st.caption("Shocks are independent, normally distributed and unrelated to seasonality or macro conditions. "
               "Treat this as a stress-test, not a forecast.")

# --------------------------------------------------------------------------- #
# Report & exports
# --------------------------------------------------------------------------- #
def build_markdown() -> str:
    lines = [
        f"# {APP_NAME} — Simulation report",
        f"**Project:** {company}  ",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**Horizon:** {months} months ({periods[0].strftime('%b %Y')} – {periods[-1].strftime('%b %Y')}) · **Currency:** {currency}",
        "", "## Summary", "",
        "| Metric | Value |", "|---|---|",
        f"| Total revenue | {money(kpi['revenue'], compact=False)} |",
        f"| Total EBITDA | {money(kpi['ebitda'], compact=False)} ({kpi['margin']:.1f}% margin) |",
        f"| Estimated net income | {money(kpi['net_income'], compact=False)} |",
        f"| Closing cash | {money(kpi['ending_cash'], compact=False)} |",
        f"| Lowest cash ({kpi['min_cash_month'].strftime('%b %Y')}) | {money(kpi['min_cash'], compact=False)} |",
        f"| Funding gap | {money(kpi['funding_gap'], compact=False)} |",
        f"| EBITDA break-even revenue | {money(kpi['breakeven'], compact=False)} / month |",
        "", "## Scenarios", "",
        "| Scenario | Growth | Var. costs | Closing cash | Lowest cash | Cash runs out |", "|---|---|---|---|---|---|",
    ]
    for r in scenario_rows:
        lines.append(f"| {r['Scenario']} | {r['Monthly growth (%)']:.1f}% | {r['Variable costs (%)']:.1f}% | "
                     f"{money(r['Closing cash'], compact=False)} | {money(r['Lowest cash'], compact=False)} | {r['Cash runs out']} |")
    lines += ["", "## Observations", ""]
    if kpi["first_negative"] is not None:
        lines.append(f"- Cash first turns negative in **{kpi['first_negative'].strftime('%B %Y')}**; "
                     f"the funding gap is {money(kpi['funding_gap'], compact=False)}.")
    else:
        lines.append("- Cash stays non-negative throughout the simulated horizon.")
    lines.append("- Cumulative EBITDA margin is below 10%; review costs, pricing and structure." if kpi["margin"] < 10
                 else "- Cumulative EBITDA margin is above 10% under the current assumptions.")
    lines += ["", "## Key assumptions", "", "| Variable | Value | Unit |", "|---|---|---|"]
    for name, value, unit in assumption_rows:
        lines.append(f"| {name} | {value:,.1f} | {unit} |" if isinstance(value, float) else f"| {name} | {value} | {unit} |")
    lines += ["", "## Scope and limitations",
              "This is a simplified simulation. It is not accounting, financial, legal or tax advice. It does not "
              "model inflation of revenue, VAT, seasonality, inventory, detailed payroll, new financing or working-"
              "capital changes beyond the approximate collection and payment lags."]
    return "\n".join(lines)


def build_excel() -> bytes:
    from openpyxl.styles import Alignment, Font, PatternFill

    summary = pd.DataFrame([
        ("Total revenue", kpi["revenue"]), ("Total EBITDA", kpi["ebitda"]),
        ("EBITDA margin (%)", kpi["margin"]), ("Estimated net income", kpi["net_income"]),
        ("Closing cash", kpi["ending_cash"]), ("Lowest cash", kpi["min_cash"]),
        ("Funding gap", kpi["funding_gap"]), ("EBITDA break-even revenue / month", kpi["breakeven"]),
    ], columns=["Metric", "Value"])
    assumptions = pd.DataFrame(assumption_rows, columns=["Assumption", "Value", "Unit"])
    assumptions["Value"] = assumptions["Value"].astype(str)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        assumptions.to_excel(xw, sheet_name="Assumptions", index=False)
        base.to_excel(xw, sheet_name="Projection", index=False)
        scenario_df.to_excel(xw, sheet_name="Scenarios", index=False)
        for ws in xw.book.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="0F766E")
                cell.alignment = Alignment(horizontal="center")
            ws.freeze_panes = "A2"
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(12, width + 2), 48)
                for c in col[1:]:
                    if hasattr(c.value, "year"):
                        c.number_format = "mmm yyyy"
                    elif isinstance(c.value, float):
                        c.number_format = "#,##0.0" if abs(c.value) < 1000 else "#,##0"
    return buf.getvalue()


with tab_report:
    st.subheader("Executive report")
    st.write("Automatic summary based exclusively on the assumptions and calculations in this simulation.")
    report_text = build_markdown()
    st.markdown(report_text)
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇ Report (Markdown)", report_text.encode("utf-8"),
                       file_name="finance_lab_report.md", mime="text/markdown", **STRETCH)
    d2.download_button("⬇ Workbook (Excel)", build_excel(), file_name="finance_lab_workbook.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", **STRETCH)
    d3.download_button("⬇ Full data (CSV)", base.to_csv(index=False).encode("utf-8-sig"),
                       file_name="finance_lab_data.csv", mime="text/csv", **STRETCH)

st.divider()
st.caption(f"{APP_NAME.upper()} v{APP_VERSION} · Demonstration tool for financial planning. Figures are estimates "
           "based on editable assumptions and do not represent guaranteed results.")
