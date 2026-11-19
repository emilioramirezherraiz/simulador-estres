"""Simulador narrativo de estrés para carteras (Streamlit)."""

import datetime as dt
import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from correlations import compute_correlations
from engine import compute_impacts
from llm import DEFAULT_MODEL, call_llm, parse_json
from prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from market_data import load_prices
from scenarios import ASSET_CLASSES, ASSET_SHORT, PHASES, SCENARIOS
from validation import validate_report

LOG_PATH = Path("logs/runs.jsonl")
DEFAULT_WEIGHTS = {
    "rv_desarrollada": 40.0, "rv_emergente": 10.0, "bonos_core": 25.0,
    "high_yield": 5.0, "oro": 10.0, "bitcoin": 5.0, "liquidez": 5.0,
}


def get_secret(name: str, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


def save_run(run: dict) -> None:
    """Guarda cada ejecución en logs/runs.jsonl (en local). En la nube puede no persistir."""
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(run, ensure_ascii=False) + "\n")
    except OSError:
        pass


@st.cache_data(ttl=24 * 3600, show_spinner="Cargando datos de mercado...")
def get_prices():
    return load_prices()


def heatmap(matriz: pd.DataFrame, titulo: str) -> alt.Chart:
    orden = [ASSET_SHORT[a] for a in matriz.index]
    m = matriz.rename(index=ASSET_SHORT, columns=ASSET_SHORT)
    m.index.name = "fila"
    largo = m.reset_index().melt(id_vars="fila", var_name="columna", value_name="correlacion").dropna()
    base = alt.Chart(largo).encode(
        x=alt.X("columna:N", sort=orden, title=None, axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("fila:N", sort=orden, title=None),
    )
    celdas = base.mark_rect().encode(
        color=alt.Color("correlacion:Q", scale=alt.Scale(domain=[-1, 1], scheme="redblue", reverse=True),
                        legend=alt.Legend(title="Correlación")),
        tooltip=["fila", "columna", alt.Tooltip("correlacion:Q", format=".2f")],
    )
    texto = base.mark_text(fontSize=11).encode(text=alt.Text("correlacion:Q", format=".2f"))
    return (celdas + texto).properties(title=titulo, height=40 * len(orden) + 60)


def render_correlations(corr: dict | None, fuente: str) -> None:
    st.subheader("Correlaciones: calma frente a estrés")
    if corr is None:
        st.info(
            "No hay datos de mercado suficientes para esta cartera. Hacen falta al menos dos clases de activo "
            f"con precio histórico (fuente: {fuente})."
        )
        return
    vc, ve = corr["ventana_calma"], corr["ventana_estres"]
    st.caption(
        f"Calma: {vc['inicio']} a {vc['fin']}. Estrés: {ve['inicio']} a {ve['fin']} ({ve['justificacion']}) "
        f"Datos: {fuente}. Cubre el {corr['peso_cubierto_pct']:.1f} % de la cartera."
    )
    def fmt(v):
        return "n/d" if v is None else f"{v:.2f}"

    def delta(clave):
        a, b = corr["calma"].get(clave), corr["estres"].get(clave)
        return None if a is None or b is None else f"{b - a:+.2f} frente a calma"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correlación entre activos de riesgo", fmt(corr["estres"]["correlacion_media_entre_riesgo"]),
              delta("correlacion_media_entre_riesgo"), delta_color="inverse",
              help="Media de las correlaciones entre los activos de riesgo de la cartera. Si sube, convergen.")
    c2.metric("Correlación riesgo-refugio", fmt(corr["estres"]["correlacion_media_riesgo_refugio"]),
              delta("correlacion_media_riesgo_refugio"), delta_color="inverse",
              help="Media de las correlaciones entre activos de riesgo y refugios (bonos core, oro). "
                   "Si baja o es negativa, los refugios protegen.")
    c3.metric("Volatilidad anual de la cartera", f"{corr['estres']['volatilidad_cartera_pct']:.1f} %",
              f"{corr['estres']['volatilidad_cartera_pct'] - corr['calma']['volatilidad_cartera_pct']:+.1f} pp frente a calma",
              delta_color="inverse")
    c4.metric("Ratio de diversificación", f"{corr['estres']['ratio_diversificacion']:.2f}",
              f"{corr['estres']['ratio_diversificacion'] - corr['calma']['ratio_diversificacion']:+.2f} frente a calma",
              help="Media ponderada de las volatilidades dividida entre la volatilidad de la cartera. "
                   "Cuanto más cerca de 1, menos beneficio aporta la diversificación.")
    h1, h2 = st.columns(2)
    h1.altair_chart(heatmap(corr["calma"]["matriz"], "Calma"), width="stretch")
    h2.altair_chart(heatmap(corr["estres"]["matriz"], "Estrés"), width="stretch")
    st.markdown("**Pares con más impacto en el riesgo de la cartera**")
    st.caption("Impacto: parte de la varianza de la cartera en estrés que se debe al cambio de correlación del par. "
               "Positivo, el cambio aumenta el riesgo; negativo, lo reduce.")
    st.dataframe(
        pd.DataFrame([{"Par": c["par"], "Tipo": c["tipo"], "Calma": c["calma"], "Estrés": c["estres"],
                       "Cambio": c["cambio"], "Impacto (% varianza)": c["impacto_en_varianza_pct"]}
                      for c in corr["pares_mas_relevantes"]]),
        hide_index=True, width="stretch",
    )
    notas = []
    if corr["sin_precio"]:
        notas.append("sin precio de mercado útil: " + ", ".join(ASSET_SHORT[a] for a in corr["sin_precio"]))
    if corr["sin_historico"]:
        notas.append("sin histórico suficiente: " + ", ".join(ASSET_SHORT[a] for a in corr["sin_historico"]))
    if notas:
        st.caption("Excluidos del cálculo (" + "; ".join(notas) + "). La volatilidad se calcula sobre la parte cubierta.")


