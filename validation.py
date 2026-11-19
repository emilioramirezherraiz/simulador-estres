"""Detección automática de posibles alucinaciones.

No sustituye a tu revisión como analista: marca candidatos para que los
revises y, si son errores reales, los documentes en la bitácora.
"""

import re

from confidence import assess_confidence
from scenarios import ASSET_CLASSES, PHASES, SCENARIOS

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


# Campos del formato que no son texto para personas (v1.4.2: evita falsos positivos).
NON_PROSE_KEYS = {"fase", "activo", "direccion_fase_1", "direccion_fase_2", "confianza"}


def _iter_strings(obj, prose_only: bool = False):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if prose_only and key in NON_PROSE_KEYS:
                continue
            yield from _iter_strings(value, prose_only)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_strings(value, prose_only)


def _allowed_numbers(portfolio: dict, scenario_key: str, impacts: dict, corr: dict | None = None) -> set[float]:
    allowed = {100.0, 0.0}
    allowed.update(abs(float(w)) for w in portfolio.values())
    for fase in PHASES:
        allowed.update(abs(float(v)) for v in SCENARIOS[scenario_key]["shocks"][fase].values())
        allowed.add(abs(float(impacts["totales"][fase])))
    for fila in impacts["filas"]:
        for fase in PHASES:
            allowed.add(abs(float(fila[f"{fase}_contrib"])))
        allowed.add(abs(float(fila.get("diferencia_entre_fases_pp", 0))))
    # v1.4: diferencia entre fases de la cartera
    allowed.add(abs(float(impacts.get("diferencia_total_entre_fases_pp", 0))))
    # v1.1: también son legítimas las agregaciones por grupo calculadas en engine.py
    for grupo in impacts.get("grupos", {}).values():
        allowed.update(abs(float(v)) for v in grupo.values())
    # v1.2: volatilidades y peso cubierto del análisis de correlaciones
    if corr:
        allowed.add(abs(float(corr["peso_cubierto_pct"])))
        for periodo in ("calma", "estres"):
            allowed.add(abs(float(corr[periodo]["volatilidad_cartera_pct"])))
            allowed.update(abs(float(v)) for v in corr[periodo]["volatilidades_pct"].values())
        allowed.update(abs(float(c["impacto_en_varianza_pct"])) for c in corr["pares_mas_relevantes"])
    return allowed


def _allowed_correlations(corr: dict | None) -> set[float]:
    if not corr:
        return set()
    values = set()
    for periodo in ("calma", "estres"):
        values.update(abs(float(v)) for v in corr[periodo]["matriz"].to_numpy().ravel())
        for clave in ("correlacion_media", "correlacion_media_entre_riesgo", "correlacion_media_riesgo_refugio"):
            if corr[periodo].get(clave) is not None:
                values.add(abs(float(corr[periodo][clave])))
    values.update(abs(float(c["cambio"])) for c in corr["pares_mas_relevantes"])
    for r in corr.get("refugios", {}).values():  # v1.4
        values.update(abs(float(v)) for k, v in r.items() if not isinstance(v, bool))
    return values


SENTENCE_RE = re.compile(r"[^.;]+(?:\.(?=\d)[^.;]*)*")
GENERIC_WORDS = {"Quiebra", "Crisis", "Colapso", "Crash", "Desanclaje", "Invasión", "Europa"}


def _number_variants(x: float) -> set[str]:
    out = set()
    for d in (2, 1):
        t = f"{abs(x):.{d}f}"
        out.update({t, t.replace(".", ",")})
    return out


