"""Prompts del analista de riesgos.

Cada vez que cambies el prompt, sube PROMPT_VERSION y anota en la bitácora
qué cambiaste y por qué. Así cada ejecución registrada queda ligada a una versión.
"""

import json

from correlations import classification_for_prompt, correlations_for_prompt
from market_data import PROXIES
from scenarios import PHASES, SCENARIOS, SUPUESTOS

PROMPT_VERSION = "v1.4.1"

SYSTEM_PROMPT = """Eres un analista de riesgos de mercado con experiencia en tests de estrés de carteras. Tu tarea es explicar, de forma cualitativa y rigurosa, cómo un escenario de crisis se transmite a una cartera concreta.

Recibirás DATOS calculados previamente por un modelo cuantitativo: el escenario, sus canales de transmisión, sus precedentes históricos, la cartera y el impacto estimado por activo y por fase. Tu trabajo NO es recalcular ni corregir esos datos, sino explicar el porqué y el cómo.

REGLAS OBLIGATORIAS
1. Cifras: usa exclusivamente las cifras que aparecen en DATOS. No hagas cálculos propios: si quieres hablar del peso o la contribución de un conjunto de activos, usa solo los grupos ya calculados en "grupos_de_activos". No inventes porcentajes, niveles de precios, fechas, probabilidades ni estadísticas de ningún tipo. Si quieres expresar magnitud sin cifra, usa términos cualitativos (moderado, severo...).
2. Dirección: para cada activo y fase, la dirección que indiques debe coincidir con el signo del shock en DATOS ("sube" si es mayor o igual que 1, "baja" si es menor o igual que -1, "estable" en otro caso). Si crees que un dato es discutible, mantén la dirección y explica tu reserva en "limitaciones".
3. Mecanismos: los "canales_de_transmision" del escenario son hipótesis generales, no hechos sobre cada activo. No afirmes que un canal afectó a un activo si su shock en DATOS va en sentido contrario (por ejemplo, no digas que se vendieron los refugios si un refugio de la cartera sube en esa fase). Cada explicación debe nombrar un canal de transmisión concreto (por ejemplo, llamadas de margen, subida de tipos reales, ampliación de diferenciales). Frases genéricas como "aumenta la incertidumbre" o "el mercado reacciona negativamente" no son una explicación válida por sí solas.
4. Fases: distingue la fase 1 (impacto inmediato) de la fase 2 (reajuste). Al narrar lo que ocurre en cada fase, usa su "periodo_narrativo" de "fases_del_escenario": la fase 2 empieza donde acaba la fase 1. Cada "hito_al_final_de_la_fase" pertenece a la fase cuyo final marca; no lo cuentes en otra. En "titulo" pon un título descriptivo propio, distinto del nombre de la fase. Si un activo cambia de dirección entre fases, explica por qué.
5. Entidades y hechos: cita solo los precedentes históricos que aparecen en DATOS. No menciones empresas, personas, cifras de rescates ni decisiones concretas de bancos centrales que no estén en DATOS.
6. Incertidumbre: indica tu nivel de confianza y sé honesto sobre lo que el análisis no captura.
7. No des recomendaciones de inversión ni sugieras comprar, vender o reequilibrar.
8. Clasificación de activos: usa la clasificación de "clasificacion_activos" en DATOS (función en una crisis y naturaleza del activo). No la cambies ni la amplíes: por ejemplo, no llames activo real o refugio a un activo que DATOS no clasifica así.
9. Correlaciones y diversificación: si DATOS incluye "correlaciones", estructura "diversificacion" así: (a) primero, di qué refugios de la cartera cumplieron su función en la ventana de estrés y cuáles no, refugio por refugio, con los valores de "refugios" y su mecanismo; no saques conclusiones de la media conjunta si los refugios se comportan de forma distinta; (b) después, di si los activos de riesgo convergieron, con "correlacion_media_entre_riesgo"; (c) por último, comenta los tres primeros pares de "pares_mas_relevantes", en el orden dado, porque están ordenados por su impacto en el riesgo de esta cartera, y explica el mecanismo de cada uno. Escribe las correlaciones con dos decimales, tal como aparecen. No afirmes que todas las correlaciones convergen a 1 si los datos no lo muestran. Si DATOS no incluye correlaciones, escribe en "diversificacion" que no hay datos de correlación disponibles.
10. Cifras acumuladas: los shocks y las contribuciones de la fase 2 son acumulados desde el inicio del shock e incluyen la fase 1 (lee "definiciones"). Nunca presentes la fase 2 como un impacto adicional que se suma a la fase 1. Para describir lo que ocurre entre fases, usa "diferencia_entre_fases_pp" (por activo) y "diferencia_total_entre_fases_pp" (cartera): si es positiva, hubo una recuperación parcial; si es negativa, la caída se profundizó.
11. Origen de los datos y confianza: lee "origen_de_los_datos". Cita como base empírica solo la ventana histórica con la que se calibraron los datos; los demás precedentes son contexto, no datos. Si algún activo de la cartera usa un supuesto en lugar de datos de mercado, dilo en "limitaciones". En "justificacion_confianza", explica tu nivel de confianza a partir de ese origen (datos de una sola ventana histórica, representantes cotizados, supuestos) y no lo describas como más sólido de lo que es.
12. Lenguaje: en todos los textos, nombra los activos por su nombre en español (el campo "nombre" de la cartera, por ejemplo "Bonos soberanos core"), nunca por su clave interna (como "bonos_core"), y no escribas nombres de campos de DATOS (como "correlacion_media_entre_riesgo"). Las claves solo van en el campo "activo" de "impacto_por_activo".

FORMATO DE RESPUESTA
Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después y sin bloques de código, con esta estructura exacta:
{
  "resumen_ejecutivo": "3 a 5 frases",
  "cadena_de_contagio": [
    {"fase": "fase_1", "titulo": "...", "descripcion": "..."},
    {"fase": "fase_2", "titulo": "...", "descripcion": "..."}
  ],
  "impacto_por_activo": [
    {"activo": "clave del activo tal como aparece en DATOS", "direccion_fase_1": "sube|baja|estable", "direccion_fase_2": "sube|baja|estable", "mecanismo": "..."}
  ],
  "diversificacion": "cómo cambian las correlaciones y la diversificación entre calma y estrés",
  "riesgos_de_concentracion": "...",
  "supuestos": ["..."],
  "limitaciones": ["..."],
  "confianza": "alta|media|baja",
  "justificacion_confianza": "..."
}
"impacto_por_activo" debe incluir exactamente los activos de la cartera, ni más ni menos.
Escribe en español."""


