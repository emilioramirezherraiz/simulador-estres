"""Detección automática de posibles alucinaciones.

No sustituye a tu revisión como analista: marca candidatos para que los
revises y, si son errores reales, los documentes en la bitácora.
"""

import re

from scenarios import PHASES, SCENARIOS

REQUIRED_KEYS = [
    "resumen_ejecutivo", "cadena_de_contagio", "impacto_por_activo", "diversificacion",
    "riesgos_de_concentracion", "supuestos", "limitaciones",
    "confianza", "justificacion_confianza",
]
VALID_DIRECTIONS = {"sube", "baja", "estable"}
PERCENT_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s?%")
# Números tipo correlación (0,85 / -0,3) que no son porcentajes.
CORR_RE = re.compile(r"(?<![\d.,])[-−]?(0[.,]\d{1,2})(?![\d%])")


def expected_direction(shock: float) -> str:
    if shock >= 1:
        return "sube"
    if shock <= -1:
        return "baja"
    return "estable"


def _iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_strings(value)


def _allowed_numbers(portfolio: dict, scenario_key: str, impacts: dict, corr: dict | None = None) -> set[float]:
    allowed = {100.0, 0.0}
    allowed.update(abs(float(w)) for w in portfolio.values())
    for fase in PHASES:
        allowed.update(abs(float(v)) for v in SCENARIOS[scenario_key]["shocks"][fase].values())
        allowed.add(abs(float(impacts["totales"][fase])))
    for fila in impacts["filas"]:
        for fase in PHASES:
            allowed.add(abs(float(fila[f"{fase}_contrib"])))
    # v1.1: también son legítimas las agregaciones por grupo calculadas en engine.py
    for grupo in impacts.get("grupos", {}).values():
        allowed.update(abs(float(v)) for v in grupo.values())
    # v1.2: volatilidades y peso cubierto del análisis de correlaciones
    if corr:
        allowed.add(abs(float(corr["peso_cubierto_pct"])))
        for periodo in ("calma", "estres"):
            allowed.add(abs(float(corr[periodo]["volatilidad_cartera_pct"])))
            allowed.update(abs(float(v)) for v in corr[periodo]["volatilidades_pct"].values())
    return allowed


def _allowed_correlations(corr: dict | None) -> set[float]:
    if not corr:
        return set()
    values = set()
    for periodo in ("calma", "estres"):
        values.update(abs(float(v)) for v in corr[periodo]["matriz"].to_numpy().ravel())
        values.add(abs(float(corr[periodo]["correlacion_media"])))
    values.update(abs(float(c["cambio"])) for c in corr["mayores_cambios"])
    return values


def validate_report(report: dict, portfolio: dict, scenario_key: str, impacts: dict,
                    corr: dict | None = None) -> list[dict]:
    issues = []

    # 1. Estructura
    for key in REQUIRED_KEYS:
        if key not in report:
            issues.append({"tipo": "estructura", "detalle": f"Falta el campo '{key}'."})

    # 2. Activos y direcciones
    shocks = SCENARIOS[scenario_key]["shocks"]
    items = {item.get("activo"): item for item in report.get("impacto_por_activo", []) if isinstance(item, dict)}

    for activo in portfolio:
        if activo not in items:
            issues.append({"tipo": "activo_ausente", "detalle": f"El informe no analiza '{activo}'."})
            continue
        for fase in PHASES:
            got = str(items[activo].get(f"direccion_{fase}", "")).strip().lower()
            expected = expected_direction(shocks[fase][activo])
            if got not in VALID_DIRECTIONS:
                issues.append({"tipo": "direccion_invalida", "detalle": f"'{activo}' en {fase}: valor '{got}'."})
            elif got != expected:
                issues.append({
                    "tipo": "direccion_contradictoria",
                    "detalle": f"'{activo}' en {fase}: el informe dice '{got}' y los datos indican '{expected}' ({shocks[fase][activo]} %).",
                })

    for activo in items:
        if activo not in portfolio:
            issues.append({"tipo": "activo_inventado", "detalle": f"El informe incluye '{activo}', que no está en la cartera."})

    # 3. Cifras que no aparecen en los datos
    allowed = _allowed_numbers(portfolio, scenario_key, impacts, corr)
    seen = set()
    for text in _iter_strings(report):
        for match in PERCENT_RE.finditer(text):
            value = abs(float(match.group(1).replace(",", ".")))
            if value in seen:
                continue
            seen.add(value)
            if not any(abs(value - a) <= 0.06 for a in allowed):
                issues.append({
                    "tipo": "cifra_no_respaldada",
                    "detalle": f"Aparece '{match.group(0)}', que no está en los datos.",
                })

    # 3b. Correlaciones que no aparecen en los datos (v1.2)
    if corr:
        allowed_corr = _allowed_correlations(corr)
        seen_corr = set()
        for text in _iter_strings(report):
            for match in CORR_RE.finditer(text):
                raw = match.group(1)
                value = float(raw.replace(",", "."))
                if value in seen_corr:
                    continue
                seen_corr.add(value)
                tol = 0.011 if len(raw) == 4 else 0.051  # dos decimales o uno
                if not any(abs(value - a) <= tol for a in allowed_corr):
                    issues.append({
                        "tipo": "correlacion_no_respaldada",
                        "detalle": f"Aparece la correlación '{match.group(0)}', que no está en los datos.",
                    })

    # 4. Confianza
    if str(report.get("confianza", "")).lower() not in {"alta", "media", "baja"}:
        issues.append({"tipo": "estructura", "detalle": "El campo 'confianza' no es alta, media ni baja."})

    return issues
