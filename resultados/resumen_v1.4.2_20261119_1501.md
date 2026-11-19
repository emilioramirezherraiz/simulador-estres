# Evaluación del prompt v1.4.2

Modelo gemini-3.5-flash-lite, 19/11/2026 15:15. Datos: copia guardada de Yahoo Finance (hasta 12/11/2026).

Informes sin incidencias: 3 de 9. Informes que necesitaron reintento: 0.

| Cartera | Escenario | Intentos | Incidencias | Tipos |
|---|---|---|---|---|
| equilibrada | Colapso sistémico de stablecoins | 1 | 1 | error_api (1) |
| equilibrada | Shock energético global | 1 | 1 | error_api (1) |
| equilibrada | Pánico global de liquidez | 1 | 0 | - |
| cripto_agresiva | Colapso sistémico de stablecoins | 1 | 1 | error_api (1) |
| cripto_agresiva | Shock energético global | 1 | 0 | - |
| cripto_agresiva | Pánico global de liquidez | 1 | 0 | - |
| defensiva | Colapso sistémico de stablecoins | 1 | 1 | direccion_contradictoria (1) |
| defensiva | Shock energético global | 1 | 3 | direccion_contradictoria (1), cifra_no_respaldada (1), correlacion_no_respaldada (1) |
| defensiva | Pánico global de liquidez | 1 | 1 | cifra_no_respaldada (1) |

## Total por tipo de incidencia

- error_api: 3
- direccion_contradictoria: 2
- cifra_no_respaldada: 2
- correlacion_no_respaldada: 1
