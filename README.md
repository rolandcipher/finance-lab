# Finance Lab — Simulador financiero empresarial

Aplicación demostrativa desarrollada con Python y Streamlit para explorar proyecciones financieras, flujo de caja y escenarios.

## Funciones

- Panel ejecutivo con ingresos, EBITDA, margen y evolución de caja.
- Supuestos editables desde la barra lateral.
- Proyección mensual de resultados y flujo de caja.
- Desfases simplificados de cobro y pago (0, 1 o 2 meses).
- Comparación de escenarios pesimista, base y optimista.
- Exportación de proyecciones a CSV e informe a Markdown.

## Ejecutar localmente

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate      # Windows
pip install -r requirements.txt
streamlit run app.py
```

La aplicación se abrirá normalmente en `http://localhost:8501`.

## Publicar en Streamlit Community Cloud

1. Creá un repositorio público en GitHub.
2. Subí `app.py` y `requirements.txt` a la raíz del repositorio.
3. Entrá en https://share.streamlit.io/ e iniciá sesión con GitHub.
4. Elegí el repositorio, la rama y `app.py` como archivo principal.
5. Seleccioná **Deploy**.

## Modelo y supuestos importantes

- Ingresos y costos se proyectan mensualmente con crecimiento compuesto.
- Los costos variables se calculan como porcentaje de ingresos.
- Los gastos fijos se mantienen constantes nominalmente.
- El EBITDA se calcula como ingresos menos costos variables y gastos fijos.
- El resultado neto estimado resta depreciación, intereses e impuestos aproximados.
- El flujo de caja aproxima cobros y pagos desplazando ingresos y costos variables por meses completos.
- Los saldos iniciales de cuentas por cobrar/pagar se contemplan únicamente como una aproximación inicial cuando el desfase es de un mes.
- CAPEX se registra como salida de caja inicial, no como gasto del estado de resultados.

## Limitaciones

Este MVP no modela inflación, IVA, estacionalidad, inventarios, nómina detallada, deuda nueva, amortizaciones de préstamos, dividendos ni variaciones separadas de precio y volumen. La tasa de impuesto es una aproximación aplicada al resultado antes de impuestos positivo. No debe utilizarse como sustituto de contabilidad, asesoramiento financiero o asesoramiento impositivo.

## Próximas mejoras posibles

- Importación de CSV/Excel.
- Inflación y actualización nominal de costos.
- Calendario de deuda y servicio de intereses.
- Capital de trabajo más detallado.
- Punto de equilibrio y sensibilidad de variables.
- Exportación de informes PDF.
