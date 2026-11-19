"""Nivel de confianza asignado por reglas (v1.4.2).

Con el mismo prompt, la IA dio confianza "media" en una ejecución y "alta" en la
siguiente. Como el nivel de confianza depende del origen de los datos, que el
código conoce, lo decide el código con reglas transparentes y la IA solo lo
justifica. Revisa y defiende estos umbrales en la bitácora.
"""

PESO_SUPUESTOS_BAJA = 20  # % de la cartera basado en supuestos a partir del cual la confianza es baja
COBERTURA_MINIMA = 50     # % de la cartera con datos de correlación por debajo del cual la confianza es baja


def assess_confidence(impacts: dict, corr: dict | None) -> dict:
    motivos = [
        "Los shocks se calibran con una única ventana histórica, que puede no repetirse en otra crisis.",
        "Cada clase de activo se representa con un fondo cotizado, no con la cartera real del inversor.",
    ]
    nivel = "media"  # nunca "alta": haría falta contrastar con varias ventanas históricas

    peso_supuestos = sum(f["peso"] for f in impacts["filas"] if f.get("origen") == "supuesto")
    if peso_supuestos >= PESO_SUPUESTOS_BAJA:
        nivel = "baja"
        motivos.append(f"El {peso_supuestos:.1f} % de la cartera se basa en supuestos, no en datos de mercado.")
    elif peso_supuestos > 0:
        motivos.append(f"Una parte pequeña de la cartera ({peso_supuestos:.1f} %) se basa en supuestos.")

    if corr is None:
        nivel = "baja"
        motivos.append("No hay datos de correlación para esta cartera.")
    elif corr["peso_cubierto_pct"] < COBERTURA_MINIMA:
        nivel = "baja"
        motivos.append(f"Las correlaciones solo cubren el {corr['peso_cubierto_pct']:.1f} % de la cartera.")

    return {"nivel": nivel, "motivos": motivos, "peso_con_supuestos_pct": round(peso_supuestos, 1)}
