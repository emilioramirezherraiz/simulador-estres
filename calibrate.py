"""Calibración de los shocks con precios reales (v1.4).

Para cada escenario calcula la variación acumulada de cada clase de activo
desde el inicio de su ventana de estrés hasta el final de cada fase, con los
precios guardados en data/precios.csv. Las clases sin precio útil
(stablecoins y liquidez) mantienen los supuestos de scenarios.py.

Uso:
    python calibrate.py           comprueba que scenarios.py coincide con los datos
                                  y compara con las cifras ilustrativas de la v1.0
"""

import pandas as pd

from market_data import PROXIES, load_snapshot
from scenarios import ASSET_SHORT, PHASES, SCENARIOS

# Cifras ilustrativas de las versiones v1.0 a v1.3, guardadas para comparar en la bitácora.
ILUSTRATIVAS = {
    "stablecoins": {
        "fase_1": {"rv_desarrollada": -6, "rv_emergente": -8, "bonos_core": 0, "high_yield": -4, "inmobiliario": -5, "oro": 1, "petroleo": -3, "bitcoin": -40},
        "fase_2": {"rv_desarrollada": -10, "rv_emergente": -14, "bonos_core": 3, "high_yield": -7, "inmobiliario": -9, "oro": 5, "petroleo": -6, "bitcoin": -55},
    },
    "energia": {
        "fase_1": {"rv_desarrollada": -8, "rv_emergente": -10, "bonos_core": -4, "high_yield": -5, "inmobiliario": -7, "oro": 3, "petroleo": 40, "bitcoin": -15},
        "fase_2": {"rv_desarrollada": -15, "rv_emergente": -18, "bonos_core": -10, "high_yield": -10, "inmobiliario": -18, "oro": 2, "petroleo": 25, "bitcoin": -35},
    },
    "panico_liquidez": {
        "fase_1": {"rv_desarrollada": -30, "rv_emergente": -32, "bonos_core": 3, "high_yield": -20, "inmobiliario": -38, "oro": -8, "petroleo": -50, "bitcoin": -45},
        "fase_2": {"rv_desarrollada": -15, "rv_emergente": -20, "bonos_core": 6, "high_yield": -10, "inmobiliario": -20, "oro": 8, "petroleo": -30, "bitcoin": -20},
    },
}


def calibrated_shocks(prices: pd.DataFrame, scenario_key: str) -> dict:
    """Variación acumulada (%) por fase para las clases con precio de mercado.

    Se usan los días en que cotiza la bolsa de EE. UU. (bitcoin se alinea con ellos)
    y el precio de cierre ajustado del último día disponible de cada fase.
    """
    sc = SCENARIOS[scenario_key]
    us = prices[prices["rv_desarrollada"].notna()].ffill()
    window = us.loc[sc["ventana_estres"]["inicio"]:]
    base = window.iloc[0]
    out = {}
    for fase in PHASES:
        end = window.loc[:sc["fases"][fase]["fin"]].iloc[-1]
        out[fase] = {a: round(float((end[a] / base[a] - 1) * 100), 1) for a in PROXIES}
    return out


def main() -> None:
    prices = load_snapshot()
    if prices is None:
        raise SystemExit("No hay data/precios.csv. Ejecuta antes la acción 'Actualizar datos de mercado'.")
    ok = True
    for key, sc in SCENARIOS.items():
        real = calibrated_shocks(prices, key)
        print(f"\n{sc['nombre']} ({sc['ventana_estres']['inicio']} a {sc['ventana_estres']['fin']})")
        print(f"{'Activo':<14}" + "".join(f"{'v1.0 ' + f[-1]:>10}{'real ' + f[-1]:>10}" for f in PHASES))
        for a in PROXIES:
            row = f"{ASSET_SHORT[a]:<14}"
            for fase in PHASES:
                row += f"{ILUSTRATIVAS[key][fase][a]:>10}{real[fase][a]:>10}"
                if abs(sc["shocks"][fase][a] - real[fase][a]) > 0.05:
                    ok = False
                    row += f"  <- scenarios.py tiene {sc['shocks'][fase][a]}"
            print(row)
    print("\nscenarios.py coincide con los datos." if ok else
          "\nscenarios.py NO coincide con los datos: actualiza las cifras marcadas.")


if __name__ == "__main__":
    main()
