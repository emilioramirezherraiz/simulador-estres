"""Cálculo determinista del impacto (sin IA)."""

from scenarios import ASSET_CLASSES, PHASES, SCENARIOS


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
        filas.append(fila)

    return {
        "filas": filas,
        "totales": {fase: round(valor, 2) for fase, valor in totales.items()},
    }