def _context_keywords(scenario_key: str) -> set[str]:
    """Palabras distintivas de los precedentes que no se usaron para calibrar."""
    sc = SCENARIOS[scenario_key]
    words = set()
    for p in sc["precedentes"]:
        if p == sc.get("precedente_calibracion"):
            continue
        for w in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ0-9/]+", p):
            if (w[0].isupper() and len(w) >= 4 and w not in GENERIC_WORDS) or w.isupper() or re.fullmatch(r"19\d\d", w):
                words.add(w)
    return words


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

    # 3c. Omisiones relevantes (v1.3): los tres pares con más impacto en el riesgo
    # de la cartera deben aparecer en "diversificacion" (se busca su correlación en estrés).
    if corr:
        texto = str(report.get("diversificacion", ""))
        for par in corr["pares_mas_relevantes"][:3]:
            v = f"{abs(par['estres']):.2f}"
            if v not in texto and v.replace(".", ",") not in texto:
                issues.append({
                    "tipo": "omision_relevante",
                    "detalle": f"'diversificacion' no comenta el par {par['par']}, uno de los tres con más impacto en el riesgo de la cartera ({par['impacto_en_varianza_pct']} % de la varianza).",
                })

    # 3d. Fase 2 leída como adicional (v1.4): las cifras son acumuladas.
    fase2 = _number_variants(impacts["totales"]["fase_2"])
    for text in _iter_strings(report):
        for frase in SENTENCE_RE.findall(text):
            if "adicional" in frase.lower() and any(v in frase for v in fase2):
                issues.append({
                    "tipo": "fase_acumulada_mal_leida",
                    "detalle": f"Presenta la fase 2 como adicional, pero es acumulada: «{frase.strip()[:160]}».",
                })
                break

    # 3e. Precedentes de contexto citados como base de la confianza (v1.4)
    justif = str(report.get("justificacion_confianza", ""))
    citados = sorted(w for w in _context_keywords(scenario_key) if w in justif)
    if citados:
        issues.append({
            "tipo": "base_empirica_inventada",
            "detalle": f"La justificación de la confianza cita {', '.join(citados)}, que no se usó para calibrar los datos.",
        })

    # 3f. Confianza distinta de la asignada por reglas (v1.4.2)
    asignada = assess_confidence(impacts, corr)["nivel"]
    dada = str(report.get("confianza", "")).strip().lower()
    if dada in {"alta", "media", "baja"} and dada != asignada:
        issues.append({"tipo": "confianza_distinta_de_la_asignada",
                       "detalle": f"Declara confianza '{dada}', pero las reglas asignan '{asignada}'."})

    # 3g. Claves internas en el texto (v1.4.1; v1.4.2 ignora campos que no son prosa).
    claves = set(ASSET_CLASSES) | {"correlacion_media", "correlacion_media_entre_riesgo",
                                   "correlacion_media_riesgo_refugio", "diferencia_entre_fases_pp",
                                   "pares_mas_relevantes", "fase_1", "fase_2"}
    encontradas = sorted({w for t in _iter_strings(report, prose_only=True)
                          for w in re.findall(r"[a-zóáéíú_0-9]+_[a-zóáéíú_0-9]+", t)
                          if w.replace("ó", "o").replace("á", "a") in claves})
    if encontradas:
        issues.append({"tipo": "claves_internas_en_texto",
                       "detalle": f"El texto usa claves internas en lugar de nombres legibles: {', '.join(encontradas)}."})

    # 3h. Fase 2 descrita como caída cuando la cartera se recupera (v1.4.2)
    if impacts.get("movimiento_cartera_en_fase_2") == "recupera":
        patrones = re.compile(r"sigu\w* cayendo|contin[uú]\w* cayendo|contin[uú]\w* (?:bajo|sometid\w* a) (?:la )?presi[oó]n"
                              r"|ritmo de (?:las )?ca[ií]das|ca[ií]das? se (?:modera|desacelera|suaviza)\w*|se profundiza\w*", re.I)
        fase2 = [p.get("descripcion", "") for p in report.get("cadena_de_contagio", [])
                 if isinstance(p, dict) and p.get("fase") == "fase_2"]
        for texto in fase2 + [str(report.get("resumen_ejecutivo", ""))]:
            m = patrones.search(texto)
            if m:
                issues.append({"tipo": "movimiento_fase_2_contradictorio",
                               "detalle": f"Dice «{m.group(0)}» en la fase 2, pero la cartera se recupera "
                                          f"({impacts['diferencia_total_entre_fases_pp']:+.2f} pp entre fases)."})
                break

    # 4. Confianza
    if str(report.get("confianza", "")).lower() not in {"alta", "media", "baja"}:
        issues.append({"tipo": "estructura", "detalle": "El campo 'confianza' no es alta, media ni baja."})

    return issues