def render_report(run: dict, scenario_key: str, portfolio: dict) -> None:
    if run["escenario"] != scenario_key or run["cartera"] != portfolio:
        st.info(
            f"El último informe se generó para «{SCENARIOS[run['escenario']]['nombre']}» con otra cartera o escenario. "
            "Pulsa «Generar informe» para analizar la selección actual."
        )
        return
    st.caption(
        f"Informe para «{SCENARIOS[run['escenario']]['nombre']}», "
        f"modelo {run['modelo']}, prompt {run['prompt_version']}, {run['timestamp']}"
        + (f". Hicieron falta {run['intentos']} intentos porque la primera respuesta no era un JSON válido."
           if run.get("intentos", 1) > 1 else "")
    )

    issues = run["incidencias"]
    if issues:
        st.warning(f"La validación automática ha detectado {len(issues)} posibles problemas. Revísalos antes de dar el informe por bueno.")
        for issue in issues:
            st.markdown(f"- **{issue['tipo']}**: {issue['detalle']}")
    else:
        st.success("La validación automática no ha detectado incidencias. Revisa igualmente el razonamiento.")

    report = run["informe"]
    if report is None:
        st.error("La respuesta del modelo no es un JSON válido. Texto recibido:")
        st.code(run["respuesta_bruta"], line_numbers=True)
        return

    st.markdown("#### Resumen ejecutivo")
    st.write(report.get("resumen_ejecutivo", ""))

    st.markdown("#### Cadena de contagio")
    for paso in report.get("cadena_de_contagio", []):
        fase = PHASES.get(paso.get("fase"), paso.get("fase", ""))
        st.markdown(f"**{fase}. {paso.get('titulo', '')}**")
        st.write(paso.get("descripcion", ""))

    st.markdown("#### Impacto por activo")
    filas = [
        {
            "Activo": ASSET_CLASSES.get(item.get("activo"), item.get("activo")),
            "Fase 1": item.get("direccion_fase_1"),
            "Fase 2": item.get("direccion_fase_2"),
            "Mecanismo": item.get("mecanismo"),
        }
        for item in report.get("impacto_por_activo", [])
    ]
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

    st.markdown("#### Diversificación")
    st.write(report.get("diversificacion", ""))

    st.markdown("#### Riesgos de concentración")
    st.write(report.get("riesgos_de_concentracion", ""))

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Supuestos")
        for s in report.get("supuestos", []):
            st.markdown(f"- {s}")
    with col_b:
        st.markdown("#### Limitaciones")
        for s in report.get("limitaciones", []):
            st.markdown(f"- {s}")

    st.markdown(f"**Confianza del modelo:** {report.get('confianza', '?')}. {report.get('justificacion_confianza', '')}")

    with st.expander("Ver el prompt enviado y la respuesta en bruto"):
        st.markdown("**Mensaje con los datos**")
        st.code(run["prompt_usuario"], language="json")
        st.markdown("**Respuesta del modelo**")
        st.code(run["respuesta_bruta"], language="json")


# ---------------------------------------------------------------- página
st.set_page_config(page_title="Simulador narrativo de estrés", page_icon="📉", layout="wide")

st.session_state.setdefault("runs", [])
st.session_state.setdefault("last_run", None)

st.title("Simulador narrativo de estrés para carteras")
st.caption("Proyecto académico. No constituye asesoramiento financiero.")

