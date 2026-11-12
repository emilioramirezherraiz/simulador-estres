"""Descarga los precios de Yahoo Finance y los guarda en data/precios.csv.

Se ejecuta automáticamente con la acción de GitHub "Actualizar datos de mercado"
(.github/workflows/snapshot.yml), así no depende de tu ordenador.
"""

from market_data import SNAPSHOT, download_prices

prices = download_prices()
if prices.empty or prices["rv_desarrollada"].notna().sum() < 100:
    raise SystemExit("La descarga ha fallado o está incompleta; no se guarda nada.")
SNAPSHOT.parent.mkdir(exist_ok=True)
prices.round(6).to_csv(SNAPSHOT)
print(f"Guardado {SNAPSHOT}: {prices.shape[0]} días, {prices.index.min():%Y-%m-%d} a {prices.index.max():%Y-%m-%d}")
print(prices.notna().sum().to_string())
