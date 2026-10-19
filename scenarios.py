"""Escenarios de estrés y tabla de sensibilidades.

IMPORTANTE: las cifras de esta versión son ILUSTRATIVAS (v0). Antes de
entregar, revisa cada una y justifícala con datos del episodio histórico de
referencia (y documenta en la bitácora de dónde sale cada número).

Cada cifra es la variación ACUMULADA (%) del precio de la clase de activo
desde el inicio del shock hasta el final de la fase indicada.
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
    "fase_1": "Fase 1: pánico de liquidez (0 a 2 semanas)",
    "fase_2": "Fase 2: reajuste (1 a 6 meses)",
}

SCENARIOS = {
    "stablecoins": {
        "nombre": "Colapso sistémico de stablecoins",
        "descripcion": (
            "Una de las mayores stablecoins pierde su paridad con el dólar y el "
            "pánico se extiende al resto del ecosistema cripto, con reembolsos "
            "masivos y ventas forzadas de las reservas que las respaldan."
        ),
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
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -6, "rv_emergente": -8, "bonos_core": 0,
                "high_yield": -4, "inmobiliario": -5, "oro": 1, "petroleo": -3,
                "bitcoin": -40, "stablecoins": -20, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -10, "rv_emergente": -14, "bonos_core": 3,
                "high_yield": -7, "inmobiliario": -9, "oro": 5, "petroleo": -6,
                "bitcoin": -55, "stablecoins": -30, "liquidez": 0,
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
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -8, "rv_emergente": -10, "bonos_core": -4,
                "high_yield": -5, "inmobiliario": -7, "oro": 3, "petroleo": 40,
                "bitcoin": -15, "stablecoins": 0, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -15, "rv_emergente": -18, "bonos_core": -10,
                "high_yield": -10, "inmobiliario": -18, "oro": 2, "petroleo": 25,
                "bitcoin": -35, "stablecoins": 0, "liquidez": 0,
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
        "precedentes": [
            "Quiebra de Lehman Brothers (septiembre de 2008)",
            "Crash por la COVID-19 (marzo de 2020)",
        ],
        "canales": [
            "Llamadas de margen que fuerzan la venta incluso de activos refugio",
            "Ampliación de diferenciales de crédito y cierre del mercado de financiación",
            "Caída brusca de la demanda esperada",
            "Intervención posterior de bancos centrales y gobiernos",
        ],
        "shocks": {
            "fase_1": {
                "rv_desarrollada": -30, "rv_emergente": -32, "bonos_core": 3,
                "high_yield": -20, "inmobiliario": -38, "oro": -8, "petroleo": -50,
                "bitcoin": -45, "stablecoins": -1, "liquidez": 0,
            },
            "fase_2": {
                "rv_desarrollada": -15, "rv_emergente": -20, "bonos_core": 6,
                "high_yield": -10, "inmobiliario": -20, "oro": 8, "petroleo": -30,
                "bitcoin": -20, "stablecoins": 0, "liquidez": 0,
            },
        },
    },
}
