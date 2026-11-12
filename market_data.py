"""Datos de mercado para el cálculo de correlaciones (v1.2).

Cada clase de activo se representa con un ETF o un precio cotizado en Yahoo
Finance. Decisión de diseño: la app usa primero la copia guardada en
data/precios.csv, para que los resultados sean reproducibles y no dependan de
que Yahoo responda; solo si no existe la copia descarga los datos en vivo.
"""

from pathlib import Path

import pandas as pd

# Representantes de cada clase de activo. Revísalos y justifícalos en la bitácora.
PROXIES = {
    "rv_desarrollada": "SPY",   # S&P 500 (EE. UU. como aproximación a desarrollados)
    "rv_emergente": "EEM",      # MSCI Emerging Markets
    "bonos_core": "IEF",        # Bonos del Tesoro de EE. UU. a 7-10 años
    "high_yield": "HYG",        # Bonos corporativos high yield de EE. UU.
    "inmobiliario": "VNQ",      # REITs de EE. UU.
    "oro": "GLD",               # Oro físico
    "petroleo": "USO",          # Futuros de petróleo WTI
    "bitcoin": "BTC-USD",
}

# Clases sin un precio de mercado útil para calcular correlaciones.
SIN_PRECIO = {
    "stablecoins": "su precio está anclado a 1 dólar, así que su correlación no es informativa",
    "liquidez": "no tiene variaciones de precio",
}

START = "2016-12-01"
SNAPSHOT = Path(__file__).parent / "data" / "precios.csv"


def download_prices(end: str | None = None) -> pd.DataFrame:
    """Descarga precios de cierre ajustados de Yahoo Finance."""
    import yfinance as yf

    raw = yf.download(list(PROXIES.values()), start=START, end=end,
                      auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    by_ticker = {ticker: clase for clase, ticker in PROXIES.items()}
    close = close.rename(columns=by_ticker)
    return close[[c for c in PROXIES if c in close.columns]].sort_index()


def load_snapshot() -> pd.DataFrame | None:
    if SNAPSHOT.exists():
        return pd.read_csv(SNAPSHOT, index_col=0, parse_dates=True)
    return None


def load_prices() -> tuple[pd.DataFrame | None, str]:
    """Devuelve (precios, descripción de la fuente)."""
    prices = load_snapshot()
    if prices is not None and not prices.empty:
        return prices, f"copia guardada de Yahoo Finance (hasta {prices.index.max():%d/%m/%Y})"
    try:
        prices = download_prices()
        if not prices.empty and prices["rv_desarrollada"].notna().sum() > 100:
            return prices, "Yahoo Finance, descargado en vivo"
    except Exception:  # noqa: BLE001
        pass
    return None, "sin datos"
