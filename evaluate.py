"""Evaluación en lote: ejecuta todos los escenarios con carteras de prueba.

Uso (desde la carpeta del proyecto):
    $env:GEMINI_API_KEY="tu_clave"   (PowerShell)
    python evaluate.py

Genera logs/evaluacion_<version>_<fecha>.csv. Ejecútalo cada vez que cambies
el prompt y compara el número de incidencias entre versiones en la bitácora.
"""

import csv
import datetime as dt
import json
import os
import time
from pathlib import Path

from engine import compute_impacts
from llm import DEFAULT_MODEL, call_llm, parse_json
from prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from scenarios import SCENARIOS
from validation import validate_report

TEST_PORTFOLIOS = {
    "equilibrada": {"rv_desarrollada": 40, "rv_emergente": 10, "bonos_core": 25,
                    "high_yield": 5, "oro": 10, "bitcoin": 5, "liquidez": 5},
    "cripto_agresiva": {"rv_desarrollada": 30, "bitcoin": 30, "stablecoins": 30, "liquidez": 10},
    "defensiva": {"bonos_core": 50, "oro": 20, "liquidez": 20, "rv_desarrollada": 10},
}


def main() -> None:
    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out = Path("logs") / f"evaluacion_{PROMPT_VERSION}_{stamp}.csv"
    out.parent.mkdir(exist_ok=True)

    rows = []
    for p_name, portfolio in TEST_PORTFOLIOS.items():
        for s_key in SCENARIOS:
            impacts = compute_impacts(portfolio, s_key)
            raw = call_llm(SYSTEM_PROMPT, build_user_prompt(portfolio, s_key, impacts), api_key, model)
            try:
                report = parse_json(raw)
                issues = validate_report(report, portfolio, s_key, impacts)
            except Exception as e:  # noqa: BLE001
                issues = [{"tipo": "json_invalido", "detalle": str(e)}]
            time.sleep(5)  # margen para el límite del nivel gratuito
            print(f"{p_name:16} {s_key:16} incidencias: {len(issues)}")
            rows.append({
                "prompt_version": PROMPT_VERSION, "modelo": model,
                "cartera": p_name, "escenario": s_key,
                "n_incidencias": len(issues),
                "incidencias": json.dumps(issues, ensure_ascii=False),
                "respuesta_bruta": raw,
            })

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    total = sum(r["n_incidencias"] for r in rows)
    print(f"\nTotal de incidencias: {total}. Resultados en {out}")


if __name__ == "__main__":
    main()