with st.sidebar:
    st.subheader("Modelo de lenguaje")
    model = st.text_input("Identificador del modelo", value=get_secret("GEMINI_MODEL", DEFAULT_MODEL))
    st.caption(f"Versión del prompt: {PROMPT_VERSION}")
    api_key = get_secret("GEMINI_API_KEY")
    if api_key:
        st.success("Clave de API configurada.")
    else:
        st.warning("Falta GEMINI_API_KEY en los secretos. Puedes calcular el impacto, pero no generar el informe.")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("1. Tu cartera")
    st.caption("Indica el peso de cada clase de activo. Deben sumar 100 %.")
    df = pd.DataFrame({
        "clave": list(ASSET_CLASSES),
        "Clase de activo": list(ASSET_CLASSES.values()),
        "Peso (%)": [DEFAULT_WEIGHTS.get(k, 0.0) for k in ASSET_CLASSES],
    })
    edited = st.data_editor(
        df,
        column_config={
            "clave": None,
            "Clase de activo": st.column_config.TextColumn(disabled=True),
            "Peso (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
        },
        hide_index=True,
        width="stretch",
        key="portfolio_editor",
    )
    total = float(edited["Peso (%)"].fillna(0).sum())
    portfolio = {
        row["clave"]: float(row["Peso (%)"])
        for _, row in edited.iterrows()
        if pd.notna(row["Peso (%)"]) and row["Peso (%)"] > 0
    }
    weights_ok = abs(total - 100) < 0.01
    if weights_ok:
        st.caption(f"Total: {total:.1f} %")
    else:
        st.error(f"Los pesos suman {total:.1f} %. Ajústalos para que sumen 100 %.")

with col_right:
    st.subheader("2. Escenario de crisis")
    scenario_key = st.selectbox("Escenario", options=list(SCENARIOS), format_func=lambda k: SCENARIOS[k]["nombre"])
    sc = SCENARIOS[scenario_key]
    st.write(sc["descripcion"])
    with st.expander("Canales de transmisión y precedentes"):
        st.markdown("**Canales de transmisión**")
        st.markdown("\n".join(f"- {c}" for c in sc["canales"]))
        st.markdown("**Precedentes históricos**")
        st.markdown("\n".join(f"- {p}" for p in sc["precedentes"]))

st.divider()
st.subheader("3. Impacto estimado")

if not weights_ok or not portfolio:
    st.info("Completa la cartera para ver el impacto.")
    st.stop()

impacts = compute_impacts(portfolio, scenario_key)

m1, m2 = st.columns(2)
m1.metric(PHASES["fase_1"], f"{impacts['totales']['fase_1']:+.2f} %")
m2.metric(PHASES["fase_2"], f"{impacts['totales']['fase_2']:+.2f} %")

tabla = pd.DataFrame([
    {
        "Clase de activo": f["nombre"],
        "Peso (%)": f["peso"],
        "Shock fase 1 (%)": f["fase_1_shock"],
        "Contribución fase 1 (pp)": f["fase_1_contrib"],
        "Shock fase 2 (%)": f["fase_2_shock"],
        "Contribución fase 2 (pp)": f["fase_2_contrib"],
    }
    for f in impacts["filas"]
])
st.dataframe(tabla, hide_index=True, width="stretch")
st.caption("Calculado sin IA a partir de la tabla de sensibilidades del escenario (scenarios.py). Variación acumulada desde el inicio del shock.")

prices, fuente = get_prices()
corr = compute_correlations(prices, portfolio, scenario_key)
render_correlations(corr, fuente)

st.divider()
st.subheader("4. Informe narrativo")

if st.button("Generar informe", type="primary", disabled=not api_key):
    user_prompt = build_user_prompt(portfolio, scenario_key, impacts, corr)
    report, raw, issues, intentos = None, "", [], 0
    for intentos in (1, 2):  # si la respuesta no es un JSON válido, se pide una vez más
        with st.spinner("Generando el informe..." if intentos == 1 else "Respuesta mal formada, generando de nuevo..."):
            try:
                raw = call_llm(SYSTEM_PROMPT, user_prompt, api_key=api_key, model=model)
            except Exception as e:  # noqa: BLE001
                st.error(f"La llamada a la API ha fallado: {e}")
                st.stop()
        try:
            report = parse_json(raw)
            issues = validate_report(report, portfolio, scenario_key, impacts, corr)
            break
        except Exception as e:  # noqa: BLE001
            report = None
            issues = [{"tipo": "json_invalido", "detalle": f"{e} (intento {intentos} de 2)"}]

    run = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        "modelo": model,
        "escenario": scenario_key,
        "cartera": portfolio,
        "totales": impacts["totales"],
        "correlaciones_medias": ({p: {k: corr[p][k] for k in ("correlacion_media", "correlacion_media_entre_riesgo",
                                                         "correlacion_media_riesgo_refugio")}
                                 for p in ("calma", "estres")} if corr else None),
        "intentos": intentos,
        "n_incidencias": len(issues),
        "incidencias": issues,
        "informe": report,
        "respuesta_bruta": raw,
        "prompt_usuario": user_prompt,
    }
    st.session_state.last_run = run
    st.session_state.runs.append(run)
    save_run(run)

if st.session_state.last_run:
    render_report(st.session_state.last_run, scenario_key, portfolio)

if st.session_state.runs:
    st.divider()
    registro = pd.DataFrame([
        {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in r.items()}
        for r in st.session_state.runs
    ])
    st.download_button(
        "Descargar registro de ejecuciones (CSV)",
        registro.to_csv(index=False).encode("utf-8"),
        file_name="registro_ejecuciones.csv",
        mime="text/csv",
    )
