import io
from datetime import date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Finance Lab | Simulador financiero",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Visual system ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1440px;}
    [data-testid="stMetric"] {background: rgba(128,128,128,.08); padding: 14px 16px; border-radius: 12px;}
    .eyebrow {font-size: .75rem; letter-spacing: .12em; font-weight: 700; opacity: .65;}
    .hero {padding: 1.2rem 1.4rem; border: 1px solid rgba(128,128,128,.25); border-radius: 16px; margin-bottom: 1rem;}
    .small-note {font-size: .82rem; opacity: .72;}
    div[data-testid="stTabs"] button {font-weight: 600;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">FINANCIAL PLANNING & SCENARIO SIMULATOR</div>', unsafe_allow_html=True)
st.title("Finance Lab")
st.caption("Simulador de planificación financiera empresarial · Modelo ilustrativo, editable y transparente")

with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.caption("Definí las condiciones iniciales de la empresa.")
    currency = st.selectbox("Moneda", ["ARS", "USD", "EUR"], index=0)
    months = st.select_slider("Horizonte de proyección", options=[6, 12, 18, 24, 36], value=12)
    st.divider()
    st.markdown("### Empresa de ejemplo")
    company = st.text_input("Nombre del proyecto", "Empresa Demo")
    start_month = st.date_input("Inicio de la proyección", value=date.today().replace(day=1))
    st.divider()
    st.caption("Los resultados dependen de los supuestos ingresados. No reemplazan estados contables, asesoramiento impositivo ni una evaluación profesional.")

def money(v, cur=currency):
    try:
        return f"{cur} {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{cur} 0"

def make_model(p, n_months, growth_override=None, cost_delta=0.0):
    """Monthly simplified accrual and cash model.
    Collection/payment lags are whole-month approximations (0, 1 or 2 months).
    """
    growth = p["growth"] if growth_override is None else growth_override
    cost_pct = np.clip(p["variable_cost_pct"] + cost_delta, 0, 0.99)
    periods = pd.date_range(pd.Timestamp(start_month).replace(day=1), periods=n_months, freq="MS")
    idx = np.arange(n_months)
    revenue = p["revenue"] * np.power(1 + growth / 100, idx)
    variable_costs = revenue * cost_pct
    fixed_costs = np.full(n_months, p["fixed_costs"], dtype=float)
    depreciation = np.full(n_months, p["depreciation"], dtype=float)
    interest = np.full(n_months, p["interest"], dtype=float)
    ebitda = revenue - variable_costs - fixed_costs
    ebit = ebitda - depreciation
    ebt = ebit - interest
    taxes = np.maximum(ebt, 0) * (p["tax_pct"] / 100)
    net_income = ebt - taxes

    collections = np.zeros(n_months)
    supplier_payments = np.zeros(n_months)
    for i in range(n_months):
        ci = i - p["collection_lag"]
        pi = i - p["payment_lag"]
        if ci >= 0:
            collections[i] = revenue[ci]
        elif i == 0 and p["collection_lag"] > 0:
            collections[i] = p["opening_receivables"] if p["collection_lag"] == 1 else 0
        if pi >= 0:
            supplier_payments[i] = variable_costs[pi]
        elif i == 0 and p["payment_lag"] > 0:
            supplier_payments[i] = p["opening_payables"] if p["payment_lag"] == 1 else 0

    fixed_cash = fixed_costs.copy()
    tax_cash = taxes.copy()
    capex = np.zeros(n_months)
    capex[0] = p["capex"]
    net_cash_flow = collections - supplier_payments - fixed_cash - tax_cash - capex
    opening_cash = np.zeros(n_months)
    closing_cash = np.zeros(n_months)
    cash = p["opening_cash"]
    for i in range(n_months):
        opening_cash[i] = cash
        cash += net_cash_flow[i]
        closing_cash[i] = cash

    df = pd.DataFrame({
        "Mes": periods,
        "Ingresos": revenue,
        "Costos variables": variable_costs,
        "Gastos fijos": fixed_costs,
        "EBITDA": ebitda,
        "Depreciación": depreciation,
        "Intereses": interest,
        "Impuestos estimados": taxes,
        "Resultado neto estimado": net_income,
        "Cobros": collections,
        "Pagos a proveedores": supplier_payments,
        "Inversión (CAPEX)": capex,
        "Flujo neto de caja": net_cash_flow,
        "Caja inicial": opening_cash,
        "Caja final": closing_cash,
    })
    return df

# ---------- Input model ----------
with st.sidebar:
    st.markdown("### Supuestos operativos")
    revenue = st.number_input("Ingresos mensuales iniciales", min_value=0.0, value=10_000_000.0, step=250_000.0, format="%.0f")
    growth = st.slider("Crecimiento mensual de ingresos (%)", -20.0, 20.0, 2.0, 0.5)
    variable_cost_pct = st.slider("Costos variables (% de ventas)", 0, 95, 55)
    fixed_costs = st.number_input("Gastos fijos mensuales", min_value=0.0, value=2_500_000.0, step=100_000.0, format="%.0f")
    st.markdown("### Finanzas y caja")
    opening_cash = st.number_input("Caja inicial", min_value=0.0, value=5_000_000.0, step=250_000.0, format="%.0f")
    collection_lag = st.selectbox("Demora de cobro", [0, 1, 2], format_func=lambda x: ["Mismo mes", "1 mes", "2 meses"][x], index=1)
    payment_lag = st.selectbox("Demora de pago a proveedores", [0, 1, 2], format_func=lambda x: ["Mismo mes", "1 mes", "2 meses"][x], index=1)
    opening_receivables = st.number_input("Cuentas por cobrar iniciales", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
    opening_payables = st.number_input("Cuentas por pagar iniciales", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
    capex = st.number_input("Inversión inicial (CAPEX)", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
    depreciation = st.number_input("Depreciación mensual estimada", min_value=0.0, value=0.0, step=50_000.0, format="%.0f")
    interest = st.number_input("Intereses mensuales estimados", min_value=0.0, value=0.0, step=50_000.0, format="%.0f")
    tax_pct = st.slider("Tasa efectiva de impuesto estimada (%)", 0, 50, 30)

params = {
    "revenue": revenue, "growth": growth, "variable_cost_pct": variable_cost_pct,
    "fixed_costs": fixed_costs, "opening_cash": opening_cash,
    "collection_lag": collection_lag, "payment_lag": payment_lag,
    "opening_receivables": opening_receivables, "opening_payables": opening_payables,
    "capex": capex, "depreciation": depreciation, "interest": interest,
    "tax_pct": tax_pct,
}
base = make_model(params, months)

# ---------- Tabs ----------
tab_dash, tab_inputs, tab_projection, tab_scenarios, tab_report = st.tabs([
    "▦  Dashboard", "⚙  Supuestos", "↗  Proyección", "⇄  Escenarios", "▤  Informe"
])

with tab_dash:
    st.markdown(f'<div class="hero"><div class="eyebrow">{company.upper()} · RESUMEN EJECUTIVO</div><h3 style="margin:.35rem 0">Panorama financiero proyectado</h3><div class="small-note">Horizonte: {months} meses · Moneda: {currency}</div></div>', unsafe_allow_html=True)
    total_revenue = base["Ingresos"].sum()
    total_ebitda = base["EBITDA"].sum()
    ending_cash = base["Caja final"].iloc[-1]
    min_cash = base["Caja final"].min()
    margin = (total_ebitda / total_revenue * 100) if total_revenue else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos acumulados", money(total_revenue))
    c2.metric("EBITDA acumulado", money(total_ebitda), f"{margin:.1f}% margen")
    c3.metric("Caja al cierre", money(ending_cash), delta=None)
    c4.metric("Punto mínimo de caja", money(min_cash), delta="Riesgo" if min_cash < 0 else "Positivo", delta_color="inverse" if min_cash < 0 else "normal")

    left, right = st.columns([1.6, 1])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=base["Mes"], y=base["Ingresos"], name="Ingresos", mode="lines+markers", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=base["Mes"], y=base["Gastos fijos"] + base["Costos variables"], name="Costos y gastos", mode="lines", line=dict(width=2, dash="dot")))
        fig.update_layout(title="Ingresos vs. estructura de costos", height=350, margin=dict(l=10,r=10,t=50,b=10), legend=dict(orientation="h", y=-.22), yaxis_title=currency, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig2 = go.Figure(go.Scatter(x=base["Mes"], y=base["Caja final"], name="Caja final", fill="tozeroy", mode="lines+markers", line=dict(width=3)))
        fig2.add_hline(y=0, line_dash="dash", line_color="red")
        fig2.update_layout(title="Evolución de caja", height=350, margin=dict(l=10,r=10,t=50,b=10), yaxis_title=currency)
        st.plotly_chart(fig2, use_container_width=True)

    warnings = []
    if min_cash < 0:
        first_negative = base.loc[base["Caja final"] < 0, "Mes"].iloc[0].strftime("%b %Y")
        warnings.append(("🔴", f"La caja proyectada se vuelve negativa en {first_negative}. Revisá plazos de cobro, pagos, costos o financiación."))
    if margin < 10:
        warnings.append(("🟠", "El margen EBITDA acumulado es inferior al 10 %. La estructura de costos merece revisión."))
    if growth < 0:
        warnings.append(("🟠", "Se proyecta una contracción mensual de ingresos. Evaluá el impacto acumulado sobre la liquidez."))
    if not warnings:
        warnings.append(("🟢", "No se detectan alertas básicas con los supuestos actuales. Esto no garantiza solvencia ni rentabilidad futura."))
    st.markdown("#### Señales para revisar")
    for icon, message in warnings:
        st.info(f"{icon}  {message}")

with tab_inputs:
    st.subheader("Supuestos del modelo")
    st.write("Todos los cálculos se derivan de las variables ingresadas en la barra lateral. Los desfases de cobro y pago se modelan en meses completos.")
    input_rows = [
        ("Ingresos mensuales iniciales", revenue, currency),
        ("Crecimiento mensual", growth, "%"),
        ("Costos variables", variable_cost_pct, "% de ingresos"),
        ("Gastos fijos mensuales", fixed_costs, currency),
        ("Caja inicial", opening_cash, currency),
        ("Demora de cobro", collection_lag, "meses"),
        ("Demora de pago", payment_lag, "meses"),
        ("Cuentas por cobrar iniciales", opening_receivables, currency),
        ("Cuentas por pagar iniciales", opening_payables, currency),
        ("CAPEX inicial", capex, currency),
        ("Depreciación mensual", depreciation, currency),
        ("Intereses mensuales", interest, currency),
        ("Impuesto efectivo estimado", tax_pct, "%"),
    ]
    st.dataframe(pd.DataFrame(input_rows, columns=["Variable", "Valor", "Unidad"]), use_container_width=True, hide_index=True)
    st.warning("Simplificaciones: no se modelan inflación, IVA, cargas sociales, estacionalidad, inventarios, deuda nueva, dividendos ni cambios de precios/cantidades por separado. El impuesto es una aproximación aplicada al resultado antes de impuestos positivo.")

with tab_projection:
    st.subheader("Proyección mensual")
    view = st.radio("Vista", ["Resultados", "Flujo de caja", "Detalle completo"], horizontal=True)
    if view == "Resultados":
        cols = ["Mes", "Ingresos", "Costos variables", "Gastos fijos", "EBITDA", "Depreciación", "Intereses", "Impuestos estimados", "Resultado neto estimado"]
    elif view == "Flujo de caja":
        cols = ["Mes", "Cobros", "Pagos a proveedores", "Gastos fijos", "Impuestos estimados", "Inversión (CAPEX)", "Flujo neto de caja", "Caja inicial", "Caja final"]
    else:
        cols = list(base.columns)
    display = base[cols].copy()
    display["Mes"] = display["Mes"].dt.strftime("%b %Y")
    st.dataframe(display.style.format({c: (lambda x: f"{x:,.0f}") for c in display.columns if c != "Mes"}), use_container_width=True, hide_index=True)
    st.download_button("⬇ Descargar proyección CSV", data=base.to_csv(index=False).encode("utf-8-sig"), file_name="finance_lab_proyeccion.csv", mime="text/csv")

with tab_scenarios:
    st.subheader("Comparador de escenarios")
    st.write("Compará tres hipótesis. Los cambios se aplican al crecimiento mensual y al porcentaje de costos variables.")
    scenario_specs = [
        ("Pesimista", growth - 3, 5, "Contracción del crecimiento y presión sobre costos"),
        ("Base", growth, 0, "Supuestos actuales"),
        ("Optimista", growth + 3, -3, "Mayor crecimiento y mejora de costos"),
    ]
    scenario_results = []
    scenario_frames = {}
    for name, g, cd, desc in scenario_specs:
        frame = make_model(params, months, growth_override=g, cost_delta=cd)
        scenario_frames[name] = frame
        scenario_results.append({
            "Escenario": name, "Crecimiento mensual": f"{g:.1f}%",
            "Costos variables": f"{np.clip(variable_cost_pct+cd,0,99):.1f}%",
            "Ingresos acumulados": frame["Ingresos"].sum(),
            "EBITDA acumulado": frame["EBITDA"].sum(),
            "Caja final": frame["Caja final"].iloc[-1],
            "Caja mínima": frame["Caja final"].min(),
            "Descripción": desc,
        })
    sdf = pd.DataFrame(scenario_results)
    st.dataframe(sdf.style.format({c: (lambda x: f"{currency} {x:,.0f}") for c in ["Ingresos acumulados","EBITDA acumulado","Caja final","Caja mínima"]}), use_container_width=True, hide_index=True)
    fig = go.Figure()
    for name, frame in scenario_frames.items():
        fig.add_trace(go.Scatter(x=frame["Mes"], y=frame["Caja final"], mode="lines+markers", name=name))
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.update_layout(title="Caja final por escenario", height=420, yaxis_title=currency, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Los escenarios optimista y pesimista son sensibilidades ilustrativas, no probabilidades ni pronósticos.")

with tab_report:
    st.subheader("Informe ejecutivo")
    st.write("Síntesis automática basada exclusivamente en los supuestos y cálculos de esta simulación.")
    net_total = base["Resultado neto estimado"].sum()
    first_low = base.loc[base["Caja final"] < 0, "Mes"]
    report = [
        f"# Finance Lab — Informe de simulación",
        f"**Proyecto:** {company}",
        f"**Fecha de generación:** {date.today().isoformat()}",
        f"**Horizonte:** {months} meses | **Moneda:** {currency}",
        "",
        "## Resumen",
        f"- Ingresos acumulados: {money(total_revenue)}",
        f"- EBITDA acumulado: {money(total_ebitda)}",
        f"- Margen EBITDA acumulado: {margin:.1f}%",
        f"- Resultado neto estimado acumulado: {money(net_total)}",
        f"- Caja final proyectada: {money(ending_cash)}",
        f"- Caja mínima proyectada: {money(min_cash)}",
        "",
        "## Observaciones",
    ]
    if len(first_low):
        report.append(f"- La caja se vuelve negativa por primera vez en {first_low.iloc[0].strftime('%B %Y')}.")
    else:
        report.append("- La caja se mantiene no negativa durante el horizonte simulado.")
    if margin < 10:
        report.append("- El margen EBITDA acumulado es reducido; revisar costos, precios y estructura.")
    else:
        report.append("- El margen EBITDA acumulado supera el 10 % bajo los supuestos ingresados.")
    report += [
        "",
        "## Alcance y limitaciones",
        "Este documento es una simulación simplificada. No constituye asesoramiento contable, financiero, legal ni impositivo. No contempla inflación, IVA, estacionalidad, inventarios, nómina detallada, financiación nueva ni cambios en capital de trabajo más allá de los desfases aproximados de cobro y pago.",
    ]
    report_text = "\n".join(report)
    st.markdown(report_text)
    st.download_button("⬇ Descargar informe Markdown", data=report_text.encode("utf-8"), file_name="finance_lab_informe.md", mime="text/markdown")
    st.download_button("⬇ Descargar datos completos CSV", data=base.to_csv(index=False).encode("utf-8-sig"), file_name="finance_lab_datos.csv", mime="text/csv")

st.divider()
st.caption("FINANCE LAB · Herramienta demostrativa de planificación financiera. Las cifras son estimaciones basadas en supuestos editables y no representan resultados garantizados.")
