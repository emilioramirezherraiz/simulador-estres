"""Cálculo determinista del impacto (sin IA)."""

from market_data import PROXIES
from scenarios import ASSET_CLASSES, ASSET_GROUPS, PHASES, SCENARIOS, SIN_VARIACION


def movimiento(diferencia_pp: float) -> str:
    """Qué hace el activo (o la cartera) entre el final de la fase 1 y el de la fase 2 (v1.4.2)."""
    if diferencia_pp >= 1:
        return "recupera"
    if diferencia_pp <= -1:
        return "cae más"
    return "se mantiene"


def compute_impacts(portfolio: dict[str, float], scenario_key: str) -> dict:
    """Aplica los shocks del escenario a una cartera.

    portfolio: {clave_activo: peso_en_%}, con pesos que suman 100.
    Devuelve las filas por activo y el impacto total de la cartera por fase.
    La contribución está en puntos porcentuales de la cartera.
    """
    shocks = SCENARIOS[scenario_key]["shocks"]
    filas = []
    totales = {fase: 0.0 for fase in PHASES}

    for activo, peso in portfolio.items():
        fila = {"activo": activo, "nombre": ASSET_CLASSES[activo], "peso": peso}
        for fase in PHASES:
            shock = shocks[fase][activo]
            contribucion = peso / 100 * shock
            fila[f"{fase}_shock"] = shock
            fila[f"{fase}_contrib"] = round(contribucion, 2)
            totales[fase] += contribucion
        # v1.4: las cifras son acumuladas; esta diferencia (en puntos) es lo que pasa
        # entre el final de la fase 1 y el de la fase 2. Positiva: recuperación parcial.
        fila["diferencia_entre_fases_pp"] = round(fila["fase_2_shock"] - fila["fase_1_shock"], 1)
        fila["movimiento_en_fase_2"] = movimiento(fila["diferencia_entre_fases_pp"])
        fila["origen"] = ("calibrado" if activo in PROXIES
                          else "sin variación por definición" if activo in SIN_VARIACION else "supuesto")
        filas.append(fila)

    grupos = {}
    for grupo, miembros in ASSET_GROUPS.items():
        presentes = [f for f in filas if f["activo"] in miembros]
        if len(presentes) >= 2:  # solo tiene sentido agregar si hay varios
            grupos[grupo] = {
                "peso": round(sum(f["peso"] for f in presentes), 2),
                **{f"{fase}_contrib": round(sum(f[f"{fase}_contrib"] for f in presentes), 2) for fase in PHASES},
            }

    totales = {fase: round(valor, 2) for fase, valor in totales.items()}
    return {
        "filas": filas,
        "grupos": grupos,
        "totales": totales,
        "diferencia_total_entre_fases_pp": round(totales["fase_2"] - totales["fase_1"], 2),
        "movimiento_cartera_en_fase_2": movimiento(totales["fase_2"] - totales["fase_1"]),
    }
