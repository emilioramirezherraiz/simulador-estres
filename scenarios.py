"""Escenarios de estrés y tabla de sensibilidades.

v1.4: los shocks están CALIBRADOS con precios reales (data/precios.csv) en la
ventana histórica de cada escenario. Los calcula calibrate.py; si cambias las
fechas o los datos, ejecuta `python calibrate.py` y copia aquí lo que imprima.
Las clases sin precio de mercado útil (stablecoins y liquidez) son SUPUESTOS,
justificados en SUPUESTOS.

Cada cifra es la variación ACUMULADA (%) del precio desde el inicio del shock
hasta el final de la fase: la fase 2 incluye la fase 1, no se suma a ella.
"""

ASSET_CLASSES = {
    "rv_desarrollada": "Renta variable desarrollada",
    "rv_emergente": "Renta variable emergente",
    "bonos_core": "Bonos soberanos core (EE. UU., Alemania)",
    "high_yield": "Bonos corporativos high yield",
    "inmobiliario": "Inmobiliario cotizado (REITs/SOCIMIs)",
    "oro": "Oro",
    "petroleo": "Petróleo",
    "bitcoin": "Bitcoin",
    "stablecoins": "Stablecoins",
    "liquidez": "Liquidez / monetario",
}

PHASES = {
    "fase_1": "Fase 1: impacto inmediato",
    "fase_2": "Fase 2: reajuste",
}

# Activos cuyos shocks no salen de precios de mercado, con su justificación (v1.4).
SUPUESTOS = {
    "stablecoins": (
        "Supuesto: su precio está anclado a 1 dólar, así que no hay una serie de precios útil. "
        "En el escenario de stablecoins se supone una pérdida para una cesta de stablecoins "
        "en un colapso más amplio que el de Terra/UST (que perdió casi todo su valor mientras "
        "las grandes mantuvieron casi la paridad); en los demás, que mantienen la paridad."
    ),
}
# El efectivo no cambia de precio por definición: no es un supuesto que discutir.
SIN_VARIACION = {"liquidez"}

# Etiquetas cortas para tablas y gráficos.
ASSET_SHORT = {
    "rv_desarrollada": "RV desarr.", "rv_emergente": "RV emerg.",
    "bonos_core": "Bonos core", "high_yield": "High yield",
    "inmobiliario": "Inmobiliario", "oro": "Oro", "petroleo": "Petróleo",
    "bitcoin": "Bitcoin", "stablecoins": "Stablecoins", "liquidez": "Liquidez",
}

# Clasificación de activos (v1.3). Se pasa a la IA como dato para que no la
# improvise. "funcion" indica su papel en una crisis; "naturaleza", qué tipo de activo es.
ASSET_ROLE = {
    "rv_desarrollada": "riesgo", "rv_emergente": "riesgo", "high_yield": "riesgo",
    "inmobiliario": "riesgo", "petroleo": "riesgo", "bitcoin": "riesgo",
    "bonos_core": "refugio", "oro": "refugio",
    "stablecoins": "liquidez", "liquidez": "liquidez",
}
ASSET_NATURE = {
    "rv_desarrollada": "activo financiero", "rv_emergente": "activo financiero",
    "bonos_core": "activo financiero", "high_yield": "activo financiero",
    "inmobiliario": "activo real", "oro": "activo real", "petroleo": "activo real (materia prima)",
    "bitcoin": "criptoactivo (no es un activo real)", "stablecoins": "criptoactivo (no es un activo real)",
    "liquidez": "efectivo",
}

# Periodo de referencia "en calma" con el que se comparan las ventanas de estrés (v1.2).
CALM_WINDOW = {
    "inicio": "2017-01-01", "fin": "2019-12-31",
    "justificacion": "Periodo previo a la COVID-19, con inflación baja y sin crisis sistémica; bitcoin ya cotiza.",
}

# Agregaciones con sentido financiero que el modelo puede usar (v1.1).
# El código calcula sus pesos y se los pasa como datos, así el modelo no tiene
# que sumar por su cuenta y el validador sabe qué cifras agregadas son legítimas.
ASSET_GROUPS = {
    "renta_variable": ["rv_desarrollada", "rv_emergente"],
    "renta_fija": ["bonos_core", "high_yield"],
    "cripto": ["bitcoin", "stablecoins"],
    "materias_primas": ["oro", "petroleo"],
}

