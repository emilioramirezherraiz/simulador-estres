"""Evaluación en lote: ejecuta todos los escenarios con carteras de prueba.

Lo normal es lanzarla en GitHub (no necesita tu ordenador):
    gh workflow run evaluate.yml
    gh run watch
    git pull

También funciona en local:
    $env:GEMINI_API_KEY="tu_clave"   (PowerShell)
    python evaluate.py

Guarda en resultados/ dos archivos por ejecución: un CSV con cada informe y sus
incidencias, y un resumen en Markdown con el recuento por tipo de incidencia.
Ejecútala cada vez que cambies el prompt y compara versiones en la bitácora.
"""

import csv
import datetime as dt
import json
import os
import time
from collections import Counter
from pathlib import Path

from correlations import compute_correlations
from engine import compute_impacts
from llm import DEFAULT_MODEL, call_llm, parse_json
from market_data import load_prices
from prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from scenarios import SCENARIOS
from validation import validate_report

TEST_PORTFOLIOS = {
    "equilibrada": {"rv_desarrollada": 40, "rv_emergente": 10, "bonos_core": 25,
                    "high_yield": 5, "oro": 10, "bitcoin": 5, "liquidez": 5},
    "cripto_agresiva": {"rv_desarrollada": 30, "bitcoin": 30, "stablecoins": 30, "liquidez": 10},
    "defensiva": {"bonos_core": 50, "oro": 20, "liquidez": 20, "rv_desarrollada": 10},
}
PAUSA_SEGUNDOS = 5  # margen para el límite de peticiones del nivel gratuito


def run_one(portfolio: dict, s_key: str, prices, api_key: str, model: str) -> dict:
    impacts = compute_impacts(portfolio, s_key)
    corr = compute_correlations(prices, portfolio, s_key)
    user_prompt = build_user_prompt(portfolio, s_key, impacts, corr)
    raw, issues, intentos = "", [], 0
    for intentos in (1, 2):  # mismo criterio que la app: un reintento si el JSON no es válido
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, api_key, model)
        except Exception as e:  # noqa: BLE001
            return {"intentos": intentos, "issues": [{"tipo": "error_api", "detalle": str(e)[:300]}], "raw": ""}
        try:
            issues = validate_report(parse_json(raw), portfolio, s_key, impacts, corr)
            break
        except Exception as e:  # noqa: BLE001
            issues = [{"tipo": "json_invalido", "detalle": f"{e} (intento {intentos} de 2)"}]
            time.sleep(PAUSA_SEGUNDOS)
    return {"intentos": intentos, "issues": issues, "raw": raw}


def main() -> None:
    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = Path("resultados")
    out_dir.mkdir(exist_ok=True)

    prices, fuente = load_prices()
    print(f"Prompt {PROMPT_VERSION}, modelo {model}. Datos de mercado: {fuente}")
    rows = []
    for p_name, portfolio in TEST_PORTFOLIOS.items():
        for s_key in SCENARIOS:
            res = run_one(portfolio, s_key, prices, api_key, model)
            tipos = Counter(i["tipo"] for i in res["issues"])
            print(f"{p_name:16} {s_key:16} intentos: {res['intentos']}  incidencias: {len(res['issues'])} {dict(tipos)}")
            rows.append({
                "prompt_version": PROMPT_VERSION, "modelo": model,
                "cartera": p_name, "escenario": s_key, "intentos": res["intentos"],
                "n_incidencias": len(res["issues"]),
                "tipos": json.dumps(dict(tipos), ensure_ascii=False),
                "incidencias": json.dumps(res["issues"], ensure_ascii=False),
                "respuesta_bruta": res["raw"],
            })
            time.sleep(PAUSA_SEGUNDOS)

    csv_path = out_dir / f"evaluacion_{PROMPT_VERSION}_{stamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    total = Counter()
    for r in rows:
        total.update(json.loads(r["tipos"]))
    limpios = sum(1 for r in rows if r["n_incidencias"] == 0)
    md = [
        f"# Evaluación del prompt {PROMPT_VERSION}",
        "",
        f"Modelo {model}, {dt.datetime.now():%d/%m/%Y %H:%M}. Datos: {fuente}.",
        "",
        f"Informes sin incidencias: {limpios} de {len(rows)}. "
        f"Informes que necesitaron reintento: {sum(1 for r in rows if r['intentos'] > 1)}.",
        "",
        "| Cartera | Escenario | Intentos | Incidencias | Tipos |",
        "|---|---|---|---|---|",
        *[f"| {r['cartera']} | {SCENARIOS[r['escenario']]['nombre']} | {r['intentos']} | {r['n_incidencias']} | "
          f"{', '.join(f'{k} ({v})' for k, v in json.loads(r['tipos']).items()) or '-'} |" for r in rows],
        "",
        "## Total por tipo de incidencia",
        "",
        *([f"- {k}: {v}" for k, v in total.most_common()] or ["- Ninguna"]),
        "",
    ]
    md_path = out_dir / f"resumen_{PROMPT_VERSION}_{stamp}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\nInformes sin incidencias: {limpios} de {len(rows)}. Resultados en {csv_path} y {md_path}")


if __name__ == "__main__":
    main()
