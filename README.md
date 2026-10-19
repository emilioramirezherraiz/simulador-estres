# Simulador narrativo de estrés para carteras

Herramienta web que aplica un escenario de crisis a una cartera y genera, con un LLM, un informe narrativo sobre la cadena de contagio. Proyecto académico; no es asesoramiento financiero.

## Cómo funciona

La app separa dos capas. La capa cuantitativa (`scenarios.py` y `engine.py`) calcula el impacto con una tabla de sensibilidades definida a mano, sin IA. La capa narrativa (`prompts.py` y `llm.py`) envía esos datos al modelo, que solo tiene que explicarlos. Después, `validation.py` revisa el informe y marca posibles alucinaciones: direcciones que contradicen los datos, cifras inventadas, activos que no están en la cartera o campos que faltan.

| Archivo | Función |
|---|---|
| `app.py` | Interfaz en Streamlit |
| `scenarios.py` | Escenarios, clases de activo y shocks por fase (cifras ilustrativas, revísalas) |
| `engine.py` | Cálculo del impacto en la cartera |
| `prompts.py` | Prompt de sistema y versión del prompt |
| `llm.py` | Llamada a la API de Google Gemini |
| `validation.py` | Detector automático de posibles alucinaciones |
| `evaluate.py` | Evaluación en lote para comparar versiones del prompt |

## Clave de API

La app usa Google Gemini. Crea una clave gratuita en Google AI Studio y ponla en `.streamlit/secrets.toml` (en local) o en los secretos de Streamlit Cloud.

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y pon tu clave
streamlit run app.py
```

## Desplegar en Streamlit Community Cloud

1. Sube el proyecto a un repositorio público de GitHub (comprueba que `secrets.toml` NO se sube).
2. En share.streamlit.io, crea una app nueva apuntando a `app.py`.
3. En la configuración de la app, pega el contenido de tu `secrets.toml` en el apartado de secretos.

## Flujo de trabajo para la bitácora

1. Cada vez que cambies el prompt, sube `PROMPT_VERSION` en `prompts.py`.
2. Ejecuta `python evaluate.py` (antes, en PowerShell: `$env:GEMINI_API_KEY="tu_clave"`) y guarda el CSV de `logs/`.
3. Revisa a mano los informes, además de las incidencias automáticas: el validador no detecta un razonamiento absurdo con la dirección correcta.
4. Anota en la bitácora: qué falló, cómo lo detectaste, qué cambiaste y si el número de incidencias bajó.