SCENARIOS = {
    "stablecoins": {
        "nombre": "Colapso sistémico de stablecoins",
        "descripcion": (
            "Una de las mayores stablecoins pierde su paridad con el dólar y el "
            "pánico se extiende al resto del ecosistema cripto, con reembolsos "
            "masivos y ventas forzadas de las reservas que las respaldan."
        ),
        "precedente_calibracion": "Colapso de Terra/UST (mayo de 2022)",
        "precedentes": [
            "Colapso de Terra/UST (mayo de 2022)",
            "Quiebra de FTX (noviembre de 2022)",
            "Desanclaje temporal de USDC tras la caída de SVB (marzo de 2023)",
        ],
        "canales": [
            "Reembolsos masivos que obligan a vender reservas (letras del Tesoro, depósitos, papel comercial)",
            "Desapalancamiento forzado en exchanges y protocolos DeFi",
            "Pérdida de confianza que se extiende a activos de riesgo con inversores comunes",
        ],
        "ventana_estres": {
            "inicio": "2022-05-01", "fin": "2022-06-30",
            "justificacion": "Colapso de Terra/UST y contagio posterior en el ecosistema cripto.",
        },
        "fases": {
            "fase_1": {"fin": "2022-05-12", "hito": "UST pierde la paridad y Terra colapsa"},
            "fase_2": {"fin": "2022-06-30", "hito": "contagio a prestamistas cripto y mínimo de bitcoin"},
        },
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -5.3, "rv_emergente": -6.9, "bonos_core": 1.2, "high_yield": -1.9,
                "inmobiliario": -7.0, "oro": -2.0, "petroleo": 1.1, "bitcoin": -24.6,
                "stablecoins": -20, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -8.6, "rv_emergente": -4.4, "bonos_core": 0.5, "high_yield": -5.5,
                "inmobiliario": -9.6, "oro": -3.0, "petroleo": 2.5, "bitcoin": -48.7,
                "stablecoins": -30, "liquidez": 0,
            },
        },
    },
    "energia": {
        "nombre": "Shock energético global",
        "descripcion": (
            "Una interrupción grave del suministro dispara el precio del petróleo "
            "y del gas. La inflación repunta y los bancos centrales endurecen la "
            "política monetaria pese al deterioro del crecimiento."
        ),
        "precedente_calibracion": "Invasión de Ucrania y crisis del gas en Europa (2022)",
        "precedentes": [
            "Crisis del petróleo de 1973",
            "Invasión de Ucrania y crisis del gas en Europa (2022)",
        ],
        "canales": [
            "Subida de costes de producción y caída de márgenes empresariales",
            "Repunte de la inflación y subida de tipos de interés",
            "Caída de la renta disponible y del consumo",
            "Deterioro de las balanzas de los países importadores de energía",
        ],
        "ventana_estres": {
            "inicio": "2022-02-24", "fin": "2022-10-31",
            "justificacion": "Invasión de Ucrania, escalada de los precios de la energía y subidas de tipos.",
        },
        "fases": {
            "fase_1": {"fin": "2022-03-08", "hito": "máximo del petróleo tras la invasión"},
            "fase_2": {"fin": "2022-10-31", "hito": "subidas de tipos y caída conjunta de bolsa y bonos hasta octubre de 2022"},
        },
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -2.8, "rv_emergente": -7.3, "bonos_core": 0.9, "high_yield": -1.6,
                "inmobiliario": 1.0, "oro": 8.1, "petroleo": 28.8, "bitcoin": 1.1,
                "stablecoins": 0, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -8.8, "rv_emergente": -25.8, "bonos_core": -13.9, "high_yield": -8.6,
                "inmobiliario": -16.5, "oro": -14.2, "petroleo": 7.8, "bitcoin": -46.5,
                "stablecoins": 0, "liquidez": 0,
            },
        },
    },
    "panico_liquidez": {
        "nombre": "Pánico global de liquidez",
        "descripcion": (
            "Un evento inesperado provoca una huida generalizada hacia el efectivo. "
            "Los inversores venden lo que pueden, no lo que quieren, hasta que los "
            "bancos centrales intervienen."
        ),
        "precedente_calibracion": "Crash por la COVID-19 (marzo de 2020)",
        "precedentes": [
            "Quiebra de Lehman Brothers (septiembre de 2008)",
            "Crash por la COVID-19 (marzo de 2020)",
        ],
        "canales": [
            "Llamadas de margen que obligan a vender lo que tiene liquidez, incluidos algunos activos considerados refugio",
            "Ampliación de diferenciales de crédito y cierre del mercado de financiación",
            "Caída brusca de la demanda esperada",
            "Intervención posterior de bancos centrales y gobiernos",
        ],
        "fases": {
            "fase_1": {"fin": "2020-03-23", "hito": "mínimo de la bolsa y anuncio de compras ilimitadas de la Reserva Federal"},
            "fase_2": {"fin": "2020-04-30", "hito": "estabilización tras la intervención"},
        },
        "ventana_estres": {
            "inicio": "2020-02-19", "fin": "2020-04-30",
            "justificacion": "Crash por la COVID-19: del máximo del S&P 500 a la estabilización tras la intervención de la Reserva Federal.",
        },
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -33.7, "rv_emergente": -30.8, "bonos_core": 6.4, "high_yield": -21.9,
                "inmobiliario": -41.5, "oro": -3.6, "petroleo": -56.4, "bitcoin": -33.4,
                "stablecoins": -1, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -13.6, "rv_emergente": -17.2, "bonos_core": 7.5, "high_yield": -8.0,
                "inmobiliario": -21.8, "oro": 4.6, "petroleo": -78.6, "bitcoin": -10.1,
                "stablecoins": 0, "liquidez": 0,
            },
        },
    },
}
