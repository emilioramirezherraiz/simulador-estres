"""Correlaciones en calma frente a estrés (v1.2).

Compara el comportamiento conjunto de los activos de la cartera en un periodo
tranquilo y en la ventana histórica de crisis de cada escenario. Todo se
calcula aquí, sin IA; el modelo solo recibe los resultados para explicarlos.
"""

import numpy as np
import pandas as pd

from market_data import PROXIES, SIN_PRECIO
from scenarios import ASSET_SHORT, CALM_WINDOW, SCENARIOS

MIN_OBS = 15  # días mínimos con datos para calcular una correlación
TRADING_DAYS = 252


def window_returns(prices: pd.DataFrame, inicio: str, fin: str) -> pd.DataFrame:
    """Rentabilidades logarítmicas diarias en días de mercado de EE. UU.

    Bitcoin cotiza también en fin de semana: se alinea con los días en que
    cotiza la bolsa para que todas las series sean comparables.
    """
    p = prices.loc[inicio:fin]
    p = p[p["rv_desarrollada"].notna()].ffill()
    return np.log(p).diff().iloc[1:]


def _stats(returns: pd.DataFrame, weights: pd.Series) -> dict:
    corr = returns.corr(min_periods=MIN_OBS)
    cov = returns.cov(min_periods=MIN_OBS) * TRADING_DAYS
    vols = np.sqrt(np.diag(cov))
    w = weights.loc[returns.columns].to_numpy()
    w = w / w.sum()
    port_vol = float(np.sqrt(w @ cov.to_numpy() @ w))
    upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
    return {
        "matriz": corr.round(2),
        "correlacion_media": round(float(upper.mean()), 2),
        "volatilidades_pct": {a: round(float(v) * 100, 1) for a, v in zip(returns.columns, vols)},
        "volatilidad_cartera_pct": round(port_vol * 100, 1),
        "ratio_diversificacion": round(float(w @ vols) / port_vol, 2),
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

    weights = pd.Series(portfolio, dtype=float)
    calma = _stats(calma_r[activos].dropna(), weights)
    estres = _stats(estres_r[activos].dropna(), weights)

    cambios = []
    for i, a in enumerate(activos):
        for b in activos[i + 1:]:
            c0, c1 = calma["matriz"].loc[a, b], estres["matriz"].loc[a, b]
            cambios.append({"par": f"{ASSET_SHORT[a]} / {ASSET_SHORT[b]}", "activos": [a, b],
                            "calma": float(c0), "estres": float(c1), "cambio": round(float(c1 - c0), 2)})
    cambios.sort(key=lambda x: abs(x["cambio"]), reverse=True)

    return {
        "ventana_calma": CALM_WINDOW,
        "ventana_estres": ventana,
        "activos": activos,
        "sin_historico": sin_historico,
        "sin_precio": [a for a in portfolio if a in SIN_PRECIO],
        "peso_cubierto_pct": round(sum(portfolio[a] for a in activos), 1),
        "calma": calma,
        "estres": estres,
        "mayores_cambios": cambios[:5],
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
        "mayores_cambios": [{k: v for k, v in c.items() if k != "activos"} for c in corr["mayores_cambios"]],
    }