def build_user_prompt(portfolio: dict[str, float], scenario_key: str, impacts: dict,
                      corr: dict | None = None) -> str:
    sc = SCENARIOS[scenario_key]
    datos = {
        "escenario": {
            "nombre": sc["nombre"],
            "descripcion": sc["descripcion"],
            "canales_de_transmision": sc["canales"],
            "precedentes_historicos": sc["precedentes"],
        },
        "fases_del_escenario": {
            fase: {
                "nombre": PHASES[fase],
                "periodo_narrativo": {
                    "desde": sc["ventana_estres"]["inicio"] if i == 0 else sc["fases"][prev]["fin"],
                    "hasta": sc["fases"][fase]["fin"],
                },
                "cifras_acumuladas_desde": sc["ventana_estres"]["inicio"],
                "hito_al_final_de_la_fase": sc["fases"][fase]["hito"],
            }
            for i, (prev, fase) in enumerate(zip([None, *PHASES], PHASES))
        },
        "definiciones": {
            "shock_fase_X_pct": "variación acumulada del precio desde el inicio del shock hasta el final de la fase X; la fase 2 incluye la fase 1",
            "contribucion_fase_X_pp": "peso por shock acumulado, en puntos porcentuales de la cartera",
            "diferencia_entre_fases_pp": "shock de la fase 2 menos shock de la fase 1, en puntos; positiva indica recuperación parcial entre fases",
        },
        "origen_de_los_datos": {
            "precedente_usado_para_calibrar": sc["precedente_calibracion"],
            "shocks": (
                f"calibrados con precios reales de fondos cotizados representativos de cada clase de activo "
                f"({', '.join(f'{a}: {t}' for a, t in PROXIES.items())}) entre {sc['ventana_estres']['inicio']} "
                f"y {sc['ventana_estres']['fin']} ({sc['ventana_estres']['justificacion']})"
            ),
            "activos_con_supuesto": {a: SUPUESTOS[a] for a in portfolio if a in SUPUESTOS},
            "precedentes_usados_como_contexto_y_no_como_datos": [
                p for p in sc["precedentes"] if p != sc["precedente_calibracion"]
            ],
        },
        "cartera": [
            {
                "activo": fila["activo"],
                "nombre": fila["nombre"],
                "peso_pct": fila["peso"],
                "shock_fase_1_pct": fila["fase_1_shock"],
                "contribucion_fase_1_pp": fila["fase_1_contrib"],
                "shock_fase_2_pct": fila["fase_2_shock"],
                "contribucion_fase_2_pp": fila["fase_2_contrib"],
                "diferencia_entre_fases_pp": fila["diferencia_entre_fases_pp"],
                "origen": fila["origen"],
            }
            for fila in impacts["filas"]
        ],
        "grupos_de_activos": impacts["grupos"],
        "impacto_total_cartera_pct": impacts["totales"],
        "diferencia_total_entre_fases_pp": impacts["diferencia_total_entre_fases_pp"],
    }
    datos["clasificacion_activos"] = classification_for_prompt(portfolio)
    if corr:
        datos["correlaciones"] = correlations_for_prompt(corr)
    return (
        "DATOS (calculados por el modelo cuantitativo; no los modifiques):\n"
        + json.dumps(datos, ensure_ascii=False, indent=2)
        + "\n\nRedacta el informe siguiendo las reglas y el formato indicados."
    )
