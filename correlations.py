"""Correlaciones en calma frente a estrés (v1.3).

Compara el comportamiento conjunto de los activos de la cartera en un periodo
tranquilo y en la ventana histórica de crisis de cada escenario. Todo se
calcula aquí, sin IA; el modelo solo recibe los resultados para explicarlos.

v1.3: los pares se ordenan por su impacto en el riesgo de la cartera (no por el
tamaño del cambio de correlación) y la correlación media se separa entre
activos de riesgo y entre activos de riesgo y refugios.
"""

import numpy as np
import pandas as pd

from market_data import PROXIES, SIN_PRECIO
from scenarios import ASSET_NATURE, ASSET_ROLE, ASSET_SHORT, CALM_WINDOW, SCENARIOS

MIN_OBS = 15  # días mínimos con datos para calcular una correlación
TRADING_DAYS = 252
TOP_PAIRS = 5


def window_returns(prices: pd.DataFrame, inicio: str, fin: str) -> pd.DataFrame:
    """Rentabilidades logarítmicas diarias en días de mercado de EE. UU.

    Bitcoin cotiza también en fin de semana: se alinea con los días en que
    cotiza la bolsa para que todas las series sean comparables.
    """
    p = prices.loc[inicio:fin]
    p = p[p["rv_desarrollada"].notna()].ffill()
    return np.log(p).diff().iloc[1:]


def _mean_corr(corr: pd.DataFrame, pairs: list[tuple[str, str]]) -> float | None:
    values = [corr.loc[a, b] for a, b in pairs if pd.notna(corr.loc[a, b])]
    return round(float(np.mean(values)), 2) if values else None


def _stats(returns: pd.DataFrame, w: pd.Series, pares: dict) -> dict:
    corr = returns.corr(min_periods=MIN_OBS)
    cov = returns.cov(min_periods=MIN_OBS) * TRADING_DAYS
    vols = pd.Series(np.sqrt(np.diag(cov)), index=returns.columns)
    wv = w.loc[returns.columns].to_numpy()
    port_vol = float(np.sqrt(wv @ cov.to_numpy() @ wv))
    return {
        "matriz": corr.round(2),
        "correlacion_media": _mean_corr(corr, pares["todos"]),
        "correlacion_media_entre_riesgo": _mean_corr(corr, pares["riesgo"]),
        "correlacion_media_riesgo_refugio": _mean_corr(corr, pares["riesgo_refugio"]),
        "volatilidades_pct": {a: round(float(v) * 100, 1) for a, v in vols.items()},
        "volatilidad_cartera_pct": round(port_vol * 100, 1),
        "ratio_diversificacion": round(float(wv @ vols.to_numpy()) / port_vol, 2),
        "_vols": vols,
        "_var": port_vol ** 2,
    }


def compute_correlations(prices: pd.DataFrame | None, portfolio: dict[str, float], scenario_key: str) -> dict | None:
    """Devuelve el análisis de correlaciones, o None si no hay datos suficientes."""
    if prices is None:
        return None
    ventana = SCENARIOS[scenario_key]["ventana_estres"]
    calma_r = window_returns(prices, CALM_WINDOW["inicio"], CALM_WINDOW["fin"])
    estres_r = window_returns(prices, ventana["inicio"], ventana["fin"])

    activos, sin_historico = [], []
    for activo in portfolio:
        if activo not in PROXIES:
            continue
        ok = all(activo in r.columns and r[activo].notna().sum() >= MIN_OBS for r in (calma_r, estres_r))
        (activos if ok else sin_historico).append(activo)
    if len(activos) < 2:
        return None

    todos = [(a, b) for i, a in enumerate(activos) for b in activos[i + 1:]]
    pares = {
        "todos": todos,
        "riesgo": [(a, b) for a, b in todos if ASSET_ROLE[a] == ASSET_ROLE[b] == "riesgo"],
        "riesgo_refugio": [(a, b) for a, b in todos if {ASSET_ROLE[a], ASSET_ROLE[b]} == {"riesgo", "refugio"}],
    }
    w = pd.Series(portfolio, dtype=float).loc[activos]
    w = w / w.sum()  # pesos sobre la parte de la cartera con datos de mercado
    calma = _stats(calma_r[activos].dropna(), w, pares)
    estres = _stats(estres_r[activos].dropna(), w, pares)

    # Impacto de cada cambio de correlación en el riesgo de la cartera en estrés:
    # 2·wi·wj·σi·σj·Δρ, expresado como % de la varianza de la cartera en estrés.
    # Positivo: el cambio aumenta el riesgo; negativo: lo reduce (la cobertura mejora).
    s = estres["_vols"]
    relevantes = []
    for a, b in todos:
        c0, c1 = calma["matriz"].loc[a, b], estres["matriz"].loc[a, b]
        if pd.isna(c0) or pd.isna(c1):
            continue
        impacto = 2 * w[a] * w[b] * s[a] * s[b] * (c1 - c0) / estres["_var"] * 100
        relevantes.append({
            "par": f"{ASSET_SHORT[a]} / {ASSET_SHORT[b]}", "activos": [a, b],
            "tipo": f"{ASSET_ROLE[a]} / {ASSET_ROLE[b]}",
            "calma": float(c0), "estres": float(c1), "cambio": round(float(c1 - c0), 2),
            "impacto_en_varianza_pct": round(float(impacto), 1),
        })
    relevantes.sort(key=lambda x: abs(x["impacto_en_varianza_pct"]), reverse=True)

    for st in (calma, estres):
        st.pop("_vols"), st.pop("_var")
    return {
        "ventana_calma": CALM_WINDOW,
        "ventana_estres": ventana,
        "activos": activos,
        "sin_historico": sin_historico,
        "sin_precio": [a for a in portfolio if a in SIN_PRECIO],
        "peso_cubierto_pct": round(sum(portfolio[a] for a in activos), 1),
        "calma": calma,
        "estres": estres,
        "pares_mas_relevantes": relevantes[:TOP_PAIRS],
    }


def correlations_for_prompt(corr: dict) -> dict:
    """Versión serializable (sin DataFrames) para enviar al modelo."""
    def stats(s):
        return {**{k: v for k, v in s.items() if k != "matriz"},
                "matriz": {a: {b: float(s["matriz"].loc[a, b]) for b in corr["activos"] if b != a}
                           for a in corr["activos"]}}
    return {
        "ventana_calma": f"{corr['ventana_calma']['inicio']} a {corr['ventana_calma']['fin']}",
        "ventana_estres": f"{corr['ventana_estres']['inicio']} a {corr['ventana_estres']['fin']} ({corr['ventana_estres']['justificacion']})",
        "activos_incluidos": corr["activos"],
        "activos_sin_historico": corr["sin_historico"],
        "activos_sin_precio": corr["sin_precio"],
        "peso_de_la_cartera_cubierto_pct": corr["peso_cubierto_pct"],
        "calma": stats(corr["calma"]),
        "estres": stats(corr["estres"]),
        "pares_mas_relevantes": {
            "criterio": "ordenados por el impacto del cambio de correlación en la varianza de la cartera en estrés; "
                        "impacto positivo aumenta el riesgo, negativo lo reduce",
            "pares": [{k: v for k, v in c.items() if k != "activos"} for c in corr["pares_mas_relevantes"]],
        },
    }


def classification_for_prompt(portfolio: dict) -> dict:
    return {a: {"funcion_en_crisis": ASSET_ROLE[a], "naturaleza": ASSET_NATURE[a]} for a in portfolio}
